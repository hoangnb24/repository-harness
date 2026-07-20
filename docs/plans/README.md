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

No active execution plans are currently indexed.

## Completed Plans

See `completed/README.md`. Phase 1 workflow decoupling is retained there because
it records a consequential source-of-truth and compatibility transition.
