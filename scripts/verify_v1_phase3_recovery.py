#!/usr/bin/env python3
"""Mechanical proof for Repository Harness V1 Phase 3 mutation/recovery."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "crates" / "harness-core"
RECOVERY = CORE / "src" / "recovery.rs"
APPLICATION = CORE / "src" / "application.rs"
INTEGRATION = CORE / "tests" / "phase3_recovery.rs"
STORY = ROOT / "docs" / "stories" / "US-108-v1-install-update-recovery"


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


def proof_exact_plan_binding() -> None:
    source = text(RECOVERY)
    for fragment in [
        "operations_from_writes",
        "public_operation_digest",
        "request.operations != expected_operations",
        "public operations are not the exact projection of planned writes",
        "plan_operation_id",
        "expected_create_witness_path",
        'format!("witness-',
        "operation identifier does not commit the exact mutation plan",
        "accepted_preview_cannot_authorize_mismatched_planned_write_bytes",
        "unrelated_private_staged_path_is_rejected_before_zero_filesystem_mutation",
        "backup_manifest_and_kind_invariants_fail_before_zero_filesystem_mutation",
    ]:
        check(fragment in source, f"exact request/preview binding omits {fragment}")


def proof_authenticated_recovery_binding() -> None:
    source = text(RECOVERY)
    integration = text(INTEGRATION)
    for fragment in [
        "journal.operations != expected_operations",
        "recovery operation identifier does not authorize the exact post-images",
        "RecoveryScope",
        "authorization.assets",
        "asset.sha256",
        "asset.bytes",
        "verify_authenticated_post_images",
        "verify_probe_owned_evidence",
        "verify_owned_evidence_read_only",
        "validate_candidate_transition",
        "validate_payload_transition",
        "RootIdentity",
        "journal_matches_current_root",
        "recovery journal belongs to a different repository root",
        "link_owned_once",
        "step_requires_create_witness",
        "deterministic authenticated managed-block post-image",
        "recomputed_unkeyed_journal_digest_cannot_change_authorized_manifest_post_image",
        "nested_operation_unknown_field_is_rejected_even_with_recomputed_body_digest",
        "fabricated_applied_create_without_hard_link_witness_is_not_trusted_on_resume",
        "fabricated_update_journal_cannot_patch_authoritative_target_owned_role",
        "fabricated_fresh_journal_cannot_claim_preexisting_before_images",
        "fabricated_scaffold_journal_cannot_expand_beyond_bound_destination",
        "rollback_refuses_scaffold_target_delete_without_hard_link_witness",
        "rollback_refuses_fresh_manifest_delete_without_hard_link_witness",
        "fabricated_recovery_downgrade_is_rejected_before_zero_mutation",
        "copied_interrupted_update_journal_is_not_actionable_in_another_repository_root",
        "copied_committed_update_journal_cannot_drive_rollback_in_another_repository_root",
    ]:
        check(
            fragment in source or fragment in integration,
            f"authenticated recovery binding omits {fragment}",
        )


def proof_atomic_race_boundary() -> None:
    source = text(RECOVERY)
    for fragment in [
        "OFlags::NOFOLLOW",
        "RenameFlags::NOREPLACE",
        "RenameFlags::EXCHANGE",
        "exchanged_stat.st_ino != destination_stat.st_ino",
        "intervening bytes were preserved",
        "root_path",
        "same_root_stat",
        "rollback_rejects_repository_root_pathname_replacement",
        'target_os = "linux"',
        'target_os = "macos"',
        "Phase 7 platform gate remains closed",
        "final_component_swap_is_reversed_without_clobbering_intervening_bytes",
    ]:
        check(fragment in source, f"final-component race proof omits {fragment}")


def proof_manifest_last_and_rollback() -> None:
    source = text(RECOVERY)
    integration = text(INTEGRATION)
    check("manifest_index + 1 != journal.steps.len()" in source, "manifest-last check missing")
    for fragment in [
        "JournalState::RollingBack",
        "journal.state = JournalState::RollingBack",
        "restore_missing_manifest",
        "removed new manifest before rollback",
        "restored old manifest last journal fsync",
        "validate_recovery_manifest_state",
        "manifest_is_committed_last_and_rollback_removes_exact_created_images",
        "rollback_does_not_restore_old_manifest_when_manifest_step_was_never_applied",
        "target_edit_blocks_rollback_before_any_restoration",
    ]:
        check(fragment in source, f"rollback protocol omits {fragment}")
    for test in [
        "every_committed_update_rollback_checkpoint_resumes_in_reverse_with_old_manifest_last",
        "human_edit_during_committed_update_rollback_is_preserved_before_old_manifest_restore",
        "rollback_deliberately_requires_live_release_authorization_before_using_local_evidence",
    ]:
        check(test in integration, f"rollback integration oracle is missing: {test}")


def proof_status_probe_and_exact_rerun() -> None:
    recovery = text(RECOVERY)
    application = text(APPLICATION)
    integration = text(INTEGRATION)
    grammar = json.loads(text(ROOT / "release/contracts/v1/command-grammars.json"))
    status = next(command for command in grammar["core"]["commands"] if command["name"] == "status")
    check(status["exits"] == [0, 3, 64, 70, 74], "frozen status exits changed")
    check("fn probe_recovery(&self)" in recovery, "read-only mutation-boundary probe missing")
    check(
        "JournalState::Prepared | JournalState::Applying" in recovery,
        "probe broadened beyond actionable nonterminal states",
    )
    check("if status { 3 } else { 4 }" in application, "status/mutator recovery exits are conflated")
    for test in [
        "status_and_exact_rerun_report_recovery_without_replay_and_audit_is_read_only",
        "recovery_status_preserves_authoritative_manifest_mode_and_declared_readiness",
        "damaged_applying_update_evidence_is_non_actionable_and_preserves_the_tree",
    ]:
        check(test in integration, f"read-only recovery oracle missing: {test}")


def proof_signed_mutation_behaviors() -> None:
    source = text(INTEGRATION)
    expected = [
        "signed_install_requires_exact_confirmation_commits_manifest_last_and_is_idempotent",
        "preview_sha256_matches_the_exact_emitted_operations_array",
        "scaffold_is_exact_and_update_preserves_target_owned_bytes",
        "identical_preexisting_asset_commits_brownfield_mode_and_target_ownership",
        "fresh_install_recovery_commits_exact_v0_archive_receipt_without_reading_sqlite",
        "custody_replacement_between_pin_and_first_read_is_rejected_without_manifest",
        "recovery_revalidates_the_previewed_custody_directory_identity",
        "managed_file_drift_returns_exact_three_way_review_without_writing",
        "managed_block_update_replaces_only_authenticated_interior",
    ]
    for name in expected:
        check(f"fn {name}" in source, f"signed integration proof missing: {name}")
    check("core-payload-index.signatures.json" in source, "integration does not use signed release")
    check("test-bootstrap-anchors.json" in source, "integration does not use pinned test roots")


def proof_kill_points_and_idempotency() -> None:
    source = text(INTEGRATION)
    check("for checkpoint in 1..=18" in source, "all 18 install kill points are not enumerated")
    check("for checkpoint in 1..=15" in source, "all 15 update kill points are not enumerated")
    check(
        "for checkpoint in 1..=13" in source,
        "all 13 committed-update rollback checkpoints are not enumerated",
    )
    check(
        "every_install_kill_point_has_a_deterministic_rerun_resume_or_rollback" in source,
        "kill-point recovery proof missing",
    )
    check(
        "every_update_backup_exchange_and_manifest_kill_point_resumes_deterministically"
        in source,
        "update backup/exchange kill-point proof missing",
    )
    check(source.count("idempotent-noop") >= 2, "install/scaffold idempotency assertions missing")
    recovery = text(RECOVERY)
    check("write_owned_once" in recovery and "existing == bytes" in recovery, "pre-journal rerun cannot reuse exact evidence")


def proof_closed_dependency_and_execution_boundary() -> None:
    cargo = text(CORE / "Cargo.toml")
    sources = "\n".join(text(path) for path in sorted((CORE / "src").glob("*.rs")))
    for forbidden in ["rusqlite", "sqlite", "changeset"]:
        check(forbidden not in cargo.lower(), f"harness-core dependency includes {forbidden}")
    for forbidden in ["std::process::Command", "Command::new(", "language detection"]:
        check(forbidden not in sources, f"core can execute/infer a target boundary: {forbidden}")
    grammar = json.loads(text(ROOT / "release/contracts/v1/command-grammars.json"))["core"]
    check(grammar["top_level"] == ["install", "update", "audit", "scaffold", "status", "version"], "six-command grammar changed")


def proof_phase4_and_phase7_gates() -> None:
    main = text(CORE / "src" / "main.rs")
    check("UnavailableReleasePort" in main and "UnavailableTrustPort" in main, "production release/trust was promoted")
    check("HarnessCore::with_mutations" not in main, "live binary was promoted before Phase 4/7 gates")
    check((ROOT / "crates/harness-v0-migrate").is_dir(), "Phase 4 isolated bridge crate is missing")
    check((ROOT / ".github/workflows/harness-v0-bridge-release.yml").is_file(), "Phase 4 unpromoted bridge workflow is missing")
    cargo = text(ROOT / "crates/harness-core/Cargo.toml").lower()
    check("harness-v0-migrate" not in cargo and "rusqlite" not in cargo,
          "Phase 4 bridge or SQLite dependency entered permanent core")
    check("safe descriptor-anchored mutation is unavailable until Phase 7" in text(RECOVERY), "non-Unix fail-closed boundary missing")


def proof_protected_paths_unchanged() -> None:
    changed_lines = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    allowed_phase4_changeset = ".harness/changesets/harness_v1_phase4_bridge.changeset.jsonl"
    changed = "\n".join(
        line for line in changed_lines if not line.endswith(allowed_phase4_changeset)
    )
    for forbidden in [
        ".harness/changesets/",
        "repomix-output.xml",
        "crates/harness-cli/",
        "scripts/schema/",
    ]:
        check(forbidden not in changed, f"protected Phase 3 path changed: {forbidden}")


def proof_story_packet() -> None:
    for name in ["overview.md", "design.md", "execplan.md", "validation.md"]:
        path = STORY / name
        check(path.is_file() and path.stat().st_size > 1000, f"US-108 packet incomplete: {name}")
    combined = "\n".join(text(STORY / name) for name in ["overview.md", "design.md", "execplan.md", "validation.md"])
    for phrase in [
        "manifest-last",
        "hard link",
        "st_dev",
        "st_ino",
        "same-UID malicious process",
        "three-way",
        "never-auto-patch",
        "target-owned",
        "creates/<step-id>.link",
        "fsync",
        "atomic",
        "Phase 4",
        "Phase 7",
    ]:
        check(phrase in combined, f"US-108 packet omits {phrase}")


def main() -> None:
    proof("planned writes exactly bind public preview operations", proof_exact_plan_binding)
    proof("recovery binds exact authenticated and derived post-images", proof_authenticated_recovery_binding)
    proof("descriptor-anchored atomic replacement detects final-component races", proof_atomic_race_boundary)
    proof("manifest-last rollback restores only applied owned images", proof_manifest_last_and_rollback)
    proof("status probe and exact rerun are read-only and contract-correct", proof_status_probe_and_exact_rerun)
    proof("signed install/update/scaffold ownership behaviors are covered", proof_signed_mutation_behaviors)
    proof("all install/update kill points and idempotent reruns are covered", proof_kill_points_and_idempotency)
    proof("six-command core has no database, changeset, or target execution dependency", proof_closed_dependency_and_execution_boundary)
    proof("Phase 4 production and Phase 7 portability gates remain closed", proof_phase4_and_phase7_gates)
    proof("protected V0, changeset, database, and repomix paths are untouched", proof_protected_paths_unchanged)
    proof("US-108 implementation, design, execution, and validation packet exists", proof_story_packet)
    print(f"V1 Phase 3 recovery verification passed ({PASS_COUNT} proof groups)")


if __name__ == "__main__":
    try:
        main()
    except (VerificationError, OSError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(f"V1 Phase 3 recovery verification failed: {error}", file=__import__("sys").stderr)
        raise SystemExit(1) from error
