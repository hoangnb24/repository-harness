#!/usr/bin/env python3
"""Read-only verifier and collector for V1 non-production build receipts."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Any

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
    reject_command_fields,
    relative_filename,
    sha256_bytes,
    validate_contract,
)


GIT_REVISION = re.compile(r"^[0-9a-f]{40}$")
ARTIFACT_DIRECTORY_PREFIX = "harness-v1-build-receipt-"


def git_bytes(*arguments: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=ROOT,
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as error:
        raise ReceiptError("cannot execute git for candidate identity verification") from error
    check(result.returncode == 0, f"git {' '.join(arguments)} failed")
    return result.stdout


def expected_identity_from_repository(candidate: str, workflow_revision: str) -> tuple[dict[str, Any], dict[str, str], bytes]:
    check(GIT_REVISION.fullmatch(candidate) is not None, "candidate must be exactly 40 lowercase hexadecimal characters")
    check(GIT_REVISION.fullmatch(workflow_revision) is not None, "workflow revision must be exactly 40 lowercase hexadecimal characters")
    head = git_bytes("rev-parse", "HEAD").decode("ascii").strip()
    check(head == candidate, "verification candidate does not equal HEAD")
    tree = git_bytes("rev-parse", "HEAD^{tree}").decode("ascii").strip()
    check(GIT_REVISION.fullmatch(tree) is not None, "candidate tree is not an exact 40-hex object")

    committed: dict[str, bytes] = {}
    for path in (CARGO_LOCK_PATH, COMMAND_BINDING_PATH, COMMAND_GRAMMAR_PATH):
        committed[path] = git_bytes("show", f"{candidate}:{path}")
    grammar = parse_json_bytes(committed[COMMAND_GRAMMAR_PATH], COMMAND_GRAMMAR_PATH)
    check(isinstance(grammar, dict), "committed command grammar is not an object")
    identity = {
        "source_commit": candidate,
        "source_tree": tree,
        "cargo_lock": {"path": CARGO_LOCK_PATH, "sha256": sha256_bytes(committed[CARGO_LOCK_PATH])},
        "command_implementation_binding": {
            "path": COMMAND_BINDING_PATH,
            "sha256": sha256_bytes(committed[COMMAND_BINDING_PATH]),
        },
    }
    workflow_bytes = git_bytes("show", f"{workflow_revision}:{WORKFLOW_PATH}")
    execution_workflow = {
        "path": WORKFLOW_PATH,
        "revision": workflow_revision,
        "sha256": sha256_bytes(workflow_bytes),
    }
    return identity, execution_workflow, exact_core_help_bytes(grammar)


def safe_directory(path: Path, label: str) -> None:
    check(path.is_dir() and not path.is_symlink(), f"{label} is missing or unsafe: {path}")
    metadata = path.lstat()
    check(stat.S_ISDIR(metadata.st_mode), f"{label} is not a directory: {path}")


def exact_members(directory: Path) -> set[str]:
    safe_directory(directory, "receipt directory")
    members: set[str] = set()
    for member in directory.iterdir():
        check(not member.is_symlink(), f"receipt directory contains a symlink: {member.name}")
        check(member.is_file() and stat.S_ISREG(member.lstat().st_mode), f"receipt directory contains a non-file member: {member.name}")
        members.add(member.name)
    return members


def read_member(directory: Path, name: str, field: str) -> bytes:
    relative_filename(name, field)
    path = directory / name
    check(path.is_file() and not path.is_symlink(), f"{field}: missing or unsafe file")
    try:
        return path.read_bytes()
    except OSError as error:
        raise ReceiptError(f"{field}: cannot read file") from error


def fixed_results() -> dict[str, str]:
    return {
        "build": "passed",
        "help_grammar_only": "passed",
        "installer": "pending",
        "full_direct_binary": "pending",
        "provenance": "checksum-only-unattested",
    }


def fixed_authority() -> dict[str, Any]:
    return {
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
    }


def verify_receipt_directory(
    directory: Path,
    expected_candidate: dict[str, Any],
    expected_execution_workflow: dict[str, str],
    expected_help: bytes,
) -> str:
    receipt_path = directory / RECEIPT_NAME
    receipt_payload = read_member(directory, RECEIPT_NAME, "receipt")
    document = parse_json_bytes(receipt_payload, str(receipt_path))
    validate_contract(document)
    reject_command_fields(document)
    check(receipt_payload == canonical_json_bytes(document), "receipt JSON is not canonical")
    check(document["candidate"] == expected_candidate, "candidate/input identity drift")
    check(document["execution_workflow"] == expected_execution_workflow, "execution workflow identity drift")
    check(document["results"] == fixed_results(), "unsupported result claim")
    check(document["authority"] == fixed_authority(), "unsupported acceptance or release authority claim")

    platform_name = document["environment"]["platform"]
    check(platform_name in PLATFORMS, f"unsupported platform: {platform_name}")
    target, runner, artifact_name = PLATFORMS[platform_name]
    check(
        document["environment"] == {"platform": platform_name, "target": target, "runner": runner},
        f"unsupported platform/target/runner tuple: {platform_name}",
    )
    expected_paths = {
        "artifact": artifact_name,
        "checksum": f"{artifact_name}.sha256",
        "help_output": f"{artifact_name}.help.json",
    }
    for field, expected_path in expected_paths.items():
        check(document["files"][field]["path"] == expected_path, f"{field} path drift: {platform_name}")

    expected_files = {RECEIPT_NAME, *expected_paths.values()}
    check(exact_members(directory) == expected_files, f"receipt directory has missing or extra files: {platform_name}")

    payloads: dict[str, bytes] = {}
    for field, name in expected_paths.items():
        payload = read_member(directory, name, field)
        record = document["files"][field]
        check(len(payload) == record["bytes"], f"{field} byte-length drift: {platform_name}")
        check(sha256_bytes(payload) == record["sha256"], f"{field} digest drift: {platform_name}")
        payloads[field] = payload

    artifact_sha = sha256_bytes(payloads["artifact"])
    expected_checksum = f"{artifact_sha}  {artifact_name}\n".encode("ascii")
    check(payloads["checksum"] == expected_checksum, f"checksum content substitution: {platform_name}")
    help_document = parse_json_bytes(payloads["help_output"], f"help output: {platform_name}")
    expected_help_document = parse_json_bytes(expected_help, "committed core grammar")
    check(payloads["help_output"] == expected_help and help_document == expected_help_document, f"help grammar substitution: {platform_name}")
    return platform_name


def discover_directories(root: Path, require_five: bool) -> list[Path]:
    safe_directory(root, "receipt collection root")
    if not require_five:
        check((root / RECEIPT_NAME).is_file(), "single receipt root must directly contain build-receipt.json")
        return [root]

    expected_names = {f"{ARTIFACT_DIRECTORY_PREFIX}{platform}" for platform in PLATFORMS}
    actual_names: set[str] = set()
    directories: list[Path] = []
    for member in root.iterdir():
        check(not member.is_symlink(), f"receipt collection contains a symlink: {member.name}")
        check(member.is_dir(), f"receipt collection contains an extra file: {member.name}")
        actual_names.add(member.name)
        directories.append(member)
    check(actual_names == expected_names, "receipt collection has missing, duplicate-named, or extra platform directories")
    return sorted(directories, key=lambda item: list(PLATFORMS).index(item.name.removeprefix(ARTIFACT_DIRECTORY_PREFIX)))


def verify_collection(
    root: Path,
    candidate: str,
    workflow_revision: str,
    require_five: bool,
    *,
    expected: tuple[dict[str, Any], dict[str, str], bytes] | None = None,
) -> list[str]:
    expected_candidate, expected_execution_workflow, expected_help = expected or expected_identity_from_repository(candidate, workflow_revision)
    directories = discover_directories(root, require_five)
    platforms = [verify_receipt_directory(directory, expected_candidate, expected_execution_workflow, expected_help) for directory in directories]
    check(len(platforms) == len(set(platforms)), "duplicate platform receipts")
    if require_five:
        check(platforms == list(PLATFORMS), f"receipt matrix must contain the exact five-platform order: {list(PLATFORMS)}")
    else:
        check(len(platforms) == 1, "single verification requires exactly one receipt")
    return platforms


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--workflow-revision", required=True)
    parser.add_argument("--require-five", action="store_true")
    parser.add_argument("receipt_root", type=Path)
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    try:
        platforms = verify_collection(
            arguments.receipt_root,
            arguments.candidate,
            arguments.workflow_revision,
            arguments.require_five,
        )
    except ReceiptError as error:
        print(f"V1 build receipt verification failed: {error}", file=sys.stderr)
        return 1
    print(
        "V1 non-production build receipt verification passed for "
        + ", ".join(platforms)
        + "; no platform is accepted and installer, full direct-binary, authenticated provenance, and release remain blocked"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
