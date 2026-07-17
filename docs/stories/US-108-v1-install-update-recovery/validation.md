# US-108 V1 Install, Update, And Recovery Validation

Status: **Implemented and locally validated; orchestrator acceptance pending**

## Proof Strategy

Acceptance requires cause-and-effect proof at four boundaries:

1. Invalid or unavailable authentication never constructs a mutation request.
2. A canonical preview digest names every target write, backup, journal, and
   manifest result; a different digest produces zero mutation.
3. Every crash before the last manifest rename leaves no new success manifest
   and can resume or roll back only matching journal-owned images.
4. Every conflict or host failure exits nonzero, preserves target edits, and
   leaves enough deterministic evidence for the next allowed action.

The Phase 1 and Phase 2 verifiers must pass unchanged. Phase 3 proof does not
claim production promotion, bridge behavior, non-Unix safe handles, or
five-platform parity.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Deterministic operation IDs and preview digests; manifest construction; unresolved markers; monotonic transitions; replace-if-base; managed-block interior replacement; three-way-review tuple; never-auto-patch; journal canonical digest and path ownership. |
| Integration | Threshold-signed fixture install/update/scaffold through the real Unix adapter; exact confirmation; backups; manifest-last commit; read-only audit of result; no promoted live adapter. |
| Recovery | Failure after journal prepare, each backup/staged image, each target rename, candidate validation, manifest temporary, manifest rename, and journal commit; safe resume/rollback and target-edit conflicts. |
| Idempotency | Repeated preview is byte-identical; repeated confirmed install/update does no duplicate target write; repeated resume/rollback is harmless and deterministic. |
| Negative | Wrong preview digest; absent update manifest; unsupported downgrade/equal-different release; unsafe/link path; target-owned candidate; managed-file base drift; managed-block edit; journal/staged/backup tamper; injected I/O failure; no false exit 0/2. |
| Boundary | Exact six commands; no V0/SQLite/process dependency; bridge entrypoints/workflow absent; production workflow still unpromoted; non-Unix mutation fails closed. |

## Fixtures

- Accepted Phase 1 signed core index, detached envelopes, test bootstrap roots,
  canonical path ledger, and indexed decision/story bytes.
- Temporary fresh and existing V1 repositories created per test.
- Managed-file manifests with equal base, changed recorded current, and
  target-owned roles.
- Managed-block files with stable prefix/suffix, one marker pair, unchanged
  base, and human-edited interior.
- Journals interrupted at every durable boundary plus copies with changed
  operation ID, command, release identity, body digest, path, backup, staged
  image, and current post-image.

Fixture keys remain test-only and never enter the live production adapter.

## Commands

```bash
scripts/verify-v1-phase1-contracts.sh
scripts/verify-v1-phase2-core.sh
scripts/verify-v1-phase3-recovery.sh
cargo fmt --all -- --check
cargo check --workspace --locked --offline
cargo test --workspace --locked --offline
cargo clippy --workspace --all-targets --locked --offline -- -D warnings
git diff --check
scripts/validate-premerge.sh
git status --short -- .harness repomix-output.xml crates/harness-cli \
  scripts/schema scripts/install-harness.sh scripts/install-harness.ps1 \
  scripts/harness-install-files.txt '.github/workflows/*bridge*' \
  'scripts/bin/harness-v0-migrate*'
```

## Acceptance Evidence

The candidate contains 26 focused Phase 3 Rust test functions: ten recovery
unit adversaries and sixteen signed-release integration tests. The integration
kill matrix interrupts all 18 install and 15 update checkpoints and proves
deterministic pre-journal rerun, journal-owned resume, repeated resume, rollback,
and repeated rollback. `harness-core` has 72 passing tests total (33 library
unit, one binary unit, 22 Phase 2 integration, sixteen Phase 3 integration); the
workspace has 164 passing Rust tests. The Phase 3 mechanical verifier passes
11/11 proof groups.

The focused evidence explicitly includes:

- changed private write bytes under an unchanged accepted preview;
- unowned staged paths, missing backups, unsupported kinds, and an incorrect
  manifest kind/disposition rejected before zero filesystem mutation;
- altered journal/staged/manifest bytes with a recomputed unkeyed body hash and
  a nested-operation unknown field;
- rollback with an old but never-applied manifest;
- an intervening final-component swap preserved by compensating exchange;
- read-only status/audit and exact-rerun behavior around partial targets;
- commit- and resume-time authenticated payload identity changes rejected before
  the sole manifest commit;
- resume skips already applied operations and preserves their inode and bytes;
- downgrade and mixed-invalid repositories refused before journaling or mutation;
- repeat scaffold idempotency;
- one-destination scaffold recovery with no adjacent template or target-owned
  file mutation;
- fresh brownfield ownership/mode and converted-mode receipt preservation; and
- managed-file three-way conflict plus managed-block prefix/suffix preservation.

On 2026-07-17, the same worktree passed locked offline fmt/check/test/clippy,
the unchanged Phase 1 verifier (9/9 groups), the unchanged Phase 2 verifier
(11/11 groups), the Phase 3 verifier (11/11 groups), `git diff --check`, and
full `scripts/validate-premerge.sh`. No commit, production promotion, or Phase
4/7 opening is claimed; orchestrator acceptance remains the outstanding gate.
