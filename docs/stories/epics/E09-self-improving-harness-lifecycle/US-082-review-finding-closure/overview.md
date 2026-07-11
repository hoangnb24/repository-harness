# US-082 Review Finding Closure

## Current Behavior

The branch review in
`docs/reviews/feature-self-improving-harness-lifecycle-to-main-review.md`
records eleven branch findings and two reproducible baseline defects. They cover
lossy semantic replay, unstable proof ordering, audit identity, proposal input
handling, lightweight Symphony state, committed rebuild drift, Unicode safety,
and living documentation.

## Target Behavior

Every F- and B-item in the review is closed with code, focused regression proof,
full live-versus-rebuilt parity, and an updated review ledger. A fresh rebuild
must preserve lifecycle decisions and produce the same zero-entropy audit state
as the live database.

## Affected Users

- Harness CLI operators accepting, rejecting, completing, rebuilding, or
  observing improvement work.
- Symphony operators running isolated or lightweight stories.
- Agents relying on committed changesets as durable state.

## Affected Product Docs

- `docs/IMPROVEMENT_PROTOCOL.md`
- `docs/GLOSSARY.md`
- `docs/SYMPHONY_SCOPE.md`
- `docs/reviews/feature-self-improving-harness-lifecycle-to-main-review.md`

## Non-Goals

- Redesigning the E09 lifecycle beyond the already accepted contracts.
- Deleting historical review, decision, trace, or friction evidence.
- Weakening completion, replay, audit, or verification gates.
