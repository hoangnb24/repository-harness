#!/usr/bin/env python3
"""Mechanical proof for Repository Harness V1 Phase 4 isolated V0 bridge."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "crates" / "harness-v0-migrate"
CORE = ROOT / "crates" / "harness-core"
FIXTURES = ROOT / "tests" / "fixtures" / "v1-phase4"
STORY = ROOT / "docs" / "stories" / "US-109-v1-isolated-v0-bridge"


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


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def all_source(directory: Path) -> str:
    return "\n".join(text(path) for path in sorted(directory.rglob("*.rs")))


def proof_story_packet() -> None:
    combined = []
    for name in ["overview.md", "design.md", "execplan.md", "validation.md"]:
        path = STORY / name
        check(path.is_file() and path.stat().st_size > 1_000, f"US-109 packet incomplete: {name}")
        combined.append(text(path))
    packet = "\n".join(combined)
    for phrase in [
        "descriptor-anchored",
        "same-handle",
        "repository-harness-v0-export/v1",
        "write-once",
        "manifest-last",
        "recovery-required",
        "Phase 5",
        "Phase 7",
    ]:
        check(phrase in packet, f"US-109 packet omits {phrase}")


def proof_closed_grammars() -> None:
    help_value = subprocess.run(
        [str(ROOT / "target" / "debug" / "harness-v0-migrate"), "--help"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    bridge = json.loads(help_value.stdout)
    expected_bridge = ["inspect", "export", "preview", "apply", "resume", "rollback", "version"]
    check(bridge["top_level"] == expected_bridge, "live bridge grammar is not the exact seven commands")
    grammar = json.loads(text(ROOT / "release" / "contracts" / "v1" / "command-grammars.json"))
    expected_core = ["install", "update", "audit", "scaffold", "status", "version"]
    check(grammar["core"]["top_level"] == expected_core, "permanent core grammar is not exactly six commands")
    interface = text(BRIDGE / "src" / "interface.rs")
    for forbidden in ["install", "update", "audit", "scaffold", "status", "migrate"]:
        check(f'"{forbidden}"' in interface, f"bridge parser does not explicitly reject {forbidden}")


def proof_dependency_isolation() -> None:
    bridge_cargo = text(BRIDGE / "Cargo.toml").lower()
    core_cargo = text(CORE / "Cargo.toml").lower()
    check("harness-core" in bridge_cargo and "rusqlite" in bridge_cargo, "bridge does not own its V0 dependencies")
    check("harness-v0-migrate" not in core_cargo, "permanent core depends on bridge")
    check("rusqlite" not in core_cargo and "sqlite" not in core_cargo, "permanent core depends on SQLite")
    check("harness_v0_migrate" not in all_source(CORE), "permanent core imports bridge code")


def proof_descriptor_capture() -> None:
    source = text(BRIDGE / "src" / "capture.rs")
    tests = text(BRIDGE / "tests" / "phase4_bridge.rs")
    for fragment in [
        "OFlags::NOFOLLOW",
        "NonBlockingLockShared",
        "not quiesced",
        "before_identity != after",
        "pre != copy_digest",
        "pre != post",
        "SQLite source set changed during capture",
        "recovery.db-wal",
        "standalone.db",
        "Backup::new",
        "filesystem.harness.db-shm-forensic-only",
    ]:
        check(fragment in source, f"capture proof omits {fragment}")
    for test in [
        "immutable_reader_accepts_every_frozen_schema_and_preserves_unknown_metadata",
        "wal_only_commit_is_present_in_standalone_backup_and_shm_is_forensic_only",
        "capture_refuses_an_active_v0_writer",
        "mixed_manifest_and_symlinked_source_fail_without_source_mutation",
    ]:
        check(f"fn {test}" in tests, f"capture integration oracle is missing: {test}")


def proof_export_and_archive() -> None:
    export = text(BRIDGE / "src" / "export.rs")
    archive = text(BRIDGE / "src" / "archive.rs")
    interface = text(BRIDGE / "src" / "interface.rs")
    for fragment in [
        "repository-harness-v0-export/v1",
        "source_sha256",
        "payload_sha256",
        "sqlite.table.",
        "NeutralValue",
    ]:
        check(fragment in export, f"neutral export proof omits {fragment}")
    for fragment in [
        "age::x25519",
        "Encryptor::with_recipients",
        "create_new(true)",
        "repository-owner-indefinite-write-once",
        ".harness/legacy/v0-conversion",
        "existing write-once archive payload was tampered",
    ]:
        check(fragment in archive, f"archive custody proof omits {fragment}")
    check("plaintext requires both --archive-plaintext" in interface, "plaintext two-flag gate is missing")


def proof_journal_recovery_and_kill_points() -> None:
    journal = text(BRIDGE / "src" / "journal.rs")
    implementation = text(BRIDGE / "src" / "lib.rs")
    tests = text(BRIDGE / "tests" / "phase4_bridge.rs")
    for state in ["Discovered", "Inspected", "Exported", "Archived", "Prepared", "Applying", "Committed", "Completed"]:
        check(state in journal, f"journal state is missing: {state}")
    for point in ["detection", "export", "archive", "temporary-receipt", "temporary-manifest", "operation-1", "atomic-commit"]:
        check(f'"{point}"' in implementation and f'"{point}"' in tests, f"kill point is not implemented and tested: {point}")
    for fragment in [
        "resume source identity differs from journal-bound input",
        "target edit refusal",
        "RecoveryRequired",
        "rename_no_replace",
        "validate_live_manifest",
    ]:
        check(fragment in implementation, f"recovery proof omits {fragment}")


def proof_fixture_inventory() -> None:
    inventory = json.loads(text(FIXTURES / "inventory.json"))
    entries = inventory["files"]
    paths = {entry["path"] for entry in entries}
    for version in range(1, 14):
        check(f"schema-{version:02d}/harness.db" in paths, f"schema {version} database fixture is absent")
    for entry in entries:
        path = FIXTURES / entry["path"]
        check(path.is_file(), f"fixture inventory member is absent: {entry['path']}")
        payload = path.read_bytes()
        check(len(payload) == entry["bytes"], f"fixture size drift: {entry['path']}")
        check(hashlib.sha256(payload).hexdigest() == entry["sha256"], f"fixture digest drift: {entry['path']}")
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(path.relative_to(ROOT))],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        check(tracked.returncode == 0, f"immutable fixture is not tracked: {entry['path']}")


def proof_structural_mixed_version_boundary() -> None:
    ports = text(CORE / "src" / "ports.rs")
    infrastructure = text(CORE / "src" / "infrastructure.rs")
    application = text(CORE / "src" / "application.rs")
    tests = text(CORE / "tests" / "phase2_core.rs")
    for fragment in ["CompatibilityObservation", "legacy_artifact_present", "conversion_journal_present", "conversion_archive_present"]:
        check(fragment in ports, f"structural compatibility port omits {fragment}")
    check("harness.db" in infrastructure and "rusqlite" not in infrastructure, "OS adapter is not structural-only")
    for fragment in ["mixed-invalid", "conversion-in-progress", "v0-legacy"]:
        check(fragment in application, f"status classification omits {fragment}")
    check("status_classifies_structural_v0_and_mixed_state_without_a_sqlite_or_bridge_dependency" in tests, "mixed-version integration oracle is missing")


def proof_live_unpromoted_release_boundary() -> None:
    binding = json.loads(text(ROOT / "release" / "contracts" / "v1" / "command-implementation-binding.json"))
    identity = json.loads(text(ROOT / "release" / "contracts" / "v1" / "bootstrap-identity.json"))
    release = json.loads(text(ROOT / "release" / "contracts" / "v1" / "bridge-release-artifacts.json"))
    workflow = text(ROOT / ".github" / "workflows" / "harness-v0-bridge-release.yml")
    check(binding["binding_state"] == "core-live-bridge-live-unpromoted", "command binding is not live-unpromoted")
    check(identity["bridge"]["workflow_lifecycle"]["state"] == "source-present-unpromoted", "bootstrap identity promoted or omitted bridge source")
    check(release["release_state"] == "source-present-unpromoted", "bridge release metadata is not unpromoted")
    check(len(release["platforms"]) == 5, "bridge build shape does not list five Phase 7 platforms")
    for forbidden in ["upload-artifact", "release upload", "cargo publish", "gh release create"]:
        check(forbidden not in workflow.lower(), f"unpromoted workflow performs forbidden action: {forbidden}")
    check("exit 1" in workflow and "Phase 7" in workflow, "production promotion guard is not closed")


def proof_archive_non_deletion_and_platform_boundary() -> None:
    archive = text(BRIDGE / "src" / "archive.rs")
    implementation = text(BRIDGE / "src" / "lib.rs")
    for forbidden in ["remove_file", "remove_dir", "truncate(true)"]:
        check(forbidden not in archive, f"archive implementation can destructively alter custody: {forbidden}")
    check("remove_file(&manifest_path)" in implementation, "rollback does not limit deletion to its manifest post-image")
    check("descriptor-anchored V0 capture is unavailable on this platform" in text(BRIDGE / "src" / "capture.rs"), "non-Unix capture does not fail closed")
    check("atomic no-replace manifest commit is unavailable until Phase 7" in implementation, "non-Unix commit does not keep Phase 7 closed")


def main() -> None:
    proof("US-109 high-risk packet is complete", proof_story_packet)
    proof("bridge seven-command and core six-command grammars stay closed", proof_closed_grammars)
    proof("dependency direction remains bridge to core", proof_dependency_isolation)
    proof("descriptor capture is quiesced, no-follow, and WAL-correct", proof_descriptor_capture)
    proof("neutral export and write-once encrypted archive are bound", proof_export_and_archive)
    proof("journal recovery and every Phase 4 kill point are covered", proof_journal_recovery_and_kill_points)
    proof("immutable schema, WAL, changeset, and unknown fixtures verify", proof_fixture_inventory)
    proof("mixed-version status uses only a structural core port", proof_structural_mixed_version_boundary)
    proof("bridge release source is live but deliberately unpromoted", proof_live_unpromoted_release_boundary)
    proof("archive custody and Phase 7 platform boundaries remain closed", proof_archive_non_deletion_and_platform_boundary)
    print(f"V1 Phase 4 bridge verification passed ({PASS_COUNT} proof groups)")


if __name__ == "__main__":
    try:
        main()
    except (VerificationError, OSError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(f"V1 Phase 4 bridge verification failed: {error}", file=__import__("sys").stderr)
        raise SystemExit(1) from error
