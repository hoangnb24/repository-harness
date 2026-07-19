#!/usr/bin/env python3
"""Fail-closed Phase 6 framework and candidate-evidence verifier."""

from __future__ import annotations

import argparse
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "tests" / "evals" / "v1-phase6"
EVIDENCE = EVAL / "evidence"
SCHEMAS = EVAL / "schemas"
SCHEMA_NAMES = (
    "baseline-lock",
    "candidate-result",
    "candidate-subject",
    "comparison-report",
    "condition-lock",
    "evidence-index",
    "intervention-log",
    "lane-assignment",
    "packet-manifest",
    "prompt-authentication",
    "signature",
    "warm-v0-capture",
)
BASE_COMMIT = "5d6e6bc516cd60e47c60ae3b516363cd99b433a5"
NAMESPACE = "repository-harness-phase6"
ALL_CARDS = [f"P{number}" for number in range(8)]
WARM_CARDS = ["P0", "P1"]
MANDATORY_NEGATIVES = {
    "phase5-baseline-mutation",
    "condition-drift",
    "acceptance-test-failure",
    "unlogged-intervention",
    "target-data-loss",
    "raw-v0-evidence-custody",
    "held-out-hint-leakage",
    "candidate-functional-regression",
    "missing-applicability-finding",
    "gardening-scope-churn",
    "release-boundary-violation",
    "live-v0-source-mutation",
}
PHASE5_VERIFIER_COMPATIBILITY_PATH = "scripts/verify_v1_phase5_evidence.py"
PHASE5_FORWARDING_COMPATIBILITY_PATH = (
    "tests/evals/test-phase5-premerge-trust-forwarding.sh"
)
PHASE5_FORWARDING_COMPATIBILITY_GIT_OID = (
    "9cf3290dc24d5abb1b299a0dff38771ffa7577fd"
)
ALLOWED_CHANGED_FILES = {
    ".github/harness-v1-diagnostic-request",
    ".github/workflows/harness-v1-release.yml",
    ".harness/changesets/harness_v1_phase6_00_intake.changeset.jsonl",
    ".harness/changesets/harness_v1_phase6_01_story.changeset.jsonl",
    ".harness/changesets/harness_v1_phase7_00_intake.changeset.jsonl",
    ".harness/changesets/harness_v1_phase7_01_story.changeset.jsonl",
    ".harness/changesets/harness_v1_phase7_02_proof_contract.changeset.jsonl",
    ".harness/changesets/harness_v1_phase7_03_build_receipts.changeset.jsonl",
    ".harness/changesets/harness_v1_phase7_04_execution_proof.changeset.jsonl",
    ".harness/changesets/harness_v1_phase7_05_review_corrections.changeset.jsonl",
    ".harness/changesets/harness_v1_phase7_06_cross_binding_corrections.changeset.jsonl",
    ".harness/changesets/harness_v1_phase7_07_github_attestation.changeset.jsonl",
    ".harness/changesets/harness_v1_phase7_08_windows_compile_fix.changeset.jsonl",
    ".harness/changesets/harness_v1_phase7_09_windows_refusal_capture.changeset.jsonl",
    "crates/harness-core/src/infrastructure.rs",
    "crates/harness-core/src/main.rs",
    "crates/harness-core/src/recovery.rs",
    "crates/harness-core/tests/phase7_direct_binary.rs",
    "crates/harness-core/tests/phase2_core.rs",
    "crates/harness-core/tests/phase3_recovery.rs",
    "docs/REFACTOR_PLAN.md",
    "docs/TEST_MATRIX.md",
    "docs/decisions/0015-phase6-cold-warm-evaluation-custody.md",
    "docs/decisions/0016-phase6-framework-acceptance-and-phase7-opening.md",
    "docs/decisions/README.md",
    "docs/stories/README.md",
    "docs/stories/US-105-harness-v1-implementation/design.md",
    "docs/stories/US-105-harness-v1-implementation/execplan.md",
    "docs/stories/US-105-harness-v1-implementation/overview.md",
    "docs/stories/US-105-harness-v1-implementation/validation.md",
    "docs/stories/US-111-v1-phase6-capability-evaluation/design.md",
    "docs/stories/US-111-v1-phase6-capability-evaluation/execplan.md",
    "docs/stories/US-111-v1-phase6-capability-evaluation/overview.md",
    "docs/stories/US-111-v1-phase6-capability-evaluation/validation.md",
    "docs/stories/US-112-v1-phase7-portability-release-proof/design.md",
    "docs/stories/US-112-v1-phase7-portability-release-proof/execplan.md",
    "docs/stories/US-112-v1-phase7-portability-release-proof/overview.md",
    "docs/stories/US-112-v1-phase7-portability-release-proof/validation.md",
    "docs/templates/agent-map.md",
    "docs/templates/high-risk-story/execplan.md",
    "docs/templates/high-risk-story/validation.md",
    "docs/templates/story.md",
    "docs/templates/validation-report.md",
    "release/contracts/v1/path-dispositions.json",
    "release/contracts/v1/schemas/build-receipt-v1.schema.json",
    "release/contracts/v1/schemas/phase7-release-proof-v1.schema.json",
    "scripts/capture-v1-build-receipt.sh",
    "scripts/capture_v1_build_receipt.py",
    "scripts/finalize_v1_build_receipt.py",
    "scripts/install-harness-v1.ps1",
    "scripts/install-harness-v1.sh",
    "scripts/prepare-v1-phase7-test-release.py",
    "scripts/README.md",
    "scripts/run_v1_phase7_execution_proof.py",
    "scripts/capture-v1-phase6-warm-v0.py",
    "scripts/harness-install-files.txt",
    "scripts/validate-premerge.sh",
    "scripts/v1_build_receipt_common.py",
    "scripts/v1_artifact_provenance.py",
    "scripts/verify-v1-build-receipts.sh",
    "scripts/verify-v1-phase6-evidence.sh",
    "scripts/verify-v1-phase7-release-proof.sh",
    "scripts/verify-v1-phase7-execution-proof.sh",
    PHASE5_VERIFIER_COMPATIBILITY_PATH,
    "scripts/verify_v1_phase1_contracts.py",
    "scripts/verify_v1_phase2_core.py",
    "scripts/verify_v1_phase3_recovery.py",
    "scripts/verify_v1_phase6_evidence.py",
    "scripts/verify_v1_build_receipts.py",
    "scripts/verify_v1_attestation_workflow.py",
    "scripts/verify_v1_phase7_release_proof.py",
    "scripts/verify_v1_phase7_execution_proof.py",
    "tests/evals/test-v1-phase6-evidence.sh",
    PHASE5_FORWARDING_COMPATIBILITY_PATH,
    "tests/evals/v1-phase6/README.md",
    "tests/evals/v1-phase6/baseline-lock.json",
    "tests/evals/v1-phase6/evidence/index.json",
    "tests/evals/v1-phase6/schemas/baseline-lock.schema.json",
    "tests/evals/v1-phase6/schemas/candidate-result.schema.json",
    "tests/evals/v1-phase6/schemas/candidate-subject.schema.json",
    "tests/evals/v1-phase6/schemas/comparison-report.schema.json",
    "tests/evals/v1-phase6/schemas/condition-lock.schema.json",
    "tests/evals/v1-phase6/schemas/evidence-index.schema.json",
    "tests/evals/v1-phase6/schemas/intervention-log.schema.json",
    "tests/evals/v1-phase6/schemas/lane-assignment.schema.json",
    "tests/evals/v1-phase6/schemas/packet-manifest.schema.json",
    "tests/evals/v1-phase6/schemas/prompt-authentication.schema.json",
    "tests/evals/v1-phase6/schemas/signature.schema.json",
    "tests/evals/v1-phase6/schemas/warm-v0-capture.schema.json",
    "tests/fixtures/v1-phase2/README.md",
    "tests/fixtures/v1-phase2/current-core-payload-index.json",
    "tests/fixtures/v1-phase2/current-core-payload-index.signatures.json",
    "tests/fixtures/v1-phase2/historical-phase1-story.md",
    "tests/fixtures/v1-phase7/.gitattributes",
    "tests/fixtures/v1-phase7/artifacts/harness-linux-arm64",
    "tests/fixtures/v1-phase7/artifacts/harness-linux-arm64.sha256",
    "tests/fixtures/v1-phase7/artifacts/harness-linux-x64",
    "tests/fixtures/v1-phase7/artifacts/harness-linux-x64.sha256",
    "tests/fixtures/v1-phase7/artifacts/harness-macos-arm64",
    "tests/fixtures/v1-phase7/artifacts/harness-macos-arm64.sha256",
    "tests/fixtures/v1-phase7/artifacts/harness-macos-x64",
    "tests/fixtures/v1-phase7/artifacts/harness-macos-x64.sha256",
    "tests/fixtures/v1-phase7/artifacts/harness-windows-x64.exe",
    "tests/fixtures/v1-phase7/artifacts/harness-windows-x64.exe.sha256",
    "tests/fixtures/v1-phase7/phase7-release-proof.json",
    "tests/fixtures/v1-phase7/repositories/bridge/legacy/bridge-record.txt",
    "tests/fixtures/v1-phase7/repositories/brownfield/existing.txt",
    "tests/fixtures/v1-phase7/repositories/crlf/line-endings.txt",
    "tests/fixtures/v1-phase7/repositories/custom-update/.harness/custom-update.txt",
    "tests/fixtures/v1-phase7/repositories/docs-only/docs/guide.md",
    "tests/fixtures/v1-phase7/repositories/fresh/README.md",
    "tests/fixtures/v1-phase7/repositories/lf/line-endings.txt",
    "tests/fixtures/v1-phase7/repositories/monorepo/apps/web/README.md",
    "tests/fixtures/v1-phase7/repositories/nested-instructions/packages/api/AGENTS.md",
    "tests/fixtures/v1-phase7/repositories/spaces-unicode/docs/Release notes/你好.md",
    "tests/release/test-v1-phase7-release-proof.sh",
    "tests/release/schemas/phase7-execution-proof-v1.schema.json",
    "tests/release/test-install-harness-v1-destination.ps1",
    "tests/release/test-install-harness-v1-windows-unsupported.ps1",
    "tests/release/test-v1-phase7-execution-proof.sh",
    "tests/release/test-v1-build-receipt-workflow.sh",
    "tests/release/test-v1-build-receipts.sh",
    "tests/release/test-v1-artifact-provenance.sh",
    "tests/release/test-v1-attestation-workflow.sh",
    "tests/release/test_v1_artifact_provenance.py",
    "tests/release/test_v1_build_receipts.py",
}
FORBIDDEN_PHASE6_FILENAMES = {
    "harness.db",
    "harness.db-wal",
    "harness.db-shm",
    "standalone-backup.sqlite",
    "archive.age",
    "archive.bin",
}
PHASE7_INTAKE_CHANGESET = (
    ROOT / ".harness/changesets/harness_v1_phase7_00_intake.changeset.jsonl"
)
PHASE7_STORY_CHANGESET = (
    ROOT / ".harness/changesets/harness_v1_phase7_01_story.changeset.jsonl"
)
PHASE7_PROOF_CONTRACT_CHANGESET = (
    ROOT
    / ".harness/changesets/harness_v1_phase7_02_proof_contract.changeset.jsonl"
)
PHASE7_BUILD_RECEIPT_CHANGESET = (
    ROOT
    / ".harness/changesets/harness_v1_phase7_03_build_receipts.changeset.jsonl"
)
PHASE7_EXECUTION_PROOF_CHANGESET = (
    ROOT
    / ".harness/changesets/harness_v1_phase7_04_execution_proof.changeset.jsonl"
)
PHASE7_REVIEW_CORRECTION_CHANGESET = (
    ROOT
    / ".harness/changesets/harness_v1_phase7_05_review_corrections.changeset.jsonl"
)
PHASE7_SECOND_CORRECTION_CHANGESET = (
    ROOT
    / ".harness/changesets/harness_v1_phase7_06_cross_binding_corrections.changeset.jsonl"
)
PHASE7_ATTESTATION_CHANGESET = (
    ROOT / ".harness/changesets/harness_v1_phase7_07_github_attestation.changeset.jsonl"
)
PHASE7_WINDOWS_COMPILE_FIX_CHANGESET = (
    ROOT / ".harness/changesets/harness_v1_phase7_08_windows_compile_fix.changeset.jsonl"
)
PHASE7_WINDOWS_REFUSAL_CAPTURE_CHANGESET = (
    ROOT
    / ".harness/changesets/harness_v1_phase7_09_windows_refusal_capture.changeset.jsonl"
)
PHASE7_DECISION_ID = "0016-phase6-framework-acceptance-and-phase7-opening"
PHASE7_STORY_ID = "US-112"
PHASE7_INTAKE_UID = "ink_b3b36388c90ab25b8d5f518a0306d0a6"
PHASE7_DECISION_VERIFY_COMMAND = "tests/docs/test-doc-contracts.sh"
PHASE7_STORY_VERIFY_COMMAND = (
    "tests/docs/test-doc-contracts.sh && "
    "scripts/verify-v1-phase6-evidence.sh --framework-only"
)
PHASE7_PROOF_VERIFY_COMMAND = (
    "tests/release/test-v1-phase7-release-proof.sh && "
    "scripts/verify-v1-phase6-evidence.sh --framework-only"
)
PHASE7_PROOF_EVIDENCE = (
    "Fixture-only Phase 7 proof-contract candidate 73d4ec7 passed focused and "
    "adversarial verification, trust-enabled full premerge integration, and "
    "independent rereview. No real Phase 6 P0-P7 or Phase 7 five-platform "
    "evidence is recorded; all such evidence remains pending, and acceptance, "
    "tag, publish, signing, and promotion remain blocked."
)
PHASE7_PROOF_TRACE_UID = "trc_84dd40dc582ff69a980492f2288b81b2"
PHASE7_PROOF_TRACE_SUMMARY = (
    "Completed the bounded Phase 7 fixture-only proof-contract slice and "
    "integrated its fail-closed verification"
)
PHASE7_PROOF_RECORD_SHA256 = (
    "c8eaf2ad197bd0b26afdefb4af1c1efafc05a5704ff3b5c16a16bc1303f1b883",
    "5c3e500371ab88e09f2fa8f1a9e238cc999eca8d035645ef82a8381ab230929e",
    "158b209edbc95f30701ac492eae03b173b547ea9651afed052cab41b5350ad5f",
)
PHASE7_BUILD_RECEIPT_RECORD_SHA256 = (
    "93af80461ce10d9f378ebefa1fcd0f34bb3b0faf209d16be049ab2c6a37bd3b7",
    "594114bad088b5c8b5ad82e6d70524bf6d2dab10d98b691d387e2b19b342e23a",
    "a31be10e72b6d4da8349c7e5e35fd15a6fee443b1e0fdc8f5860a90b13784862",
    "3f6237d2cd7fa8f335bf3161f144f17ec585e72cdac31fe585b30f48f7672ef7",
)
PHASE7_BUILD_RECEIPT_VERIFY_COMMAND = (
    "tests/release/test-v1-build-receipts.sh && "
    "tests/release/test-v1-build-receipt-workflow.sh && "
    "tests/release/test-v1-phase7-release-proof.sh && "
    "scripts/verify-v1-phase6-evidence.sh --framework-only"
)
PHASE7_BUILD_RECEIPT_EVIDENCE = (
    "Reviewed build-receipt infrastructure candidate b04753e passed local "
    "macOS arm64 native capture, focused adversaries, cross-platform/security "
    "review, and trust-enabled full premerge. Remote five-runner execution has "
    "not occurred; installer, full direct-binary, authenticated provenance, "
    "Phase 6 live P0-P7, platform acceptance, Phase 7 acceptance, tag, publish, "
    "signing, promotion, and Phase 8 remain pending or blocked."
)
PHASE7_EXECUTION_VERIFY_COMMAND = (
    "tests/release/test-v1-phase7-execution-proof.sh && "
    "tests/release/test-v1-build-receipts.sh && "
    "tests/release/test-v1-build-receipt-workflow.sh && "
    "tests/release/test-v1-phase7-release-proof.sh && "
    "scripts/verify-v1-phase6-evidence.sh --framework-only"
)
PHASE7_EXECUTION_EVIDENCE = (
    "The locally implementable Phase 7 execution candidate passed checksum/"
    "platform preflight, signed test-fixture install/update/scaffold, all-six-"
    "command ten-fixture normalized equivalence, focused build/release/workflow "
    "regressions, and framework-only Phase 6 verification. The no-trust "
    "premerge gate passed Phases 1-4, then stopped at the required external "
    "Phase 5 trust boundary. No remote five-runner or PowerShell execution occurred; "
    "artifact provenance, safe Windows mutation, Phase 6 live P0-P7, platform "
    "acceptance, Phase 7 acceptance, tag, publish, signing, promotion, and "
    "Phase 8 remain pending or blocked."
)
PHASE7_EXECUTION_TRACE_UID = "trc_6ab48fb2c5074f9e968949bf72df4a31"
PHASE7_EXECUTION_TRACE_SUMMARY = (
    "Completed the locally implementable Phase 7 authenticated execution proof "
    "slice without platform acceptance or promotion"
)
PHASE7_EXECUTION_RECORD_SHA256 = (
    "d12d2f0c331b412f0ce118d3205f00a3b5a29a60c374292c5ffe105a9e091a47",
    "c8801063a20e9ac9e14e017412979aaff0bd2a213c3d07852eebdd7d1785f5cc",
    "a59910e7f735770a2bea06e88ea9f1d91689e98ba368e8b254282c9cbe5ed9a5",
    "ce21e3f34f025684d1c0f263ebbc76b5bac3119bdfbb20a3447c1d6d4f2be8cc",
)
PHASE7_REVIEW_VERIFY_COMMAND = PHASE7_EXECUTION_VERIFY_COMMAND
PHASE7_REVIEW_EVIDENCE = (
    "The reviewed Phase 7 correction candidate rejects linked installer "
    "destination roots/components, binds exact-five receipts to independently "
    "resolved candidate and workflow Git identities, recomputes fixture and "
    "collection digests from closed normalized payloads, and scopes diagnostics "
    "to sentinel pushes on refactor/harness-v1. Unix local execution passes; "
    "Windows remains controlled-unsupported-before-mutation and five-platform "
    "equivalence remains pending. No remote workflow or PowerShell execution "
    "occurred; Phase 6 live P0-P7, provenance, platform acceptance, Phase 7 "
    "acceptance, promotion, and Phase 8 remain pending or blocked."
)
PHASE7_REVIEW_TRACE_UID = "trc_546a6759ac9be2d6c0ee44d1d0811cff"
PHASE7_REVIEW_TRACE_SUMMARY = (
    "Corrected reviewed Phase 7 installer containment identity and Windows "
    "evidence defects without acceptance or promotion"
)
PHASE7_REVIEW_RECORD_SHA256 = (
    "343269ff4c9b64d80bbfc0dd977b2b0489eefcc6809c9d6121243bebfb2e519b",
    "16f10dcb4bcb7b92ea878f7f23d9cf5f75f8397fc25e969a5fa4da098177c108",
    "0fefc1d5e551d119b051a9229a6d924c07cce8930ec6d78ceb0367bbc7837892",
    "2024395d2fca271e70ba4289ffb72c4371b814ec0f718fb5ab11b187556e5626",
)
PHASE7_SECOND_CORRECTION_VERIFY_COMMAND = PHASE7_EXECUTION_VERIFY_COMMAND
PHASE7_SECOND_CORRECTION_EVIDENCE = (
    "The second reviewed Phase 7 correction removes the unconditional failing "
    "promotion job, makes repository identity mismatches fail explicitly, binds "
    "every exact-five execution proof to its independently verified build receipt "
    "platform/target/runner/artifact-name/SHA-256 tuple, and records PowerShell "
    "publication as controlled-unsupported after authentication and before "
    "destination mutation. Focused execution/build/workflow/release tests and "
    "workspace fmt/test/clippy pass locally. The no-trust premerge reached the "
    "required external Phase 5 registry boundary after Phases 1-4 passed. No "
    "Windows runner or remote workflow executed; Phase 6 live P0-P7, provenance, "
    "Windows safe publication, five-platform equivalence, platform acceptance, "
    "Phase 7 acceptance, release authority, promotion, and Phase 8 remain pending "
    "or blocked."
)
PHASE7_SECOND_CORRECTION_TRACE_UID = "trc_9d8e7f645e4c4b7186a2c14f430612ab"
PHASE7_SECOND_CORRECTION_TRACE_SUMMARY = (
    "Corrected Phase 7 diagnostic authority build cross-binding and Windows "
    "publication claims"
)
PHASE7_SECOND_CORRECTION_RECORD_SHA256 = (
    "2d8b588fd46aebb11d33cbcd23cd8e0f1a38d2ff1e30a4b74dbe31b0652a1d72",
    "23f163cf02b5b8ee34579325c47443077be800d1df87fcd6d00113ff6a4f65d5",
    "43119769ae9952c3b7d795dbaef87ca86d6b597740403eac0639759ab0bef682",
    "f531132ab2e3261b9b6e527ea464cc1c6b1c53a94998852d8afa8de37e2ea128",
)
PHASE7_ATTESTATION_VERIFY_COMMAND = (
    "tests/release/test-v1-artifact-provenance.sh && "
    "tests/release/test-v1-attestation-workflow.sh && "
    "tests/release/test-v1-build-receipts.sh && "
    "tests/release/test-v1-build-receipt-workflow.sh && "
    "tests/release/test-v1-phase7-execution-proof.sh && "
    "tests/release/test-v1-phase7-release-proof.sh && "
    "scripts/verify-v1-phase6-evidence.sh --framework-only"
)
PHASE7_ATTESTATION_EVIDENCE = (
    "The GitHub provenance continuation pins actions/attest-build-provenance "
    "v3.2.0 to verified commit 96278af6caaf10aea03fd8d33a09a777ca52d62f and "
    "pins privileged artifact download v8.0.1 to 3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c "
    "and bundle upload v7.0.1 to 043fb46d1a93c77aae656e7c1c64a875d1fc6a0a, "
    "and orders exact-five read-only build, isolated attestation, and read-only "
    "verify/execute jobs through immutable artifact handoffs. Only that non-executing "
    "three-action pinned job receives OIDC and attestation writes. Verification uses "
    "one exact certificate-identity mode plus repository, signer/source digest, "
    "source ref, artifact name/digest, event, runner, and transparency-log binding "
    "before execution. Every platform invokes finalization, execution proof, and "
    "receipt verification through the setup-python output. Capture and finalization "
    "disable bytecode before repository-local imports and the workflow exports "
    "PYTHONDONTWRITEBYTECODE=1, so invoking receipt code cannot self-invalidate the "
    "clean candidate check with untracked Python caches. Candidate subprocess "
    "environments are reconstructed from a minimal launch/temp/locale/Windows "
    "allowlist plus four explicit trusted HARNESS_V1 bindings; GitHub command-file "
    "channels, Actions runtime/OIDC variables, tokens, Python injection, home, and "
    "cache state are absent. Build collectors repeat verification read-only and "
    "cross-bind the retained bundle and bounded verification record to the existing "
    "platform/target/runner/artifact-name/SHA-256 tuple. Real-CLI, static, and "
    "adversarial tests cover conflicting flags, missing or substituted attestations "
    "and privileged actions, identities, permissions, Python selection, environment "
    "injection, ordering, handoff, and authority overclaim. No remote workflow or "
    "Windows runner executed; Phase 6 live P0-P7, Windows safe publication/mutation, "
    "five-platform semantic equivalence, platform acceptance, Phase 7 acceptance, "
    "production signing, promotion, and Phase 8 remain pending or blocked."
)
PHASE7_ATTESTATION_TRACE_UID = "trc_4f681bb2cc14464eafd382826dc48e51"
PHASE7_ATTESTATION_TRACE_SUMMARY = (
    "Implemented verified GitHub Sigstore provenance gates for Phase 7 native "
    "diagnostic artifacts"
)
PHASE7_ATTESTATION_RECORD_SHA256 = (
    "4739ff91951ffaaf67a505321d2081917db0885718429d6bace12bc818697645",
    "f7ee28f81387aa34b424b89faa6133c0ab6680350b75e4014112fcb839184e6b",
    "4ffef19e17e80ca19d91655b4073ed2f80f1e38fe93a93e40ba1620827b81908",
    "08d1ca046de6cf76faf70a61fae44733c7fa1b7c0b523e5568743b69db1e700e",
)
PHASE7_WINDOWS_COMPILE_FIX_TRACE_UID = "trc_8e53b06c09d047f197fd376f2ce5a6a1"
PHASE7_WINDOWS_COMPILE_FIX_TRACE_SUMMARY = (
    "Corrected the Phase 7 Windows journal-validation cfg compile leak without "
    "enabling mutation"
)
PHASE7_WINDOWS_COMPILE_FIX_RECORD_SHA256 = (
    "5e2854b86d1817a23064c9444cfc88ca0f21a94d18a942613e3090c5675e27c9",
    "33329265db6a9b650ec7424c77a4669ff69090070c5f14306d460d7f8281acab",
)
PHASE7_WINDOWS_REFUSAL_CAPTURE_TRACE_UID = "trc_472743323f88203ddbbf72ab150c6bbf"
PHASE7_WINDOWS_REFUSAL_CAPTURE_TRACE_SUMMARY = (
    "Corrected the Windows refusal test harness without weakening installer refusal"
)
PHASE7_WINDOWS_REFUSAL_CAPTURE_RECORD_SHA256 = (
    "1cf34f45a8fd079d7d6ef5cc09e3aaa20b42f637fd0baa1974e78f05c023ffea",
    "d69b82758c2a0a2161ad07fcc70127004928bda34279548eecfdea9fa2a08b63",
)
PHASE7_BUILD_RECEIPT_TRACE_UIDS = (
    "trc_1af4542310616a192351f13e21302f03",
    "trc_5273b3afc47ea2ac942889f1b60cf6ce",
)
PHASE7_BUILD_RECEIPT_TRACE_SEMANTICS = (
    {
        "task_summary": "Implemented reviewed Phase 7 immutable native build-receipt infrastructure without promotion",
        "actions_taken": [
            "implemented closed native build receipt schema and exact byte verifier",
            "wired five native CI runners and exact collection",
            "separated candidate SHA from executing workflow SHA",
            "restricted candidates to approved branch ancestry",
            "removed persisted checkout credentials",
            "added shell-input and Windows collection-root hardening",
            "ran local native capture and independent reviews",
            "ran trust-enabled full premerge",
        ],
        "decisions_made": [
            "record candidate source and executing workflow as separate immutable identities",
            "permit only candidates reachable from origin/refactor/harness-v1",
            "keep receipts checksum-only-unattested and every release authority false",
            "do not dispatch or mutate remote state without separate authorization",
        ],
        "errors": [
            "initial review rejected false workflow identity evidence",
            "review rejected arbitrary ref execution with stored checkout credentials",
            "review rejected direct candidate_ref shell interpolation",
            "empty temporary owner registry correctly failed full validation",
        ],
        "harness_friction": "Independent review found candidate/workflow identity conflation, unrestricted ref reachability, persisted checkout credentials, and shell interpolation; all were corrected before integration. Full validation requires the existing external owner registry and rejects an empty placeholder.",
        "notes": "US-112 remains in_progress with every proof flag zero. Local macOS arm64 artifact SHA-256 babe4fdca008d6ca82aee420d9d266468ea22dec6000865482a5f0fdbf26b27d is diagnostic only. No push, dispatch, tag, release, publish, signing, attestation, promotion, or Phase 8 action occurred.",
    },
    {
        "task_summary": "Verified Phase 7 build-receipt slice after corrections",
        "actions_taken": [
            "reproduced focused adversaries",
            "captured and verified native macOS arm64 receipt",
            "completed security rereview",
            "completed cross-platform audit",
            "completed trust-enabled full premerge",
        ],
        "decisions_made": [
            "accept reviewed infrastructure only",
            "retain every proof flag at zero",
            "defer remote five-runner proof and all promotion authority",
        ],
        "errors": [
            "empty placeholder registry failed as designed",
            "external authorized registry was required for the successful full gate",
        ],
        "harness_friction": "Security review corrected workflow identity, branch reachability, credential persistence, and shell interpolation before integration; cross-platform review then pinned the collector root.",
        "notes": "Detailed verification trace. Exact duration_seconds and token_estimate are unavailable because this continuation resumed after a process crash and the session does not expose stable end-to-end measurements. Candidate b04753e is reviewed; macOS artifact digest is diagnostic; no remote mutation occurred.",
    },
)
PHASE7_PROOF_TRACE_ACTIONS = (
    "implemented the closed fixture-only candidate and five-platform placeholder contract",
    "bound V1 harness artifact identity and Cargo.lock build input",
    "added focused digest identity promotion and schema-override adversaries",
    "corrected platform-mode and semantic-identity bypasses after review",
    "integrated the thirteenth schema and exact Phase 6 compatibility boundaries",
    "integrated the durable changeset through the exact Phase 3 protected-path boundary",
    "ran focused framework Rust documentation workflow and trust-enabled full-premerge validation",
    "incorporated independent rereview findings",
)
PHASE7_PROOF_TRACE_DECISIONS = (
    "keep this evidence fixture-only and every Phase 6 and Phase 7 live result pending",
    "use the V1 harness and harness.exe artifact identity while retaining the V0 bridge as separate",
    "bind the locked V1 build input to Cargo.lock",
    "do not change production workflows or authorize tags publishing signing release or promotion",
    "leave US-112 in_progress with unit integration e2e and platform proof flags all zero",
    "use exact changeset path and canonical record pins rather than broadening historical boundaries",
)
PHASE7_PROOF_TRACE_NOTES = (
    "Detailed trace for the bounded proof-contract slice only. The isolated CLI "
    "row resolves the existing Phase 7 intake recorded as intake 9 in its "
    "originating run to stable UID ink_b3b36388c90ab25b8d5f518a0306d0a6. "
    "US-112 remains in_progress with every proof flag zero; real Phase 6 P0-P7 "
    "and Phase 7 five-platform evidence remains pending. Exact duration and "
    "token values are unavailable because this session does not expose stable "
    "end-to-end measurements."
)
PHASE7_PROOF_TRACE_FRICTION = (
    "The default Harness state could not be used because it contained "
    "Symphony-owned records; durable evidence required an isolated replay "
    "database. Review also exposed fail-open Phase 7 mode and identity "
    "relabeling paths, the protected forwarding fixture required an exact OID "
    "pin rather than a broad allowance, and CLI compare-and-set mode cannot "
    "combine proof or evidence updates. Rebuild row numbers differ from the "
    "originating database, so semantic validation must pin the stable intake "
    "UID. Full integration also required one exact Phase 3 changeset-path "
    "allowance."
)


