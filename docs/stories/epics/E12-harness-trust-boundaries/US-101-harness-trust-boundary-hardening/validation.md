# Validation

## Proof Strategy

Each workstream adds a negative regression that reproduces the prior failure and
a positive regression that preserves intended behavior. The final wrapper runs
all focused regressions plus the existing Rust, replay, installer, release, and
documentation contracts.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Lifecycle target validation, matrix filters, coherence tuple evaluation, context/request classification. |
| Integration | Completion bypass rejection, fresh-proof completion, SQLite query-only enforcement, schema/version drift reporting. |
| E2E | Fresh source bootstrap, focused agent intake, read-only audit, normal implementation task, stale-runtime recovery. |
| Platform | Bash and PowerShell shim parity; native CLI help/version/coherence behavior. |
| Performance | Default intake context and matrix output remain bounded relative to the previous full bootstrap. |
| Logs/Audit | Rejected bypasses create no story mutation or semantic changeset; read-only workflows create no Harness rows. |

## Fixtures

- Fresh schema-13 database with one planned story.
- Story with a passing verify command and one with no command.
- Database copy containing a mutation sentinel table.
- Matching and mismatching executable/release/schema tuples.
- Canonical instruction block rendered through fresh, Bash refresh, PowerShell
  refresh, and Claude import paths.
- Representative tiny/read-only, normal change, high-risk change, and missing-tool
  task fixtures.

## Commands

The final wrapper will be added during implementation. Until then, every commit
runs its focused test plus the relevant existing gates:

```text
cargo fmt --check
cargo test -p harness-cli --locked
cargo clippy -p harness-cli --all-targets --locked -- -D warnings
scripts/validate-changeset-rebuild.sh
tests/core/assert-command-contract.sh
tests/installer/test-install-harness-modes.sh
git diff --check
```

## Acceptance Evidence

- Main synchronized to `3ed8bb6`; release CLI rebuilt as `0.1.15`.
- Local database migrated from schema 10 to schema 13 and contract state became
  `current`.
- Remaining evidence is appended after each independently committed workstream
  and the final release-grade run.
