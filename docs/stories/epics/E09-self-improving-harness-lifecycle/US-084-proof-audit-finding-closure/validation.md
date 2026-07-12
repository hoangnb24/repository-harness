# Validation

## Required Proof

| Finding | Executable evidence |
| --- | --- |
| F-018 | Mixed v1/v2 semantic history produces identical live/replay completion. |
| F-019 | Shell test covers default build, explicit override, missing override, and unrelated newer binary. |
| F-020 | A copied repository history with a later verification rebuilds to the later value. |
| F-021 | Latest US-084 detailed trace contains clean JSON arrays and no false errors. |
| F-022 | Missing/garbage timestamps fail; canonical timestamp passes for every proof-checked story. |

## Commands

```bash
cargo test -p harness-cli proof_audit -- --nocapture
scripts/test-validate-changeset-rebuild.sh
cargo test --workspace
cargo clippy --workspace --all-targets -- -D warnings
cargo fmt --check
scripts/validate-changeset-rebuild.sh
git diff --check
```

## Acceptance Evidence

- Both focused `proof_audit` tests passed.
- Validator contract shell tests passed all seven selection/proof scenarios.
- Full workspace passed with 71 Harness CLI and 99 external orchestrators tests.
- Trace 232 is detailed with six clean actions and zero errors.
- Rebuild restored 58 stories and both live/rebuilt audits have zero entropy.
