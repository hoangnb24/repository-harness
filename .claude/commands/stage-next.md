---
description: Run the next workflow stage via the stage-runner subagent so the main session stays small
allowed-tools: Read, Bash, Task
---

Goal: hand the next workflow stage to the `stage-runner` subagent, then summarise the result to the user. Keep this turn focused on orchestration — do NOT do the stage work in the main session.

## Steps

1. Read `STAGE.md` at repo root to find:
   - Current stage (Snapshot.Current stage)
   - Lane (Snapshot.Lane)
   - Last completed stage and any blockers

2. Determine the next stage to run:
   - If Current = 2 → next is `2` (the stage in Current is what needs to run, not "the one after")
   - If a stage is marked DONE in Snapshot but Current still points to it, advance to the next per `docs/WORKFLOW.md` (2 → 3.A → 3.B → 4 → 5 Phase 1 → 5 Phase 2 → 6 sub-A → 6 sub-B → 6 sub-C → 7 → 8 → 10 → 11 → 12 → 13)
   - Skip stages disabled by lane per `docs/FEATURE_INTAKE.md`

3. Read the matching `## Stage <N>` block in `docs/STAGE_GOALS.md` and extract the verbatim Goal body (everything between `Goal:` and the next blank line).

4. Substitute placeholders in the goal:
   - `{date}` → today's `YYYY-MM-DD` (use `date +%Y-%m-%d` via Bash)
   - `{slug}` → derive from repo basename or pass-through
   - `{client}` / `{epic_id}` / `{story_id}` / `{run_id}` → only if the user provided them in the slash invocation arguments

5. Spawn the stage-runner via the Task tool:

   ```
   Task({
     description: "Run stage <N>",
     subagent_type: "stage-runner",
     prompt: <built prompt — see template below>
   })
   ```

   Prompt template to build:
   ```
   Run stage <N> (<stage name>) end-to-end per docs/STAGE_GOALS.md.

   Goal (verbatim, substitutions applied):
   <substituted goal body>

   Project context:
   - Today: <YYYY-MM-DD>
   - Repo: <basename>
   - <any extra context from user>

   Read AGENTS.md and your own agent definition first. Stop at MANUAL_CHECKPOINT or when the goal holds. Return the final status block as your last message.
   ```

6. When stage-runner returns, do NOT repeat its full output to the user. Quote ONLY the final status block (lines starting with `**Status:**` through `**Summary:**`). Add a one-line recommendation:
   - `Status: DONE` → "Ready for `/stage-next` again, or stop here for review."
   - `Status: MANUAL_CHECKPOINT_PENDING` → "Waiting on offline work — see MANUAL_CHECKPOINT blocks above."
   - `Status: BLOCKED` → relay the blocker; suggest unblock action.
   - `Status: NEEDS_CONTEXT` → ask the user for the missing info; do NOT re-spawn until provided.

## Arguments

The user may pass extras after `/stage-next`. Honor these:
- `--stage <token>` → override auto-detected next stage
- `--turn-budget <N>` → override default 25 turns in stage-runner
- Free text → append to "extra context" in the prompt

If no arguments, auto-pick from STAGE.md.

## Failure modes

- `STAGE.md` missing → tell user to bootstrap first (`scripts/install-harness.sh --bootstrap`).
- Stage in STAGE.md not in STAGE_GOALS.md (e.g. Stage 1 or 9) → say "stage <N> has no goal template — execute inline or skip per WORKFLOW.md per-tier matrix."
- No next stage (Current=done at stage 13) → congratulate the project is closed; suggest archiving.

Stay terse. The harness already keeps the verbose work in artifacts on disk.
