# Project Status Snapshot Playbook

**Lifecycle:** experimental · **First use:** TBD · **Verified by:** none

> Read-only "where are we now" snapshot. Agent reads existing harness
> files and emits a structured markdown report plus a one-line summary.
> No write side. No script — agent-read by contract.

## When To Run

- Session start, when picking up after a gap > 1 day.
- Weekly status, regardless of activity level.
- Before an audit, handover, or stakeholder review.
- After any session producing 3+ commits, to surface what shifted.

Skip when the prior snapshot is < 24h old and nothing material has
changed (no new commits, no new decisions, no story status changes).

## Read-Only Contract

This playbook produces a snapshot. It does NOT:

- Update story status, test matrix rows, or decision records.
- Promote any playbook lifecycle.
- Re-categorise backlog entries.

Any "fix the gap" item surfaced by the snapshot becomes a separate
task or backlog entry — never an in-place edit during the snapshot
pass.

## Inputs

Agent reads these paths top-to-bottom:

1. `docs/stories/` — story state (open / in progress / blocked /
   awaiting review / shipped).
2. `docs/TEST_MATRIX.md` — proof coverage (green / red / empty rows).
3. `docs/decisions/` — accepted / superseded / deprecated decisions
   still constraining today's work.
4. `docs/playbooks/` — lifecycle state of each playbook
   (`experimental` / `verified` / `deprecated`).
5. `plans/reports/retro-*.md` — last 3 retro reports, if they exist
   (for "what was learned recently").

## Report Shape

Save to `plans/reports/status-<YYYYMMDD>-<HHMM>-<scope-slug>.md`.

```markdown
# Project Status Snapshot — <scope-slug>

**Date:** YYYY-MM-DD · **Snapshot of:** <branch> @ <short sha>

## One-Line Summary

<see template below>

## 1. Stories

| Bucket | Count | Notable IDs |
| --- | --- | --- |
| Open | N | `US-NNN`, ... |
| In progress | N | `US-NNN`, ... |
| Blocked | N | `US-NNN` (blocker: ...) |
| Awaiting review | N | `US-NNN`, ... |
| Shipped (last 7 days) | N | `US-NNN`, ... |

## 2. Proof

| Metric | Value |
| --- | --- |
| TEST_MATRIX rows | N |
| Green (proven) | N (X%) |
| Red (failing) | N |
| Empty (no proof) | N |
| Composite tokens cited | N unique |

List red and empty rows by token (`US-NNN.SC-MMM`).

## 3. Decisions

| Decision | Status | Still binding today? |
| --- | --- | --- |
| `NNNN-title.md` | accepted | yes — affects <area> |
| `NNNN-title.md` | superseded by NNNN | no |

## 4. Playbook Lifecycle

| Lifecycle | Count | Promotion candidates |
| --- | --- | --- |
| experimental | N | <list playbooks at ≥ 2 real uses with no Variant> |
| verified | N | — |
| deprecated | N | — |

## Open Threads

Items the snapshot surfaced that need follow-up. Each links to a
story candidate, backlog entry, or decision draft.
```

## One-Line Summary Template

For session-start echo. Pick the salient signal — not every metric.

```text
<N> stories open (<N> blocked); matrix <X>% green; <N>
experimental playbooks past 2-use threshold; last decision:
NNNN (accepted YYYY-MM-DD).
```

Examples:

- `12 stories open (3 blocked); matrix 62% green; 2 experimental playbooks past 2-use threshold; last decision: 0006 (accepted 2026-05-17).`
- `4 stories open (0 blocked); matrix 100% green; 0 promotion candidates; last decision: 0003 (accepted 2026-04-12).`

## Hand-Off

- Save the markdown report at the canonical path.
- Echo the one-line summary in the next agent message (or session
  start) so it appears in transcript and is searchable.
- If the snapshot is consistently post-processed to answer "what
  features exist", that signals Plan E A2 (feature register) friction
  — log evidence to `plans/reports/plan-e-trigger-evidence.md`.

## Promotion-To-Script Escape Hatch

Decision 0005 § 6 keeps this as a playbook because the bottleneck has
not been measured. Promote to a script via standard backlog →
decision flow when:

- A snapshot routinely takes > 5 minutes of agent read time, AND
- The snapshot is run weekly or more often, AND
- The output shape has stabilised over 5+ uses without Variant
  amendments.

Until those three hit simultaneously, keep this as a read-loop
playbook.

## Variant Section

(Append a Variant block when the read-loop fails or partially works.
Do not delete the original report shape.)

## Related

- `docs/decisions/0005-roadmap-execution-direction.md` § 6 — why this
  is a playbook, not a script.
- `docs/HARNESS.md` § Source Hierarchy — the input list this playbook
  walks.
- `docs/playbooks/session-retrospective.md` — distinct concern
  (session-end insight vs project-wide state).
- `docs/playbooks/README.md` § Use Order — Variant convention.
