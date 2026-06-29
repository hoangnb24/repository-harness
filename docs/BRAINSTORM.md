# Brainstorm Workflow

Brainstorming is for exploring possible directions before the harness commits
to a product contract, story, validation requirement, or implementation plan.

Use this workflow when the user asks to explore, compare, ideate, name, shape,
prioritize, or pressure-test ideas and has not yet selected a specific change
to implement.

## Position In The Harness

```text
human idea
  -> brainstorm
  -> selected intent
  -> feature intake
  -> story packet or direct patch
  -> validation proof
```

Brainstorming is optional. If the user gives a clear implementation request,
go directly to `docs/FEATURE_INTAKE.md`.

## Rules

- Keep brainstorm output provisional until the user selects an option.
- Separate observations, assumptions, options, risks, and recommended next
  steps.
- Do not create product truth from brainstorm notes alone.
- Do not create story packets unless the brainstorm resolves into selected
  work.
- Record durable intake only when the brainstorm becomes a work item, a saved
  artifact, or a harness change.
- If the brainstorm reveals a clear product decision, route it through feature
  intake before implementation.
- If the brainstorm reveals a durable architecture, authorization, data, API,
  or validation decision, use the normal decision process before treating it as
  accepted.

## Output Modes

Choose the lightest artifact that preserves useful context:

| Mode | Use when | Artifact |
| --- | --- | --- |
| Conversational | The user wants quick exploration only | Chat response |
| Captured | The ideas should be saved for later slicing | `docs/product/ideas/...` or another scoped note |
| Intake-ready | One option is selected for work | Feature intake plus story/direct patch |

Use `docs/templates/brainstorm.md` when a captured brainstorm is useful. Keep
captured brainstorm notes out of `docs/product/` unless the note clearly labels
itself as provisional and not product truth.

## Agent Loop

1. Restate the open question in one sentence.
2. Identify constraints already known from product docs, stories, decisions, or
   the user's prompt.
3. Generate a small set of distinct options.
4. For each option, name the tradeoff, risk, and proof that would be needed if
   selected.
5. Recommend one next move, while preserving viable alternatives.
6. Ask the user to choose only when selection is genuinely needed before work
   can continue.
7. When the user selects a direction, run feature intake and continue in the
   appropriate lane.

## Validation

Brainstorming itself usually has no executable proof. Validate it by checking:

- The options are meaningfully distinct.
- Assumptions are labeled.
- No provisional idea is written as accepted product truth.
- Follow-up work has a clear intake path.
- Any saved note states its status and owner.