class VerificationError(RuntimeError):
    pass


def check(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def proof(label: str, function: Callable[[], None]) -> None:
    function()
    print(f"Phase 6 proof passed: {label}")


def run(arguments: list[str], *, cwd: Path = ROOT, input_bytes: bytes | None = None) -> bytes:
    environment = dict(os.environ)
    for name in list(environment):
        if name.startswith("GIT_") or name.startswith("HARNESS_PHASE"):
            environment.pop(name, None)
    environment.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_OPTIONAL_LOCKS": "0",
            "LC_ALL": "C",
        }
    )
    result = subprocess.run(
        arguments,
        cwd=cwd,
        input=input_bytes,
        capture_output=True,
        check=False,
        env=environment,
    )
    if result.returncode != 0:
        raise VerificationError(
            f"command failed ({result.returncode}): {' '.join(arguments)}"
        )
    return result.stdout


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in pairs:
        if key in document:
            raise VerificationError(f"duplicate JSON object key: {key}")
        document[key] = value
    return document


def strict_json_loads(payload: str) -> Any:
    return json.loads(payload, object_pairs_hook=reject_duplicate_keys)


def load_json(path: Path) -> Any:
    try:
        return strict_json_loads(path.read_text(encoding="utf-8"))
    except VerificationError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise VerificationError(f"cannot load closed JSON record: {path}") from error


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise VerificationError(f"cannot load closed JSONL record: {path}") from error
    check(lines, f"closed JSONL record is empty: {path}")
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        check(line.strip() == line and line, f"blank or padded JSONL line: {path}:{line_number}")
        try:
            record = strict_json_loads(line)
        except (VerificationError, json.JSONDecodeError) as error:
            raise VerificationError(
                f"cannot load closed JSONL record: {path}:{line_number}"
            ) from error
        check(isinstance(record, dict), f"JSONL operation is not an object: {path}:{line_number}")
        records.append(record)
    return records


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
    except OSError as error:
        raise VerificationError(f"cannot hash evidence artifact: {path}") from error
    return digest.hexdigest()


def canonical_bytes(document: dict[str, Any], omitted: str | None = None) -> bytes:
    content = dict(document)
    if omitted is not None:
        content.pop(omitted, None)
    return json.dumps(
        content, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def canonical_digest(document: dict[str, Any], omitted: str) -> str:
    return sha256_bytes(canonical_bytes(document, omitted))


def schema(name: str) -> dict[str, Any]:
    return load_json(SCHEMAS / f"{name}.schema.json")


def type_matches(instance: Any, expected: str) -> bool:
    return {
        "object": isinstance(instance, dict),
        "array": isinstance(instance, list),
        "string": isinstance(instance, str),
        "integer": isinstance(instance, int) and not isinstance(instance, bool),
        "boolean": isinstance(instance, bool),
        "null": instance is None,
    }.get(expected, False)


def validate(instance: Any, contract: dict[str, Any], location: str = "$") -> None:
    if "const" in contract:
        check(instance == contract["const"], f"{location}: const mismatch")
    if "enum" in contract:
        check(instance in contract["enum"], f"{location}: value outside enum")
    expected = contract.get("type")
    if expected is not None:
        expected_types = expected if isinstance(expected, list) else [expected]
        check(
            any(type_matches(instance, item) for item in expected_types),
            f"{location}: wrong JSON type",
        )
    if isinstance(instance, dict):
        required = set(contract.get("required", []))
        check(required <= set(instance), f"{location}: missing {sorted(required - set(instance))}")
        properties = contract.get("properties", {})
        if contract.get("additionalProperties") is False:
            check(
                set(instance) <= set(properties),
                f"{location}: unknown fields {sorted(set(instance) - set(properties))}",
            )
        for key, value in instance.items():
            if key in properties:
                validate(value, properties[key], f"{location}.{key}")
    if isinstance(instance, list):
        if "minItems" in contract:
            check(len(instance) >= contract["minItems"], f"{location}: too few items")
        if "maxItems" in contract:
            check(len(instance) <= contract["maxItems"], f"{location}: too many items")
        if contract.get("uniqueItems") is True:
            check(
                all(
                    item not in instance[:index]
                    for index, item in enumerate(instance)
                ),
                f"{location}: duplicate array items",
            )
        if "items" in contract:
            for index, value in enumerate(instance):
                validate(value, contract["items"], f"{location}[{index}]")
    if isinstance(instance, str):
        if "minLength" in contract:
            check(len(instance) >= contract["minLength"], f"{location}: string is empty")
        if "pattern" in contract:
            check(re.fullmatch(contract["pattern"], instance) is not None, f"{location}: pattern mismatch")
    if isinstance(instance, int) and not isinstance(instance, bool):
        if "minimum" in contract:
            check(instance >= contract["minimum"], f"{location}: below minimum")
        if "maximum" in contract:
            check(instance <= contract["maximum"], f"{location}: above maximum")


def parse_time(value: str, field: str) -> datetime:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as error:
        raise VerificationError(f"{field}: invalid strict UTC timestamp") from error
    return parsed


def relative_name(value: str, field: str) -> PurePosixPath:
    candidate = PurePosixPath(value)
    check(not candidate.is_absolute(), f"{field}: absolute path is prohibited")
    check(all(part not in {"", ".", ".."} for part in candidate.parts), f"{field}: traversal is prohibited")
    check(str(candidate) == value and "\\" not in value, f"{field}: path is not canonical POSIX form")
    return candidate


def contained_member(root: Path, value: str, field: str) -> Path:
    relative = relative_name(value, field)
    candidate = root.joinpath(*relative.parts)
    check(candidate.exists() and candidate.is_file() and not candidate.is_symlink(), f"{field}: missing or unsafe member")
    check(candidate.resolve().is_relative_to(root.resolve()), f"{field}: member escaped custody")
    return candidate


def exact_cards(records: list[Any], expected: list[str], location: str) -> None:
    identifiers = [record if isinstance(record, str) else record.get("card_id") for record in records]
    check(identifiers == expected, f"{location}: expected exact ordered cards {expected}, got {identifiers}")


def validate_evidence_references(
    references: list[dict[str, str]], artifact_digests: dict[str, str], location: str
) -> None:
    check(isinstance(references, list) and references, f"{location}: custody evidence must be a non-empty array")
    check(
        all(
            isinstance(reference, dict)
            and set(reference) == {"artifact", "sha256"}
            and isinstance(reference["artifact"], str)
            and isinstance(reference["sha256"], str)
            for reference in references
        ),
        f"{location}: custody evidence must contain exact artifact/digest objects",
    )
    artifacts = [reference["artifact"] for reference in references]
    check(len(artifacts) == len(set(artifacts)), f"{location}: duplicate custody artifact")
    for reference in references:
        check(
            artifact_digests.get(reference["artifact"]) == reference["sha256"],
            f"{location}: evidence is outside exact packet-manifest custody: {reference['artifact']}",
        )


def validate_baseline_lock() -> dict[str, Any]:
    for name in SCHEMA_NAMES:
        definition = schema(name)
        check(definition.get("type") == "object", f"{name} schema must describe an object")
        check(
            definition.get("additionalProperties") is False,
            f"{name} schema must be closed at its root",
        )
        check(isinstance(definition.get("required"), list), f"{name} schema must declare required fields")
    path = EVAL / "baseline-lock.json"
    document = load_json(path)
    validate(document, schema("baseline-lock"), "baseline lock")
    check(document["lock_sha256"] == canonical_digest(document, "lock_sha256"), "baseline lock self-digest mismatch")
    check(document["source_commit"] == BASE_COMMIT, "baseline lock changed accepted source commit")
    check(len(document["protected_git_objects"]) == 4, "baseline lock protected-object set changed")
    check(len(document["pilots"]) == 2, "baseline lock must contain exactly two accepted pilots")
    return document


def git_oid(commit: str, path: str) -> str:
    return run(["git", "rev-parse", f"{commit}:{path}"]).decode("ascii").strip()


def verify_tree_against_worktree(commit: str, root: str) -> None:
    output = run(["git", "ls-tree", "-r", commit, "--", root]).decode("utf-8")
    expected: dict[str, str] = {}
    for line in output.splitlines():
        metadata, path = line.split("\t", 1)
        _, kind, oid = metadata.split(" ")
        check(kind == "blob", f"protected tree contains non-blob member: {path}")
        expected[path] = oid
    actual = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / root).rglob("*")
        if path.is_file() or path.is_symlink()
    }
    check(actual == set(expected), f"Phase 5 protected tree inventory changed under {root}")
    for path, oid in expected.items():
        candidate = ROOT / path
        check(not candidate.is_symlink(), f"Phase 5 protected path became a symlink: {path}")
        current_oid = run(["git", "hash-object", "--no-filters", path]).decode("ascii").strip()
        check(current_oid == oid, f"Phase 5 protected bytes changed: {path}")


def verify_phase5_immutability(lock: dict[str, Any]) -> None:
    compatibility_applied = False
    forwarding_compatibility_applied = False
    for entry in lock["protected_git_objects"]:
        check(git_oid(lock["source_commit"], entry["path"]) == entry["git_oid"], f"frozen Git object mismatch: {entry['path']}")
        if entry["kind"] == "tree":
            verify_tree_against_worktree(lock["source_commit"], entry["path"])
        else:
            path = ROOT / entry["path"]
            check(path.is_file() and not path.is_symlink(), f"protected Phase 5 file missing: {entry['path']}")
            current_oid = run(["git", "hash-object", "--no-filters", entry["path"]]).decode("ascii").strip()
            expected_oid = entry["git_oid"]
            if entry["path"] == PHASE5_VERIFIER_COMPATIBILITY_PATH:
                expected_oid = lock["phase5_verifier_compatibility_git_oid"]
                compatibility_applied = True
            elif entry["path"] == PHASE5_FORWARDING_COMPATIBILITY_PATH:
                expected_oid = PHASE5_FORWARDING_COMPATIBILITY_GIT_OID
                forwarding_compatibility_applied = True
            check(current_oid == expected_oid, f"protected Phase 5 file changed: {entry['path']}")
    check(
        compatibility_applied,
        "Phase 5 verifier compatibility path is outside the frozen protected surface",
    )
    check(
        forwarding_compatibility_applied,
        "Phase 5 forwarding compatibility path is outside the frozen protected surface",
    )
    check(sha256_file(ROOT / "tests/evals/v1-phase5/cards/catalog.json") == lock["card_catalog_sha256"], "Phase 5 card catalog digest changed")
    check(sha256_file(ROOT / "tests/evals/v1-phase5/evidence/index.json") == lock["phase5_evidence_index_sha256"], "Phase 5 evidence index digest changed")
    for pilot in lock["pilots"]:
        root = ROOT / "tests/evals/v1-phase5/evidence" / pilot["pilot_id"]
        check(sha256_file(root / "authentication.json") == pilot["authentication_sha256"], f"{pilot['pilot_id']} authentication changed")
        check(sha256_file(root / "packet-manifest.json") == pilot["packet_manifest_sha256"], f"{pilot['pilot_id']} packet manifest changed")
        check(sha256_file(root / "repository.bundle") == pilot["repository_bundle_sha256"], f"{pilot['pilot_id']} bundle changed")


def changed_paths() -> set[str]:
    tracked = run(
        ["git", "diff", "--name-only", "-z", BASE_COMMIT, "--"]
    ).decode("utf-8").split("\0")
    untracked = run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"]
    ).decode("utf-8").split("\0")
    return {path for path in tracked + untracked if path}


def validate_release_boundary(paths: set[str] | None = None) -> None:
    for path in changed_paths() if paths is None else paths:
        check(
            path in ALLOWED_CHANGED_FILES,
            f"Phase 6 framework crossed its owned-file boundary: {path}",
        )


def self_test_release_boundary() -> None:
    validate_release_boundary(ALLOWED_CHANGED_FILES)
    expect_rejection(
        "unrelated documentation path",
        lambda: validate_release_boundary({"docs/unrelated.md"}),
    )
    expect_rejection(
        "unrelated Harness changeset path",
        lambda: validate_release_boundary(
            {".harness/changesets/unrelated.changeset.jsonl"}
        ),
    )
    expect_rejection(
        "unrelated Phase 7 story path",
        lambda: validate_release_boundary(
            {
                "docs/stories/US-112-v1-phase7-portability-release-proof/"
                "unrelated.md"
            }
        ),
    )
    expect_rejection(
        "unrelated Phase 6 evaluation path",
        lambda: validate_release_boundary(
            {"tests/evals/v1-phase6/unrelated-core.bin"}
        ),
    )
    expect_rejection(
        "unrelated Rust path",
        lambda: validate_release_boundary(
            {"crates/harness-core/tests/unrelated.rs"}
        ),
    )
    expect_rejection(
        "unrelated fixture path",
        lambda: validate_release_boundary(
            {"tests/fixtures/v1-phase2/unrelated.json"}
        ),
    )


