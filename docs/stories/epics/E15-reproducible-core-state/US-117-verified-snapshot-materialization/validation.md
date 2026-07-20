# Validation

## Proof Strategy

Exercise the materializer with a small snapshot and pre/post-snapshot
changesets, then publish and restore the real core tuple in a disposable path.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Manifest fields, checksum comparison, included-id lookup, ordering. |
| Integration | Included changeset skips; later changeset applies exactly once. |
| E2E | Missing source database restores and matches live logical state. |
| Platform | Bash executes locally; PowerShell contract runs in the platform matrix. |
| Security | Snapshot path/token scans and ownership verifier fail closed. |
| Failure | Tampered snapshot/changeset and existing output leave state untouched. |

## Commands

```text
tests/bootstrap/test-core-state-materialization.sh
scripts/verify-core-snapshot.sh
scripts/verify-materialized-core-parity.sh
scripts/validate-premerge.sh
git diff --check
```

## Acceptance Evidence

- The current published tuple is schema `14`, has snapshot byte SHA-256
  `3a2b30bedc7dc9c373c3788827b67b69c3e2a6bb2b7ad35db62568d194a41a73`,
  and logical SHA-256
  `72267125cbdccff423136c6070ce94c5a11379a53aff7354978309d12b77f387`.
  US-119 compacted the completed epic into this final tuple.
- `tests/bootstrap/test-core-state-materialization.sh` proves incorporated-file
  skipping, later replay, changed-snapshot refusal, changed-JSONL refusal,
  output atomicity, and the PowerShell contract.
- `scripts/verify-materialized-core-parity.sh` rebuilds from tracked inputs and
  matches every durable source table; only `changeset_applied` is excluded as
  epoch-derived replay bookkeeping.
- `replay_preserves_generated_timestamps_for_new_core_state` proves that story,
  dependency, hierarchy, and decision timestamps survive replay exactly.
- `scripts/validate-premerge.sh` passes all 97 Rust tests and the complete
  ownership, bootstrap, protocol, installer, documentation, evaluation, and
  release contract.
