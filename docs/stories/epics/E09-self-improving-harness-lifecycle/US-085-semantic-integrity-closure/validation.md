# Validation

```bash
cargo test -p harness-cli semantic_integrity -- --nocapture
scripts/test-validate-changeset-rebuild.sh
cargo test --workspace
cargo clippy --workspace --all-targets -- -D warnings
cargo fmt --check
scripts/validate-changeset-rebuild.sh
git diff --check
```

Acceptance requires exact canonical/noncanonical/missing cases for every v2
timestamp family, JSON list shape cases, isolated binary selection, isolated
SQL proof validation, 59-story rebuild, and zero live/rebuilt entropy.

## Acceptance Evidence

- Both focused `semantic_integrity` tests passed.
- Validator contract shell tests passed selection, operation parsing, later
  verification, and direct SQL proof mutations.
- Full workspace passed with 73 Harness CLI and 99 external orchestrators tests.
- Traces 233 and 234 are detailed with actual empty error arrays.
- Rebuild restored 59 stories; both audits have zero entropy.