def validate_phase7_opening_records(
    intake_records: list[dict[str, Any]],
    story_records: list[dict[str, Any]],
) -> None:
    check(
        [record.get("op") for record in intake_records]
        == ["changeset.header", "intake.add"],
        "Phase 7 intake changeset operation sequence changed",
    )
    check(
        intake_records[0]
        == {
            "base_schema_version": 13,
            "op": "changeset.header",
            "run_id": "harness_v1_phase7_00_intake",
            "version": 1,
        },
        "Phase 7 intake changeset header changed",
    )
    intake = intake_records[1]
    check(
        set(intake) == {"op", "payload", "uid", "version"}
        and intake["version"] == 2
        and isinstance(intake["uid"], str)
        and intake["uid"].startswith("ink_"),
        "Phase 7 intake envelope changed",
    )
    intake_payload = intake.get("payload")
    check(isinstance(intake_payload, dict), "Phase 7 intake payload is not an object")
    check(
        intake_payload.get("story_id") == PHASE7_STORY_ID
        and intake_payload.get("risk_lane") == "high_risk"
        and intake_payload.get("input_type") == "spec_slice",
        "Phase 7 intake no longer opens the high-risk US-112 spec slice",
    )
    intake_notes = intake_payload.get("notes")
    check(
        isinstance(intake_notes, str)
        and "live P0-P7 experiments" in intake_notes
        and "remain blocked" in intake_notes,
        "Phase 7 intake no longer preserves the deferred live-evidence gate",
    )

    expected_operations = [
        "changeset.header",
        "decision.add",
        "story.add",
        "story.hierarchy.add",
        "story.update",
        "decision.verify",
        "story.verify",
        "trace.add",
        "story.verify",
        "story.verify",
    ]
    check(
        [record.get("op") for record in story_records] == expected_operations,
        "Phase 7 story changeset operation sequence changed",
    )
    check(
        story_records[0]
        == {
            "base_schema_version": 13,
            "op": "changeset.header",
            "run_id": "harness_v1_phase7_01_story",
            "version": 1,
        },
        "Phase 7 story changeset header changed",
    )

    decision = story_records[1]
    decision_payload = decision.get("payload")
    check(
        decision.get("id") == PHASE7_DECISION_ID
        and decision.get("version") == 1
        and isinstance(decision_payload, dict)
        and decision_payload.get("status") == "accepted"
        and decision_payload.get("doc_path")
        == "docs/decisions/0016-phase6-framework-acceptance-and-phase7-opening.md",
        "Phase 7 opening decision operation changed",
    )
    check(
        decision_payload.get("verify_command") == PHASE7_DECISION_VERIFY_COMMAND,
        "Phase 7 decision verification command changed",
    )
    decision_notes = decision_payload.get("notes")
    check(
        isinstance(decision_notes, str)
        and "not its custody/trust/live-card requirements" in decision_notes,
        "Phase 7 decision operation no longer preserves Decision 0015",
    )

    story_add = story_records[2]
    story_add_payload = story_add.get("payload")
    check(
        story_add.get("id") == PHASE7_STORY_ID
        and story_add.get("version") == 1
        and isinstance(story_add_payload, dict)
        and story_add_payload.get("risk_lane") == "high_risk"
        and story_add_payload.get("contract_doc")
        == "docs/stories/US-112-v1-phase7-portability-release-proof/overview.md",
        "Phase 7 story creation operation changed",
    )
    check(
        story_add_payload.get("verify_command") == PHASE7_STORY_VERIFY_COMMAND,
        "Phase 7 story verification command changed",
    )
    story_notes = story_add_payload.get("notes")
    check(
        isinstance(story_notes, str)
        and "acceptance, tag, publish, promotion, and Phase 8 remain closed"
        in story_notes,
        "Phase 7 story creation no longer preserves closed release gates",
    )

    hierarchy = story_records[3]
    check(
        hierarchy.get("id") == "US-105"
        and hierarchy.get("payload") == {"child": PHASE7_STORY_ID}
        and hierarchy.get("version") == 1,
        "Phase 7 story hierarchy changed",
    )

    story_update = story_records[4]
    story_update_payload = story_update.get("payload")
    check(
        story_update.get("id") == PHASE7_STORY_ID
        and story_update.get("version") == 1
        and isinstance(story_update_payload, dict),
        "Phase 7 story update envelope changed",
    )
    check(
        set(story_update_payload)
        == {
            "contract_doc",
            "e2e_proof",
            "evidence",
            "integration_proof",
            "platform_proof",
            "status",
            "unit_proof",
            "verify_command",
        },
        "Phase 7 story update fields changed",
    )
    check(
        story_update_payload["status"] == "in_progress"
        and all(
            story_update_payload[field] == 0
            for field in ("unit_proof", "integration_proof", "e2e_proof", "platform_proof")
        )
        and story_update_payload["contract_doc"] is None
        and story_update_payload["verify_command"] is None,
        "Phase 7 story is no longer engineering-only with zero proof",
    )
    opening_evidence = story_update_payload.get("evidence")
    check(
        isinstance(opening_evidence, str)
        and opening_evidence.startswith(
            "Decision 0016 accepts the Phase 6 framework for sequencing"
        )
        and "No executable Phase 7 proof" in opening_evidence
        and "promotion" in opening_evidence,
        "Phase 7 story evidence makes an unsupported acceptance claim",
    )

    check(
        story_records[5].get("id") == PHASE7_DECISION_ID
        and story_records[5].get("payload") == {"result": "pass"},
        "Phase 7 decision verification operation changed",
    )
    story_verify = story_records[6]
    check(
        story_verify.get("id") == PHASE7_STORY_ID
        and isinstance(story_verify.get("payload"), dict)
        and story_verify["payload"].get("result") == "pass",
        "Phase 7 story verification operation changed",
    )
    trace = story_records[7]
    trace_payload = trace.get("payload")
    check(
        trace.get("version") == 2
        and isinstance(trace.get("uid"), str)
        and trace["uid"].startswith("trc_")
        and isinstance(trace_payload, dict)
        and trace_payload.get("story_id") == PHASE7_STORY_ID
        and trace_payload.get("intake_uid") == intake["uid"]
        and trace_payload.get("outcome") == "completed",
        "Phase 7 opening trace no longer binds Intake #9 and US-112",
    )
    trace_notes = trace_payload.get("notes")
    check(
        isinstance(trace_notes, str)
        and "No live pilot, tag, push, publish, release, promotion, or Phase 8 action"
        in trace_notes,
        "Phase 7 opening trace makes an unauthorized external-action claim",
    )
    semantic_verify = story_records[8]
    check(
        semantic_verify.get("id") == PHASE7_STORY_ID
        and isinstance(semantic_verify.get("payload"), dict)
        and semantic_verify["payload"].get("result") == "pass",
        "Phase 7 story was not reverified after the semantic gate was installed",
    )
    command_verify = story_records[9]
    check(
        command_verify.get("id") == PHASE7_STORY_ID
        and isinstance(command_verify.get("payload"), dict)
        and command_verify["payload"].get("result") == "pass",
        "Phase 7 story was not reverified after command pinning was installed",
    )


def self_test_phase7_opening_records(
    intake_records: list[dict[str, Any]],
    story_records: list[dict[str, Any]],
) -> None:
    completed = deepcopy(story_records)
    completed[4]["payload"]["status"] = "implemented"
    expect_rejection(
        "same-filename Phase 7 completion",
        lambda: validate_phase7_opening_records(intake_records, completed),
    )
    proof_claim = deepcopy(story_records)
    proof_claim[4]["payload"]["platform_proof"] = 1
    expect_rejection(
        "same-filename Phase 7 proof claim",
        lambda: validate_phase7_opening_records(intake_records, proof_claim),
    )
    release_operation = deepcopy(story_records)
    release_operation.insert(
        7,
        {
            "id": PHASE7_STORY_ID,
            "op": "story.complete",
            "payload": {},
            "version": 1,
        },
    )
    expect_rejection(
        "same-filename Phase 7 release operation",
        lambda: validate_phase7_opening_records(intake_records, release_operation),
    )
    tag_command = deepcopy(story_records)
    tag_command[2]["payload"]["verify_command"] = "git tag harness-v1-phase7-unauthorized"
    expect_rejection(
        "same-filename Phase 7 tag command",
        lambda: validate_phase7_opening_records(intake_records, tag_command),
    )
    publish_command = deepcopy(story_records)
    publish_command[1]["payload"]["verify_command"] = (
        "gh release create harness-v1-phase7-unauthorized"
    )
    expect_rejection(
        "same-filename Phase 7 publish command",
        lambda: validate_phase7_opening_records(intake_records, publish_command),
    )


def authenticate_phase7_proof_contract_records(
    proof_records: list[dict[str, Any]],
) -> None:
    check(
        tuple(sha256_bytes(canonical_bytes(record)) for record in proof_records)
        == PHASE7_PROOF_RECORD_SHA256,
        "Phase 7 proof-contract changeset record bytes changed",
    )


def validate_phase7_proof_contract_semantics(
    intake_records: list[dict[str, Any]],
    proof_records: list[dict[str, Any]],
) -> None:
    check(
        [record.get("op") for record in proof_records]
        == ["changeset.header", "story.update", "trace.add"],
        "Phase 7 proof-contract changeset operation sequence changed",
    )
    check(
        proof_records[0]
        == {
            "base_schema_version": 13,
            "op": "changeset.header",
            "run_id": "harness_v1_phase7_02_proof_contract",
            "version": 1,
        },
        "Phase 7 proof-contract changeset header changed",
    )
    check(
        len(intake_records) == 2
        and intake_records[1].get("uid") == PHASE7_INTAKE_UID,
        "Phase 7 proof trace no longer targets the existing Intake #9 identity",
    )

    story_update = proof_records[1]
    story_payload = story_update.get("payload")
    check(
        story_update.get("id") == PHASE7_STORY_ID
        and story_update.get("version") == 1
        and isinstance(story_payload, dict),
        "Phase 7 proof-contract story update envelope changed",
    )
    check(
        set(story_payload)
        == {
            "contract_doc",
            "e2e_proof",
            "evidence",
            "integration_proof",
            "platform_proof",
            "status",
            "unit_proof",
            "verify_command",
        },
        "Phase 7 proof-contract story update fields changed",
    )
    check(
        story_payload["status"] == "in_progress"
        and all(
            story_payload[field] == 0
            for field in (
                "unit_proof",
                "integration_proof",
                "e2e_proof",
                "platform_proof",
            )
        )
        and story_payload["contract_doc"] is None
        and story_payload["evidence"] == PHASE7_PROOF_EVIDENCE
        and story_payload["verify_command"] == PHASE7_PROOF_VERIFY_COMMAND,
        "Phase 7 proof-contract story no longer records bounded in-progress evidence",
    )

    trace = proof_records[2]
    trace_payload = trace.get("payload")
    check(
        set(trace) == {"op", "payload", "uid", "version"}
        and trace.get("op") == "trace.add"
        and trace.get("uid") == PHASE7_PROOF_TRACE_UID
        and trace.get("version") == 2
        and isinstance(trace_payload, dict),
        "Phase 7 proof-contract trace envelope changed",
    )
    check(
        set(trace_payload)
        == {
            "actions_taken",
            "agent",
            "created_at",
            "decisions_made",
            "duration_seconds",
            "errors",
            "files_changed",
            "files_read",
            "harness_friction",
            "intake_uid",
            "notes",
            "outcome",
            "recorded_at_unix_ns",
            "story_id",
            "task_summary",
            "token_estimate",
        },
        "Phase 7 proof-contract trace fields changed",
    )
    check(
        trace_payload["task_summary"] == PHASE7_PROOF_TRACE_SUMMARY
        and trace_payload["intake_uid"] == PHASE7_INTAKE_UID
        and trace_payload["story_id"] == PHASE7_STORY_ID
        and trace_payload["agent"] == "codex"
        and trace_payload["outcome"] == "completed"
        and trace_payload["duration_seconds"] is None
        and trace_payload["token_estimate"] is None,
        "Phase 7 proof-contract trace identity, outcome, or unavailable metrics changed",
    )
    trace_lists: dict[str, list[Any]] = {}
    for field in (
        "actions_taken",
        "files_read",
        "files_changed",
        "decisions_made",
        "errors",
    ):
        parsed = strict_json_loads(trace_payload[field])
        check(
            isinstance(parsed, list)
            and parsed
            and all(isinstance(item, str) and item for item in parsed),
            f"Phase 7 proof-contract trace {field} is not a nonempty string list",
        )
        trace_lists[field] = parsed
    check(
        trace_lists["actions_taken"] == list(PHASE7_PROOF_TRACE_ACTIONS)
        and trace_lists["decisions_made"] == list(PHASE7_PROOF_TRACE_DECISIONS)
        and len(trace_lists["errors"]) >= 3
        and "scripts/verify_v1_phase7_release_proof.py" in trace_lists["files_read"]
        and "scripts/verify_v1_phase3_recovery.py" in trace_lists["files_changed"]
        and ".harness/changesets/harness_v1_phase7_02_proof_contract.changeset.jsonl"
        in trace_lists["files_changed"],
        "Phase 7 proof-contract trace changed its closed actions/decisions policy or Detailed quality",
    )
    decisions = "\n".join(trace_lists["decisions_made"])
    check(
        "keep this evidence fixture-only" in decisions
        and "V1 harness and harness.exe artifact identity" in decisions
        and "bind the locked V1 build input to Cargo.lock" in decisions
        and "do not change production workflows" in decisions
        and "proof flags all zero" in decisions,
        "Phase 7 proof-contract trace lost a bounded implementation decision",
    )
    errors = "\n".join(trace_lists["errors"])
    check(
        "Symphony-owned records" in errors
        and "platform-mode and semantic-identity bypasses" in errors
        and "exact Git blob OID compatibility allowance" in errors
        and "frozen Phase 3 boundary" in errors,
        "Phase 7 proof-contract trace lost required errors and friction",
    )
    notes = trace_payload.get("notes")
    friction = trace_payload.get("harness_friction")
    check(
        notes == PHASE7_PROOF_TRACE_NOTES
        and friction == PHASE7_PROOF_TRACE_FRICTION,
        "Phase 7 proof-contract trace changed its closed notes/friction authority policy",
    )


def validate_phase7_proof_contract_records(
    intake_records: list[dict[str, Any]],
    proof_records: list[dict[str, Any]],
) -> None:
    authenticate_phase7_proof_contract_records(proof_records)
    validate_phase7_proof_contract_semantics(intake_records, proof_records)


def self_test_phase7_proof_contract_records(
    intake_records: list[dict[str, Any]],
    proof_records: list[dict[str, Any]],
) -> None:
    digest_drift = deepcopy(proof_records)
    digest_drift[2]["payload"]["created_at"] = "2026-07-18 17:05:15"
    expect_rejection(
        "same-filename Phase 7 proof-contract digest drift",
        lambda: authenticate_phase7_proof_contract_records(digest_drift),
    )
    for status in ("implemented", "completed"):
        completed = deepcopy(proof_records)
        completed[1]["payload"]["status"] = status
        expect_rejection(
            f"same-filename Phase 7 proof-contract {status} status",
            lambda completed=completed: validate_phase7_proof_contract_semantics(
                intake_records, completed
            ),
        )
    for field in (
        "unit_proof",
        "integration_proof",
        "e2e_proof",
        "platform_proof",
    ):
        asserted = deepcopy(proof_records)
        asserted[1]["payload"][field] = 1
        expect_rejection(
            f"same-filename Phase 7 proof-contract {field}",
            lambda asserted=asserted: validate_phase7_proof_contract_semantics(
                intake_records, asserted
            ),
        )
    changed_outcome = deepcopy(proof_records)
    changed_outcome[2]["payload"]["outcome"] = "partial"
    expect_rejection(
        "same-filename Phase 7 proof-contract trace outcome",
        lambda: validate_phase7_proof_contract_semantics(
            intake_records, changed_outcome
        ),
    )
    for label, claim in (
        ("acceptance authority", "Phase 7 acceptance authorized"),
        ("tag authority", "release tag authorized"),
        ("publish authority", "publishing authorized"),
        ("signing authority", "production signing authorized"),
        ("production-promotion authority", "production promotion authorized"),
        ("Phase 8 authority", "Phase 8 opened and authorized"),
    ):
        contradictory = deepcopy(proof_records)
        decisions = strict_json_loads(
            contradictory[2]["payload"]["decisions_made"]
        )
        check(
            decisions == list(PHASE7_PROOF_TRACE_DECISIONS),
            "Phase 7 authority adversary lost the approved safe decisions",
        )
        decisions.append(claim)
        contradictory[2]["payload"]["decisions_made"] = json.dumps(
            decisions, separators=(",", ":")
        )
        expect_rejection(
            f"same-filename Phase 7 proof-contract {label}",
            lambda contradictory=contradictory: validate_phase7_proof_contract_semantics(
                intake_records, contradictory
            ),
        )
    action_claim = deepcopy(proof_records)
    actions = strict_json_loads(action_claim[2]["payload"]["actions_taken"])
    actions.append("published and tagged the Phase 7 release")
    action_claim[2]["payload"]["actions_taken"] = json.dumps(
        actions, separators=(",", ":")
    )
    expect_rejection(
        "same-filename Phase 7 proof-contract action authority",
        lambda: validate_phase7_proof_contract_semantics(
            intake_records, action_claim
        ),
    )
    notes_claim = deepcopy(proof_records)
    notes_claim[2]["payload"]["notes"] += " Phase 8 promotion is authorized."
    expect_rejection(
        "same-filename Phase 7 proof-contract notes authority",
        lambda: validate_phase7_proof_contract_semantics(
            intake_records, notes_claim
        ),
    )
    friction_claim = deepcopy(proof_records)
    friction_claim[2]["payload"]["harness_friction"] += (
        " Production signing is now authorized."
    )
    expect_rejection(
        "same-filename Phase 7 proof-contract friction authority",
        lambda: validate_phase7_proof_contract_semantics(
            intake_records, friction_claim
        ),
    )


def authenticate_phase7_build_receipt_records(
    records: list[dict[str, Any]],
) -> None:
    check(
        tuple(sha256_bytes(canonical_bytes(record)) for record in records)
        == PHASE7_BUILD_RECEIPT_RECORD_SHA256,
        "Phase 7 build-receipt changeset record bytes changed",
    )


def validate_phase7_build_receipt_semantics(
    records: list[dict[str, Any]],
) -> None:
    check(
        [record.get("op") for record in records]
        == ["changeset.header", "story.update", "trace.add", "trace.add"],
        "Phase 7 build-receipt changeset operation sequence changed",
    )
    check(
        records[0]
        == {
            "base_schema_version": 13,
            "op": "changeset.header",
            "run_id": "harness_v1_phase7_03_build_receipts",
            "version": 1,
        },
        "Phase 7 build-receipt changeset header changed",
    )
    story = records[1]
    payload = story.get("payload")
    check(
        story.get("id") == PHASE7_STORY_ID
        and story.get("version") == 1
        and isinstance(payload, dict)
        and payload.get("status") == "in_progress"
        and payload.get("contract_doc") is None
        and all(
            payload.get(field) == 0
            for field in (
                "unit_proof",
                "integration_proof",
                "e2e_proof",
                "platform_proof",
            )
        )
        and payload.get("evidence") == PHASE7_BUILD_RECEIPT_EVIDENCE
        and payload.get("verify_command") == PHASE7_BUILD_RECEIPT_VERIFY_COMMAND,
        "Phase 7 build-receipt story no longer records bounded in-progress evidence",
    )
    traces = records[2:]
    check(
        tuple(trace.get("uid") for trace in traces)
        == PHASE7_BUILD_RECEIPT_TRACE_UIDS,
        "Phase 7 build-receipt trace identities or order changed",
    )
    for trace, approved in zip(traces, PHASE7_BUILD_RECEIPT_TRACE_SEMANTICS):
        trace_payload = trace.get("payload")
        check(
            trace.get("version") == 2
            and isinstance(trace_payload, dict)
            and trace_payload.get("intake_uid") == PHASE7_INTAKE_UID
            and trace_payload.get("story_id") == PHASE7_STORY_ID
            and trace_payload.get("agent") == "codex"
            and trace_payload.get("outcome") == "completed"
            and trace_payload.get("duration_seconds") is None
            and trace_payload.get("token_estimate") is None,
            "Phase 7 build-receipt trace lost stable intake, story, or bounded outcome identity",
        )
        parsed_lists: dict[str, list[str]] = {}
        for field in (
            "actions_taken",
            "files_read",
            "files_changed",
            "decisions_made",
            "errors",
        ):
            values = strict_json_loads(trace_payload.get(field, ""))
            check(
                isinstance(values, list)
                and values
                and all(isinstance(value, str) and value for value in values),
                f"Phase 7 build-receipt trace {field} is not Detailed",
            )
            parsed_lists[field] = values
        check(
            trace_payload["task_summary"] == approved["task_summary"]
            and parsed_lists["actions_taken"] == approved["actions_taken"]
            and parsed_lists["decisions_made"] == approved["decisions_made"]
            and parsed_lists["errors"] == approved["errors"]
            and trace_payload["harness_friction"] == approved["harness_friction"]
            and trace_payload["notes"] == approved["notes"],
            "Phase 7 build-receipt trace changed approved actions, decisions, notes, friction, or authority boundary",
        )
    latest = traces[1]["payload"]
    check(
        latest["recorded_at_unix_ns"] > traces[0]["payload"]["recorded_at_unix_ns"]
        and latest["created_at"] > traces[0]["payload"]["created_at"]
        and latest["task_summary"]
        == PHASE7_BUILD_RECEIPT_TRACE_SEMANTICS[1]["task_summary"]
        and latest["notes"].startswith("Detailed verification trace."),
        "Phase 7 build-receipt latest trace is not the Detailed verification record",
    )


def validate_phase7_build_receipt_records(
    records: list[dict[str, Any]],
) -> None:
    authenticate_phase7_build_receipt_records(records)
    validate_phase7_build_receipt_semantics(records)


