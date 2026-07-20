# Validation

## Proof Strategy

Create changesets from the same baseline, apply them in both independent-entity
and same-entity combinations, and inspect both data and revision values after
success or rollback.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Revision starts at zero and advances once for every mutable entity update. |
| Integration | Independent story updates both apply; stale same-story update fails with no partial changeset effects. |
| E2E | CLI `db changeset apply --json` returns `CONFLICT` with run and entity details. |
| Platform | Migration and error-envelope tests run in the existing platform matrix. |
| Performance | Indexed primary-key revision lookup only; no global scan. |
| Logs/Audit | Conflict details are deterministic and do not claim a resolution. |

## Fixtures

- One baseline with two stories and revision `0`.
- Two changesets updating different stories from revision `0`.
- Two changesets updating the same story from revision `0`.
- One legacy unguarded changeset.

## Commands

```text
cargo test -p harness-cli revision_guard
scripts/validate-changeset-rebuild.sh
cargo test --workspace --locked
cargo clippy --workspace --all-targets --locked -- -D warnings
tests/docs/test-doc-contracts.sh
git diff --check
```

## Acceptance Evidence

- `cargo test -p harness-cli revision_guard` passes the same-entity conflict,
  independent-entity merge, atomic rollback, legacy replay, and all five mutable
  entity-family cases.
- `cargo test --workspace --locked` passes all 96 tests.
- `scripts/validate-changeset-rebuild.sh` passes schema `14` replay across four
  fixtures and 22 semantic operations.
- `scripts/validate-premerge.sh` passes the complete repository contract,
  including revision coherence, ownership, source isolation, bootstrap,
  native-protocol, installer, documentation, evaluation, and release checks.
- `cargo clippy --workspace --all-targets --locked -- -D warnings` and
  `git diff --check` pass.
- The PowerShell native-protocol fixture asserts the same structured stale-write
  conflict and remains covered by the five-platform CI matrix.
