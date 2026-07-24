# Execution Plans

Execution plans are Git-native working memory for complex tasks. They preserve
enough context for another agent or human to resume work without reconstructing
intent from chat history or a partial diff.

## When To Create A Plan

Use an ephemeral plan for bounded, single-session work.

Create one durable plan when work spans sessions, coordinates contributors, has
meaningful dependencies or ordering, requires recovery steps, or would be unsafe
to resume from the diff alone.

Use `docs/templates/exec-plan.md` and place the file under `active/`.
For an explicitly authorized baseline-to-rerun Harness experiment, use
`docs/templates/harness-improvement.md` instead.

## Lifecycle

```text
docs/plans/active/<slug>.md
  -> update progress and decisions during implementation
  -> record final validation and result
  -> move to docs/plans/completed/<slug>.md
```

The plan is the primary task artifact. Do not split one task across parallel
story, overview, design, validation, and trace files unless a document has an
independent long-term audience.

Promote a decision into `docs/decisions/` when it changes lasting product
behavior, architecture, data ownership, public compatibility, security policy,
or validation requirements. Keep local implementation choices in the plan.

## Active Plans

- `application-legibility.md`: prove one complete real-consumer runtime,
  reproduction, diagnosis, implementation, verification, and cleanup loop.

## Completed Plans

See `completed/README.md`. Phase 1 and Phase 2 are retained there because they
record consequential source-of-truth, payload, and compatibility transitions.
Phase 4 is retained because it records the consumer audit, explicit-intent
boundary, write freeze, and decision to preserve the still-used compatibility
implementation.
Phase 5 is retained because it records the final optional-consumer ownership
boundary and why generic atomic protocol primitives remain in compatibility.
The Rust core-maintenance plan is retained because it records the provenance,
three-way merge, transaction, bootstrap, and release boundaries of `harness`.
The repository-cleanup plan is retained because it records the removal boundary
between current product proof, published compatibility, and one-time migration
verification.
The self-update plan is retained because it records release discovery,
candidate handoff, executable replacement, conflict staging, human-directed
agent resolution, and recovery boundaries.
The self-update hardening plan is retained because it records the application
orchestration boundary, full-plan freezing, candidate trust, installer
continuation, and executable-skew recovery added after independent review.
