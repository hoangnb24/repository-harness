# Agent Operating Guide

This repository is in Harness v0. There is no product implementation yet.

The current job of agents is to preserve and grow the collaboration harness
before writing application code. Do not scaffold application source folders,
platform shells, package scripts, CI, or tests unless a later story explicitly
moves the project into implementation.

## Source Of Truth

Read in this order:

1. `STAGE.md` (repo root) for current WORKFLOW.md stage — answers "where is this repo at?" in one glance before anything else.
2. `README.md` for project status.
3. `docs/HARNESS.md` for the human-agent operating model.
4. `docs/FEATURE_INTAKE.md` before turning any prompt into work.
5. The user-provided spec or prompt, when one exists.
6. `docs/product/` for current product contracts.
7. `docs/ARCHITECTURE.md` before proposing implementation shape.
8. `docs/stories/` for story packets and backlog.
9. `docs/TEST_MATRIX.md` for proof status.
10. `docs/decisions/` for why important choices were made.
11. `docs/playbooks/` for reusable recipes that fix recurring tooling or
    environment problems across projects.
12. `docs/WORKFLOW.md` for the 13-stage delivery map — playbook /
    template / decision / gate per stage, plus folder, token chain, and
    per-tier matrix.

After the entrypoints above, retrieve by need (not in fixed order):

- `docs/CONTEXT_RULES.md` — what to read per stage and lane (pairs with the
  `context-monitor.sh` token-budget warnings). Read this when unsure what
  context a stage needs.
- `docs/TRACE_SPEC.md` — how to record the session trace before reporting done.
- `docs/HARNESS_MATURITY.md` / `docs/HARNESS_COMPONENTS.md` — self-position the
  harness and audit coverage; read only for harness-improvement work.

This harness does not ship with a project-specific `SPEC.md`. When the human
provides a spec for a new project, treat that spec as input material for the
first buildout. Derive product docs, story packets, architecture decisions, and
validation expectations from it. Product docs, stories, tests, and decisions
then become the living contract that agents should update as the system evolves.

## Task Loop

For every task:

0. Read `STAGE.md` at repo root. Confirm the task you're about to do matches the Current stage (or is an explicit move into the next stage). If the task spans multiple stages, surface that to the human before proceeding.
1. Classify the request with `docs/FEATURE_INTAKE.md`. Default lane is `self-review` — all 13 stages required. Only opt into `tiny | normal | high-risk` if the human has explicitly declared the opt-out, and record that in `STAGE.md` Lane Notes.
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
   - Did a WORKFLOW.md stage complete? If yes, update `STAGE.md` (move the
     stage row from Pending to History with today's date + commit SHA
     placeholder, update Snapshot.Current/Last completed/Next gate). The
     STAGE.md edit MUST land in the same commit as the stage's artifact
     per `docs/decisions/0012-stage-boundary-commits.md` + `0013`.
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
   - Did we exercise any `experimental` playbook? If yes, was it usable
     without modification? If yes, promote its `Lifecycle:` line to
     `verified` and fill the `First-use` field
     (see `docs/HARNESS.md` § Playbook Lifecycle).
   - Did any playbook we used need an unwritten workaround? If yes,
     append a `§ Variant` section to that playbook
     (see `docs/playbooks/README.md` § Use Order step 4).
   - Is this the end of a multi-task session (3+ commits, or work
     spanning multiple intake items)? If yes, run
     `docs/playbooks/session-retrospective.md` and save the report
     to `plans/reports/retro-<date>-<slug>.md` before reporting "done".
10. Update routine harness files directly, or add a proposal to
    `docs/HARNESS_BACKLOG.md` when the change is structural.

## Stage Orchestration

To keep the main session's context small, **delegate stage execution to the `stage-runner` subagent** instead of running the stage inline. The subagent reads `docs/STAGE_GOALS.md` + the relevant playbook in isolation, writes the stage artifacts, updates `STAGE.md`, and returns a compact summary (≤200 words) — the main agent only sees the summary, not the 10-30k tokens of stage work.

How to invoke:

- Slash command: `/stage-next` (preferred, auto-detects next stage from STAGE.md).
- Direct: `Task({ subagent_type: "stage-runner", prompt: "Run stage <N> per goal: …" })`.

When NOT to delegate:

- The user explicitly asks to do a stage inline (review-as-you-go).
- A non-stage task (refactor, bugfix, harness tweak) that doesn't map to a WORKFLOW.md row.
- A change-request flow — the always-on layer is not a "stage" and has no goal template.

The subagent returns a `**Status:**` block with one of `DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT | MANUAL_CHECKPOINT_PENDING`. Handle per `~/.claude/rules/orchestration-protocol.md` § Subagent Status Protocol. Never silently retry on `BLOCKED` — change context, simplify, or escalate.

The `.claude/hooks/stage-deliver.sh` Telegram hook fires on the subagent's stage-boundary commit, so the human gets the artifact and the next stage's `/goal` text in their phone without the main agent needing to do anything extra.

## Manual Checkpoint Signaling

Several workflow stages require the human to do offline work the agent cannot do — open `claude.ai/design` for the prototype, sign a SOW, review a gap analysis, run UAT, hand over credentials. When you reach one of these handoffs, end the turn with a `MANUAL_CHECKPOINT` block so the human sees a structured alert (Telegram / IDE notification / log) and knows exactly what to do and when to come back.

Format (write in the last assistant message of the turn that ends in handoff):

```
MANUAL_CHECKPOINT: <one-line action — start with a verb>
- URL: <link if any>
- Reference: <file or spec the human reads first>
- Save to: <where the output lands, if applicable>
- Return condition: <what the human says/does when finished>

<blank line ends the block>
```

Use this at stage 3.B (gap analysis review round), 4 (SOW signoff), 5 (Spec Approval Gate Phase 1→2), 6 sub-step B (prototype generation in claude.ai/design or fallback tool), 6 client review round, 11 (UAT signoff), 13 (credentials handover), and any change-request review. Anywhere `docs/WORKFLOW.md` says "client review round", "human approves", or "signoff" is a manual checkpoint.

If multiple manual steps are pending, list each as its own `MANUAL_CHECKPOINT` block separated by a blank line. The parser captures from the first `MANUAL_CHECKPOINT` line to the end of the assistant message, so blank lines between blocks are fine and trailing prose ("I'll resume once you confirm") is included as context.

## Harness Change Policy

Agents may update directly:

- `STAGE.md` Snapshot / History / Pending rows on stage completion.
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
- The **Pre-Close Verification Gate** is satisfied: the story's Verify command
  in `docs/TEST_MATRIX.md` § Verification Register ran with `Result: pass`, or
  a recorded reason explains why none exists (`docs/FEATURE_INTAKE.md`
  § Pre-Close Verification Gate).
- A **session trace** is recorded per `docs/TRACE_SPEC.md` (inline for a single
  task, or in the retro report for a multi-task session) and self-scored to the
  lane's required tier.
- Missing harness capabilities were added to `docs/HARNESS_BACKLOG.md`.
- The final response says what changed and what was not attempted.
