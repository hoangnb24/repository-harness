#!/usr/bin/env python3
"""Run the locally honest Phase 7 installer/direct-binary fixture matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform as host_platform
import re
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parent.parent
CASES = [
    "fresh", "brownfield", "nested-instructions", "docs-only", "monorepo",
    "spaces-unicode", "lf", "crlf", "custom-update", "bridge",
]
COMMANDS = ["install", "update", "audit", "scaffold", "status", "version"]
PLATFORMS = {
    "macos-arm64": ("aarch64-apple-darwin", "macos-15", "harness-macos-arm64"),
    "macos-x64": ("x86_64-apple-darwin", "macos-15-intel", "harness-macos-x64"),
    "linux-x64": ("x86_64-unknown-linux-gnu", "ubuntu-24.04", "harness-linux-x64"),
    "linux-arm64": ("aarch64-unknown-linux-gnu", "ubuntu-24.04-arm", "harness-linux-arm64"),
    "windows-x64": ("x86_64-pc-windows-msvc", "windows-latest", "harness-windows-x64.exe"),
}
SHA256 = re.compile(r"^[0-9a-f]{64}$")
BLOCKERS = [
    "deferred-phase6-live-p0-p7-evidence-pending",
    "remote-five-platform-execution-pending",
    "safe-windows-repository-mutation-pending",
    "artifact-provenance-attestation-pending",
    "platform-acceptance-pending",
]


class ProofError(Exception):
    pass


def check(condition: bool, message: str) -> None:
    if not condition:
        raise ProofError(message)


def canonical(document: object) -> bytes:
    return (json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def digest_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def git_bytes(*arguments: str) -> bytes:
    result = subprocess.run(
        ["git", *arguments], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    check(result.returncode == 0, f"git {' '.join(arguments)} failed")
    return result.stdout


def immutable_identity(candidate: str, workflow_revision: str) -> tuple[dict[str, str], dict[str, str]]:
    check(re.fullmatch(r"[0-9a-f]{40}", candidate) is not None, "candidate must be exact 40-hex")
    check(re.fullmatch(r"[0-9a-f]{40}", workflow_revision) is not None, "workflow revision must be exact 40-hex")
    check(candidate == workflow_revision, "candidate and workflow revision must be identical")
    head = git_bytes("rev-parse", "HEAD").decode("ascii").strip()
    check(candidate == head, "candidate does not equal HEAD")
    check(git_bytes("status", "--porcelain=v1", "--untracked-files=all") == b"", "worktree is not clean")
    tree = git_bytes("rev-parse", "HEAD^{tree}").decode("ascii").strip()
    cargo_lock = git_bytes("show", f"{candidate}:Cargo.lock")
    command_binding = git_bytes("show", f"{candidate}:release/contracts/v1/command-implementation-binding.json")
    workflow_path = ".github/workflows/harness-v1-release.yml"
    workflow = git_bytes("show", f"{workflow_revision}:{workflow_path}")
    return (
        {
            "source_commit": candidate,
            "source_tree": tree,
            "cargo_lock_sha256": digest_bytes(cargo_lock),
            "command_binding_sha256": digest_bytes(command_binding),
        },
        {"path": workflow_path, "revision": workflow_revision, "sha256": digest_bytes(workflow)},
    )


def native_platform() -> str:
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
    value = mapping.get((host_platform.system().casefold(), host_platform.machine().casefold()))
    check(value is not None, "unsupported native platform")
    return value


def exact_checksum(artifact: Path, checksum: Path) -> str:
    check(artifact.is_file() and not artifact.is_symlink(), "artifact is missing or unsafe")
    check(checksum.is_file() and not checksum.is_symlink(), "checksum is missing or unsafe")
    match = re.fullmatch(r"([0-9a-f]{64})  ([^/\\\r\n]+)\n", checksum.read_text(encoding="ascii"))
    check(match is not None, "checksum record is not exact")
    expected, name = match.groups()
    check(name == artifact.name, "checksum filename does not bind artifact")
    check(digest_bytes(artifact.read_bytes()) == expected, "artifact checksum mismatch")
    return expected


def invoke(arguments: list[str], cwd: Path, environment: dict[str, str]) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            arguments,
            cwd=cwd,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as error:
        raise ProofError(f"could not execute {arguments[0]}") from error


def install_unix(artifact: Path, checksum: Path, platform_name: str, repository: Path) -> tuple[Path, str]:
    check(platform_name != "windows-x64", "Windows publication is controlled unsupported")
    result = invoke(
        ["/bin/bash", str(ROOT / "scripts/install-harness-v1.sh"),
         "--artifact", str(artifact), "--checksum", str(checksum),
         "--platform", platform_name, "--directory", str(repository)],
        repository,
        os.environ.copy(),
    )
    installed = repository / "scripts/bin/harness"
    installer = "bash"
    check(result.returncode == 0, f"{installer} installer failed: {result.stderr.decode(errors='replace')}")
    check(installed.is_file() and not installed.is_symlink(), "installed artifact is missing or unsafe")
    return installed, installer


def namespace_snapshot(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            result[relative] = f"link:{os.readlink(path)}"
        elif path.is_dir():
            result[relative] = "directory"
        elif path.is_file():
            result[relative] = f"file:{digest_bytes(path.read_bytes())}"
        else:
            result[relative] = "other"
    return result


def windows_direct_after_installer_refusal(
    artifact: Path,
    checksum: Path,
    platform_name: str,
    repository: Path,
) -> tuple[Path, str]:
    shell = shutil.which("pwsh") or shutil.which("powershell")
    check(shell is not None, "PowerShell is unavailable")
    before = namespace_snapshot(repository)
    result = invoke(
        [shell, "-NoProfile", "-File", str(ROOT / "scripts/install-harness-v1.ps1"),
         "-Artifact", str(artifact), "-Checksum", str(checksum),
         "-Platform", platform_name, "-Directory", str(repository)],
        repository,
        os.environ.copy(),
    )
    message = "Harness V1 installer refused: safe Windows destination publication is controlled-unsupported before mutation"
    check(result.returncode == 1, f"PowerShell installer did not return controlled unsupported: {result.stderr.decode(errors='replace')}")
    check(result.stdout == b"", "PowerShell installer wrote success output while controlled unsupported")
    check(result.stderr.decode(errors="replace").splitlines() == [message], f"PowerShell installer refusal changed: {result.stderr.decode(errors='replace')}")
    check(namespace_snapshot(repository) == before, "PowerShell installer mutated the destination before refusal")
    check(exact_checksum(artifact, checksum) == digest_bytes(artifact.read_bytes()), "Windows direct artifact changed after installer refusal")
    return artifact, "powershell-controlled-unsupported-before-mutation"


def parse_human(payload: bytes) -> dict[str, object]:
    fields: dict[str, object] = {}
    notices: list[str] = []
    for line in payload.decode("utf-8").splitlines():
        if line.startswith("notice "):
            notices.append(line.split(":", 1)[0].removeprefix("notice ").split(" [", 1)[0])
            continue
        if ": " in line:
            key, value = line.split(": ", 1)
            fields[key] = int(value) if key in {"exit-code", "release-sequence"} else value
    fields["notice-codes"] = notices
    return fields


def run_json(binary: Path, arguments: list[str], cwd: Path, environment: dict[str, str], expected: int) -> dict[str, object]:
    result = invoke([str(binary), *arguments], cwd, environment)
    check(result.returncode == expected, f"{' '.join(arguments)} exited {result.returncode}: stdout={result.stdout.decode(errors='replace')} stderr={result.stderr.decode(errors='replace')}")
    check(result.stderr == b"", f"{' '.join(arguments)} wrote stderr")
    try:
        document = json.loads(result.stdout)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ProofError(f"{' '.join(arguments)} did not return JSON") from error
    return document


def run_human(binary: Path, arguments: list[str], cwd: Path, environment: dict[str, str], expected: int) -> dict[str, object]:
    result = invoke([str(binary), *arguments], cwd, environment)
    check(result.returncode == expected, f"{' '.join(arguments)} exited {result.returncode}: stdout={result.stdout.decode(errors='replace')} stderr={result.stderr.decode(errors='replace')}")
    check(result.stderr == b"", f"{' '.join(arguments)} wrote stderr")
    return parse_human(result.stdout)


def preview_and_commit(binary: Path, command: list[str], cwd: Path, environment: dict[str, str]) -> dict[str, object]:
    preview = run_human(binary, [*command, "--preview"], cwd, environment, 0)
    digest = None
    result = invoke([str(binary), *command, "--preview"], cwd, environment)
    for line in result.stdout.decode("utf-8").splitlines():
        match = re.fullmatch(r"notice preview-sha256: ([0-9a-f]{64})", line)
        if match:
            digest = match.group(1)
    check(digest is not None, f"{command[0]} preview omitted its confirmation digest")
    committed = run_human(
        binary,
        [*command, "--non-interactive", "--accept-preview-sha256", digest],
        cwd,
        environment,
        0,
    )
    check(preview.get("mutation") == "preview", f"{command[0]} did not preview")
    check(committed.get("mutation") == "committed", f"{command[0]} did not commit")
    return committed


def snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): digest_bytes(path.read_bytes())
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink()
    }


def normalized_command(document: dict[str, object], *, human: bool = False) -> dict[str, object]:
    details = {} if human else document.get("details", {})
    notices = document.get("notice-codes", []) if human else [
        notice.get("code") for notice in document.get("notices", [])
    ]
    return {
        "command": document.get("command"),
        "outcome": document.get("outcome"),
        "exit_code": document.get("exit-code" if human else "exit_code"),
        "mutation": document.get("mutation"),
        "repository_mode": document.get("repository-mode" if human else "repository_mode"),
        "release_role": document.get("release-role") if human else None,
        "release_sequence": document.get("release-sequence") if human else None,
        "release_index_sha256": document.get("release-index-sha256") if human else None,
        "readiness": details.get("readiness"),
        "violation_codes": [
            violation.get("code") if isinstance(violation, dict) else str(violation)
            for violation in details.get("violations", [])
        ],
        "notice_codes": notices,
    }


def fixture_record(case: str, mode: str, normalized_result: dict[str, object]) -> dict[str, object]:
    return {
        "case": case,
        "execution_status": mode,
        "owner_bytes_preserved": True,
        "language_manifests_ignored": True,
        "line_endings_preserved": True,
        "normalized_result": normalized_result,
        "normalized_sha256": digest_bytes(canonical(normalized_result)),
    }


def run_unsupported_windows_case(
    case: str,
    source: Path,
    workspace: Path,
    artifact: Path,
    checksum: Path,
    artifact_sha: str,
    platform_name: str,
    release_directory: Path,
    trust_state: Path,
) -> tuple[dict[str, object], str]:
    repository = workspace / case
    shutil.copytree(source, repository)
    (repository / "package.json").write_bytes(b'{"scripts":{"phase7-canary":"must-not-run"}}\n')
    (repository / "Cargo.toml").write_bytes(b'[package]\nname = "must-not-interpret"\n')
    before = snapshot(repository)
    binary, installer = windows_direct_after_installer_refusal(
        artifact, checksum, platform_name, repository
    )
    environment = os.environ.copy()
    environment.update({
        "HARNESS_V1_ARTIFACT_SHA256": artifact_sha,
        "HARNESS_V1_PLATFORM": platform_name,
        "HARNESS_V1_RELEASE_DIRECTORY": str(release_directory),
        "HARNESS_V1_TRUST_STATE": str(trust_state),
    })
    install_result = run_human(binary, ["install", "--preview"], repository, environment, 74)
    update_result = run_human(binary, ["update", "--preview"], repository, environment, 74)
    audit_result = run_json(binary, ["audit", "--json"], repository, environment, 74)
    scaffold_result = run_human(
        binary,
        ["scaffold", "--template", "decision-template", "--destination", "docs/templates/decision.md", "--preview"],
        repository,
        environment,
        74,
    )
    status_result = run_json(binary, ["status", "--json"], repository, environment, 74)
    version_result = run_json(binary, ["version", "--json"], repository, environment, 0)
    recovery_result = run_human(
        binary, ["update", "--resume", "missing-operation"], repository, environment, 74
    )
    for name, result in (
        ("install", install_result),
        ("update", update_result),
        ("audit", audit_result),
        ("scaffold", scaffold_result),
        ("status", status_result),
        ("recovery", recovery_result),
    ):
        check(result.get("mutation") == "none", f"Windows {name} crossed the mutation boundary")
    after = snapshot(repository)
    check(all(after.get(path) == digest for path, digest in before.items()), f"owner bytes changed in {case}")
    check(not (repository / ".harness/manifest.json").exists(), "Windows unsupported proof created a manifest")
    normalized_result = {
        "mode": "controlled-unsupported-before-mutation",
        "commands": [
            normalized_command(install_result, human=True),
            normalized_command(update_result, human=True),
            normalized_command(audit_result),
            normalized_command(scaffold_result, human=True),
            normalized_command(status_result),
            normalized_command(version_result),
        ],
        "recovery_refusal": normalized_command(recovery_result, human=True),
    }
    return fixture_record(case, "controlled-unsupported-before-mutation", normalized_result), installer


def run_case(
    case: str,
    source: Path,
    workspace: Path,
    artifact: Path,
    checksum: Path,
    artifact_sha: str,
    platform_name: str,
    release_directory: Path,
    trust_state: Path,
) -> tuple[dict[str, object], str]:
    if platform_name == "windows-x64":
        return run_unsupported_windows_case(
            case, source, workspace, artifact, checksum, artifact_sha,
            platform_name, release_directory, trust_state,
        )
    repository = workspace / case
    shutil.copytree(source, repository)
    (repository / "package.json").write_bytes(b'{"scripts":{"phase7-canary":"must-not-run"}}\n')
    (repository / "Cargo.toml").write_bytes(b'[package]\nname = "must-not-interpret"\n')
    before = snapshot(repository)
    binary, installer = install_unix(artifact, checksum, platform_name, repository)
    environment = os.environ.copy()
    environment.update({
        "HARNESS_V1_ARTIFACT_SHA256": artifact_sha,
        "HARNESS_V1_PLATFORM": platform_name,
        "HARNESS_V1_RELEASE_DIRECTORY": str(release_directory),
        "HARNESS_V1_TRUST_STATE": str(trust_state),
    })
    scaffold_repository = workspace / f"{case}-scaffold"
    scaffold_repository.mkdir()
    scaffold_binary, scaffold_installer = install_unix(
        artifact, checksum, platform_name, scaffold_repository
    )
    check(scaffold_installer == installer, "installer changed for scaffold surface")
    scaffold_result = preview_and_commit(
        scaffold_binary,
        ["scaffold", "--template", "decision-template", "--destination", "docs/templates/decision.md"],
        scaffold_repository,
        environment | {},
    )
    install_result = preview_and_commit(binary, ["install"], repository, environment)
    update_result = run_human(binary, ["update", "--preview"], repository, environment, 0)
    check(update_result.get("mutation") == "none", "idempotent update mutated or required confirmation")
    status = run_json(binary, ["status", "--json"], repository, environment, 0)
    audit = run_json(binary, ["audit", "--json"], repository, environment, 0)
    version = run_json(binary, ["version", "--json"], repository, environment, 0)
    recovery = run_human(binary, ["update", "--resume", "missing-operation"], repository, environment, 3)
    check(recovery.get("mutation") == "none", "missing recovery operation crossed mutation boundary")
    after = snapshot(repository)
    check(all(after.get(path) == digest for path, digest in before.items()), f"owner bytes changed in {case}")
    manifest = json.loads((repository / ".harness/manifest.json").read_text(encoding="utf-8"))
    role_paths = {role["path"] for role in manifest["roles"]}
    check("package.json" not in role_paths and "Cargo.toml" not in role_paths, "language manifest was interpreted")
    normalized_result = {
        "mode": "full-native-test-fixture",
        "commands": [
            normalized_command(install_result, human=True),
            normalized_command(update_result, human=True),
            normalized_command(audit),
            normalized_command(scaffold_result, human=True),
            normalized_command(status),
            normalized_command(version),
        ],
        "recovery_refusal": normalized_command(recovery, human=True),
    }
    return fixture_record(case, "full-native-test-fixture", normalized_result), installer


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--checksum", required=True)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--runner", required=True)
    parser.add_argument("--release-directory", required=True)
    parser.add_argument("--trust-state", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--workflow-revision", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    try:
        artifact = Path(arguments.artifact).resolve(strict=True)
        checksum = Path(arguments.checksum).resolve(strict=True)
        release_directory = Path(arguments.release_directory).resolve(strict=True)
        trust_state = Path(arguments.trust_state).resolve(strict=True)
        output = Path(arguments.output)
        check(output.is_absolute() and not output.exists() and output.parent.is_dir(), "output must be a new absolute path")
        check(arguments.platform == native_platform(), "requested platform is not native")
        check(arguments.platform in PLATFORMS, "requested platform is unsupported")
        target, runner, artifact_name = PLATFORMS[arguments.platform]
        check(arguments.target == target, "requested target does not match platform")
        check(arguments.runner == runner, "requested runner does not match platform")
        check(artifact.name == artifact_name, "artifact filename does not match platform")
        artifact_sha = exact_checksum(artifact, checksum)
        candidate_identity, workflow_identity = immutable_identity(
            arguments.candidate, arguments.workflow_revision
        )
        fixtures_root = ROOT / "tests/fixtures/v1-phase7/repositories"
        with tempfile.TemporaryDirectory(prefix="harness-v1-phase7-execution-") as temporary:
            workspace = Path(temporary)
            records = []
            installers = set()
            for case in CASES:
                record, installer = run_case(
                    case, fixtures_root / case, workspace, artifact, checksum,
                    artifact_sha, arguments.platform, release_directory, trust_state,
                )
                records.append(record)
                installers.add(installer)
        check(len(installers) == 1, "installer identity changed across fixtures")
        contract_sha = digest_bytes(canonical([
            {"case": record["case"], "normalized_result": record["normalized_result"]}
            for record in records
        ]))
        behavior = (
            "controlled-unsupported-before-mutation"
            if arguments.platform == "windows-x64"
            else "full-native-test-fixture"
        )
        document = {
            "schema": "repository-harness-v1-phase7-execution-proof/v1",
            "evidence_kind": "local-or-runner-test-fixture-non-production",
            "candidate": candidate_identity,
            "execution_workflow": workflow_identity,
            "environment": {
                "platform": arguments.platform,
                "installer": installers.pop(),
                "behavior": behavior,
            },
            "artifact": {
                "platform": arguments.platform,
                "target": target,
                "runner": runner,
                "name": artifact_name,
                "sha256": artifact_sha,
                "authentication": "checksum-verified-before-every-execution",
                "provenance": "unattested-not-authenticated",
            },
            "commands": COMMANDS,
            "fixtures": records,
            "normalized_contract_sha256": contract_sha,
            "authority": {
                "phase6_live_evidence": "pending",
                "five_platform_equivalence": "pending",
                "platform_accepted": False,
                "phase7_accepted": False,
                "promotable": False,
                "production": False,
                "phase8": "closed",
                "blockers": BLOCKERS,
            },
        }
        descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(canonical(document))
        print(output)
        return 0
    except (OSError, ProofError) as error:
        print(f"Phase 7 execution proof failed: {error}", file=os.sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
