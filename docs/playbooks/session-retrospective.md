# Session Retrospective Playbook

**Lifecycle:** verified · **First use:** 2026-05-17 (claudekit-custom port retro) · **Verified by:** plans/reports/retro-260517-1527-plan-d-execution.md (3 uses without Variant amendment)

> Structured checklist an agent runs at the end of a multi-task session
> to capture cross-task insight before the session memory disappears.

## When To Run

Run this playbook when EITHER:

- The session produced 3+ commits.
- The session spanned multiple intake items (e.g. one task triggered
  a decision, that decision triggered a plan, that plan touched multiple
  files).

Skip when:

- Single-task session with one focused change. Per-task review
  (`AGENTS.md` Task Loop step 9) is sufficient.

## When NOT To Use

This playbook is for the agent that did the work, at the end of the
session. It is not:

- A code review (use `docs/playbooks/` review-class entries for that).
- A project status snapshot (a separate playbook will cover that;
  see `plans/260517-1242-quality-and-closure-tools/` Plan D).
- A QA report (per-story responsibility, not session-level).

## Output Shape

Save the retro report to
`plans/reports/retro-<YYYYMMDD>-<HHMM>-<topic-slug>.md` using the
section template below. Keep each section terse — sacrifice grammar
for concision. Empty sections are valid signals ("no friction" is a
useful data point).

```markdown
# Session Retrospective — <topic-slug>

**Date:** YYYY-MM-DD · **Commits in session:** N · **Branch:** <branch>

## Tasks Completed

Brief list. One line each. Cite commit SHAs where useful.

## Friction Encountered

For each friction point:
- **What:** one sentence.
- **Where:** file path, command, or step.
- **Root cause:** one sentence if known; "unknown — needs investigation" if not.
- **Recurring?:** first-time / second-time / 3+ times.
- **Suggested capture:** existing playbook / new playbook / backlog entry / decision / nothing.

## Playbooks Used

For each playbook touched in this session:
- **Playbook:** path.
- **Lifecycle on entry:** experimental / verified / deprecated.
- **UX rating:** worked-as-written / needed Variant / failed.
- **Promote?:** experimental → verified candidate? yes / no / not-yet.
- **Variant added?:** yes (link section) / no.

## Lifecycle Promotion Candidates

List each `experimental` playbook that was exercised this session
without needing modification. These are candidates to promote to
`verified` in this commit batch.

## Backlog Candidates

For each new `Missing Harness Capability` discovered:
- **Title:** short name.
- **One-line problem:** what's missing.
- **Demand evidence so far:** count of hits this session, plus prior
  sessions if known.
- **Promotion check:** does it meet the 2-project or 3-hit threshold
  yet? (See `docs/HARNESS_BACKLOG.md` § Promotion Rule.)

## Decisions Made

For each decision-class change in this session:
- **Decision ID + title** (e.g. `0006 — Session Retrospective Mechanic`).
- **Consequence ladder:** which downstream files / plans are now
  affected and need attention next session.

## Recommendations For The Next Agent

What would have helped this session's agent? Capture as either:
- A specific instruction the next agent should follow.
- A playbook draft (move into `docs/playbooks/` if substantial).
- A `HARNESS_BACKLOG.md` entry (move if cross-project).

If everything ran smoothly, write "none — session ran clean" and stop.

## Open Threads

Items the session did not close. Each links to where they live now
(plan dir, backlog entry, decision draft) so the next agent picks
them up.
```

## Steps To Run

1. List commits in the session: `git log --oneline <session-start>..HEAD`.
2. For each commit, note what task it served.
3. Walk the section template top-to-bottom, filling each. Skip none —
   write "none" if a section is empty.
4. Apply the Lifecycle Promotion Candidates immediately if any:
   open each affected playbook, update its Lifecycle line, fill
   First-use field. Stage and commit the lifecycle change separately
   so it has a clean diff.
5. Apply new Backlog Candidates immediately if they meet the
   promotion threshold; otherwise stage as `proposed` entries.
6. Save the retro report at the canonical path. Reference it in any
   downstream decision doc that emerged this session.

## Pitfalls

- **Thin retros.** If sections are empty because the agent skipped
  them, future sessions cannot trust the file. Always write "none"
  explicitly rather than omit a section.
- **Retro-as-changelog.** The git log already lists commits. This
  retro is about insight, not commits. If a section reads like a
  commit list, rewrite it to surface what was learned.
- **Premature lifecycle promotion.** Promoting an `experimental`
  playbook to `verified` after one self-use (the playbook's author
  using it on a contrived example) does not satisfy the rule. The
  real use must come from work that would have happened regardless
  of the playbook's existence.
- **Decision creep.** Not every session needs a decision doc. Only
  promote insight to a decision when it changes operating model or
  architecture direction.

## Variant Section

(Append a Variant block when this playbook fails or partially works.
Do not delete the original recipe.)

## Related

- `docs/HARNESS.md` § Growth Rule — the principle this playbook
  mechanises.
- `docs/HARNESS.md` § Playbook Lifecycle — the promotion target this
  playbook checks.
- `AGENTS.md` Task Loop step 9 — the per-task hook that calls this
  playbook at session end.
- `docs/HARNESS_BACKLOG.md` § Promotion Rule — the threshold this
  playbook applies to surfaced backlog candidates.
- `docs/decisions/0006-session-retrospective-mechanic.md` — why this
  playbook exists.
