# Trace Specification

What an agent records after a task so the next agent (or the human-as-customer)
can trust what happened. Adapted from the upstream trace spec, but **markdown-
first**: the trace is a block, not a SQLite row. It lands in the session
retrospective (`docs/playbooks/session-retrospective.md`) for multi-task
sessions, or inline in the final response for a single task.

The point is the same as upstream: a trace makes work auditable, surfaces
friction for the Growth Rule, and lets the human verify "done" without
re-reading the whole diff.

## Trace Block Shape

Append this block where the trace lands (retro report, or final message):

```markdown
### Trace — <one-line outcome>

- **Outcome:** completed | partial | blocked | failed
- **Stage / Lane:** <WORKFLOW stage> / <self-review | tiny | normal | high-risk>
- **Story / tokens:** <US-NNN or n/a> · cites <REQ/SC/TC tokens or n/a>
- **Files read:** path, path, command …
- **Files changed:** path, path …   (omit only if nothing changed)
- **Decisions:** scope calls, validation choices, explicit non-goals
- **Verify:** <command run + pass/fail>  or  <why no command exists>
- **Friction:** concrete pain / missing rule / stale doc — or `none` (only after checking)
```

Fields map to local conventions, not a database: tokens are `US-NNN.REQ/SC/TC`
(`docs/HARNESS.md` § Traceability Tokens), Verify ties to `docs/TEST_MATRIX.md`,
Friction feeds `docs/HARNESS_BACKLOG.md`.

## Quality Tiers And Self-Scoring

Score your own trace before the final response. The tier must match the lane.

| Tier | Score | Required fields | Acceptable for |
| --- | --- | --- | --- |
| **Minimal** | 1 | `Outcome` + one-line summary | Tiny-lane, no file change or low-risk copy edit only. |
| **Standard** | 2 | Minimal + Stage/Lane + Files read + Files changed + (Friction or Decisions) | Normal / self-review lane; any tiny task that changed harness rules or durable records. |
| **Detailed** | 3 | Standard + Story/tokens + Decisions + Verify + Friction (`none` only after checking) | High-risk; anything touching architecture, auth, data ownership, API shape, or validation rules. |

Self-score rule: pick the tier whose required fields you actually filled. If
the tier is below what the lane demands (table below), the trace is incomplete
— fill the missing fields before claiming done.

| Lane | Required tier |
| --- | --- |
| Tiny | Minimal (Standard if friction or harness docs changed) |
| Normal / Self-review | Standard |
| High-risk | Detailed |

> No binary computes this score. Self-scoring is the markdown-first stand-in
> for upstream's `score-trace` command — cheap, honest, and enough for solo
> use. If self-scoring ever feels like theatre, that is a signal the lane is
> mis-set, not that the trace is optional.

## Friction Capture Protocol

Fill **Friction** when any of these happened:
- Had to infer a missing rule or source of truth.
- Required validation was unclear, unavailable, or too costly to run.
- A doc, story, or decision was stale or contradictory.
- A manual step repeated and should become a template / playbook / checklist.
- A requested change was out of scope but likely important later.

How to write it:
- Name the concrete pain, not a mood. Good: *"WORKFLOW stage 6 has no template
  for the role-permission matrix; copied from a prior project by hand."*
  Weak: *"docs confusing."*
- If the friction should become work, add or update a `docs/HARNESS_BACKLOG.md`
  item (Growth Rule, `docs/HARNESS.md`).
- `none` is a valid, useful signal — but only for Detailed traces and only
  after actively checking.

## Detailed Trace ≠ Decision Record

For high-risk work, the `Decisions` field summarizes what was decided. It does
**not** replace a durable decision record. If the work changed behavior,
architecture, authorization, data ownership, API shape, or validation
requirements, also add a `docs/decisions/NNNN-*.md` file. The trace is
evidence; the decision log is the contract.

## Where Traces Live

| Situation | Trace lands in |
| --- | --- |
| Single focused task | Final response message (inline block). |
| Multi-task session (3+ commits, or spanning intake items) | `plans/reports/retro-<date>-<slug>.md` § Trace, per `docs/playbooks/session-retrospective.md`. |
| Stage-boundary delivery | The stage-runner subagent's compact summary already carries the trace fields; the commit + `STAGE.md` History row is the durable record. |

## Review Checklist

Before final response:
- Trace tier matches the lane (self-score above).
- `Files changed` matches the real changed set (`git status --short`).
- `Verify` names the command + result, or explains why none exists.
- `Friction` names a concrete issue or is an intentional `none`.
- Friction that should become work is in `docs/HARNESS_BACKLOG.md`.
