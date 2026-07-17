#!/usr/bin/env python3
"""Executable proof for the isolated Phase 4 V0 bridge."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "v1-phase4"
STORY = ROOT / "docs" / "stories" / "US-109-v1-isolated-v0-bridge"
BINARY = ROOT / "target" / "debug" / "harness-v0-migrate"


class VerificationError(RuntimeError):
    pass


PASS_COUNT = 0


def check(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def proof(label: str, function: Callable[[], None]) -> None:
    global PASS_COUNT
    function()
    PASS_COUNT += 1
    print(f"ok {PASS_COUNT:02d} - {label}")


def run(command: list[str], *, cwd: Path = ROOT, expected: int = 0, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != expected:
        raise VerificationError(
            f"command returned {completed.returncode}, expected {expected}: {' '.join(command)}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def bridge(arguments: list[str], root: Path, expected: int = 0, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return run([str(BINARY), *arguments], cwd=root, expected=expected, env=env)


def inventory_snapshot() -> dict[str, tuple[int, str]]:
    inventory = json.loads((FIXTURES / "inventory.json").read_text(encoding="utf-8"))
    snapshot: dict[str, tuple[int, str]] = {}
    for entry in inventory["files"]:
        path = FIXTURES / entry["path"]
        check(path.is_file(), f"fixture inventory member is absent: {entry['path']}")
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        check(len(payload) == entry["bytes"], f"fixture size drift: {entry['path']}")
        check(digest == entry["sha256"], f"fixture digest drift: {entry['path']}")
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(path.relative_to(ROOT))],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        check(tracked.returncode == 0, f"immutable fixture is not tracked: {entry['path']}")
        snapshot[entry["path"]] = (len(payload), digest)
    return snapshot


def fixture_copy(name: str) -> tempfile.TemporaryDirectory[str]:
    temporary = tempfile.TemporaryDirectory(prefix="phase4-verifier-")
    shutil.copytree(FIXTURES / name, Path(temporary.name), dirs_exist_ok=True)
    return temporary


def tree_digest(root: Path, excluded_prefixes: tuple[str, ...] = ()) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        relative = path.relative_to(root).as_posix()
        if relative.startswith(excluded_prefixes):
            continue
        result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def proof_story_status() -> None:
    packet = "\n".join(
        (STORY / name).read_text(encoding="utf-8")
        for name in ["overview.md", "design.md", "execplan.md", "validation.md"]
    )
    check("in_progress" in packet, "US-109 must remain in progress")
    check("Phase 5" in packet and "Phase 7" in packet, "later production/platform gates are not explicitly closed")


def proof_closed_grammar() -> None:
    help_value = json.loads(bridge(["--help"], ROOT).stdout)
    check(
        help_value["top_level"]
        == ["inspect", "export", "preview", "apply", "resume", "rollback", "version"],
        "bridge machine grammar changed",
    )
    for rejected in ["--version", "install", "update", "audit", "scaffold", "status", "migrate", "init", "query"]:
        bridge([rejected], ROOT, expected=64)


def proof_all_frozen_schemas_execute() -> None:
    for version in range(1, 14):
        with fixture_copy(f"schema-{version:02d}") as directory:
            root = Path(directory)
            before = tree_digest(root)
            report = json.loads(bridge(["inspect", "--json"], root).stdout)
            check(report["source_schema"] == version, f"schema {version} was not identified exactly")
            check(tree_digest(root) == before, f"schema {version} fixture copy changed during inspect")


def proof_wal_export_and_exact_values() -> None:
    with fixture_copy("wal-only-schema-13") as directory:
        root = Path(directory)
        report = json.loads(bridge(["inspect", "--json"], root).stdout)
        check(report["source_schema"] == 13, "WAL-only fixture did not recover schema 13")
    run(
        [
            "cargo",
            "test",
            "--locked",
            "--offline",
            "--package",
            "harness-v0-migrate",
            "export::tests::neutral_values_preserve_text_bytes_nul_extremes_real_bits_and_blobs",
            "--",
            "--exact",
        ]
    )


def proof_crash_resume_and_archive_binding() -> None:
    with fixture_copy("schema-13") as directory:
        root = Path(directory)
        preview = json.loads(bridge(["preview", "--json"], root).stdout)
        conversion_id = preview["conversion_id"]
        environment = os.environ.copy()
        environment["HARNESS_V0_MIGRATE_TEST_KILL_AFTER"] = "archive"
        bridge(
            [
                "apply",
                "--non-interactive",
                "--accept-preview-sha256",
                preview["preview_sha256"],
                "--archive-plaintext",
                "--acknowledge-plaintext-recovery-risk",
            ],
            root,
            expected=4,
            env=environment,
        )
        check(not (root / ".harness/manifest.json").exists(), "archive kill point reported a false cutover")
        resumed = json.loads(bridge(["resume", "--conversion-id", conversion_id], root).stdout)
        check(resumed["journal_state"] == "completed", "resume did not reach completed")
        journal = json.loads(
            (root / f".harness/recovery/v0-conversion/{conversion_id}/journal.json").read_text(encoding="utf-8")
        )
        check(journal["state"] == "completed" and len(journal["authentication"]) == 64, "journal is not durably authenticated")
        archive = root / f".harness/legacy/v0-conversion/{conversion_id}"
        check(
            sorted(path.name for path in archive.iterdir()) == ["archive-manifest.json", "conversion.bin"],
            "published archive member set is not exact",
        )
        (archive / "conversion.bin").write_bytes(b"tampered")
        bridge(["resume", "--conversion-id", conversion_id], root, expected=4)


def proof_symlink_and_plan_drift_fail_closed() -> None:
    if os.name == "nt":
        return
    with fixture_copy("schema-13") as directory, tempfile.TemporaryDirectory(prefix="phase4-outside-") as outside:
        root = Path(directory)
        (root / "out").symlink_to(Path(outside), target_is_directory=True)
        bridge(
            [
                "export",
                "--output",
                "out/export.json",
                "--archive-plaintext",
                "--acknowledge-plaintext-recovery-risk",
            ],
            root,
            expected=4,
        )
        check(not (Path(outside) / "export.json").exists(), "output symlink escaped the repository")
        check(not (root / ".harness/recovery").exists(), "failed output preflight created custody state")
    with fixture_copy("schema-13") as directory:
        root = Path(directory)
        preview = json.loads(bridge(["preview", "--json"], root).stdout)
        (root / "AGENTS.md").write_text("edited after preview\n", encoding="utf-8")
        bridge(
            [
                "apply",
                "--non-interactive",
                "--accept-preview-sha256",
                preview["preview_sha256"],
                "--archive-plaintext",
                "--acknowledge-plaintext-recovery-risk",
            ],
            root,
            expected=4,
        )
        check(not (root / ".harness/manifest.json").exists(), "plan drift mutated the target")


def proof_private_custody_permissions() -> None:
    if os.name == "nt":
        return
    with fixture_copy("schema-13") as directory:
        root = Path(directory)
        preview = json.loads(bridge(["preview", "--json"], root).stdout)
        conversion_id = preview["conversion_id"]
        bridge(
            [
                "apply",
                "--non-interactive",
                "--accept-preview-sha256",
                preview["preview_sha256"],
                "--archive-plaintext",
                "--acknowledge-plaintext-recovery-risk",
            ],
            root,
        )
        for path in [
            root / ".harness/recovery",
            root / f".harness/recovery/v0-conversion/{conversion_id}",
            root / f".harness/legacy/v0-conversion/{conversion_id}",
        ]:
            check(stat.S_IMODE(path.stat().st_mode) == 0o700, f"custody directory is not 0700: {path}")
        for path in [
            root / f".harness/recovery/v0-conversion/{conversion_id}/journal.json",
            root / f".harness/legacy/v0-conversion/{conversion_id}/conversion.bin",
        ]:
            check(stat.S_IMODE(path.stat().st_mode) == 0o600, f"custody file is not 0600: {path}")


def proof_core_boundary_and_receipt_authentication() -> None:
    core_cargo = (ROOT / "crates/harness-core/Cargo.toml").read_text(encoding="utf-8").lower()
    core_sources = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted((ROOT / "crates/harness-core/src").glob("*.rs"))
    ).lower()
    check("rusqlite" not in core_cargo and "harness-v0-migrate" not in core_cargo, "core gained a SQLite or bridge dependency")
    check("rusqlite" not in core_sources and "harness_v0_migrate" not in core_sources, "core imports V0 implementation code")
    run(
        [
            "cargo",
            "test",
            "--locked",
            "--offline",
            "--package",
            "harness-v0-migrate",
            "--test",
            "phase4_rejection",
            "core_status_authenticates_receipt_archive_export_and_snapshot_without_bridge_or_sqlite",
            "--",
            "--exact",
        ]
    )


def proof_windows_phase7_boundary() -> None:
    workflow = (ROOT / ".github/workflows/harness-v0-bridge-release.yml").read_text(encoding="utf-8")
    check("Windows compile, grammar, and fail-closed repository commands" in workflow, "Windows Phase 4 job is not explicitly constrained")
    check("if: runner.os == 'Windows'" in workflow, "Windows fail-closed job is absent")
    check("$LASTEXITCODE -ne 5" in workflow, "Windows repository command does not assert fail-closed exit 5")
    check("Phase 7" in workflow and "exit 1" in workflow, "production/platform promotion guard is not closed")


def proof_unpromoted_release_boundary() -> None:
    binding = json.loads((ROOT / "release/contracts/v1/command-implementation-binding.json").read_text(encoding="utf-8"))
    release = json.loads((ROOT / "release/contracts/v1/bridge-release-artifacts.json").read_text(encoding="utf-8"))
    check(binding["binding_state"] == "core-live-bridge-live-unpromoted", "bridge binding was promoted")
    check(release["release_state"] == "source-present-unpromoted", "bridge release state was promoted")


def main() -> None:
    before = inventory_snapshot()
    run(["cargo", "test", "--quiet", "--locked", "--offline", "--package", "harness-v0-migrate"])
    run(["cargo", "build", "--quiet", "--locked", "--offline", "--package", "harness-v0-migrate", "--bin", "harness-v0-migrate"])
    proof("US-109 stays in progress with later gates closed", proof_story_status)
    proof("live grammar accepts only the contracted bridge tokens", proof_closed_grammar)
    proof("all frozen schemas execute against temporary copies without mutation", proof_all_frozen_schemas_execute)
    proof("WAL recovery and exact neutral value representations execute", proof_wal_export_and_exact_values)
    proof("authenticated crash resume and archive tamper refusal execute", proof_crash_resume_and_archive_binding)
    proof("symlink output and adopted-document drift fail before mutation", proof_symlink_and_plan_drift_fail_closed)
    proof("custody permissions are private", proof_private_custody_permissions)
    proof("six-command core authenticates conversion evidence without SQLite", proof_core_boundary_and_receipt_authentication)
    proof("Windows remains compile/grammar/fail-closed until Phase 7", proof_windows_phase7_boundary)
    proof("bridge remains live-unpromoted", proof_unpromoted_release_boundary)
    after = inventory_snapshot()
    check(after == before, "committed fixture inventory changed during the complete executable proof")
    print(f"V1 Phase 4 bridge verification passed ({PASS_COUNT} executable proof groups)")


if __name__ == "__main__":
    try:
        main()
    except (VerificationError, OSError, json.JSONDecodeError) as error:
        print(f"V1 Phase 4 bridge verification failed: {error}", file=__import__("sys").stderr)
        raise SystemExit(1) from error
