# US-109 Execution Plan

Status: **in_progress; implementation complete locally, independent acceptance pending**

## Intake and context limitation

This is a high-risk change because it affects data retention, trust, filesystem
publication, cross-platform behavior, and accepted contracts. The required
`scripts/bootstrap-harness.sh` was run first and failed as expected because the
authoritative core state is unavailable. No empty `harness.db` was initialized.
The matrix query consequently could not run; the committed US-109 packet and
changeset are the durable fallback context under `docs/CONTEXT_RULES.md`.

## Completed implementation sequence

1. Record Decision 0014 without rewriting Decisions 0011–0013 history.
2. Freeze grammar to `inspect`, `export`, `archive`, `version`; remove conversion
   journal, mapping, target mutation, resume, and rollback code/tests.
3. Reuse the core path validator and retain descriptor-safe exact capture.
4. Implement live/archive neutral export and append-only authenticated custody.
5. Add only `harness install --v0-archive-manifest` plus the closed write-once
   receipt; keep core six-command and SQLite-free.
6. Bind receipt commit/resume to the existing Phase 3 recovery transaction.
7. Replace Phase 4 tests/verifier and update Phase 1–3 assertions, workflow,
   schemas, bindings, lifecycle metadata, US-105/US-109, and refactor/test plans.
8. Preserve tracked fixture bytes; all behavioral runs use temporary copies.

## Verification and commit sequence

Run focused archive/export/rejection and core receipt recovery tests, then Phase
1–4 verifiers, `cargo test --workspace --locked --offline`, formatting, clippy
with warnings denied, `scripts/validate-premerge.sh`, `git diff --check`, and a
fixture diff/inventory comparison. Create logical local commits only after the
tree passes. Do not use network, push, publish, create production keys, open a
PR, modify the primary checkout, or start Phase 5.

## Exit criteria

- Two archives of the same frozen source publish to different IDs; the first
  and an abandoned foreign stage remain byte-identical.
- Live and archived exports are exact and retain WAL-only committed data.
- Bridge creates no V1 manifest/recovery/database file.
- Interrupted core install resumes with the exact receipt and fresh mode.
- Windows workflow builds the crate, proves four-command help, and asserts exit
  5 for repository capture.
- US-109 remains `in_progress`; Phase 5, Phase 7, and production remain closed.