def self_test_phase7_build_receipt_records(
    records: list[dict[str, Any]],
) -> None:
    digest_drift = deepcopy(records)
    digest_drift[3]["payload"]["created_at"] = "2026-07-19 01:40:02"
    expect_rejection(
        "same-filename Phase 7 build-receipt digest drift",
        lambda: authenticate_phase7_build_receipt_records(digest_drift),
    )
    completed = deepcopy(records)
    completed[1]["payload"]["status"] = "completed"
    expect_rejection(
        "same-filename Phase 7 build-receipt completed status",
        lambda: validate_phase7_build_receipt_semantics(completed),
    )
    asserted = deepcopy(records)
    asserted[1]["payload"]["platform_proof"] = 1
    expect_rejection(
        "same-filename Phase 7 build-receipt platform proof",
        lambda: validate_phase7_build_receipt_semantics(asserted),
    )
    relinked = deepcopy(records)
    relinked[3]["payload"]["intake_uid"] = "ink_00000000000000000000000000000000"
    expect_rejection(
        "same-filename Phase 7 build-receipt intake relink",
        lambda: validate_phase7_build_receipt_semantics(relinked),
    )
    overclaim = deepcopy(records)
    decisions = strict_json_loads(overclaim[2]["payload"]["decisions_made"])
    decisions.append("Phase 7 acceptance authorized")
    overclaim[2]["payload"]["decisions_made"] = json.dumps(
        decisions, separators=(",", ":")
    )
    expect_rejection(
        "same-filename Phase 7 build-receipt authority overclaim",
        lambda: validate_phase7_build_receipt_semantics(overclaim),
    )
    error_overclaim = deepcopy(records)
    errors = strict_json_loads(error_overclaim[3]["payload"]["errors"])
    errors.append("production release succeeded")
    error_overclaim[3]["payload"]["errors"] = json.dumps(
        errors, separators=(",", ":")
    )
    expect_rejection(
        "same-filename Phase 7 build-receipt errors authority overclaim",
        lambda: validate_phase7_build_receipt_semantics(error_overclaim),
    )


def validate_phase7_execution_proof_records(records: list[dict[str, Any]]) -> None:
    check(
        tuple(sha256_bytes(canonical_bytes(record)) for record in records)
        == PHASE7_EXECUTION_RECORD_SHA256,
        "Phase 7 execution-proof changeset record bytes changed",
    )
    check(
        [record.get("op") for record in records]
        == ["changeset.header", "story.update", "trace.add", "story.verify"],
        "Phase 7 execution-proof changeset operation sequence changed",
    )
    check(
        records[0]
        == {
            "base_schema_version": 13,
            "op": "changeset.header",
            "run_id": "harness_v1_phase7_04_execution_proof",
            "version": 1,
        },
        "Phase 7 execution-proof changeset header changed",
    )
    story = records[1]
    story_payload = story.get("payload")
    check(
        story.get("id") == PHASE7_STORY_ID
        and story.get("version") == 1
        and isinstance(story_payload, dict)
        and story_payload.get("status") == "in_progress"
        and story_payload.get("contract_doc") is None
        and all(
            story_payload.get(field) == 0
            for field in ("unit_proof", "integration_proof", "e2e_proof", "platform_proof")
        )
        and story_payload.get("evidence") == PHASE7_EXECUTION_EVIDENCE
        and story_payload.get("verify_command") == PHASE7_EXECUTION_VERIFY_COMMAND,
        "Phase 7 execution proof changed story status, flags, evidence, or verification",
    )
    trace = records[2]
    trace_payload = trace.get("payload")
    check(
        trace.get("uid") == PHASE7_EXECUTION_TRACE_UID
        and trace.get("version") == 2
        and isinstance(trace_payload, dict)
        and trace_payload.get("task_summary") == PHASE7_EXECUTION_TRACE_SUMMARY
        and trace_payload.get("intake_uid") == PHASE7_INTAKE_UID
        and trace_payload.get("story_id") == PHASE7_STORY_ID
        and trace_payload.get("agent") == "codex"
        and trace_payload.get("outcome") == "completed"
        and trace_payload.get("duration_seconds") is None
        and trace_payload.get("token_estimate") is None,
        "Phase 7 execution-proof trace identity or bounded outcome changed",
    )
    lists = {}
    for field in ("actions_taken", "files_read", "files_changed", "decisions_made", "errors"):
        values = strict_json_loads(trace_payload.get(field, ""))
        check(
            isinstance(values, list)
            and values
            and all(isinstance(value, str) and value for value in values),
            f"Phase 7 execution-proof trace {field} is not Detailed",
        )
        lists[field] = values
    check(
        ".harness/changesets/harness_v1_phase7_04_execution_proof.changeset.jsonl"
        in lists["files_changed"]
        and any("six V1 core commands" in value for value in lists["decisions_made"])
        and any("proof flag zero" in value for value in lists["decisions_made"])
        and "no push, dispatch, tag, release, publish, signing, attestation, promotion"
        in trace_payload.get("notes", "")
        and "Symphony-owned" in trace_payload.get("harness_friction", ""),
        "Phase 7 execution-proof trace lost its closed authority or friction record",
    )
    verification = records[3]
    check(
        verification.get("id") == PHASE7_STORY_ID
        and verification.get("version") == 2
        and verification.get("payload", {}).get("result") == "pass",
        "Phase 7 execution-proof story verification changed",
    )


def self_test_phase7_execution_proof_records(records: list[dict[str, Any]]) -> None:
    asserted = deepcopy(records)
    asserted[1]["payload"]["platform_proof"] = 1
    expect_rejection(
        "same-filename Phase 7 execution platform overclaim",
        lambda: validate_phase7_execution_proof_records(asserted),
    )
    promoted = deepcopy(records)
    promoted[2]["payload"]["notes"] += " Promotion authorized."
    expect_rejection(
        "same-filename Phase 7 execution promotion overclaim",
        lambda: validate_phase7_execution_proof_records(promoted),
    )


def validate_phase7_review_correction_records(records: list[dict[str, Any]]) -> None:
    check(
        tuple(sha256_bytes(canonical_bytes(record)) for record in records)
        == PHASE7_REVIEW_RECORD_SHA256,
        "Phase 7 review-correction changeset record bytes changed",
    )
    check(
        [record.get("op") for record in records]
        == ["changeset.header", "story.update", "trace.add", "story.verify"],
        "Phase 7 review-correction operation sequence changed",
    )
    check(
        records[0]
        == {
            "base_schema_version": 13,
            "op": "changeset.header",
            "run_id": "harness_v1_phase7_05_review_corrections",
            "version": 1,
        },
        "Phase 7 review-correction header changed",
    )
    story = records[1]
    payload = story.get("payload", {})
    check(
        story.get("id") == PHASE7_STORY_ID
        and story.get("version") == 1
        and payload.get("status") == "in_progress"
        and payload.get("contract_doc") is None
        and all(payload.get(field) == 0 for field in ("unit_proof", "integration_proof", "e2e_proof", "platform_proof"))
        and payload.get("evidence") == PHASE7_REVIEW_EVIDENCE
        and payload.get("verify_command") == PHASE7_REVIEW_VERIFY_COMMAND,
        "Phase 7 review correction changed story state, proof flags, or evidence",
    )
    trace = records[2]
    trace_payload = trace.get("payload", {})
    check(
        trace.get("uid") == PHASE7_REVIEW_TRACE_UID
        and trace.get("version") == 2
        and trace_payload.get("task_summary") == PHASE7_REVIEW_TRACE_SUMMARY
        and trace_payload.get("intake_uid") == PHASE7_INTAKE_UID
        and trace_payload.get("story_id") == PHASE7_STORY_ID
        and trace_payload.get("agent") == "codex"
        and trace_payload.get("outcome") == "completed"
        and trace_payload.get("duration_seconds") is None
        and trace_payload.get("token_estimate") is None
        and "No push, dispatch, main mutation" in trace_payload.get("notes", ""),
        "Phase 7 review correction lost trace identity or closed authority",
    )
    for field in ("actions_taken", "files_read", "files_changed", "decisions_made", "errors"):
        values = strict_json_loads(trace_payload.get(field, ""))
        check(isinstance(values, list) and values and all(isinstance(value, str) and value for value in values), f"Phase 7 review correction trace {field} is not Detailed")
    check(
        records[3].get("id") == PHASE7_STORY_ID
        and records[3].get("version") == 2
        and records[3].get("payload", {}).get("result") == "pass",
        "Phase 7 review correction verification changed",
    )


def self_test_phase7_review_correction_records(records: list[dict[str, Any]]) -> None:
    asserted = deepcopy(records)
    asserted[1]["payload"]["platform_proof"] = 1
    expect_rejection(
        "same-filename Phase 7 review correction platform overclaim",
        lambda: validate_phase7_review_correction_records(asserted),
    )


def validate_phase7_second_correction_records(records: list[dict[str, Any]]) -> None:
    check(
        tuple(sha256_bytes(canonical_bytes(record)) for record in records)
        == PHASE7_SECOND_CORRECTION_RECORD_SHA256,
        "Phase 7 second-correction changeset record bytes changed",
    )
    check(
        [record.get("op") for record in records]
        == ["changeset.header", "story.update", "trace.add", "story.verify"],
        "Phase 7 second-correction operation sequence changed",
    )
    check(
        records[0]
        == {
            "base_schema_version": 13,
            "op": "changeset.header",
            "run_id": "harness_v1_phase7_06_cross_binding_corrections",
            "version": 1,
        },
        "Phase 7 second-correction header changed",
    )
    story = records[1]
    payload = story.get("payload", {})
    check(
        story.get("id") == PHASE7_STORY_ID
        and story.get("version") == 1
        and payload.get("status") == "in_progress"
        and payload.get("contract_doc") is None
        and all(
            payload.get(field) == 0
            for field in ("unit_proof", "integration_proof", "e2e_proof", "platform_proof")
        )
        and payload.get("evidence") == PHASE7_SECOND_CORRECTION_EVIDENCE
        and payload.get("verify_command") == PHASE7_SECOND_CORRECTION_VERIFY_COMMAND,
        "Phase 7 second correction changed story state, proof flags, or evidence",
    )
    trace = records[2]
    trace_payload = trace.get("payload", {})
    check(
        trace.get("uid") == PHASE7_SECOND_CORRECTION_TRACE_UID
        and trace.get("version") == 2
        and trace_payload.get("task_summary") == PHASE7_SECOND_CORRECTION_TRACE_SUMMARY
        and trace_payload.get("intake_uid") == PHASE7_INTAKE_UID
        and trace_payload.get("story_id") == PHASE7_STORY_ID
        and trace_payload.get("agent") == "codex"
        and trace_payload.get("outcome") == "completed"
        and trace_payload.get("duration_seconds") is None
        and trace_payload.get("token_estimate") is None
        and "No push, dispatch, main mutation" in trace_payload.get("notes", ""),
        "Phase 7 second correction lost trace identity or closed authority",
    )
    for field in ("actions_taken", "files_read", "files_changed", "decisions_made", "errors"):
        values = strict_json_loads(trace_payload.get(field, ""))
        check(
            isinstance(values, list)
            and values
            and all(isinstance(value, str) and value for value in values),
            f"Phase 7 second correction trace {field} is not Detailed",
        )
    check(
        records[3].get("id") == PHASE7_STORY_ID
        and records[3].get("version") == 2
        and records[3].get("payload", {}).get("result") == "pass",
        "Phase 7 second correction verification changed",
    )


def self_test_phase7_second_correction_records(records: list[dict[str, Any]]) -> None:
    asserted = deepcopy(records)
    asserted[1]["payload"]["platform_proof"] = 1
    expect_rejection(
        "same-filename Phase 7 second correction platform overclaim",
        lambda: validate_phase7_second_correction_records(asserted),
    )


def validate_phase7_attestation_records(records: list[dict[str, Any]]) -> None:
    check(
        tuple(sha256_bytes(canonical_bytes(record)) for record in records)
        == PHASE7_ATTESTATION_RECORD_SHA256,
        "Phase 7 attestation changeset record bytes changed",
    )
    check(
        [record.get("op") for record in records]
        == ["changeset.header", "story.update", "trace.add", "story.verify"],
        "Phase 7 attestation operation sequence changed",
    )
    check(
        records[0]
        == {
            "base_schema_version": 13,
            "op": "changeset.header",
            "run_id": "harness_v1_phase7_07_github_attestation",
            "version": 1,
        },
        "Phase 7 attestation header changed",
    )
    story = records[1]
    payload = story.get("payload", {})
    check(
        story.get("id") == PHASE7_STORY_ID
        and story.get("version") == 1
        and payload.get("status") == "in_progress"
        and payload.get("contract_doc") is None
        and all(
            payload.get(field) == 0
            for field in ("unit_proof", "integration_proof", "e2e_proof", "platform_proof")
        )
        and payload.get("evidence") == PHASE7_ATTESTATION_EVIDENCE
        and payload.get("verify_command") == PHASE7_ATTESTATION_VERIFY_COMMAND,
        "Phase 7 attestation changed story state, proof flags, or evidence",
    )
    trace = records[2]
    trace_payload = trace.get("payload", {})
    check(
        trace.get("uid") == PHASE7_ATTESTATION_TRACE_UID
        and trace.get("version") == 2
        and trace_payload.get("task_summary") == PHASE7_ATTESTATION_TRACE_SUMMARY
        and trace_payload.get("intake_uid") == PHASE7_INTAKE_UID
        and trace_payload.get("story_id") == PHASE7_STORY_ID
        and trace_payload.get("agent") == "codex"
        and trace_payload.get("outcome") == "completed"
        and trace_payload.get("duration_seconds") is None
        and trace_payload.get("token_estimate") is None
        and "No push, dispatch, main mutation" in trace_payload.get("notes", ""),
        "Phase 7 attestation lost trace identity or closed authority",
    )
    for field in ("actions_taken", "files_read", "files_changed", "decisions_made", "errors"):
        values = strict_json_loads(trace_payload.get(field, ""))
        check(
            isinstance(values, list)
            and values
            and all(isinstance(value, str) and value for value in values),
            f"Phase 7 attestation trace {field} is not Detailed",
        )
    check(
        records[3].get("id") == PHASE7_STORY_ID
        and records[3].get("version") == 2
        and records[3].get("payload", {}).get("result") == "pass",
        "Phase 7 attestation verification changed",
    )


def self_test_phase7_attestation_records(records: list[dict[str, Any]]) -> None:
    asserted = deepcopy(records)
    asserted[1]["payload"]["platform_proof"] = 1
    expect_rejection(
        "same-filename Phase 7 attestation platform overclaim",
        lambda: validate_phase7_attestation_records(asserted),
    )


def validate_phase7_windows_compile_fix_records(records: list[dict[str, Any]]) -> None:
    check(
        tuple(sha256_bytes(canonical_bytes(record)) for record in records)
        == PHASE7_WINDOWS_COMPILE_FIX_RECORD_SHA256,
        "Phase 7 Windows compile-fix changeset record bytes changed",
    )
    check(
        [record.get("op") for record in records] == ["changeset.header", "trace.add"],
        "Phase 7 Windows compile-fix operation sequence changed",
    )
    check(
        records[0]
        == {
            "base_schema_version": 13,
            "op": "changeset.header",
            "run_id": "harness_v1_phase7_08_windows_compile_fix",
            "version": 1,
        },
        "Phase 7 Windows compile-fix header changed",
    )
    trace = records[1]
    payload = trace.get("payload", {})
    check(
        trace.get("uid") == PHASE7_WINDOWS_COMPILE_FIX_TRACE_UID
        and trace.get("version") == 2
        and payload.get("task_summary") == PHASE7_WINDOWS_COMPILE_FIX_TRACE_SUMMARY
        and payload.get("intake_uid") == PHASE7_INTAKE_UID
        and payload.get("story_id") == PHASE7_STORY_ID
        and payload.get("agent") == "codex"
        and payload.get("outcome") == "completed"
        and payload.get("duration_seconds") is None
        and payload.get("token_estimate") is None
        and "No push, dispatch, main mutation" in payload.get("notes", ""),
        "Phase 7 Windows compile-fix trace lost identity or closed authority",
    )
    for field in ("actions_taken", "files_read", "files_changed", "decisions_made", "errors"):
        values = strict_json_loads(payload.get(field, ""))
        check(
            isinstance(values, list)
            and values
            and all(isinstance(value, str) and value for value in values),
            f"Phase 7 Windows compile-fix trace {field} is not Detailed",
        )


def validate_phase7_windows_refusal_capture_records(
    records: list[dict[str, Any]],
) -> None:
    check(
        tuple(sha256_bytes(canonical_bytes(record)) for record in records)
        == PHASE7_WINDOWS_REFUSAL_CAPTURE_RECORD_SHA256,
        "Phase 7 Windows refusal-capture changeset record bytes changed",
    )
    check(
        [record.get("op") for record in records] == ["changeset.header", "trace.add"],
        "Phase 7 Windows refusal-capture operation sequence changed",
    )
    check(
        records[0]
        == {
            "base_schema_version": 13,
            "op": "changeset.header",
            "run_id": "harness_v1_phase7_09_windows_refusal_capture",
            "version": 1,
        },
        "Phase 7 Windows refusal-capture header changed",
    )
    trace = records[1]
    payload = trace.get("payload", {})
    check(
        trace.get("uid") == PHASE7_WINDOWS_REFUSAL_CAPTURE_TRACE_UID
        and trace.get("version") == 2
        and payload.get("task_summary")
        == PHASE7_WINDOWS_REFUSAL_CAPTURE_TRACE_SUMMARY
        and payload.get("intake_uid") == PHASE7_INTAKE_UID
        and payload.get("story_id") == PHASE7_STORY_ID
        and payload.get("agent") == "codex"
        and payload.get("outcome") == "completed"
        and payload.get("duration_seconds") is None
        and payload.get("token_estimate") is None
        and "No push, dispatch, main mutation" in payload.get("notes", ""),
        "Phase 7 Windows refusal-capture trace lost identity or closed authority",
    )
    for field in ("actions_taken", "files_read", "files_changed", "decisions_made", "errors"):
        values = strict_json_loads(payload.get(field, ""))
        check(
            isinstance(values, list)
            and values
            and all(isinstance(value, str) and value for value in values),
            f"Phase 7 Windows refusal-capture trace {field} is not Detailed",
        )


