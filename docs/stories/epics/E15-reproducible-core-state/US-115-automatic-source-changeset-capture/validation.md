# Validation

## Proof Strategy

Prove behavior at the repository layer and through the real CLI. The negative
consumer case is as important as source auto-capture.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Source/default detection, generated ID shape, unique IDs, failed-write rollback. |
| Integration | A typed source write with no `HARNESS_RUN_ID` creates one parseable changeset containing the expected operation. |
| E2E | Real CLI source fixture captures automatically; consumer fixture does not. |
| Platform | Generated names contain portable characters; PowerShell consumer behavior remains unchanged. |
| Performance | No benchmark required; one small file sync already exists on captured writes. |
| Logs/Audit | Header run ID equals filename identity and operations retain the typed envelope. |

## Fixtures

- Temporary Harness source checkout marker with default `harness.db`.
- Temporary installed-consumer-style repository.
- Explicit isolated database path.
- A write closure that fails before commit.

## Commands

```text
cargo test -p harness-cli automatic_source_changeset
cargo test -p harness-cli failed_logged_write_rolls_back_without_changeset
tests/changesets/test-automatic-source-capture.sh
cargo test --workspace
cargo clippy --workspace -- -D warnings
tests/docs/test-doc-contracts.sh
git diff --check
```

## Acceptance Evidence

Validated on 2026-07-20:

- Four focused Rust tests passed: automatic source capture, unique invocation
  files, consumer isolation, and automatic failed-write rollback.
- The existing explicit-run failed-write rollback test passed.
- The CLI-level source/isolated/consumer fixture passed against both the
  workspace build and the repository-local `scripts/bin/harness-cli`.
- All 94 workspace tests passed.
- Clippy passed for all workspace targets with warnings denied.
- Documentation contracts and `git diff --check` passed.
- Source bootstrap rebuilt and installed the changed CLI before stopping at the
  pre-existing core ownership blocker; the installed binary passed the new
  CLI-level fixture.
