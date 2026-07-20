# Validation

## Commands

```text
tests/ci/test-core-state-rebuild-gate.sh
tests/snapshot/test-core-snapshot-compaction.sh
scripts/verify-materialized-core-parity.sh
scripts/validate-premerge.sh
git diff --check
```

## Acceptance Evidence

- `tests/bootstrap/test-fresh-source-checkout.sh` copies the working source
  without `.git`, `target`, the writable database, or a prebuilt CLI; bootstrap
  builds the CLI and reconstructs the completed `US-119` solely from the tracked
  snapshot and JSONL. Post-baseline replay records repository-relative
  changeset paths so later compaction cannot capture a machine checkout path.
- `.github/workflows/premerge.yml` asserts the writable database is absent and
  bootstraps tracked state before Linux and Windows validation;
  `tests/ci/test-core-state-rebuild-gate.sh` locks in that ordering and proves
  every tracked changeset has `eol=lf`. This keeps manifest-verified JSONL bytes
  identical when Git checks out the repository on Windows with CRLF defaults.
- `tests/snapshot/test-core-snapshot-compaction.sh` proves verified replacement,
  changed logical identity, stale-precondition refusal with an unchanged tuple,
  and successful materialization from the compacted candidate.
- `scripts/verify-core-snapshot.sh` and
  `scripts/verify-materialized-core-parity.sh` pass against the published tuple
  and all post-baseline E15 changesets.
- `scripts/validate-premerge.sh` passes all 97 Rust tests plus fresh checkout,
  worktree conflict/recovery, compaction, ownership, bootstrap, protocol,
  installer, documentation, evaluation, and release checks.
- Final compaction incorporates all ten cutover changesets in a sidecar-free
  `journal_mode=DELETE` snapshot with logical SHA-256
  `72267125cbdccff423136c6070ce94c5a11379a53aff7354978309d12b77f387`.