def verify_phase7_opening_gate() -> None:
    intake_records = load_jsonl(PHASE7_INTAKE_CHANGESET)
    story_records = load_jsonl(PHASE7_STORY_CHANGESET)
    proof_records = load_jsonl(PHASE7_PROOF_CONTRACT_CHANGESET)
    build_receipt_records = load_jsonl(PHASE7_BUILD_RECEIPT_CHANGESET)
    execution_proof_records = load_jsonl(PHASE7_EXECUTION_PROOF_CHANGESET)
    review_correction_records = load_jsonl(PHASE7_REVIEW_CORRECTION_CHANGESET)
    second_correction_records = load_jsonl(PHASE7_SECOND_CORRECTION_CHANGESET)
    attestation_records = load_jsonl(PHASE7_ATTESTATION_CHANGESET)
    windows_compile_fix_records = load_jsonl(PHASE7_WINDOWS_COMPILE_FIX_CHANGESET)
    windows_refusal_capture_records = load_jsonl(
        PHASE7_WINDOWS_REFUSAL_CAPTURE_CHANGESET
    )
    validate_phase7_opening_records(intake_records, story_records)
    self_test_phase7_opening_records(intake_records, story_records)
    validate_phase7_proof_contract_records(intake_records, proof_records)
    self_test_phase7_proof_contract_records(intake_records, proof_records)
    validate_phase7_build_receipt_records(build_receipt_records)
    self_test_phase7_build_receipt_records(build_receipt_records)
    validate_phase7_execution_proof_records(execution_proof_records)
    self_test_phase7_execution_proof_records(execution_proof_records)
    validate_phase7_review_correction_records(review_correction_records)
    self_test_phase7_review_correction_records(review_correction_records)
    validate_phase7_second_correction_records(second_correction_records)
    self_test_phase7_second_correction_records(second_correction_records)
    validate_phase7_attestation_records(attestation_records)
    self_test_phase7_attestation_records(attestation_records)
    validate_phase7_windows_compile_fix_records(windows_compile_fix_records)
    validate_phase7_windows_refusal_capture_records(
        windows_refusal_capture_records
    )

    with tempfile.TemporaryDirectory(prefix="phase7-opening-replay-") as temporary:
        database = Path(temporary) / "replay.db"
        prior_changesets = Path(temporary) / "prior-changesets"
        prior_changesets.mkdir()
        for changeset in sorted((ROOT / ".harness/changesets").glob("*.jsonl")):
            if changeset not in {
                PHASE7_PROOF_CONTRACT_CHANGESET,
                PHASE7_BUILD_RECEIPT_CHANGESET,
                PHASE7_EXECUTION_PROOF_CHANGESET,
                PHASE7_REVIEW_CORRECTION_CHANGESET,
                PHASE7_SECOND_CORRECTION_CHANGESET,
                PHASE7_ATTESTATION_CHANGESET,
                PHASE7_WINDOWS_COMPILE_FIX_CHANGESET,
                PHASE7_WINDOWS_REFUSAL_CAPTURE_CHANGESET,
            }:
                shutil.copyfile(changeset, prior_changesets / changeset.name)
        environment = dict(os.environ)
        for name in list(environment):
            if name.startswith("HARNESS_"):
                environment.pop(name, None)
        environment.update(
            {
                "HARNESS_REPO_ROOT": str(ROOT),
                "HARNESS_DB_PATH": str(database),
                "LC_ALL": "C",
            }
        )
        result = subprocess.run(
            [
                str(ROOT / "scripts/bin/harness-cli"),
                "db",
                "rebuild",
                "--from",
                str(prior_changesets),
            ],
            cwd=ROOT,
            capture_output=True,
            check=False,
            env=environment,
            text=True,
        )
        check(
            result.returncode == 0,
            "Phase 7 prior changesets do not rebuild into an isolated database",
        )
        check(database.is_file(), "Phase 7 isolated replay database is missing")
        connection = sqlite3.connect(str(database))
        try:
            prior_story = connection.execute(
                """
                SELECT status, unit_proof, integration_proof, e2e_proof,
                       platform_proof, evidence, last_verified_result,
                       verify_command
                FROM story WHERE id = ?
                """,
                (PHASE7_STORY_ID,),
            ).fetchall()
            check(
                len(prior_story) == 1
                and prior_story[0][0] == "in_progress"
                and prior_story[0][1:5] == (0, 0, 0, 0)
                and isinstance(prior_story[0][5], str)
                and "No executable Phase 7 proof" in prior_story[0][5]
                and prior_story[0][6] == "pass"
                and prior_story[0][7] == PHASE7_STORY_VERIFY_COMMAND,
                "isolated replay did not start from the expected in-progress US-112",
            )
            decision = connection.execute(
                """
                SELECT status, doc_path, last_verified_result, verify_command
                FROM decision WHERE id = ?
                """,
                (PHASE7_DECISION_ID,),
            ).fetchall()
            check(
                decision
                == [
                    (
                        "accepted",
                        "docs/decisions/0016-phase6-framework-acceptance-and-phase7-opening.md",
                        "pass",
                        PHASE7_DECISION_VERIFY_COMMAND,
                    )
                ],
                "isolated replay no longer contains the accepted Decision 0016",
            )
            hierarchy = connection.execute(
                """
                SELECT parent_story_id, child_story_id FROM story_hierarchy
                WHERE parent_story_id = 'US-105' AND child_story_id = 'US-112'
                """
            ).fetchall()
            check(
                hierarchy == [("US-105", "US-112")],
                "isolated replay lost the US-105 to US-112 hierarchy",
            )
        finally:
            connection.close()

        apply_result = subprocess.run(
            [
                str(ROOT / "scripts/bin/harness-cli"),
                "db",
                "changeset",
                "apply",
                str(PHASE7_PROOF_CONTRACT_CHANGESET),
            ],
            cwd=ROOT,
            capture_output=True,
            check=False,
            env=environment,
            text=True,
        )
        check(
            apply_result.returncode == 0,
            "Phase 7 proof-contract changeset does not apply to isolated prior state",
        )
        connection = sqlite3.connect(str(database))
        try:
            story = connection.execute(
                """
                SELECT status, unit_proof, integration_proof, e2e_proof,
                       platform_proof, evidence, last_verified_result,
                       verify_command
                FROM story WHERE id = ?
                """,
                (PHASE7_STORY_ID,),
            ).fetchall()
            check(
                story
                == [
                    (
                        "in_progress",
                        0,
                        0,
                        0,
                        0,
                        PHASE7_PROOF_EVIDENCE,
                        "pass",
                        PHASE7_PROOF_VERIFY_COMMAND,
                    )
                ],
                "isolated proof replay no longer keeps US-112 in progress with zero proof",
            )
            trace = connection.execute(
                """
                SELECT task_summary, intake_uid, story_id, agent, outcome,
                       duration_seconds, token_estimate
                FROM trace WHERE uid = ?
                """,
                (PHASE7_PROOF_TRACE_UID,),
            ).fetchall()
            check(
                trace
                == [
                    (
                        PHASE7_PROOF_TRACE_SUMMARY,
                        PHASE7_INTAKE_UID,
                        PHASE7_STORY_ID,
                        "codex",
                        "completed",
                        None,
                        None,
                    )
                ],
                "isolated proof replay lost the Detailed Phase 7 trace identity",
            )
        finally:
            connection.close()

        build_apply = [
            str(ROOT / "scripts/bin/harness-cli"),
            "db",
            "changeset",
            "apply",
            str(PHASE7_BUILD_RECEIPT_CHANGESET),
        ]
        build_status = [
            str(ROOT / "scripts/bin/harness-cli"),
            "db",
            "changeset",
            "status",
            str(PHASE7_BUILD_RECEIPT_CHANGESET),
            "--json",
        ]
        status_before = subprocess.run(
            build_status,
            cwd=ROOT,
            capture_output=True,
            check=False,
            env=environment,
            text=True,
        )
        status_before_document = strict_json_loads(status_before.stdout)
        check(
            status_before.returncode == 0
            and status_before_document.get("result", {}).get("applied") is False,
            "Phase 7 build-receipt status did not report unapplied before replay",
        )
        for attempt in ("initial", "idempotent"):
            build_result = subprocess.run(
                build_apply,
                cwd=ROOT,
                capture_output=True,
                check=False,
                env=environment,
                text=True,
            )
            check(
                build_result.returncode == 0,
                f"Phase 7 build-receipt changeset {attempt} apply failed",
            )
        status_after = subprocess.run(
            build_status,
            cwd=ROOT,
            capture_output=True,
            check=False,
            env=environment,
            text=True,
        )
        status_after_document = strict_json_loads(status_after.stdout)
        check(
            status_after.returncode == 0
            and status_after_document.get("result", {}).get("applied") is True,
            "Phase 7 build-receipt status did not report applied after idempotent replay",
        )
        connection = sqlite3.connect(str(database))
        try:
            story = connection.execute(
                """
                SELECT status, unit_proof, integration_proof, e2e_proof,
                       platform_proof, evidence, last_verified_result,
                       verify_command
                FROM story WHERE id = ?
                """,
                (PHASE7_STORY_ID,),
            ).fetchall()
            check(
                story
                == [
                    (
                        "in_progress",
                        0,
                        0,
                        0,
                        0,
                        PHASE7_BUILD_RECEIPT_EVIDENCE,
                        "pass",
                        PHASE7_BUILD_RECEIPT_VERIFY_COMMAND,
                    )
                ],
                "isolated build-receipt replay changed US-112 status, proof, evidence, or verification",
            )
            traces = connection.execute(
                """
                SELECT uid, intake_uid, story_id, task_summary, outcome,
                       duration_seconds, token_estimate
                FROM trace WHERE uid IN (?, ?) ORDER BY recorded_at_unix_ns
                """,
                PHASE7_BUILD_RECEIPT_TRACE_UIDS,
            ).fetchall()
            check(
                traces
                == [
                    (
                        PHASE7_BUILD_RECEIPT_TRACE_UIDS[0],
                        PHASE7_INTAKE_UID,
                        PHASE7_STORY_ID,
                        "Implemented reviewed Phase 7 immutable native build-receipt infrastructure without promotion",
                        "completed",
                        None,
                        None,
                    ),
                    (
                        PHASE7_BUILD_RECEIPT_TRACE_UIDS[1],
                        PHASE7_INTAKE_UID,
                        PHASE7_STORY_ID,
                        "Verified Phase 7 build-receipt slice after corrections",
                        "completed",
                        None,
                        None,
                    ),
                ],
                "isolated build-receipt replay lost stable intake links or Detailed latest trace",
            )
            applied = connection.execute(
                "SELECT COUNT(*) FROM changeset_applied WHERE id = ?",
                ("harness_v1_phase7_03_build_receipts",),
            ).fetchone()
            check(
                applied == (1,),
                "Phase 7 build-receipt idempotent replay recorded multiple applications",
            )
        finally:
            connection.close()

        execution_apply = [
            str(ROOT / "scripts/bin/harness-cli"),
            "db",
            "changeset",
            "apply",
            str(PHASE7_EXECUTION_PROOF_CHANGESET),
        ]
        for attempt in ("initial", "idempotent"):
            execution_result = subprocess.run(
                execution_apply,
                cwd=ROOT,
                capture_output=True,
                check=False,
                env=environment,
                text=True,
            )
            check(
                execution_result.returncode == 0,
                f"Phase 7 execution-proof changeset {attempt} apply failed",
            )
        connection = sqlite3.connect(str(database))
        try:
            story = connection.execute(
                """
                SELECT status, unit_proof, integration_proof, e2e_proof,
                       platform_proof, evidence, last_verified_result,
                       verify_command
                FROM story WHERE id = ?
                """,
                (PHASE7_STORY_ID,),
            ).fetchall()
            check(
                story
                == [
                    (
                        "in_progress",
                        0,
                        0,
                        0,
                        0,
                        PHASE7_EXECUTION_EVIDENCE,
                        "pass",
                        PHASE7_EXECUTION_VERIFY_COMMAND,
                    )
                ],
                "isolated execution-proof replay changed US-112 status or proof flags",
            )
            trace = connection.execute(
                """
                SELECT uid, intake_uid, story_id, task_summary, outcome,
                       duration_seconds, token_estimate
                FROM trace WHERE uid = ?
                """,
                (PHASE7_EXECUTION_TRACE_UID,),
            ).fetchall()
            check(
                trace
                == [
                    (
                        PHASE7_EXECUTION_TRACE_UID,
                        PHASE7_INTAKE_UID,
                        PHASE7_STORY_ID,
                        PHASE7_EXECUTION_TRACE_SUMMARY,
                        "completed",
                        None,
                        None,
                    )
                ],
                "isolated execution-proof replay lost stable trace identity",
            )
            applied = connection.execute(
                "SELECT COUNT(*) FROM changeset_applied WHERE id = ?",
                ("harness_v1_phase7_04_execution_proof",),
            ).fetchone()
            check(
                applied == (1,),
                "Phase 7 execution-proof idempotent replay recorded multiple applications",
            )
        finally:
            connection.close()

        correction_apply = [
            str(ROOT / "scripts/bin/harness-cli"),
            "db",
            "changeset",
            "apply",
            str(PHASE7_REVIEW_CORRECTION_CHANGESET),
        ]
        for attempt in ("initial", "idempotent"):
            correction_result = subprocess.run(
                correction_apply,
                cwd=ROOT,
                capture_output=True,
                check=False,
                env=environment,
                text=True,
            )
            check(
                correction_result.returncode == 0,
                f"Phase 7 review-correction changeset {attempt} apply failed",
            )
        connection = sqlite3.connect(str(database))
        try:
            story = connection.execute(
                """
                SELECT status, unit_proof, integration_proof, e2e_proof,
                       platform_proof, evidence, last_verified_result,
                       verify_command
                FROM story WHERE id = ?
                """,
                (PHASE7_STORY_ID,),
            ).fetchall()
            check(
                story
                == [
                    (
                        "in_progress",
                        0,
                        0,
                        0,
                        0,
                        PHASE7_REVIEW_EVIDENCE,
                        "pass",
                        PHASE7_REVIEW_VERIFY_COMMAND,
                    )
                ],
                "isolated review-correction replay changed US-112 status or proof flags",
            )
            trace = connection.execute(
                """
                SELECT uid, intake_uid, story_id, task_summary, outcome,
                       duration_seconds, token_estimate
                FROM trace WHERE uid = ?
                """,
                (PHASE7_REVIEW_TRACE_UID,),
            ).fetchall()
            check(
                trace
                == [
                    (
                        PHASE7_REVIEW_TRACE_UID,
                        PHASE7_INTAKE_UID,
                        PHASE7_STORY_ID,
                        PHASE7_REVIEW_TRACE_SUMMARY,
                        "completed",
                        None,
                        None,
                    )
                ],
                "isolated review-correction replay lost stable trace identity",
            )
            applied = connection.execute(
                "SELECT COUNT(*) FROM changeset_applied WHERE id = ?",
                ("harness_v1_phase7_05_review_corrections",),
            ).fetchone()
            check(
                applied == (1,),
                "Phase 7 review-correction idempotent replay recorded multiple applications",
            )
        finally:
            connection.close()

        second_correction_apply = [
            str(ROOT / "scripts/bin/harness-cli"),
            "db",
            "changeset",
            "apply",
            str(PHASE7_SECOND_CORRECTION_CHANGESET),
        ]
        for attempt in ("initial", "idempotent"):
            second_correction_result = subprocess.run(
                second_correction_apply,
                cwd=ROOT,
                capture_output=True,
                check=False,
                env=environment,
                text=True,
            )
            check(
                second_correction_result.returncode == 0,
                f"Phase 7 second-correction changeset {attempt} apply failed",
            )
        connection = sqlite3.connect(str(database))
        try:
            story = connection.execute(
                """
                SELECT status, unit_proof, integration_proof, e2e_proof,
                       platform_proof, evidence, last_verified_result,
                       verify_command
                FROM story WHERE id = ?
                """,
                (PHASE7_STORY_ID,),
            ).fetchall()
            check(
                story
                == [
                    (
                        "in_progress",
                        0,
                        0,
                        0,
                        0,
                        PHASE7_SECOND_CORRECTION_EVIDENCE,
                        "pass",
                        PHASE7_SECOND_CORRECTION_VERIFY_COMMAND,
                    )
                ],
                "isolated second-correction replay changed US-112 status or proof flags",
            )
            trace = connection.execute(
                """
                SELECT uid, intake_uid, story_id, task_summary, outcome,
                       duration_seconds, token_estimate
                FROM trace WHERE uid = ?
                """,
                (PHASE7_SECOND_CORRECTION_TRACE_UID,),
            ).fetchall()
            check(
                trace
                == [
                    (
                        PHASE7_SECOND_CORRECTION_TRACE_UID,
                        PHASE7_INTAKE_UID,
                        PHASE7_STORY_ID,
                        PHASE7_SECOND_CORRECTION_TRACE_SUMMARY,
                        "completed",
                        None,
                        None,
                    )
                ],
                "isolated second-correction replay lost stable trace identity",
            )
            applied = connection.execute(
                "SELECT COUNT(*) FROM changeset_applied WHERE id = ?",
                ("harness_v1_phase7_06_cross_binding_corrections",),
            ).fetchone()
            check(
                applied == (1,),
                "Phase 7 second-correction idempotent replay recorded multiple applications",
            )
        finally:
            connection.close()

        attestation_apply = [
            str(ROOT / "scripts/bin/harness-cli"),
            "db",
            "changeset",
            "apply",
            str(PHASE7_ATTESTATION_CHANGESET),
        ]
        for attempt in ("initial", "idempotent"):
            attestation_result = subprocess.run(
                attestation_apply,
                cwd=ROOT,
                capture_output=True,
                check=False,
                env=environment,
                text=True,
            )
            check(
                attestation_result.returncode == 0,
                f"Phase 7 attestation changeset {attempt} apply failed",
            )
        connection = sqlite3.connect(str(database))
        try:
            story = connection.execute(
                """
                SELECT status, unit_proof, integration_proof, e2e_proof,
                       platform_proof, evidence, last_verified_result,
                       verify_command
                FROM story WHERE id = ?
                """,
                (PHASE7_STORY_ID,),
            ).fetchall()
            check(
                story
                == [
                    (
                        "in_progress",
                        0,
                        0,
                        0,
                        0,
                        PHASE7_ATTESTATION_EVIDENCE,
                        "pass",
                        PHASE7_ATTESTATION_VERIFY_COMMAND,
                    )
                ],
                "isolated attestation replay changed US-112 status or proof flags",
            )
            trace = connection.execute(
                """
                SELECT uid, intake_uid, story_id, task_summary, outcome,
                       duration_seconds, token_estimate
                FROM trace WHERE uid = ?
                """,
                (PHASE7_ATTESTATION_TRACE_UID,),
            ).fetchall()
            check(
                trace
                == [
                    (
                        PHASE7_ATTESTATION_TRACE_UID,
                        PHASE7_INTAKE_UID,
                        PHASE7_STORY_ID,
                        PHASE7_ATTESTATION_TRACE_SUMMARY,
                        "completed",
                        None,
                        None,
                    )
                ],
                "isolated attestation replay lost stable trace identity",
            )
            applied = connection.execute(
                "SELECT COUNT(*) FROM changeset_applied WHERE id = ?",
                ("harness_v1_phase7_07_github_attestation",),
            ).fetchone()
            check(
                applied == (1,),
                "Phase 7 attestation idempotent replay recorded multiple applications",
            )
        finally:
            connection.close()

        windows_compile_fix_apply = [
            str(ROOT / "scripts/bin/harness-cli"),
            "db",
            "changeset",
            "apply",
            str(PHASE7_WINDOWS_COMPILE_FIX_CHANGESET),
        ]
        for attempt in ("initial", "idempotent"):
            windows_compile_fix_result = subprocess.run(
                windows_compile_fix_apply,
                cwd=ROOT,
                capture_output=True,
                check=False,
                env=environment,
                text=True,
            )
            check(
                windows_compile_fix_result.returncode == 0,
                f"Phase 7 Windows compile-fix changeset {attempt} apply failed",
            )
        connection = sqlite3.connect(str(database))
        try:
            story = connection.execute(
                """
                SELECT status, unit_proof, integration_proof, e2e_proof,
                       platform_proof, evidence, last_verified_result,
                       verify_command
                FROM story WHERE id = ?
                """,
                (PHASE7_STORY_ID,),
            ).fetchall()
            check(
                story
                == [
                    (
                        "in_progress",
                        0,
                        0,
                        0,
                        0,
                        PHASE7_ATTESTATION_EVIDENCE,
                        "pass",
                        PHASE7_ATTESTATION_VERIFY_COMMAND,
                    )
                ],
                "Windows compile-fix trace changed US-112 proof or authority state",
            )
            trace = connection.execute(
                """
                SELECT uid, intake_uid, story_id, task_summary, outcome,
                       duration_seconds, token_estimate
                FROM trace WHERE uid = ?
                """,
                (PHASE7_WINDOWS_COMPILE_FIX_TRACE_UID,),
            ).fetchall()
            check(
                trace
                == [
                    (
                        PHASE7_WINDOWS_COMPILE_FIX_TRACE_UID,
                        PHASE7_INTAKE_UID,
                        PHASE7_STORY_ID,
                        PHASE7_WINDOWS_COMPILE_FIX_TRACE_SUMMARY,
                        "completed",
                        None,
                        None,
                    )
                ],
                "isolated Windows compile-fix replay lost stable trace identity",
            )
            applied = connection.execute(
                "SELECT COUNT(*) FROM changeset_applied WHERE id = ?",
                ("harness_v1_phase7_08_windows_compile_fix",),
            ).fetchone()
            check(
                applied == (1,),
                "Phase 7 Windows compile-fix idempotent replay recorded multiple applications",
            )
        finally:
            connection.close()

        windows_refusal_capture_apply = [
            str(ROOT / "scripts/bin/harness-cli"),
            "db",
            "changeset",
            "apply",
            str(PHASE7_WINDOWS_REFUSAL_CAPTURE_CHANGESET),
        ]
        for attempt in ("initial", "idempotent"):
            windows_refusal_capture_result = subprocess.run(
                windows_refusal_capture_apply,
                cwd=ROOT,
                capture_output=True,
                check=False,
                env=environment,
                text=True,
            )
            check(
                windows_refusal_capture_result.returncode == 0,
                f"Phase 7 Windows refusal-capture changeset {attempt} apply failed",
            )
        connection = sqlite3.connect(str(database))
        try:
            story = connection.execute(
                """
                SELECT status, unit_proof, integration_proof, e2e_proof,
                       platform_proof, evidence, last_verified_result,
                       verify_command
                FROM story WHERE id = ?
                """,
                (PHASE7_STORY_ID,),
            ).fetchall()
            check(
                story
                == [
                    (
                        "in_progress",
                        0,
                        0,
                        0,
                        0,
                        PHASE7_ATTESTATION_EVIDENCE,
                        "pass",
                        PHASE7_ATTESTATION_VERIFY_COMMAND,
                    )
                ],
                "Windows refusal-capture trace changed US-112 proof or authority state",
            )
            trace = connection.execute(
                """
                SELECT uid, intake_uid, story_id, task_summary, outcome,
                       duration_seconds, token_estimate
                FROM trace WHERE uid = ?
                """,
                (PHASE7_WINDOWS_REFUSAL_CAPTURE_TRACE_UID,),
            ).fetchall()
            check(
                trace
                == [
                    (
                        PHASE7_WINDOWS_REFUSAL_CAPTURE_TRACE_UID,
                        PHASE7_INTAKE_UID,
                        PHASE7_STORY_ID,
                        PHASE7_WINDOWS_REFUSAL_CAPTURE_TRACE_SUMMARY,
                        "completed",
                        None,
                        None,
                    )
                ],
                "isolated Windows refusal-capture replay lost stable trace identity",
            )
            applied = connection.execute(
                "SELECT COUNT(*) FROM changeset_applied WHERE id = ?",
                ("harness_v1_phase7_09_windows_refusal_capture",),
            ).fetchone()
            check(
                applied == (1,),
                "Phase 7 Windows refusal-capture idempotent replay recorded multiple applications",
            )
        finally:
            connection.close()


def verify_phase7_proof_contract_boundary() -> None:
    schema_document = load_json(
        ROOT / "release/contracts/v1/schemas/phase7-release-proof-v1.schema.json"
    )
    check(
        schema_document.get("$schema")
        == "https://json-schema.org/draft/2020-12/schema",
        "Phase 7 proof schema is not Draft 2020-12",
    )
    check(
        schema_document.get("additionalProperties") is False,
        "Phase 7 proof schema root is not closed",
    )
    document = load_json(
        ROOT / "tests/fixtures/v1-phase7/phase7-release-proof.json"
    )
    check(
        document.get("evidence_kind") == "fixture-only-non-production",
        "Phase 7 opening evidence is no longer fixture-only and non-production",
    )
    promotion = document.get("promotion")
    check(isinstance(promotion, dict), "Phase 7 promotion state is missing")
    check(
        promotion
        == {
            "phase6_live_evidence": "pending",
            "phase7_results": "pending",
            "phase7_acceptance": "blocked",
            "production": False,
            "promotable": False,
            "tag_authorized": False,
            "publish_authorized": False,
            "promotion_authorized": False,
            "production_signing_authorized": False,
            "phase8": "closed",
            "blockers": [
                "deferred-phase6-live-p0-p7-evidence-pending",
                "phase7-five-platform-results-pending",
            ],
        },
        "Phase 7 fixture contract opened an acceptance or release authority",
    )
    artifacts = document.get("artifacts")
    check(
        isinstance(artifacts, list) and len(artifacts) == 5,
        "Phase 7 fixture contract lost the five-platform inventory",
    )
    for artifact in artifacts:
        check(
            artifact.get("authentication", {}).get("state") == "pending"
            and all(
                artifact.get(result, {}).get("state") == "pending"
                for result in (
                    "build_result",
                    "direct_binary_result",
                    "installer_result",
                )
            ),
            "Phase 7 fixture contract makes a platform pass claim",
        )


