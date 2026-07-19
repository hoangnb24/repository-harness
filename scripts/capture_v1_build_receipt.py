#!/usr/bin/env python3
"""Capture one honest, non-production native V1 build receipt."""

from __future__ import annotations

import argparse
from copy import deepcopy
import os
from pathlib import Path
import platform as host_platform
import re
import shutil
import stat
import subprocess
import sys

from v1_build_receipt_common import (
    BLOCKERS,
    CARGO_LOCK_PATH,
    COMMAND_BINDING_PATH,
    COMMAND_GRAMMAR_PATH,
    PLATFORMS,
    RECEIPT_NAME,
    ROOT,
    WORKFLOW_PATH,
    ReceiptError,
    canonical_json_bytes,
    check,
    exact_core_help_bytes,
    load_json,
    parse_json_bytes,
    sha256_bytes,
    validate_contract,
)


GIT_REVISION = re.compile(r"^[0-9a-f]{40}$")


def run_fixed(arguments: list[str], *, capture: bool = True) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            arguments,
            cwd=ROOT,
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
        )
    except OSError as error:
        raise ReceiptError(f"cannot execute required local tool: {arguments[0]}") from error


def fixed_output(arguments: list[str], label: str) -> bytes:
    result = run_fixed(arguments)
    check(result.returncode == 0, f"{label} failed")
    return result.stdout


def git_text(*arguments: str) -> str:
    payload = fixed_output(["git", *arguments], f"git {' '.join(arguments)}")
    try:
        return payload.decode("ascii").strip()
    except UnicodeError as error:
        raise ReceiptError("git returned a non-ASCII identity") from error


def committed_candidate_identity(candidate: str, tree: str) -> dict[str, object]:
    inputs: dict[str, bytes] = {}
    for path in (CARGO_LOCK_PATH, COMMAND_BINDING_PATH):
        worktree_path = ROOT / path
        check(
            worktree_path.is_file() and not worktree_path.is_symlink(),
            f"candidate input is missing or unsafe: {path}",
        )
        inputs[path] = fixed_output(
            ["git", "show", f"{candidate}:{path}"],
            f"committed candidate input {path}",
        )
    return {
        "source_commit": candidate,
        "source_tree": tree,
        "cargo_lock": {"path": CARGO_LOCK_PATH, "sha256": sha256_bytes(inputs[CARGO_LOCK_PATH])},
        "command_implementation_binding": {
            "path": COMMAND_BINDING_PATH,
            "sha256": sha256_bytes(inputs[COMMAND_BINDING_PATH]),
        },
    }


def committed_execution_workflow_identity(workflow_revision: str) -> dict[str, str]:
    check(
        GIT_REVISION.fullmatch(workflow_revision) is not None,
        "workflow revision must be exactly 40 lowercase hexadecimal characters",
    )
    workflow_bytes = fixed_output(
        ["git", "show", f"{workflow_revision}:{WORKFLOW_PATH}"],
        f"committed execution workflow {WORKFLOW_PATH}",
    )
    return {
        "path": WORKFLOW_PATH,
        "revision": workflow_revision,
        "sha256": sha256_bytes(workflow_bytes),
    }


def validate_candidate(candidate: str) -> tuple[str, str]:
    check(GIT_REVISION.fullmatch(candidate) is not None, "candidate must be exactly 40 lowercase hexadecimal characters")
    head = git_text("rev-parse", "HEAD")
    check(candidate == head, "candidate does not equal HEAD")
    status_output = fixed_output(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        "git worktree status",
    )
    check(status_output == b"", "tracked or untracked worktree changes are present")
    tree = git_text("rev-parse", "HEAD^{tree}")
    check(GIT_REVISION.fullmatch(tree) is not None, "HEAD tree is not an exact 40-hex object")
    return head, tree


def rust_host() -> str:
    payload = fixed_output(["rustc", "-vV"], "rustc host discovery")
    try:
        lines = payload.decode("utf-8").splitlines()
    except UnicodeError as error:
        raise ReceiptError("rustc host output is not UTF-8") from error
    hosts = [line.removeprefix("host: ") for line in lines if line.startswith("host: ")]
    check(len(hosts) == 1, "rustc did not report exactly one host target")
    return hosts[0]


