# Validation

## Acceptance Matrix

| Finding | Required proof |
| --- | --- |
| F-014 | Mixed legacy/new links accept a same-second precise post-link trace and reject a pre-link trace, live and after replay. |
| F-015 | A v11 rejected proposal migrates to the same structured reason produced by clean replay. |
| F-016 | Rebuild validation builds the workspace CLI by default, honors an explicit override, and prints the selected executable. |
| F-017 | A later valid verification timestamp rebuilds successfully; focused replay still preserves exact timestamps. |

## Commands

```bash
cargo test -p harness-cli post_review -- --nocapture
cargo test -p harness-cli proof_audit -- --nocapture
cargo test --workspace
cargo fmt --check
cargo clippy --workspace --all-targets -- -D warnings
HARNESS_CLI="$PWD/target/debug/harness-cli" scripts/validate-changeset-rebuild.sh
git diff --check
```

## Acceptance Evidence

- The migration `post_review` regression and current `proof_audit` regressions passed.
- Full workspace passed with 70 Harness CLI and 99 external orchestrators tests.
- Formatting and all-target clippy passed with warnings denied.
- The current workspace CLI rebuilt 57 stories and reported zero entropy.
- The live database also reports zero entropy.