def verify_phase7_build_receipt_boundary() -> None:
    schema_document = load_json(
        ROOT / "release/contracts/v1/schemas/build-receipt-v1.schema.json"
    )
    check(
        schema_document.get("$schema")
        == "https://json-schema.org/draft/2020-12/schema"
        and schema_document.get("additionalProperties") is False,
        "Phase 7 build receipt schema is not closed Draft 2020-12",
    )
    properties = schema_document.get("properties", {})
    check(
        properties.get("evidence_kind", {}).get("const")
        == "native-build-receipt-non-production",
        "Phase 7 build receipt schema is not explicitly non-production",
    )
    definitions = schema_document.get("$defs", {})
    result_properties = definitions.get("results", {}).get("properties", {})
    check(
        {name: value.get("const") for name, value in result_properties.items()}
        == {
            "build": "passed",
            "help_grammar_only": "passed",
            "installer": "pending",
            "full_direct_binary": "pending",
            "provenance": "github-sigstore-attested",
        },
        "Phase 7 build receipt result vocabulary opened an unsupported claim",
    )
    authority_properties = definitions.get("authority", {}).get("properties", {})
    false_authorities = (
        "platform_accepted",
        "phase7_accepted",
        "production",
        "promotable",
        "tag_authorized",
        "release_authorized",
        "publish_authorized",
        "promotion_authorized",
        "production_signing_authorized",
    )
    check(
        all(authority_properties.get(field, {}).get("const") is False for field in false_authorities)
        and authority_properties.get("platform_acceptance", {}).get("const") == "blocked"
        and authority_properties.get("phase7_acceptance", {}).get("const") == "blocked",
        "Phase 7 build receipt schema opened acceptance or release authority",
    )


def verify_phase7_execution_proof_boundary() -> None:
    schema_document = load_json(
        ROOT / "tests/release/schemas/phase7-execution-proof-v1.schema.json"
    )
    check(
        schema_document.get("$schema")
        == "https://json-schema.org/draft/2020-12/schema"
        and schema_document.get("additionalProperties") is False,
        "Phase 7 execution proof schema is not closed Draft 2020-12",
    )
    main_source = (ROOT / "crates/harness-core/src/main.rs").read_text(encoding="utf-8")
    check(
        main_source.index("authenticate_executable_and_platform()")
        < main_source.index("parse(std::env::args_os().skip(1))")
        and "HARNESS_V1_ARTIFACT_SHA256" in main_source
        and "HARNESS_V1_PLATFORM" in main_source
        and "HarnessCore::with_mutations" in main_source,
        "V1 binary no longer authenticates artifact and platform before command execution",
    )
    bash_installer = (ROOT / "scripts/install-harness-v1.sh").read_text(encoding="utf-8")
    powershell_installer = (ROOT / "scripts/install-harness-v1.ps1").read_text(encoding="utf-8")
    check(
        bash_installer.index("artifact checksum mismatch")
        < bash_installer.index("system=$(uname -s)")
        and powershell_installer.index("Get-FileHash")
        < powershell_installer.index("RuntimeInformation")
        and "cd \"$root_physical\"" in bash_installer
        and "destination component scripts/bin is unsafe" in bash_installer
        and "safe Windows destination publication is controlled-unsupported before mutation" in powershell_installer
        and all(
            fragment not in powershell_installer
            for fragment in ("Copy-Item", "Move-Item", "[IO.File]::Move", "CreateDirectory", "New-Item")
        )
        and "provenance and platform acceptance remain unclaimed" in bash_installer
        and "Write-Output" not in powershell_installer,
        "V1 installers no longer authenticate before platform selection or preserve authority wording",
    )
    runner = (ROOT / "scripts/run_v1_phase7_execution_proof.py").read_text(encoding="utf-8")
    verifier = (ROOT / "scripts/verify_v1_phase7_execution_proof.py").read_text(encoding="utf-8")
    receipt_common = (ROOT / "scripts/v1_build_receipt_common.py").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/harness-v1-release.yml").read_text(encoding="utf-8")
    for command in ("install", "update", "audit", "scaffold", "status", "version"):
        check(f'"{command}"' in runner, f"Phase 7 execution runner lost {command}")
    for case in (
        "fresh", "brownfield", "nested-instructions", "docs-only", "monorepo",
        "spaces-unicode", "lf", "crlf", "custom-update", "bridge",
    ):
        check(f'"{case}"' in runner, f"Phase 7 execution runner lost {case}")
    check(
        "github-sigstore-attested" in runner
        and "github-sigstore-attested" in verifier
        and "verify_artifact_identity_collection" in runner
        and "minimal_subprocess_environment" in runner
        and "MINIMAL_SUBPROCESS_ENVIRONMENT_NAMES" in receipt_common
        and "TRUSTED_HARNESS_V1_ENVIRONMENT_NAMES" in receipt_common
        and '"GITHUB_ENV"' not in receipt_common
        and '"PYTHONPATH"' not in receipt_common
        and "--build-receipt-directory" in runner
        and '"platform_accepted": False' in runner
        and '"five_platform_equivalence": "pending"' in runner
        and "normalized_result" in runner
        and "controlled-unsupported-before-mutation" in runner
        and "verify_collection" in verifier
        and "expected_identity" in verifier
        and "verify_artifact_identity_collection" in verifier
        and "--build-receipt-root" in verifier
        and "normalized payload digest drifted" in verifier
        and "scripts/run_v1_phase7_execution_proof.py" in workflow
        and "build-native-artifact:" in workflow
        and "attest-native-artifact:" in workflow
        and "verify-execute-native-proof:" in workflow
        and "PYTHONDONTWRITEBYTECODE: '1'" in workflow
        and "sys.dont_write_bytecode = True" in (ROOT / "scripts/capture_v1_build_receipt.py").read_text(encoding="utf-8")
        and "sys.dont_write_bytecode = True" in (ROOT / "scripts/finalize_v1_build_receipt.py").read_text(encoding="utf-8")
        and workflow.count("id-token: write") == 1
        and workflow.count("attestations: write") == 1
        and "actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c" in workflow
        and "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a" in workflow
        and '"${{ steps.python.outputs.python-path }}" scripts/run_v1_phase7_execution_proof.py' in workflow
        and 'test "$CANDIDATE_SHA" = "$WORKFLOW_REVISION"' in workflow
        and "refs/heads/refactor/harness-v1" in workflow
        and "workflow_dispatch" not in workflow
        and "candidate_ref" not in workflow
        and "--repository-root \"$REPOSITORY_ROOT\"" in workflow
        and "--build-receipt-root \"$BUILD_RECEIPT_ROOT\"" in workflow
        and "promotion-blocked:" not in workflow,
        "Phase 7 execution proof lost closed provenance, acceptance, equivalence, or diagnostic identity",
    )


def self_test_phase5_compatibility_boundary(lock: dict[str, Any]) -> None:
    tampered = deepcopy(lock)
    tampered["phase5_verifier_compatibility_git_oid"] = "0" * 40
    expect_rejection(
        "Phase 5 verifier compatibility digest mismatch",
        lambda: verify_phase5_immutability(tampered),
    )


def scan_no_raw_state(root: Path = EVAL) -> None:
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        check(not path.is_symlink(), f"Phase 6 tree contains a symlink: {path}")
        name = path.name.casefold()
        check(name not in FORBIDDEN_PHASE6_FILENAMES, f"raw V0/archive artifact is prohibited: {path}")
        check(not name.endswith((".db", ".db-wal", ".db-shm", ".sqlite", ".age")), f"raw V0/archive extension is prohibited: {path}")
        with path.open("rb") as handle:
            prefix = handle.read(64)
        check(not prefix.startswith(b"SQLite format 3\x00"), f"tracked SQLite content is prohibited: {path}")
        check(not prefix.startswith(b"age-encryption.org/v1"), f"tracked encrypted archive content is prohibited: {path}")


def intervention_totals(events: list[dict[str, Any]]) -> dict[str, Any]:
    by_card: defaultdict[str, dict[str, int]] = defaultdict(lambda: {"event_count": 0, "minutes": 0})
    by_taxonomy: defaultdict[str, dict[str, int]] = defaultdict(lambda: {"event_count": 0, "minutes": 0})
    for event in events:
        for bucket, key in [(by_card, event["card_id"]), (by_taxonomy, event["taxonomy"])]:
            bucket[key]["event_count"] += 1
            bucket[key]["minutes"] += event["minutes"]
    return {
        "event_count": len(events),
        "minutes": sum(event["minutes"] for event in events),
        "by_card": [
            {"card_id": key, **value} for key, value in sorted(by_card.items())
        ],
        "by_taxonomy": [
            {"taxonomy": key, **value}
            for key, value in sorted(by_taxonomy.items())
        ],
    }


def validate_lane(document: dict[str, Any]) -> list[str]:
    validate(document, schema("lane-assignment"), "lane assignment")
    expected = ALL_CARDS if document["lane"] == "cold-clone" else WARM_CARDS
    exact_cards(document["cards"], expected, "lane assignment")
    if document["lane"] == "cold-clone":
        check(document["warm_capture"] is None, "cold lane cannot bind warm capture")
        check(document["baseline"]["kind"] == "phase5-cold-baseline", "cold lane must bind Phase 5 baseline")
    else:
        check(document["warm_capture"] is not None, "warm lane requires external capture identity")
        check(document["baseline"]["kind"] == "warm-v0-supplement", "warm lane must bind warm supplement")
    check(document["assignment_sha256"] == canonical_digest(document, "assignment_sha256"), "lane assignment digest mismatch")
    return expected


def validate_condition(document: dict[str, Any], lane: dict[str, Any], artifact_digests: dict[str, str]) -> None:
    validate(document, schema("condition-lock"), "condition lock")
    check(document["condition_identity_sha256"] == canonical_digest(document, "condition_identity_sha256"), "condition identity digest mismatch")
    check(document["pilot_id"] == lane["pilot_id"] and document["lane_id"] == lane["lane_id"], "condition/lane identity mismatch")
    check(document["starting_revision"] == lane["starting_revision"] and document["starting_tree"] == lane["starting_tree"], "condition changed starting identity")
    capture_sha = None if lane["warm_capture"] is None else lane["warm_capture"]["sha256"]
    check(document["warm_capture_sha256"] == capture_sha, "condition warm-capture identity mismatch")
    expected = lane["cards"]
    exact_cards(document["prompts"], expected, "condition prompts")
    exact_cards(document["acceptance_commands"], expected, "condition acceptance commands")
    tool_names = [tool["name"] for tool in document["tools"]]
    check(len(tool_names) == len(set(tool_names)), "condition tool names are not unique")
    check(set(document["enabled_tools"]) <= set(tool_names), "condition enables undeclared tool")
    check(len(document["enabled_tools"]) == len(set(document["enabled_tools"])), "condition repeats enabled tool")
    for prompt in document["prompts"]:
        check(artifact_digests.get(prompt["artifact"]) == prompt["sha256"], f"prompt is outside authenticated packet: {prompt['artifact']}")
        check(
            artifact_digests.get(prompt["authentication_artifact"])
            == prompt["authentication_sha256"],
            f"prompt authentication is outside packet custody: {prompt['authentication_artifact']}",
        )
    for command in document["acceptance_commands"]:
        check(command["argv"][0] in document["enabled_tools"], f"{command['card_id']} acceptance executable is not enabled")
    limits = {item["card_id"]: item["seconds"] for item in document["time_limits"]}
    if lane["lane"] == "cold-clone":
        exact_cards(document["time_limits"], ["P3", "P6"], "condition time limits")
        check(limits == {"P3": 300, "P6": 300}, "cold lane must preserve exact P3/P6 five-minute limits")
    else:
        check(not limits, "warm P0/P1 lane cannot invent fresh-agent time limits")


def validate_cold_condition_against_phase5(
    document: dict[str, Any], lane: dict[str, Any]
) -> None:
    packet = ROOT / "tests/evals/v1-phase5/evidence" / lane["pilot_id"]
    environment = load_json(packet / "environment.json")
    baseline = load_json(packet / "baseline-result.json")
    check(document["card_catalog_sha256"] == baseline["card_set_sha256"], "cold condition changed Phase 5 card catalog")
    check(document["starting_revision"] == baseline["starting_revision"], "cold condition changed Phase 5 starting revision")
    for field in [
        "model",
        "reasoning",
        "operating_system",
        "architecture",
        "tools",
        "enabled_tools",
        "permissions",
        "evaluator_id",
        "acceptance_commands",
    ]:
        check(document[field] == environment[field], f"cold condition changed Phase 5 {field}")


def validate_subject(
    document: dict[str, Any], lane: dict[str, Any], artifact_digests: dict[str, str],
    packet: Path,
) -> None:
    validate(document, schema("candidate-subject"), "evaluation subject")
    check(document["subject_identity_sha256"] == canonical_digest(document, "subject_identity_sha256"), "subject identity digest mismatch")
    check(document["pilot_id"] == lane["pilot_id"] and document["lane_id"] == lane["lane_id"], "subject/lane identity mismatch")
    check(
        document["base_revision"] == lane["starting_revision"]
        and document["base_tree"] == lane["starting_tree"],
        "subject does not bind the lane base revision/tree",
    )
    roles = [artifact["role"] for artifact in document["artifacts"]]
    paths = [artifact["path"] for artifact in document["artifacts"]]
    check(len(paths) == len(set(paths)), "subject contains duplicate artifact paths")
    for artifact in document["artifacts"]:
        check(artifact_digests.get(artifact["path"]) == artifact["sha256"], f"subject artifact is outside authenticated packet: {artifact['path']}")
    if document["kind"] == "candidate":
        required = {"core-binary", "evaluation-payload-index", "template-set", "pilot-candidate-bundle", "capability-asset"}
        check(required <= set(roles), f"candidate subject lacks required roles: {sorted(required - set(roles))}")
        if lane["lane"] == "warm-v0-copy":
            check("bridge-binary" in roles, "warm candidate subject lacks bridge identity")
        capability_artifacts = {artifact["path"] for artifact in document["artifacts"] if artifact["role"] == "capability-asset"}
        check(
            len(document["capability_paths"])
            == len(set(document["capability_paths"])),
            "candidate capability paths are not unique",
        )
        check(set(document["capability_paths"]) == capability_artifacts, "candidate capability path set is incomplete")
        bundles = [
            artifact
            for artifact in document["artifacts"]
            if artifact["role"] == "pilot-candidate-bundle"
        ]
        check(len(bundles) == 1, "candidate subject must bind exactly one Git bundle")
        bundle = bundles[0]
        bundle_path = contained_member(packet, bundle["path"], "candidate Git bundle")
        check(
            artifact_digests.get(bundle["path"]) == bundle["sha256"],
            "candidate Git bundle is not digest-bound by the packet manifest",
        )
        with tempfile.TemporaryDirectory(prefix="phase6-candidate-git-") as temporary:
            repository = Path(temporary) / "candidate.git"
            run(["git", "init", "--bare", str(repository)])
            run(["git", "-C", str(repository), "bundle", "verify", str(bundle_path)])
            heads = run(["git", "bundle", "list-heads", str(bundle_path)]).decode("utf-8").splitlines()
            matching_refs = [
                line.split(" ", 1)[1]
                for line in heads
                if line.split(" ", 1)[0] == document["source_revision"] and " " in line
            ]
            check(matching_refs, "candidate commit is not advertised by the digest-bound bundle")
            run(
                [
                    "git",
                    "-C",
                    str(repository),
                    "fetch",
                    "--no-tags",
                    str(bundle_path),
                    f"{matching_refs[0]}:refs/phase6/candidate",
                ]
            )
            candidate_commit = run(
                ["git", "-C", str(repository), "rev-parse", "refs/phase6/candidate^{commit}"]
            ).decode("ascii").strip()
            candidate_tree = run(
                ["git", "-C", str(repository), "rev-parse", "refs/phase6/candidate^{tree}"]
            ).decode("ascii").strip()
            check(candidate_commit == document["source_revision"], "bundle resolved a different candidate commit")
            check(candidate_tree == document["source_tree"], "bundle resolved a different candidate tree")
            base_tree = run(
                ["git", "-C", str(repository), "rev-parse", f"{document['base_revision']}^{{tree}}"]
            ).decode("ascii").strip()
            check(base_tree == document["base_tree"], "bundle lane base tree mismatch")
            run(
                [
                    "git",
                    "-C",
                    str(repository),
                    "merge-base",
                    "--is-ancestor",
                    document["base_revision"],
                    document["source_revision"],
                ]
            )
            capability_artifacts_by_path = {
                artifact["path"]: artifact
                for artifact in document["artifacts"]
                if artifact["role"] == "capability-asset"
            }
            for capability in document["capability_paths"]:
                relative_name(capability, "candidate capability path")
                tree_output = run(
                    [
                        "git",
                        "-C",
                        str(repository),
                        "ls-tree",
                        "-z",
                        "--full-tree",
                        document["source_revision"],
                        "--",
                        capability,
                    ]
                )
                entries = [entry for entry in tree_output.split(b"\0") if entry]
                check(
                    len(entries) == 1 and b"\t" in entries[0],
                    f"candidate capability path is missing or ambiguous: {capability}",
                )
                metadata, resolved_path = entries[0].split(b"\t", 1)
                try:
                    mode, kind, blob_oid = metadata.decode("ascii").split(" ")
                    resolved = resolved_path.decode("utf-8")
                except (UnicodeDecodeError, ValueError) as error:
                    raise VerificationError(
                        f"candidate capability tree entry is malformed: {capability}"
                    ) from error
                check(resolved == capability, f"candidate capability resolved a different path: {capability}")
                check(
                    mode in {"100644", "100755"} and kind == "blob",
                    f"candidate capability path is not a regular file: {capability}",
                )
                blob = run(
                    ["git", "-C", str(repository), "cat-file", "blob", blob_oid]
                )
                blob_sha256 = sha256_bytes(blob)
                artifact = capability_artifacts_by_path[capability]
                packet_member = contained_member(
                    packet, capability, "candidate capability packet artifact"
                )
                packet_sha256 = sha256_file(packet_member)
                check(
                    blob_sha256
                    == packet_sha256
                    == artifact["sha256"]
                    == artifact_digests.get(capability),
                    f"candidate capability bytes differ between Git and packet custody: {capability}",
                )


def validate_interventions(document: dict[str, Any], lane: dict[str, Any]) -> None:
    validate(document, schema("intervention-log"), "intervention log")
    check(document["pilot_id"] == lane["pilot_id"] and document["lane_id"] == lane["lane_id"], "intervention/lane identity mismatch")
    check(document["totals"] == intervention_totals(document["events"]), "intervention totals are incomplete")
    check(all(event["card_id"] in lane["cards"] for event in document["events"]), "intervention cites card outside lane")
    check(document["intervention_log_sha256"] == canonical_digest(document, "intervention_log_sha256"), "intervention log digest mismatch")


def validate_hint_leakage(
    result: dict[str, Any], subject: dict[str, Any], condition: dict[str, Any],
    packet: Path, artifact_visibility: dict[str, str]
) -> None:
    cards = {record["card_id"]: record for record in result["cards"]}
    locked_prompts = {record["card_id"]: record for record in condition["prompts"]}
    for card_id in ("P3", "P6"):
        held_out = cards[card_id]["held_out"]
        check(held_out is not None, f"{card_id} candidate lacks fresh-agent visibility record")
        check(set(held_out["visible_paths"]).isdisjoint(held_out["evaluator_only_paths"]), f"{card_id} agent/evaluator visibility overlaps")
        check(all(not path.startswith("tests/evals/") and "/evidence/" not in path for path in held_out["visible_paths"]), f"{card_id} exposed evaluator evidence to fresh agent")
        check(
            held_out["prompt_artifact"] == locked_prompts[card_id]["artifact"],
            f"{card_id} held-out run did not use the authenticated condition prompt",
        )
        prompt_path = contained_member(packet, locked_prompts[card_id]["artifact"], f"{card_id} held-out prompt")
        check(artifact_visibility.get(held_out["prompt_artifact"]) == "evaluator-only", f"{card_id} prompt custody is not evaluator-only")
        prompt = prompt_path.read_text(encoding="utf-8").casefold()
        for capability in subject["capability_paths"]:
            check(capability.casefold() not in prompt, f"{card_id} prompt leaks capability path")
            descriptive = [
                token
                for token in re.split(r"[^a-z0-9]+", PurePosixPath(capability).stem.casefold())
                if len(token) >= 3
            ]
            if descriptive:
                normalized_prompt = " ".join(re.findall(r"[a-z0-9]+", prompt))
                check(
                    " ".join(descriptive) not in normalized_prompt,
                    f"{card_id} prompt descriptively leaks capability identity",
                )
        for path in held_out["evaluator_only_paths"]:
            check(path.casefold() not in prompt, f"{card_id} prompt leaks evaluator-only evidence path")
        check("original correction" not in prompt and "repair is" not in prompt, f"{card_id} prompt leaks correction content")


def validate_result(
    document: dict[str, Any], lane: dict[str, Any], condition: dict[str, Any],
    subject: dict[str, Any], interventions: dict[str, Any], artifact_digests: dict[str, str],
) -> None:
    validate(document, schema("candidate-result"), "Phase 6 result")
    check(document["result_sha256"] == canonical_digest(document, "result_sha256"), "result digest mismatch")
    check(document["pilot_id"] == lane["pilot_id"] and document["lane_id"] == lane["lane_id"], "result/lane identity mismatch")
    check(document["condition_identity_sha256"] == condition["condition_identity_sha256"], "result condition identity mismatch")
    check(document["subject_identity_sha256"] == subject["subject_identity_sha256"], "result subject identity mismatch")
    exact_cards(document["cards"], lane["cards"], "Phase 6 result")
    check(document["intervention_log_sha256"] == interventions["intervention_log_sha256"], "result intervention identity mismatch")
    check(artifact_digests.get(document["intervention_log"]) == sha256_file(Path(interventions["_path"])), "result intervention artifact digest mismatch")
    started = parse_time(document["started_at"], "result.started_at")
    completed = parse_time(document["completed_at"], "result.completed_at")
    check(started <= completed, "result completes before it starts")
    for event in interventions["events"]:
        timestamp = parse_time(event["timestamp"], "intervention.timestamp")
        check(started <= timestamp <= completed, "intervention falls outside result interval")
    for card in document["cards"]:
        commands = {
            item["card_id"]: json.dumps(
                {"argv": item["argv"]}, sort_keys=True, separators=(",", ":")
            )
            for item in condition["acceptance_commands"]
        }
        validate_evidence_references(
            card["evidence"], artifact_digests, f"{card['card_id']} result"
        )
        if card["outcome"] == "inapplicable":
            check(card["card_id"] == "P1" and card["finding"].strip(), "only P1 may be inapplicable with a finding")
            check(card["acceptance_command"] == "inapplicable", "inapplicable P1 has executable acceptance command")
            check(card["finding_evidence"], "P1 finding lacks custody evidence")
            validate_evidence_references(
                card["finding_evidence"], artifact_digests, "P1 finding"
            )
        else:
            check(not card["finding"], f"{card['card_id']} contains contradictory finding")
            check(not card["finding_evidence"], f"{card['card_id']} contains contradictory finding evidence")
            check(card["acceptance_command"] == commands[card["card_id"]], f"{card['card_id']} result changed locked acceptance argv")
        if document["run_kind"] == "candidate":
            check(card["outcome"] in {"passed", "inapplicable"}, f"candidate acceptance failed: {card['card_id']}")
    validate_negative_conditions(document["negative_conditions"], artifact_digests)