def native_platform(system: str, machine: str) -> str:
    normalized_machine = machine.casefold()
    mapping = {
        ("darwin", "arm64"): "macos-arm64",
        ("darwin", "aarch64"): "macos-arm64",
        ("darwin", "x86_64"): "macos-x64",
        ("linux", "x86_64"): "linux-x64",
        ("linux", "amd64"): "linux-x64",
        ("linux", "aarch64"): "linux-arm64",
        ("linux", "arm64"): "linux-arm64",
        ("windows", "amd64"): "windows-x64",
        ("windows", "x86_64"): "windows-x64",
    }
    detected = mapping.get((system.casefold(), normalized_machine))
    check(detected is not None, f"unsupported native host: {system}/{machine}")
    return detected


def validate_tuple(
    platform_name: str,
    target: str,
    runner: str,
    *,
    system: str,
    machine: str,
    rust_target: str,
) -> tuple[str, str, str]:
    check(platform_name in PLATFORMS, f"unsupported platform: {platform_name}")
    expected_target, expected_runner, artifact_name = PLATFORMS[platform_name]
    check((target, runner) == (expected_target, expected_runner), f"unsupported platform/target/runner tuple: {platform_name}/{target}/{runner}")
    check(native_platform(system, machine) == platform_name, "requested platform does not match the native operating system and architecture")
    check(rust_target == target, "cross-target capture is prohibited; rustc host must equal the requested target")
    return expected_target, expected_runner, artifact_name


def validate_new_output_path(raw: str, repository_root: Path = ROOT) -> Path:
    output = Path(raw)
    check(output.is_absolute(), "output directory must be an absolute path")
    check(".." not in output.parts, "output directory traversal is prohibited")
    check(not os.path.lexists(output), "output directory must not already exist")
    parent = output.parent
    check(parent.is_dir(), "output parent directory does not exist")
    for component in (parent, *parent.parents):
        check(not component.is_symlink(), f"output parent path contains a symlink: {component}")
    resolved_parent = parent.resolve(strict=True)
    resolved_repository = repository_root.resolve(strict=True)
    candidate = resolved_parent / output.name
    try:
        candidate.relative_to(resolved_repository)
    except ValueError:
        pass
    else:
        raise ReceiptError("output directory must be outside the repository")
    check(candidate != resolved_repository, "output directory must be outside the repository")
    return candidate


def write_new_file(path: Path, payload: bytes, mode: int) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, mode)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as error:
        raise ReceiptError(f"cannot create receipt member safely: {path.name}") from error
    metadata = path.lstat()
    check(stat.S_ISREG(metadata.st_mode) and not path.is_symlink(), f"receipt member is not a regular file: {path.name}")


def regular_built_artifact(target: str, artifact_name: str) -> Path:
    executable = "harness.exe" if artifact_name.endswith(".exe") else "harness"
    path = ROOT / "target" / target / "release" / executable
    check(path.is_file() and not path.is_symlink(), "native release artifact is missing or unsafe")
    try:
        path.resolve(strict=True).relative_to((ROOT / "target").resolve(strict=True))
    except ValueError as error:
        raise ReceiptError("native release artifact escaped the Cargo target directory") from error
    return path


