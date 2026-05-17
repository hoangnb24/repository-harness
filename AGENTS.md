# Agent Operating Guide

This repository is in Harness v0. There is no product implementation yet.

The current job of agents is to preserve and grow the collaboration harness
before writing application code. Do not scaffold application source folders,
platform shells, package scripts, CI, or tests unless a later story explicitly
moves the project into implementation.

## Source Of Truth

Read in this order:

1. `README.md` for project status.
2. `docs/HARNESS.md` for the human-agent operating model.
3. `docs/FEATURE_INTAKE.md` before turning any prompt into work.
4. The user-provided spec or prompt, when one exists.
5. `docs/product/` for current product contracts.
6. `docs/ARCHITECTURE.md` before proposing implementation shape.
7. `docs/stories/` for story packets and backlog.
8. `docs/TEST_MATRIX.md` for proof status.
9. `docs/decisions/` for why important choices were made.
10. `docs/playbooks/` for reusable recipes that fix recurring tooling or
    environment problems across projects.

This harness does not ship with a project-specific `SPEC.md`. When the human
provides a spec for a new project, treat that spec as input material for the
first buildout. Derive product docs, story packets, architecture decisions, and
validation expectations from it. Product docs, stories, tests, and decisions
then become the living contract that agents should update as the system evolves.

## Task Loop

For every task:

1. Classify the request with `docs/FEATURE_INTAKE.md`.
2. Identify whether the input is a new spec, spec slice, change request, new
   initiative, maintenance request, or harness improvement.
3. Locate the affected product docs and story files.
4. Check `docs/TEST_MATRIX.md` for existing proof and gaps.
5. Before fighting any tooling, environment, or workflow problem, scan
   `docs/playbooks/README.md` for a matching recipe. Apply the recipe before
   re-deriving a fix.
6. If this is the first story to touch implementation in a new spec
   buildout, confirm the **runtime stack** has been recorded in
   `docs/decisions/`. If not, apply `docs/ARCHITECTURE.md` § Discovery
   Before Shape and write a stack-selection decision before writing any
   code. Architecture drift after the first 2-3 stories is far costlier
   than picking now and adjusting later via a superseding decision.
7. If the work touches UI / visual surfaces (web, mobile, desktop, any
   user-visible interface):
   - Check `docs/design-guidelines.md` exists. If not:
     1. First run **Style Intake** (see playbook § Style Intake): pick
        one of the 5 sources (live URL / mockup / AI generate / interview
        / brand assets), then save `docs/decisions/YYYY-MM-DD-design-direction.md`
        with the resulting tokens, source, and approver.
     2. Then apply `docs/playbooks/ui-design-system-contract.md` to
        populate the contract file using tokens from the decision doc.
        The contract's §1 must open with a link to the decision doc.
   - Check the §3 Component Coverage Matrix covers every component the
     work will touch. If a needed component is missing, add the row (stub
     or implement) before building the screen.
   - Update §8 Component Inventory whenever a component file is added,
     renamed, or removed.
8. Work only inside the selected lane: tiny, normal, or high-risk.
9. Before finishing, ask:
   - Did product truth change?
   - Did validation expectations change?
   - Did architecture rules change?
   - Did story status change? If yes, update the matching row in
     `docs/TEST_MATRIX.md` in the same commit. Story status and matrix
     row are the same fact in two views — drift between them silently
     invalidates the proof column.
   - Did we discover a repeated failure pattern?
   - Did the next agent need a clearer instruction?
   - Did we just solve a non-obvious tooling or environment problem that is
     likely to recur on this or another project? If yes, add or update a file
     in `docs/playbooks/` using `docs/playbooks/template.md`.
10. Update routine harness files directly, or add a proposal to
    `docs/HARNESS_BACKLOG.md` when the change is structural.

## Harness Change Policy

Agents may update directly:

- Story status and evidence.
- `docs/TEST_MATRIX.md` rows.
- Links from story packets to product docs.
- Validation notes and reports.
- Small clarifications tied to the current task.
- New or amended `docs/playbooks/` entries that capture a reusable tooling or
  environment recipe.

Agents should ask for human confirmation before:

- Changing architecture direction.
- Removing validation requirements.
- Changing the source-of-truth hierarchy.
- Changing risk classification rules.
- Replacing the feature workflow.

## Done Definition

A task is done only when:

- The requested change is completed or the blocker is documented.
- Relevant docs, stories, and test matrix entries remain current.
- Validation commands were run when they exist.
- Missing harness capabilities were added to `docs/HARNESS_BACKLOG.md`.
- The final response says what changed and what was not attempted.