def validate_negative_conditions(
    records: list[dict[str, Any]], artifact_digests: dict[str, str]
) -> None:
    checks = {item["condition"]: item for item in records}
    check(len(checks) == len(records), "negative-condition set contains duplicates")
    check(set(checks) == MANDATORY_NEGATIVES, "mandatory negative-condition set is incomplete")
    check(all(item["outcome"] == "clear" for item in checks.values()), "candidate has a failed mandatory negative condition")
    for item in records:
        validate_evidence_references(
            item["evidence"], artifact_digests, f"negative condition {item['condition']}"
        )


def authenticated_phase5_result(lane: dict[str, Any]) -> dict[str, Any]:
    packet = ROOT / "tests/evals/v1-phase5/evidence" / lane["pilot_id"]
    manifest_path = packet / "packet-manifest.json"
    authentication = load_json(packet / "authentication.json")
    manifest = load_json(manifest_path)
    artifacts = {item["path"]: item["sha256"] for item in manifest["artifacts"]}
    check(len(artifacts) == len(manifest["artifacts"]), "Phase 5 manifest repeats artifact paths")
    check(
        authentication["statement"]["packet_manifest_sha256"]
        == sha256_file(manifest_path),
        "Phase 5 authentication does not bind its packet manifest",
    )
    check(
        authentication["statement"]["starting_revision"] == lane["starting_revision"],
        "Phase 5 authentication differs from lane base revision",
    )
    result_path = packet / "baseline-result.json"
    check(
        artifacts.get("baseline-result.json") == sha256_file(result_path),
        "Phase 5 result is outside authenticated manifest custody",
    )
    result = load_json(result_path)
    check(
        result["result_sha256"] == canonical_digest(result, "result_sha256"),
        "Phase 5 baseline result self-digest mismatch",
    )
    return result


def validate_comparison_candidate_side(
    document: dict[str, Any], lane: dict[str, Any], condition: dict[str, Any],
    subject: dict[str, Any], candidate_result: dict[str, Any],
) -> None:
    validate(document, schema("comparison-report"), "comparison report")
    check(document["comparison_sha256"] == canonical_digest(document, "comparison_sha256"), "comparison digest mismatch")
    check(document["pilot_id"] == lane["pilot_id"] and document["lane_id"] == lane["lane_id"], "comparison/lane identity mismatch")
    check(document["baseline_condition_identity_sha256"] == document["candidate_condition_identity_sha256"] == condition["condition_identity_sha256"], "baseline/candidate conditions are not identical")
    check(document["candidate_subject_identity_sha256"] == subject["subject_identity_sha256"], "comparison candidate subject mismatch")
    exact_cards(document["cards"], lane["cards"], "comparison report")
    candidate_outcomes = {
        card["card_id"]: card["outcome"] for card in candidate_result["cards"]
    }
    for card in document["cards"]:
        check(
            card["candidate_outcome"] == candidate_outcomes[card["card_id"]],
            f"comparison candidate outcome differs from signed candidate result: {card['card_id']}",
        )


def validate_comparison(
    document: dict[str, Any], lane: dict[str, Any], condition: dict[str, Any],
    subject: dict[str, Any], candidate_result: dict[str, Any],
    baseline_result: dict[str, Any], artifact_digests: dict[str, str],
) -> None:
    validate_comparison_candidate_side(
        document, lane, condition, subject, candidate_result
    )
    baseline_outcomes = {
        card["card_id"]: card["outcome"] for card in baseline_result["cards"]
    }
    if lane["lane"] == "cold-clone":
        check(
            document["baseline_subject_identity_sha256"]
            == baseline_result["evaluation_subject"]["sha256"],
            "comparison baseline subject differs from authenticated Phase 5 subject",
        )
    cards = document["cards"]
    for card in cards:
        check(
            card["baseline_outcome"] == baseline_outcomes[card["card_id"]],
            f"comparison baseline outcome differs from authenticated baseline result: {card['card_id']}",
        )
        check(
            not (
                card["baseline_outcome"] == "passed"
                and card["candidate_outcome"] != "passed"
            ),
            f"functional regression on {card['card_id']}",
        )
        check(
            card["candidate_outcome"] in {"passed", "inapplicable"},
            f"candidate comparison failed on {card['card_id']}",
        )
    derived_no_regression = all(
        not (
            card["baseline_outcome"] == "passed"
            and card["candidate_outcome"] != "passed"
        )
        for card in cards
    )
    check(
        document["no_functional_regression"] is derived_no_regression,
        "comparison regression claim is not derived from authenticated outcomes",
    )
    derived_improvement = [
        card["card_id"]
        for card in cards
        if card["baseline_outcome"] == "failed"
        and card["candidate_outcome"] == "passed"
    ]
    check(derived_improvement, "comparison lacks a derived failed-to-passed improvement")
    check(
        document["improvement"]["kind"] == "outcome"
        and document["improvement"]["cards"] == derived_improvement,
        "comparison improvement is asserted instead of derived from authenticated outcomes",
    )
    validate_evidence_references(
        document["improvement"]["evidence"], artifact_digests,
        "comparison improvement",
    )


