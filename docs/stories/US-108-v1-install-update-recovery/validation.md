# US-108 V1 Install, Update, And Recovery Validation

Status: **Implemented, fully validated, and accepted**

## Proof Strategy

Acceptance requires cause-and-effect proof at four boundaries:

1. Invalid or unavailable authentication never constructs a mutation request.
2. A canonical preview digest names every target write, backup, journal, and
   manifest result; the caller can recompute that same digest from the emitted
   `details.operations` array, and a different digest produces zero mutation.
3. Every crash before the last manifest rename leaves no new success manifest
   and can resume or roll back only matching journal-owned images plus any
   retained hard-link witness required to prove a `before_sha256=None` create.
4. Every conflict or host failure exits nonzero, preserves target edits, and
   leaves enough deterministic evidence for the next allowed action.
5. Recovery evidence is bound to the exact repository root instance by the
   pinned root `st_dev`/`st_ino` committed inside the journal body; copying a
   journal into another repository root yields no actionable status and no
   recovery authority.

The Phase 1 and Phase 2 verifiers must pass unchanged. Phase 3 proof does not
claim production promotion, bridge behavior, non-Unix safe handles, or
five-platform parity.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Deterministic operation IDs and preview digests; manifest construction; unresolved markers; monotonic transitions; replace-if-base; managed-block interior replacement; three-way-review tuple; never-auto-patch; journal canonical digest, root identity binding, and path ownership; hard-link witness authority for resume and rollback. |
| Integration | Threshold-signed fixture install/update/scaffold through the real Unix adapter; exact confirmation; backups; manifest-last commit; read-only audit of result; no promoted live adapter. |
| Recovery | Failure after journal prepare, each backup/staged image, each target rename, candidate validation, manifest temporary, manifest rename, journal commit, and all 13 committed-update rollback checkpoints; safe resume/rollback, hard-link witness gating, target-edit conflicts, and zero-mutation downgrade rejection. |
| Idempotency | Repeated preview is byte-identical; repeated confirmed install/update does no duplicate target write; repeated resume/rollback is harmless and deterministic. |
| Negative | Wrong preview digest; absent update manifest; unsupported downgrade/equal-different release; unsafe/link path; target-owned candidate; managed-file base drift; managed-block edit; copied cross-root journal; journal/staged/backup tamper; missing or mismatched hard-link witness; injected I/O failure; no false exit 0/2. |
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
  operation ID, command, release identity, body digest, repository-root
  identity, path, backup, staged image, current post-image, missing hard-link
  witness, forged applied-state create, and fabricated downgrade state.

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

The candidate contains 43 focused Phase 3 Rust test functions: eighteen
recovery unit adversaries and twenty-five signed-release integration tests. The
integration kill matrices interrupt all 18 install, 15 update, and 13
committed-update rollback checkpoints and prove deterministic pre-journal
rerun, journal-owned resume, reverse-order crash-resumable rollback, and
repeated recovery. `harness-core` has 89 passing tests total (41 library unit,
one binary unit, 22 Phase 2 integration, twenty-five Phase 3 integration); the
workspace has 181 passing Rust tests. The Phase 3 mechanical verifier passes
11/11 proof groups.

The focused evidence explicitly includes:

- changed private write bytes under an unchanged accepted preview;
- preview digest recomputed independently from the exact emitted
  `details.operations` array;
- unowned staged paths, missing backups, unsupported kinds, and an incorrect
  manifest kind/disposition rejected before zero filesystem mutation;
- altered journal/staged/manifest bytes with a recomputed unkeyed body hash and
  a nested-operation unknown field;
- rollback with an old but never-applied manifest;
- every committed-update rollback checkpoint, including the durable intent and
  new-manifest-removal gap, with old-manifest restoration last;
- a human edit during interrupted rollback preserved before any later restore;
- fabricated update/fresh/scaffold journals rejected when they broaden
  ownership, before-images, or the one-destination command scope;
- copied interrupted and committed replacement journals from another repository
  root rejected before status can emit an actionable recovery ID or recovery
  can mutate any byte in the receiving tree;
- corrupted staged evidence or a missing required backup in an `applying`
  update journal rejected read-only by probe, so status and ordinary mutators
  return invalid/non-actionable envelopes with no recovery-required action;
- fabricated applied-state resumes and scaffold/fresh-manifest rollbacks
  refused without the retained hard-link witness that pins the create inode;
- fabricated recovery downgrade rejected before any target or manifest mutation;
- current-root pathname replacement rejected before rollback mutation or
  success;
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
full `scripts/validate-premerge.sh`. Independent security (`gpt-5.4`, high
reasoning) and behavior (`gpt-5.6-sol`, medium reasoning) reviewers accepted
exact candidate `1f957ce`; it was integrated as `8e67593` with identical Git
tree `9cd22cdb24d2`. Phase 4 is unblocked but not started. No production
promotion or Phase 7 opening is claimed.

Rollback deliberately reloads the authenticated release before trusting local
journal and backup evidence. If that live authority is unavailable or has a
different identity, rollback refuses before mutation. This preserves the
forged-journal boundary; Phase 3 does not claim externally independent rollback
authority. Arbitrary same-UID malicious processes remain out of scope because
they can already delete or overwrite repository targets directly; Phase 3 is
proving the crash/race/corruption boundary, not secret local rollback tokens.
