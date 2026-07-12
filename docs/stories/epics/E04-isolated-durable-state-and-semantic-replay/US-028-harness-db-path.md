# US-028 HARNESS_DB_PATH Database Override

## Status

implemented

## Lane

normal

## Product Contract

`harness-cli` must respect `HARNESS_DB_PATH` as the canonical database path
override for isolated repository workflows. When it is set, every durable command must read and
write only that database path.

## Relevant Product Docs

- `docs/HARNESS.md`
- `docs/HARNESS.md`
- `docs/decisions/0004-sqlite-durable-layer.md`

## Acceptance Criteria

- `HARNESS_DB_PATH=/tmp/run/harness.db scripts/bin/harness-cli init` creates or
  opens only `/tmp/run/harness.db`.
- Query and write commands use `HARNESS_DB_PATH` consistently.
- If both `HARNESS_DB_PATH` and legacy `HARNESS_DB` are set,
  `HARNESS_DB_PATH` wins.
- Existing `HARNESS_DB` behavior remains as a fallback unless explicitly
  removed by a decision.
- CLI help or docs mention `HARNESS_DB_PATH` for isolated runs.

## Design Notes

- Commands: all existing `harness-cli` commands.
- Boundary: `resolve_context()` in the CLI interface.
- Domain rule: root `harness.db` is not the source of truth during isolated
  repository workflows.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-028 --unit 1 --integration 1 --e2e 0 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | Tests for env-var precedence and fallback behavior. |
| Integration | Smoke creates two temp DBs and proves writes land only in `HARNESS_DB_PATH`. |
| E2E | n/a for this CLI-only capability. |
| Platform | macOS/Linux shell smoke with the checked-in binary or cargo-run equivalent. |
| Release | `cargo test --workspace`; `cargo fmt --check`; `cargo clippy --workspace -- -D warnings`. |

## Harness Delta

This story implements the first v0 prerequisite for isolated durable state.

## Evidence

- `cargo test --workspace` passed: 30 tests.
- `cargo fmt --check` passed.
- `cargo clippy --workspace -- -D warnings` passed.
- `cargo build --workspace` passed.
- Rebuilt local `scripts/bin/harness-cli` from `target/release/harness-cli`.
- Isolation smoke with both `HARNESS_DB_PATH` and `HARNESS_DB` set created only
  the `HARNESS_DB_PATH` database, left the legacy path absent, and queried
  `intake_count = 1` from the isolated database.
