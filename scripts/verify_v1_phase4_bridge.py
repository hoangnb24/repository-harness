#!/usr/bin/env python3
"""Executable proof for the archive-only Phase 4 V0 bridge."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "v1-phase4"
STORY = ROOT / "docs" / "stories" / "US-109-v1-isolated-v0-bridge"
BINARY = ROOT / "target" / "debug" / ("harness-v0-migrate.exe" if os.name == "nt" else "harness-v0-migrate")


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


def run(command: list[str], *, cwd: Path = ROOT, expected: int = 0) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, cwd=cwd, stdin=subprocess.DEVNULL, capture_output=True, text=True, check=False)
    if completed.returncode != expected:
        raise VerificationError(
            f"command returned {completed.returncode}, expected {expected}: {' '.join(command)}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def bridge(arguments: list[str], root: Path, expected: int = 0) -> subprocess.CompletedProcess[str]:
    return run([str(BINARY), *arguments], cwd=root, expected=expected)


def inventory_snapshot() -> dict[str, tuple[int, str]]:
    inventory = json.loads((FIXTURES / "inventory.json").read_text(encoding="utf-8"))
    snapshot: dict[str, tuple[int, str]] = {}
    for entry in inventory["files"]:
        path = FIXTURES / entry["path"]
        check(path.is_file(), f"fixture inventory member is absent: {entry['path']}")
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        check((len(payload), digest) == (entry["bytes"], entry["sha256"]), f"fixture bytes drift: {entry['path']}")
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(path.relative_to(ROOT))], cwd=ROOT,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
        )
        check(tracked.returncode == 0, f"immutable fixture is not tracked: {entry['path']}")
        snapshot[entry["path"]] = (len(payload), digest)
    return snapshot


def fixture_copy(name: str) -> tempfile.TemporaryDirectory[str]:
    temporary = tempfile.TemporaryDirectory(prefix="phase4-archive-only-")
    shutil.copytree(FIXTURES / name, Path(temporary.name), dirs_exist_ok=True)
    return temporary


def tree_digest(root: Path, excluded: tuple[str, ...] = ()) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        relative = path.relative_to(root).as_posix()
        if relative.startswith(excluded):
            continue
        result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def source_grammar() -> dict[str, object]:
    source = (ROOT / "crates/harness-v0-migrate/src/command_spec.rs").read_text(encoding="utf-8")
    match = re.search(r"BRIDGE_COMMAND_SPEC_JSON_BEGIN.*?r#\"(?P<json>.*?)\"#;.*?BRIDGE_COMMAND_SPEC_JSON_END", source, re.DOTALL)
    check(match is not None, "bridge source grammar markers are missing")
    return json.loads(match.group("json"))


def proof_story_status() -> None:
    packet = "\n".join((STORY / name).read_text(encoding="utf-8") for name in ["overview.md", "design.md", "execplan.md", "validation.md"])
    check("in_progress" in packet, "US-109 must remain in progress")
    check("Decision 0014" in packet, "US-109 does not bind the archive-only decision")
    check("Phase 5" in packet and "Phase 7" in packet and "closed" in packet.lower(), "later gates are not closed")


def proof_closed_grammar() -> None:
    live = json.loads(bridge(["--help"], ROOT).stdout)
    contract = json.loads((ROOT / "release/contracts/v1/command-grammars.json").read_text(encoding="utf-8"))["bridge"]
    check(live == contract == source_grammar(), "live/source/contract bridge grammar differs")
    check(live["top_level"] == ["inspect", "export", "archive", "version"], "bridge grammar is not exactly four commands")
    for rejected in ["--version", "preview", "apply", "resume", "rollback", "install", "update", "audit", "scaffold", "status", "migrate", "init", "query"]:
        bridge([rejected], ROOT, expected=64)


def proof_all_frozen_schemas_execute() -> None:
    for version in range(1, 14):
        with fixture_copy(f"schema-{version:02d}") as directory:
            root = Path(directory)
            before = tree_digest(root)
            report = json.loads(bridge(["inspect", "--json"], root).stdout)
            check(report["source_schema"] == version, f"schema {version} was not identified exactly")
            check(tree_digest(root) == before, f"schema {version} changed during inspect")


def proof_live_and_archive_export_are_exact() -> None:
    with fixture_copy("wal-only-schema-13") as directory:
        root = Path(directory)
        source_before = tree_digest(root)
        live = json.loads(bridge(["export", "--output", "live-export.sqlite3"], root).stdout)
        live_bytes = (root / "live-export.sqlite3").read_bytes()
        check(b"wal-only-committed-row" in live_bytes, "WAL-only committed row was lost")
        archived = json.loads(bridge(["archive", "--archive-plaintext", "--acknowledge-plaintext-recovery-risk"], root).stdout)
        manifest = archived["archive_manifest_path"]
        check(manifest.startswith(".harness-v0-archive/"), "archive escaped reserved custody")
        archive_contract = json.loads((root / manifest).read_text(encoding="utf-8"))
        check(archive_contract["bridge_release"] == "1.0.0",
              "archive did not emit the closed supported bridge release")
        bridge(["export", "--output", "archive-export.sqlite3", "--archive-manifest", manifest], root)
        check((root / "archive-export.sqlite3").read_bytes() == live_bytes, "archive export does not preserve exact neutral bytes")
        for path, digest in source_before.items():
            check(hashlib.sha256((root / path).read_bytes()).hexdigest() == digest, f"source changed: {path}")
        check(live["export_sha256"] == archived["export_sha256"], "live/archive export digest differs")


def proof_append_only_publication_and_no_v1_mutation() -> None:
    with fixture_copy("schema-13") as directory:
        root = Path(directory)
        first = json.loads(bridge(["archive", "--archive-plaintext", "--acknowledge-plaintext-recovery-risk"], root).stdout)
        custody = root / ".harness-v0-archive"
        abandoned = custody / ".staging-abandoned-foreign"
        abandoned.mkdir()
        (abandoned / "foreign").write_bytes(b"do-not-overwrite")
        first_manifest = (root / first["archive_manifest_path"]).read_bytes()
        second = json.loads(bridge(["archive", "--archive-plaintext", "--acknowledge-plaintext-recovery-risk"], root).stdout)
        check(first["archive_id"] != second["archive_id"], "retry reused an accepted archive identity")
        check((root / first["archive_manifest_path"]).read_bytes() == first_manifest, "later archive overwrote the first")
        check((abandoned / "foreign").read_bytes() == b"do-not-overwrite", "foreign abandoned staging was adopted")
        check(not (root / ".harness/manifest.json").exists(), "bridge created a V1 manifest")
        check(not (root / "harness-v1.db").exists(), "bridge created forbidden harness-v1.db")
        check(not (root / ".harness/recovery").exists(), "bridge created core recovery state")


def proof_custody_permissions_and_foreign_paths() -> None:
    if os.name == "nt":
        return
    with fixture_copy("schema-13") as directory:
        root = Path(directory)
        legacy = root / ".harness/legacy/foreign.txt"
        recovery = root / ".harness/recovery/foreign.txt"
        legacy.parent.mkdir(parents=True)
        recovery.parent.mkdir(parents=True)
        legacy.write_bytes(b"legacy")
        recovery.write_bytes(b"recovery")
        report = json.loads(bridge(["archive", "--archive-plaintext", "--acknowledge-plaintext-recovery-risk"], root).stdout)
        check(legacy.read_bytes() == b"legacy" and recovery.read_bytes() == b"recovery", "foreign .harness content changed")
        check({".harness/legacy", ".harness/recovery"} <= set(report["unknown_unowned"]), "foreign custody roots were not reported unowned")
        custody = root / ".harness-v0-archive"
        check(stat.S_IMODE(custody.stat().st_mode) == 0o700, "archive custody root is not 0700")
        check(stat.S_IMODE((custody / "custody.key").stat().st_mode) == 0o600,
              "archive custody key is not 0600")
        check(stat.S_IMODE((custody / "custody.json").stat().st_mode) == 0o600,
              "archive custody marker is not 0600")
        manifest = root / report["archive_manifest_path"]
        check(stat.S_IMODE(manifest.stat().st_mode) == 0o600, "archive manifest is not 0600")


def proof_rejection_and_tamper_suite() -> None:
    run(["cargo", "test", "--locked", "--offline", "--package", "harness-v0-migrate", "--test", "phase4_rejection"])


def proof_core_boundary_and_receipt_recovery() -> None:
    core_cargo = (ROOT / "crates/harness-core/Cargo.toml").read_text(encoding="utf-8").lower()
    core_sources = "\n".join(path.read_text(encoding="utf-8").lower() for path in sorted((ROOT / "crates/harness-core/src").glob("*.rs")))
    check("rusqlite" not in core_cargo and "harness-v0-migrate" not in core_cargo, "core gained a SQLite or bridge dependency")
    check("rusqlite" not in core_sources and "harness_v0_migrate" not in core_sources, "core imports V0 implementation code")
    core_grammar = json.loads((ROOT / "release/contracts/v1/command-grammars.json").read_text(encoding="utf-8"))["core"]
    check(core_grammar["top_level"] == ["install", "update", "audit", "scaffold", "status", "version"], "core is not exactly six commands")
    run([
        "cargo", "test", "--locked", "--offline", "--package", "harness-core", "--test", "phase3_recovery",
        "fresh_install_recovery_commits_exact_v0_archive_receipt_without_reading_sqlite", "--", "--exact",
    ])
    for test in [
        "custody_replacement_between_pin_and_first_read_is_rejected_without_manifest",
        "recovery_revalidates_the_previewed_custody_directory_identity",
        "fake_or_missing_custody_cannot_become_a_v1_archive_receipt",
        "archive_member_capture_and_bridge_release_are_closed_contracts",
        "identical_preexisting_asset_commits_brownfield_mode_and_target_ownership",
    ]:
        run([
            "cargo", "test", "--locked", "--offline", "--package", "harness-core",
            "--test", "phase3_recovery", test, "--", "--exact",
        ])


def proof_windows_phase7_boundary() -> None:
    workflow = (ROOT / ".github/workflows/harness-v0-bridge-release.yml").read_text(encoding="utf-8")
    check("Windows compile, four-command grammar, and fail-closed repository capture" in workflow, "Windows archive-only job is not explicit")
    check("if: runner.os == 'Windows'" in workflow and "$LASTEXITCODE -ne 5" in workflow, "Windows controlled unsupported exit proof is absent")
    check("Phase 7" in workflow and "exit 1" in workflow, "production/platform promotion guard is open")


def proof_unpromoted_release_boundary() -> None:
    binding = json.loads((ROOT / "release/contracts/v1/command-implementation-binding.json").read_text(encoding="utf-8"))
    release = json.loads((ROOT / "release/contracts/v1/bridge-release-artifacts.json").read_text(encoding="utf-8"))
    check(binding["binding_state"] == "core-live-bridge-live-unpromoted", "bridge binding was promoted")
    check(release["release_state"] == "source-present-unpromoted", "bridge release state was promoted")


def main() -> None:
    before = inventory_snapshot()
    run(["cargo", "build", "--quiet", "--locked", "--offline", "--package", "harness-v0-migrate", "--bin", "harness-v0-migrate"])
    run(["cargo", "test", "--quiet", "--locked", "--offline", "--package", "harness-v0-migrate"])
    proof("US-109 stays in progress under Decision 0014 with later gates closed", proof_story_status)
    proof("live/source/contract grammar is exactly inspect/export/archive/version", proof_closed_grammar)
    proof("all frozen schemas inspect read-only from temporary copies", proof_all_frozen_schemas_execute)
    proof("live and archived exports preserve WAL-only committed history exactly", proof_live_and_archive_export_are_exact)
    proof("archives publish append-only without bridge-owned V1 state", proof_append_only_publication_and_no_v1_mutation)
    proof("reserved custody is private and foreign legacy/recovery stays unowned", proof_custody_permissions_and_foreign_paths)
    proof("archive tamper, foreign custody, and unsafe outputs fail closed", proof_rejection_and_tamper_suite)
    proof("six-command SQLite-free core records the exact receipt through Phase 3 recovery", proof_core_boundary_and_receipt_recovery)
    proof("Windows compiles and capture remains controlled-unsupported until Phase 7", proof_windows_phase7_boundary)
    proof("bridge lifecycle remains live-unpromoted", proof_unpromoted_release_boundary)
    check(inventory_snapshot() == before, "tracked Phase 4 fixture bytes changed during verification")
    print(f"V1 Phase 4 archive-only bridge verification passed ({PASS_COUNT} executable proof groups)")


if __name__ == "__main__":
    try:
        main()
    except (VerificationError, OSError, json.JSONDecodeError) as error:
        print(f"V1 Phase 4 bridge verification failed: {error}", file=__import__("sys").stderr)
        raise SystemExit(1) from error