def build_receipt_document(
    *,
    candidate_identity: dict[str, object],
    execution_workflow_identity: dict[str, str],
    platform_name: str,
    target: str,
    runner: str,
    artifact_name: str,
    artifact_bytes: bytes,
    checksum_bytes: bytes,
    help_name: str,
    help_bytes: bytes,
) -> dict[str, object]:
    artifact_sha = sha256_bytes(artifact_bytes)
    document: dict[str, object] = {
        "schema": "repository-harness-v1-build-receipt/v1",
        "evidence_kind": "native-build-receipt-non-production",
        "candidate": deepcopy(candidate_identity),
        "execution_workflow": deepcopy(execution_workflow_identity),
        "environment": {"platform": platform_name, "target": target, "runner": runner},
        "files": {
            "artifact": {"path": artifact_name, "bytes": len(artifact_bytes), "sha256": artifact_sha},
            "checksum": {"path": f"{artifact_name}.sha256", "bytes": len(checksum_bytes), "sha256": sha256_bytes(checksum_bytes)},
            "help_output": {"path": help_name, "bytes": len(help_bytes), "sha256": sha256_bytes(help_bytes)},
        },
        "results": {
            "build": "passed",
            "help_grammar_only": "passed",
            "installer": "pending",
            "full_direct_binary": "pending",
            "provenance": "checksum-only-unattested",
        },
        "authority": {
            "phase6_live_evidence": "pending",
            "platform_acceptance": "blocked",
            "phase7_acceptance": "blocked",
            "platform_accepted": False,
            "phase7_accepted": False,
            "production": False,
            "promotable": False,
            "tag_authorized": False,
            "release_authorized": False,
            "publish_authorized": False,
            "promotion_authorized": False,
            "signing_authorized": False,
            "attestation_authorized": False,
            "phase8": "closed",
            "blockers": BLOCKERS,
        },
    }
    return validate_contract(document)


def capture(arguments: argparse.Namespace) -> Path:
    candidate, tree = validate_candidate(arguments.candidate)
    target, runner, artifact_name = validate_tuple(
        arguments.platform,
        arguments.target,
        arguments.runner,
        system=host_platform.system(),
        machine=host_platform.machine(),
        rust_target=rust_host(),
    )
    output = validate_new_output_path(arguments.output)

    result = run_fixed(
        [
            "cargo",
            "build",
            "--release",
            "--locked",
            "-p",
            "harness-core",
            "--bin",
            "harness",
            "--target",
            target,
        ],
        capture=False,
    )
    check(result.returncode == 0, "native release build failed")
    built = regular_built_artifact(target, artifact_name)
    artifact_bytes = built.read_bytes()
    check(artifact_bytes, "native release artifact is empty")

    help_result = run_fixed([str(built), "--help"])
    check(help_result.returncode == 0, "native V1 harness --help failed")
    check(help_result.stderr == b"", "native V1 harness --help wrote stderr")
    help_document = parse_json_bytes(help_result.stdout, "native V1 harness --help")
    grammar = load_json(ROOT / COMMAND_GRAMMAR_PATH)
    expected_help = exact_core_help_bytes(grammar)
    check(help_result.stdout == expected_help and help_document == grammar["core"], "native V1 harness --help is not the exact six-command JSON grammar")

    artifact_sha = sha256_bytes(artifact_bytes)
    checksum_bytes = f"{artifact_sha}  {artifact_name}\n".encode("ascii")
    help_name = f"{artifact_name}.help.json"
    document = build_receipt_document(
        candidate_identity=committed_candidate_identity(candidate, tree),
        execution_workflow_identity=committed_execution_workflow_identity(arguments.workflow_revision),
        platform_name=arguments.platform,
        target=target,
        runner=runner,
        artifact_name=artifact_name,
        artifact_bytes=artifact_bytes,
        checksum_bytes=checksum_bytes,
        help_name=help_name,
        help_bytes=help_result.stdout,
    )

    created = False
    try:
        os.mkdir(output, 0o755)
        created = True
        write_new_file(output / artifact_name, artifact_bytes, 0o755)
        write_new_file(output / f"{artifact_name}.sha256", checksum_bytes, 0o644)
        write_new_file(output / help_name, help_result.stdout, 0o644)
        write_new_file(output / RECEIPT_NAME, canonical_json_bytes(document), 0o644)
    except Exception:
        if created and output.is_dir() and not output.is_symlink():
            shutil.rmtree(output)
        raise
    return output


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    parser.add_argument(
        "--workflow-revision",
        required=True,
        help="immutable commit whose committed workflow bytes executed this capture (use HEAD explicitly for local diagnostics)",
    )
    parser.add_argument("--platform", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--runner", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> int:
    try:
        output = capture(parse_arguments())
    except ReceiptError as error:
        print(f"V1 build receipt capture failed: {error}", file=sys.stderr)
        return 1
    print(f"V1 non-production build receipt captured: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
