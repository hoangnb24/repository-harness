# Validation

## Proof Strategy

Each review item receives a focused regression. Final proof also rebuilds a
fresh database and compares lifecycle state and audit results with the live
source.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | RFC3339 offsets, Unicode grouping/truncation, exact rejection reason |
| Integration | audit episode replacement, resolver ordering, exact timestamp replay |
| E2E | lightweight copied story can complete; live/rebuilt recurrence parity |
| Platform | Bash rebuild validator and CLI release build |
| Logs/Audit | rebuilt E09 proof and entropy match expected durable state |

## Fixtures

- Isolated SQLite repositories with controlled event timestamps and stable uids.
- Temporary external orchestrators repositories for isolated and lightweight preparation.
- Committed E09 changesets for full rebuild validation.

## Commands

```bash
cargo test -p harness-cli review_finding -- --nocapture
scripts/validate-changeset-rebuild.sh
cargo fmt --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
git diff --check
```

## Acceptance Evidence

- Four focused CLI review-finding regressions passed.
- One focused lightweight-state regression passed.
- The full Harness CLI suite passed; historical consumer integration covered
  lightweight copied-state behavior.
- Rebuild restored 56 stories and passing US-073 through US-081 proof.
- Live and rebuilt audits both reported entropy `0/100` after US-082 completion.
- Formatting, all-target clippy, Bash syntax, glossary consistency, and diff
  checks passed.
