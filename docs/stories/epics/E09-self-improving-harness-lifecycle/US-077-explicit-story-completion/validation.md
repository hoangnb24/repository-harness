# Validation

## Proof Strategy

Exercise every eligibility and transaction branch with feature-specific
verification commands, then replay completion from a separate changeset into a
fresh database.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Status, intake, trace, and resolver-target eligibility; closure result summaries; and deterministic resolution text. |
| Integration | Planned/retired/missing command refusal; missing/wrong/early or local-id-only trace refusal; pass/fail; references untouched; proposed/rejected/differently closed resolver abort; stable-trace-count baseline capture; self-closed idempotency; multiple accepted items close atomically. |
| E2E | Symphony copied story moves through in-progress, implementation, completed trace, explicit complete, review, merge, and sync with correct root state. |
| Platform | Completion changeset rebuild preserves proof, story status, resolver, closure, and pending outcome. |
| Performance | One completion transaction uses indexed relationships and does not rescan unrelated backlog. |
| Logs/Audit | Failure closes nothing; pass emits one explainable completion event and resolution evidence. |

## Fixtures

- Planned, in-progress, changed, implemented, and retired stories.
- Passing, failing, and missing verification commands.
- Accepted, proposed, implemented, and rejected backlog occurrences.
- Resolves and references links.
- Matching and mismatched `harness_improvement` intakes.
- Missing, early, incomplete, failed, and detailed completed traces.
- Injected transaction failure after verification but before closure.

## Commands

```bash
cargo fmt --check
sh -c 'cargo test -p harness-cli -- --list | rg "story_completion" && cargo test -p harness-cli story_completion -- --nocapture'
cargo test -p harness-symphony run_contract -- --nocapture
scripts/validate-changeset-rebuild.sh
cargo clippy --workspace -- -D warnings
git diff --check
```

## Acceptance Evidence

- `cargo test -p harness-cli story_completion -- --nocapture`: 6 completion
  tests passed, covering eligibility, stable intake/trace identity, failure,
  rollback, concurrent idempotency, multi-resolver closure, reference
  preservation, outcome baseline, and exact replay evidence.
- `cargo test -p harness-symphony run_contract -- --nocapture`: 2 tests passed,
  covering copied-story `in_progress` state and the explicit trace-before-complete
  contract.
- `scripts/validate-changeset-rebuild.sh`: restored 54 Symphony story rows from
  committed changesets.
- `cargo test --workspace`: 152 tests passed (`54` Harness CLI and `98`
  Symphony).
- `cargo fmt --check`, `cargo clippy --workspace -- -D warnings`, and
  `git diff --check`: passed.