def validate_manifest(packet: Path) -> tuple[dict[str, Any], dict[str, str], dict[str, str]]:
    manifest = load_json(contained_member(packet, "packet-manifest.json", "packet manifest"))
    validate(manifest, schema("packet-manifest"), "packet manifest")
    paths = [entry["path"] for entry in manifest["artifacts"]]
    check(len(paths) == len(set(paths)), "packet manifest contains duplicate paths")
    required = {"lane-assignment.json", "condition.json", "subject.json", "interventions.json", "result.json"}
    check(required <= set(paths), f"packet omits core records: {sorted(required - set(paths))}")
    digests: dict[str, str] = {}
    visibility: dict[str, str] = {}
    for entry in manifest["artifacts"]:
        path = contained_member(packet, entry["path"], "packet artifact")
        digest = sha256_file(path)
        check(digest == entry["sha256"], f"packet artifact digest mismatch: {entry['path']}")
        digests[entry["path"]] = digest
        visibility[entry["path"]] = entry["visibility"]
        lower = entry["path"].casefold()
        check(not any(name in lower for name in FORBIDDEN_PHASE6_FILENAMES), f"packet manifest attempts raw V0/archive custody: {entry['path']}")
    actual = {
        path.relative_to(packet).as_posix()
        for path in packet.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    expected = set(paths) | {"packet-manifest.json", "authentication.json"}
    check(actual == expected, f"packet inventory differs from manifest: missing={sorted(expected-actual)} unlisted={sorted(actual-expected)}")
    return manifest, digests, visibility


def load_external_trust(path: Path | None, expected_sha256: str | None) -> dict[str, dict[str, Any]]:
    check(path is not None and expected_sha256 is not None, "complete Phase 6 evidence requires external trust registry and digest")
    check(path.is_absolute() and path.is_file() and not path.is_symlink(), "external trust registry path is unsafe")
    check(not path.resolve().is_relative_to(ROOT.resolve()), "external trust registry cannot be inside candidate repository")
    check(re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is not None, "external trust digest is malformed")
    check(sha256_file(path) == expected_sha256, "external trust registry digest mismatch")
    document = load_json(path)
    validate(document, load_json(ROOT / "tests/evals/v1-phase5/schemas/trusted-owners.schema.json"), "external trusted owners")
    owners = {owner["owner_id"]: owner for owner in document["owners"]}
    check(len(owners) == len(document["owners"]), "external trust registry contains duplicate owner IDs")
    return owners


def verify_ssh_statement(
    *, owner_id: str, public_key: str, namespace: str,
    statement: dict[str, Any], signature_text: str,
) -> None:
    with tempfile.TemporaryDirectory(prefix="phase6-signature-") as temporary:
        root = Path(temporary)
        allowed = root / "allowed_signers"
        signature = root / "statement.sig"
        allowed.write_text(f"{owner_id} {public_key}\n", encoding="utf-8")
        signature.write_text(signature_text, encoding="utf-8")
        run(
            [
                "ssh-keygen", "-Y", "verify", "-f", str(allowed), "-I",
                owner_id, "-n", namespace, "-s", str(signature),
            ],
            input_bytes=canonical_bytes(statement),
        )


def validate_prompt_authentication_record(
    authentication: dict[str, Any], prompt: dict[str, Any],
    lane: dict[str, Any], result: dict[str, Any],
) -> None:
    validate(
        authentication, schema("prompt-authentication"),
        f"{prompt['card_id']} prompt authentication",
    )
    check(
        authentication["owner_id"] == lane["owner_id"],
        f"{prompt['card_id']} prompt authentication owner mismatch",
    )
    statement = authentication["statement"]
    expected = {
        "pilot_id": lane["pilot_id"],
        "lane_id": lane["lane_id"],
        "card_id": prompt["card_id"],
        "canonical_repository": lane["canonical_repository"],
        "prompt_artifact": prompt["artifact"],
        "prompt_sha256": prompt["sha256"],
    }
    for field, value in expected.items():
        check(
            statement[field] == value,
            f"{prompt['card_id']} pre-candidate prompt statement changed {field}",
        )
    check(
        parse_time(statement["authenticated_at"], "prompt.authenticated_at")
        <= parse_time(result["started_at"], "result.started_at"),
        f"{prompt['card_id']} prompt was not authenticated before candidate execution",
    )


def verify_prompt_authentications(
    condition: dict[str, Any], lane: dict[str, Any], result: dict[str, Any],
    packet: Path, artifact_digests: dict[str, str],
    owners: dict[str, dict[str, Any]],
) -> None:
    check(lane["owner_id"] in owners, "prompt owner is not externally trusted")
    owner = owners[lane["owner_id"]]
    check(
        owner["canonical_repository"] == lane["canonical_repository"],
        "prompt owner repository differs from lane",
    )
    for prompt in condition["prompts"]:
        authentication_path = contained_member(
            packet, prompt["authentication_artifact"],
            f"{prompt['card_id']} prompt authentication",
        )
        check(
            artifact_digests[prompt["authentication_artifact"]]
            == prompt["authentication_sha256"]
            == sha256_file(authentication_path),
            f"{prompt['card_id']} prompt authentication digest mismatch",
        )
        authentication = load_json(authentication_path)
        validate_prompt_authentication_record(authentication, prompt, lane, result)
        statement = authentication["statement"]
        verify_ssh_statement(
            owner_id=lane["owner_id"], public_key=owner["public_key"],
            namespace=authentication["namespace"], statement=statement,
            signature_text=authentication["signature"],
        )


def verify_authentication(
    packet: Path, authentication: dict[str, Any], manifest: dict[str, Any],
    lane: dict[str, Any], condition: dict[str, Any], subject: dict[str, Any],
    result: dict[str, Any], comparison: dict[str, Any] | None, owners: dict[str, dict[str, Any]],
) -> None:
    validate(authentication, schema("signature"), "packet authentication")
    owner_id = authentication["owner_id"]
    check(owner_id == lane["owner_id"] and owner_id in owners, "packet owner is not externally trusted for lane")
    owner = owners[owner_id]
    check(owner["canonical_repository"] == lane["canonical_repository"], "external owner repository differs from lane")
    statement = authentication["statement"]
    check(statement["packet_id"] == manifest["packet_id"], "authentication packet ID mismatch")
    check(statement["pilot_id"] == lane["pilot_id"] and statement["lane_id"] == lane["lane_id"], "authentication lane identity mismatch")
    check(statement["canonical_repository"] == lane["canonical_repository"], "authentication repository mismatch")
    check(statement["packet_manifest_sha256"] == sha256_file(packet / "packet-manifest.json"), "authentication manifest digest mismatch")
    check(statement["condition_identity_sha256"] == condition["condition_identity_sha256"], "authentication condition mismatch")
    check(statement["subject_identity_sha256"] == subject["subject_identity_sha256"], "authentication subject mismatch")
    check(statement["result_sha256"] == result["result_sha256"], "authentication result mismatch")
    expected_comparison = None if comparison is None else comparison["comparison_sha256"]
    check(statement["comparison_sha256"] == expected_comparison, "authentication comparison mismatch")
    check(statement["completed_at"] == result["completed_at"], "authentication completion mismatch")
    check(parse_time(statement["completed_at"], "statement.completed_at") <= parse_time(statement["published_at"], "statement.published_at"), "authenticated result published before completion")
    verify_ssh_statement(
        owner_id=owner_id, public_key=owner["public_key"], namespace=NAMESPACE,
        statement=statement, signature_text=authentication["signature"],
    )


def validate_packet(packet: Path, owners: dict[str, dict[str, Any]]) -> dict[str, Any]:
    manifest, digests, visibility = validate_manifest(packet)
    lane = load_json(contained_member(packet, "lane-assignment.json", "lane assignment"))
    validate_lane(lane)
    check(manifest["pilot_id"] == lane["pilot_id"] and manifest["lane_id"] == lane["lane_id"], "manifest/lane identity mismatch")
    check(digests.get(lane["baseline"]["artifact"]) == lane["baseline"]["sha256"], "lane baseline artifact is outside authenticated packet")
    if lane["warm_capture"] is not None:
        capture_path = contained_member(packet, lane["warm_capture"]["artifact"], "warm capture")
        check(digests.get(lane["warm_capture"]["artifact"]) == lane["warm_capture"]["sha256"], "lane warm capture is outside authenticated packet")
        capture = load_json(capture_path)
        validate(capture, schema("warm-v0-capture"), "warm capture")
        check(capture["capture_sha256"] == canonical_digest(capture, "capture_sha256"), "warm capture self-digest mismatch")
        check(capture["pilot_id"] == lane["pilot_id"] and capture["canonical_repository"] == lane["canonical_repository"], "warm capture owner scope differs from lane")
        check(capture["starting_revision"] == lane["starting_revision"] and capture["starting_tree"] == lane["starting_tree"], "warm capture starting identity differs from lane")
    condition = load_json(contained_member(packet, "condition.json", "condition"))
    subject = load_json(contained_member(packet, "subject.json", "subject"))
    interventions = load_json(contained_member(packet, "interventions.json", "interventions"))
    interventions["_path"] = str(packet / "interventions.json")
    result = load_json(contained_member(packet, "result.json", "result"))
    comparison = None
    if "comparison.json" in digests:
        comparison = load_json(contained_member(packet, "comparison.json", "comparison"))
    validate_condition(condition, lane, digests)
    if lane["lane"] == "cold-clone":
        validate_cold_condition_against_phase5(condition, lane)
    validate_subject(subject, lane, digests, packet)
    validate_interventions({key: value for key, value in interventions.items() if key != "_path"}, lane)
    validate_result(result, lane, condition, subject, interventions, digests)
    verify_prompt_authentications(condition, lane, result, packet, digests, owners)
    if result["run_kind"] == "candidate":
        check(comparison is not None, "candidate packet lacks baseline comparison")
        if lane["lane"] == "cold-clone":
            validate_comparison(
                comparison, lane, condition, subject, result,
                authenticated_phase5_result(lane), digests,
            )
        else:
            validate_comparison_candidate_side(
                comparison, lane, condition, subject, result
            )
    else:
        check(lane["lane"] == "warm-v0-copy", "only warm lane may publish supplemental baseline")
        check(comparison is None, "pre-disclosure warm baseline cannot contain candidate comparison")
    if result["run_kind"] == "candidate" and lane["lane"] == "cold-clone":
        validate_hint_leakage(result, subject, condition, packet, visibility)
    authentication = load_json(contained_member(packet, "authentication.json", "authentication"))
    verify_authentication(packet, authentication, manifest, lane, condition, subject, result, comparison, owners)
    return {
        "pilot_id": lane["pilot_id"],
        "lane_id": lane["lane_id"],
        "lane": lane["lane"],
        "run_kind": result["run_kind"],
        "condition_identity_sha256": condition["condition_identity_sha256"],
        "subject_identity_sha256": subject["subject_identity_sha256"],
        "comparison_baseline_subject_identity_sha256": (
            None
            if comparison is None
            else comparison["baseline_subject_identity_sha256"]
        ),
        "improvement": None if comparison is None else comparison["improvement"],
        "lane_document": lane,
        "condition": condition,
        "subject": subject,
        "result": result,
        "comparison": comparison,
        "artifact_digests": digests,
    }


def validate_index(
    *, require_complete: bool, trusted_registry: Path | None, trusted_sha256: str | None
) -> None:
    index = load_json(EVIDENCE / "index.json")
    validate(index, schema("evidence-index"), "Phase 6 evidence index")
    pilot_ids = [pilot["pilot_id"] for pilot in index["pilots"]]
    check(len(pilot_ids) == len(set(pilot_ids)), "Phase 6 index repeats pilot ID")
    lane_pairs = [(pilot["pilot_id"], lane) for pilot in index["pilots"] for lane in pilot["lanes"]]
    check(len(lane_pairs) == len(set(lane_pairs)), "Phase 6 index repeats pilot lane")
    if index["status"] == "candidate-results-pending":
        check(index["blockers"], "pending Phase 6 index hides blockers")
        check(all(not pilot["packets"] and pilot["status"] != "complete" for pilot in index["pilots"]), "pending Phase 6 index exposes candidate packets or completion")
        actual = {path.name for path in EVIDENCE.iterdir()}
        check(actual == {"index.json"}, "pending Phase 6 index must not contain undisclosed packet directories")
        if require_complete:
            raise PendingEvidence("candidate results are pending")
        print("Phase 6 candidate evidence pending: framework is valid; no acceptance claimed")
        return
    check(not index["blockers"], "complete Phase 6 index retains blockers")
    check(all(pilot["status"] == "complete" and pilot["packets"] for pilot in index["pilots"]), "complete Phase 6 index has incomplete pilot")
    owners = load_external_trust(trusted_registry, trusted_sha256)
    packets: list[dict[str, Any]] = []
    named_paths: set[str] = set()
    for pilot in index["pilots"]:
        for relative in pilot["packets"]:
            check(relative not in named_paths, "Phase 6 index repeats packet path")
            named_paths.add(relative)
            packet = EVIDENCE.joinpath(*relative_name(relative, "packet path").parts)
            check(packet.is_dir() and not packet.is_symlink() and packet.resolve().is_relative_to(EVIDENCE.resolve()), "Phase 6 packet directory is unsafe")
            record = validate_packet(packet, owners)
            check(record["pilot_id"] == pilot["pilot_id"] and record["lane"] in pilot["lanes"], "packet is outside indexed pilot lane")
            packets.append(record)
    for pilot in index["pilots"]:
        for lane in pilot["lanes"]:
            relevant = [packet for packet in packets if packet["pilot_id"] == pilot["pilot_id"] and packet["lane"] == lane]
            kinds = {packet["run_kind"] for packet in relevant}
            required = {"candidate"} if lane == "cold-clone" else {"warm-baseline", "candidate"}
            check(required <= kinds, f"complete index lacks required {pilot['pilot_id']} {lane} packets")
            if lane == "warm-v0-copy":
                baselines = [packet for packet in relevant if packet["run_kind"] == "warm-baseline"]
                candidates = [packet for packet in relevant if packet["run_kind"] == "candidate"]
                check(len(baselines) == 1 and len(candidates) == 1, f"warm lane requires exactly one baseline and candidate packet for {pilot['pilot_id']}")
                baseline = baselines[0]
                candidate = candidates[0]
                check(baseline["condition_identity_sha256"] == candidate["condition_identity_sha256"], "warm baseline/candidate condition identity differs")
                check(candidate["comparison_baseline_subject_identity_sha256"] == baseline["subject_identity_sha256"], "warm candidate comparison does not bind signed warm baseline subject")
                validate_comparison(
                    candidate["comparison"], candidate["lane_document"],
                    candidate["condition"], candidate["subject"],
                    candidate["result"], baseline["result"],
                    candidate["artifact_digests"],
                )
    check(any(packet["improvement"] and packet["improvement"]["cards"] for packet in packets if packet["run_kind"] == "candidate"), "complete Phase 6 evidence lacks concrete improvement")


class PendingEvidence(VerificationError):
    pass


def expect_rejection(label: str, function: Callable[[], None]) -> None:
    try:
        function()
    except VerificationError:
        return
    raise VerificationError(f"negative fixture was accepted: {label}")


def self_test_contracts() -> None:
    digest64 = "a" * 64
    commit40 = "b" * 40
    cold = {
        "schema": "repository-harness-phase6-lane-assignment/v1",
        "pilot_id": "synthetic-pilot",
        "owner_id": "synthetic-owner",
        "canonical_repository": "https://example.com/owner/repository.git",
        "lane_id": "synthetic-cold-lane",
        "lane": "cold-clone",
        "starting_revision": commit40,
        "starting_tree": "c" * 40,
        "baseline": {"kind": "phase5-cold-baseline", "identity": "baseline", "artifact": "baseline.json", "sha256": digest64},
        "warm_capture": None,
        "cards": ALL_CARDS,
        "assignment_sha256": "",
    }
    cold["assignment_sha256"] = canonical_digest(cold, "assignment_sha256")
    validate_lane(cold)
    warm = dict(cold)
    warm.update(
        {
            "lane_id": "synthetic-warm-lane",
            "lane": "warm-v0-copy",
            "baseline": {"kind": "warm-v0-supplement", "identity": "warm", "artifact": "warm.json", "sha256": digest64},
            "warm_capture": {"artifact": "capture.json", "sha256": "d" * 64},
            "cards": WARM_CARDS,
            "assignment_sha256": "",
        }
    )
    warm["assignment_sha256"] = canonical_digest(warm, "assignment_sha256")
    validate_lane(warm)
    unknown = dict(cold)
    unknown["pilot_fix"] = True
    expect_rejection("unknown lane field", lambda: validate_lane(unknown))
    mixed = dict(cold)
    mixed["warm_capture"] = {"artifact": "capture.json", "sha256": digest64}
    mixed["assignment_sha256"] = canonical_digest(mixed, "assignment_sha256")
    expect_rejection("warm capture in cold lane", lambda: validate_lane(mixed))
    missing = dict(cold)
    missing["cards"] = ALL_CARDS[:-1]
    missing["assignment_sha256"] = canonical_digest(missing, "assignment_sha256")
    expect_rejection("omitted P7", lambda: validate_lane(missing))

    events = [
        {
            "card_id": "P6",
            "actor": "synthetic-evaluator",
            "timestamp": "2000-01-01T00:01:00Z",
            "taxonomy": "correction",
            "reason": "synthetic event",
            "minutes": 2,
            "changed_outcome": True,
        }
    ]
    log = {
        "schema": "repository-harness-phase6-intervention-log/v1",
        "pilot_id": cold["pilot_id"],
        "lane_id": cold["lane_id"],
        "run_kind": "candidate",
        "events": events,
        "totals": intervention_totals(events),
        "intervention_log_sha256": "",
    }
    log["intervention_log_sha256"] = canonical_digest(log, "intervention_log_sha256")
    validate_interventions(log, cold)
    bad_totals = deepcopy(log)
    bad_totals["totals"]["minutes"] = 1
    expect_rejection("incomplete intervention totals", lambda: validate_interventions(bad_totals, cold))

    evidence_reference = [{"artifact": "proof.json", "sha256": digest64}]
    artifact_digests = {"proof.json": digest64}
    negative_checks = [
        {
            "condition": condition,
            "outcome": "clear",
            "evidence": deepcopy(evidence_reference),
        }
        for condition in sorted(MANDATORY_NEGATIVES)
    ]
    validate_negative_conditions(negative_checks, artifact_digests)
    missing_negative = negative_checks[:-1]
    expect_rejection(
        "missing mandatory negative condition",
        lambda: validate_negative_conditions(missing_negative, artifact_digests),
    )
    failed_negative = deepcopy(negative_checks)
    failed_negative[0]["outcome"] = "failed"
    expect_rejection(
        "failed mandatory negative condition",
        lambda: validate_negative_conditions(failed_negative, artifact_digests),
    )
    prose_negative = deepcopy(negative_checks)
    prose_negative[0]["evidence"] = "synthetic prose"
    expect_rejection(
        "prose-only negative clearance",
        lambda: validate_negative_conditions(prose_negative, artifact_digests),
    )

    comparison_lane = dict(cold)
    comparison_lane["pilot_id"] = "harness-benchmark-phase5-pilot"
    comparison = {
        "schema": "repository-harness-phase6-comparison/v1",
        "pilot_id": comparison_lane["pilot_id"],
        "lane_id": comparison_lane["lane_id"],
        "baseline_condition_identity_sha256": digest64,
        "candidate_condition_identity_sha256": digest64,
        "baseline_subject_identity_sha256": "8bf677d9c40e50ea02da38322b4a21fe59bd94f55d77ab417b7ea31a73a090a3",
        "candidate_subject_identity_sha256": "f" * 64,
        "cards": [{"card_id": card, "baseline_outcome": "failed" if card == "P6" else "passed", "candidate_outcome": "passed"} for card in ALL_CARDS],
        "no_functional_regression": True,
        "improvement": {
            "kind": "outcome",
            "cards": ["P6"],
            "evidence": deepcopy(evidence_reference),
        },
        "comparison_sha256": "",
    }
    comparison["comparison_sha256"] = canonical_digest(comparison, "comparison_sha256")
    condition = {"condition_identity_sha256": digest64}
    subject = {"subject_identity_sha256": "f" * 64}
    baseline_result = {
        "evaluation_subject": {
            "sha256": comparison["baseline_subject_identity_sha256"]
        },
        "cards": [
            {
                "card_id": card,
                "outcome": "failed" if card == "P6" else "passed",
            }
            for card in ALL_CARDS
        ],
    }
    candidate_result = {
        "cards": [{"card_id": card, "outcome": "passed"} for card in ALL_CARDS]
    }
    validate_comparison(
        comparison, comparison_lane, condition, subject, candidate_result,
        baseline_result, artifact_digests,
    )
    drift = deepcopy(comparison)
    drift["candidate_condition_identity_sha256"] = "0" * 64
    drift["comparison_sha256"] = canonical_digest(drift, "comparison_sha256")
    expect_rejection(
        "condition drift",
        lambda: validate_comparison(
            drift, comparison_lane, condition, subject, candidate_result,
            baseline_result, artifact_digests,
        ),
    )
    regression = deepcopy(comparison)
    regression["cards"][0]["candidate_outcome"] = "failed"
    regression["comparison_sha256"] = canonical_digest(regression, "comparison_sha256")
    expect_rejection(
        "forged candidate comparison outcome",
        lambda: validate_comparison(
            regression, comparison_lane, condition, subject, candidate_result,
            baseline_result, artifact_digests,
        ),
    )
    forged_baseline = deepcopy(comparison)
    forged_baseline["cards"][0]["baseline_outcome"] = "failed"
    forged_baseline["comparison_sha256"] = canonical_digest(
        forged_baseline, "comparison_sha256"
    )
    expect_rejection(
        "forged baseline comparison outcome",
        lambda: validate_comparison(
            forged_baseline, comparison_lane, condition, subject,
            candidate_result, baseline_result, artifact_digests,
        ),
    )
    asserted_improvement = deepcopy(comparison)
    asserted_improvement["improvement"]["cards"] = ["P0", "P6"]
    asserted_improvement["comparison_sha256"] = canonical_digest(
        asserted_improvement, "comparison_sha256"
    )
    expect_rejection(
        "asserted non-derived improvement",
        lambda: validate_comparison(
            asserted_improvement, comparison_lane, condition, subject,
            candidate_result, baseline_result, artifact_digests,
        ),
    )

    with tempfile.TemporaryDirectory(prefix="phase6-negative-") as temporary:
        root = Path(temporary)
        (root / "harness.db").write_bytes(b"SQLite format 3\x00synthetic")
        expect_rejection("tracked raw database", lambda: scan_no_raw_state(root))

    with tempfile.TemporaryDirectory(prefix="phase6-hint-") as temporary:
        packet = Path(temporary)
        prompt = packet / "p6-prompt.md"
        prompt.write_text(
            "Diagnose the comparable failure using normal repository instructions.\n",
            encoding="utf-8",
        )
        held_out = {
            "prompt_artifact": "p6-prompt.md",
            "visible_paths": ["AGENTS.md"],
            "evaluator_only_paths": ["evaluation/repeated-correction.md"],
            "discovery_path": ["AGENTS.md", "target feedback"],
            "time_limit_seconds": 300,
            "completed_seconds": 120,
        }
        hint_result = {
            "cards": [
                {"card_id": "P3", "held_out": held_out},
                {"card_id": "P6", "held_out": held_out},
            ]
        }
        hint_subject = {"capability_paths": ["docs/capabilities/native-check.md"]}
        visibility = {"p6-prompt.md": "evaluator-only"}
        hint_condition = {
            "prompts": [
                {"card_id": "P3", "artifact": "p6-prompt.md"},
                {"card_id": "P6", "artifact": "p6-prompt.md"},
            ]
        }
        validate_hint_leakage(
            hint_result, hint_subject, hint_condition, packet, visibility
        )
        prompt.write_text(
            "Use docs/capabilities/native-check.md to make the repair.\n",
            encoding="utf-8",
        )
        expect_rejection(
            "held-out capability-path leakage",
            lambda: validate_hint_leakage(
                hint_result, hint_subject, hint_condition, packet, visibility
            ),
        )
        prompt.write_text(
            "Use the native check capability to make the repair.\n",
            encoding="utf-8",
        )
        expect_rejection(
            "held-out descriptive capability leakage",
            lambda: validate_hint_leakage(
                hint_result, hint_subject, hint_condition, packet, visibility
            ),
        )
        dummy_condition = deepcopy(hint_condition)
        dummy_condition["prompts"][1]["artifact"] = "dummy.md"
        (packet / "dummy.md").write_text("No hints here.\n", encoding="utf-8")
        expect_rejection(
            "held-out dummy prompt substitution",
            lambda: validate_hint_leakage(
                hint_result, hint_subject, dummy_condition, packet, visibility
            ),
        )


def self_test_duplicate_json_keys() -> None:
    cases = {
        "top-level duplicate": '{"schema":"one","schema":"two"}',
        "nested duplicate": '{"statement":{"pilot_id":"one","pilot_id":"two"}}',
        "escaped-equivalent duplicate": '{"owner_id":"one","owner\\u005fid":"two"}',
        "schema duplicate": '{"type":"object","type":"array"}',
        "signature duplicate": '{"signature":"one","signature":"two"}',
        "baseline-lock duplicate": '{"source_commit":"one","source_commit":"two"}',
    }
    with tempfile.TemporaryDirectory(prefix="phase6-duplicate-json-") as temporary:
        root = Path(temporary)
        for label, payload in cases.items():
            path = root / f"{label.replace(' ', '-')}.json"
            path.write_text(payload, encoding="utf-8")
            expect_rejection(label, lambda path=path: load_json(path))


def self_test_pre_candidate_prompt_binding() -> None:
    digest = "a" * 64
    lane = {
        "pilot_id": "synthetic-pilot",
        "lane_id": "synthetic-cold-lane",
        "owner_id": "synthetic-owner",
        "canonical_repository": "https://example.com/owner/repository.git",
    }
    prompt = {
        "card_id": "P6",
        "artifact": "prompts/P6.md",
        "sha256": digest,
    }
    result = {"started_at": "2000-01-01T00:00:01Z"}
    authentication = {
        "schema": "repository-harness-phase6-prompt-authentication/v1",
        "owner_id": lane["owner_id"],
        "algorithm": "ssh-ed25519",
        "namespace": "repository-harness-phase6-prompt",
        "statement": {
            "schema": "repository-harness-phase6-pre-candidate-prompt/v1",
            "pilot_id": lane["pilot_id"],
            "lane_id": lane["lane_id"],
            "card_id": prompt["card_id"],
            "canonical_repository": lane["canonical_repository"],
            "prompt_artifact": prompt["artifact"],
            "prompt_sha256": prompt["sha256"],
            "authenticated_at": "2000-01-01T00:00:00Z",
            "candidate_not_disclosed": True,
        },
        "signature": "synthetic-detached-signature",
    }
    validate_prompt_authentication_record(authentication, prompt, lane, result)
    late = deepcopy(authentication)
    late["statement"]["authenticated_at"] = "2000-01-01T00:00:02Z"
    expect_rejection(
        "post-candidate prompt authentication",
        lambda: validate_prompt_authentication_record(late, prompt, lane, result),
    )
    substituted = deepcopy(authentication)
    substituted["statement"]["prompt_sha256"] = "b" * 64
    expect_rejection(
        "authenticated prompt substitution",
        lambda: validate_prompt_authentication_record(
            substituted, prompt, lane, result
        ),
    )


def self_test_candidate_bundle_binding() -> None:
    with tempfile.TemporaryDirectory(prefix="phase6-candidate-subject-") as temporary:
        root = Path(temporary)
        source = root / "source"
        packet = root / "packet"
        source.mkdir()
        packet.mkdir()
        run(["git", "init", str(source)])
        run(["git", "-C", str(source), "config", "user.name", "Phase 6 test"])
        run(
            [
                "git", "-C", str(source), "config", "user.email",
                "phase6@example.invalid",
            ]
        )
        (source / "README.md").write_text("base\n", encoding="utf-8")
        run(["git", "-C", str(source), "add", "README.md"])
        run(["git", "-C", str(source), "commit", "-m", "base"])
        base_revision = run(
            ["git", "-C", str(source), "rev-parse", "HEAD^{commit}"]
        ).decode("ascii").strip()
        base_tree = run(
            ["git", "-C", str(source), "rev-parse", "HEAD^{tree}"]
        ).decode("ascii").strip()
        capability = source / "docs/capabilities/native-check.md"
        capability.parent.mkdir(parents=True)
        capability.write_text("durable capability\n", encoding="utf-8")
        run(["git", "-C", str(source), "add", capability.relative_to(source).as_posix()])
        run(["git", "-C", str(source), "commit", "-m", "candidate"])
        candidate_revision = run(
            ["git", "-C", str(source), "rev-parse", "HEAD^{commit}"]
        ).decode("ascii").strip()
        candidate_tree = run(
            ["git", "-C", str(source), "rev-parse", "HEAD^{tree}"]
        ).decode("ascii").strip()
        bundle = packet / "candidate.bundle"
        run(["git", "-C", str(source), "bundle", "create", str(bundle), "HEAD"])

        roles = {
            "bin/core": "core-binary",
            "payload/index.json": "evaluation-payload-index",
            "templates/set.json": "template-set",
            "candidate.bundle": "pilot-candidate-bundle",
            "docs/capabilities/native-check.md": "capability-asset",
        }
        artifact_digests: dict[str, str] = {}
        artifacts: list[dict[str, str]] = []
        for path, role in roles.items():
            member = packet.joinpath(*PurePosixPath(path).parts)
            if path != "candidate.bundle":
                member.parent.mkdir(parents=True, exist_ok=True)
                if role == "capability-asset":
                    member.write_bytes(capability.read_bytes())
                else:
                    member.write_text(f"synthetic {role}\n", encoding="utf-8")
            digest = sha256_file(member)
            artifact_digests[path] = digest
            artifacts.append({"role": role, "path": path, "sha256": digest})
        lane = {
            "pilot_id": "synthetic-pilot",
            "lane_id": "synthetic-cold-lane",
            "lane": "cold-clone",
            "starting_revision": base_revision,
            "starting_tree": base_tree,
        }
        subject = {
            "schema": "repository-harness-phase6-evaluation-subject/v1",
            "pilot_id": lane["pilot_id"],
            "lane_id": lane["lane_id"],
            "kind": "candidate",
            "base_revision": base_revision,
            "base_tree": base_tree,
            "source_revision": candidate_revision,
            "source_tree": candidate_tree,
            "artifacts": artifacts,
            "capability_paths": ["docs/capabilities/native-check.md"],
            "subject_identity_sha256": "",
        }
        subject["subject_identity_sha256"] = canonical_digest(
            subject, "subject_identity_sha256"
        )
        validate_subject(subject, lane, artifact_digests, packet)

        duplicate_capability = deepcopy(subject)
        duplicate_capability["capability_paths"] = [
            "docs/capabilities/native-check.md",
            "docs/capabilities/native-check.md",
        ]
        duplicate_capability["subject_identity_sha256"] = canonical_digest(
            duplicate_capability, "subject_identity_sha256"
        )
        expect_rejection(
            "duplicate candidate capability declaration",
            lambda: validate_subject(
                duplicate_capability, lane, artifact_digests, packet
            ),
        )

        wrong_base = deepcopy(subject)
        wrong_base["base_tree"] = "0" * 40
        wrong_base["subject_identity_sha256"] = canonical_digest(
            wrong_base, "subject_identity_sha256"
        )
        expect_rejection(
            "candidate lane base-tree drift",
            lambda: validate_subject(wrong_base, lane, artifact_digests, packet),
        )
        wrong_tree = deepcopy(subject)
        wrong_tree["source_tree"] = base_tree
        wrong_tree["subject_identity_sha256"] = canonical_digest(
            wrong_tree, "subject_identity_sha256"
        )
        expect_rejection(
            "candidate bundle tree mismatch",
            lambda: validate_subject(wrong_tree, lane, artifact_digests, packet),
        )
        missing_capability = deepcopy(subject)
        missing_path = "docs/capabilities/missing-check.md"
        missing_member = packet / missing_path
        missing_member.parent.mkdir(parents=True, exist_ok=True)
        missing_member.write_text("packet-only claim\n", encoding="utf-8")
        missing_digest = sha256_file(missing_member)
        missing_digests = dict(artifact_digests)
        missing_digests[missing_path] = missing_digest
        for artifact in missing_capability["artifacts"]:
            if artifact["role"] == "capability-asset":
                artifact["path"] = missing_path
                artifact["sha256"] = missing_digest
        missing_capability["capability_paths"] = [missing_path]
        missing_capability["subject_identity_sha256"] = canonical_digest(
            missing_capability, "subject_identity_sha256"
        )
        expect_rejection(
            "candidate capability absent from resolved tree",
            lambda: validate_subject(
                missing_capability, lane, missing_digests, packet
            ),
        )

        capability_path = "docs/capabilities/native-check.md"
        packet_capability = packet / capability_path
        packet_capability.write_text(
            "unrelated benign packet bytes\n", encoding="utf-8"
        )
        divergent_digest = sha256_file(packet_capability)
        divergent_subject = deepcopy(subject)
        divergent_digests = dict(artifact_digests)
        divergent_digests[capability_path] = divergent_digest
        for artifact in divergent_subject["artifacts"]:
            if artifact["role"] == "capability-asset":
                artifact["sha256"] = divergent_digest
        divergent_subject["subject_identity_sha256"] = canonical_digest(
            divergent_subject, "subject_identity_sha256"
        )
        expect_rejection(
            "candidate capability packet/tree byte divergence",
            lambda: validate_subject(
                divergent_subject, lane, divergent_digests, packet
            ),
        )

        link_oid = run(
            ["git", "-C", str(source), "hash-object", "-w", "--stdin"],
            input_bytes=b"../../README.md",
        ).decode("ascii").strip()
        run(
            [
                "git", "-C", str(source), "update-index", "--add", "--cacheinfo",
                f"120000,{link_oid},{capability_path}",
            ]
        )
        run(["git", "-C", str(source), "commit", "-m", "symlink capability"])
        symlink_revision = run(
            ["git", "-C", str(source), "rev-parse", "HEAD^{commit}"]
        ).decode("ascii").strip()
        symlink_tree = run(
            ["git", "-C", str(source), "rev-parse", "HEAD^{tree}"]
        ).decode("ascii").strip()
        symlink_bundle = packet / "symlink.bundle"
        run(
            ["git", "-C", str(source), "bundle", "create", str(symlink_bundle), "HEAD"]
        )
        symlink_subject = deepcopy(subject)
        symlink_subject["source_revision"] = symlink_revision
        symlink_subject["source_tree"] = symlink_tree
        symlink_digests = dict(divergent_digests)
        symlink_digests["symlink.bundle"] = sha256_file(symlink_bundle)
        for artifact in symlink_subject["artifacts"]:
            if artifact["role"] == "pilot-candidate-bundle":
                artifact["path"] = "symlink.bundle"
                artifact["sha256"] = symlink_digests["symlink.bundle"]
            elif artifact["role"] == "capability-asset":
                artifact["sha256"] = divergent_digest
        symlink_subject["subject_identity_sha256"] = canonical_digest(
            symlink_subject, "subject_identity_sha256"
        )
        expect_rejection(
            "candidate capability symlink mode",
            lambda: validate_subject(
                symlink_subject, lane, symlink_digests, packet
            ),
        )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--framework-only", action="store_true")
    modes.add_argument("--require-candidate-results", action="store_true")
    parser.add_argument("--trusted-owner-registry")
    parser.add_argument("--trusted-owner-registry-sha256")
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    try:
        lock: dict[str, Any] = {}
        proof("closed schemas and exact Phase 5 baseline lock", lambda: lock.update(validate_baseline_lock()))
        proof("Phase 5 worktree immutability", lambda: verify_phase5_immutability(lock))
        proof("exact Phase 5 verifier compatibility digest", lambda: self_test_phase5_compatibility_boundary(lock))
        proof("duplicate-key rejection for every JSON load", self_test_duplicate_json_keys)
        proof("authenticated pre-candidate prompt binding", self_test_pre_candidate_prompt_binding)
        proof("digest-bound candidate bundle and capability paths", self_test_candidate_bundle_binding)
        proof("cold/warm, identity, totals, regression, and raw-state negatives", self_test_contracts)
        proof("exact Phase 6 integration boundary negatives", self_test_release_boundary)
        proof("owned-file and release boundary", validate_release_boundary)
        proof(
            "semantic Phase 7 engineering-only opening and isolated replay",
            verify_phase7_opening_gate,
        )
        proof(
            "Phase 7 fixture contract remains non-production and promotion-blocked",
            verify_phase7_proof_contract_boundary,
        )
        proof(
            "Phase 7 native build receipt has verified diagnostic provenance and remains non-authoritative",
            verify_phase7_build_receipt_boundary,
        )
        proof(
            "Phase 7 execution proof remains local-or-runner-only and non-authoritative",
            verify_phase7_execution_proof_boundary,
        )
        proof("no raw V0 database or archive in Phase 6 custody", scan_no_raw_state)
        registry = Path(arguments.trusted_owner_registry) if arguments.trusted_owner_registry else None
        proof(
            "honest evidence index state",
            lambda: validate_index(
                require_complete=arguments.require_candidate_results,
                trusted_registry=registry,
                trusted_sha256=arguments.trusted_owner_registry_sha256,
            ),
        )
    except PendingEvidence as error:
        print(f"Phase 6 candidate evidence pending: {error}", file=sys.stderr)
        return 2
    except VerificationError as error:
        print(f"Phase 6 verification failed: {error}", file=sys.stderr)
        return 1
    print("Phase 6 framework verification passed; candidate evidence remains pending")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
