# Harness Maturity Ladder

Where this harness sits on the path from "static agent instructions" to
"self-checking delivery system." Adapted from the upstream maturity concept
(`hoangnb24/harness-experimental`) but re-grounded in **this** fork's goal:
a solo-dev / agency delivery harness, markdown-first, no compiled tooling.

Levels are **verifiable by repository state** — a level is achieved only when
its criteria can be inspected in files, `STAGE.md`, decisions, or commit
history. No benchmark suite is required; the proof is the repo itself.

> Upstream measures maturity against an external `harness-benchmark`. This
> fork measures it against **delivery discipline**: can a human-as-customer
> trust that every stage produced its gate artifact and every claim of "done"
> carries proof?

## Levels

### H0 — Bare Prompts

Agent receives a prompt, produces a patch. The repo does not tell it how to
classify, stage, gate, or record work.

Criteria:
- No `AGENTS.md` operating block.
- No intake lanes, no stage map, no `STAGE.md`.

Status: **Passed.** This repo is well beyond H0.

### H1 — Scaffolding And Policy

Static operating instructions, risk lanes, stage map, templates, and
source-of-truth order exist. An agent can follow a documented workflow, but
durable state and proof may still be manual or skipped.

Criteria:
- `AGENTS.md` points to the operating docs.
- `docs/HARNESS.md`, `docs/FEATURE_INTAKE.md`, `docs/ARCHITECTURE.md`,
  `docs/WORKFLOW.md` exist.
- Story, decision, validation, and delivery templates exist under
  `docs/templates/`.
- `docs/TEST_MATRIX.md` defines proof columns and status meanings.

Status: **Achieved.** All H1 files exist and are referenced by the Task Loop.

### H2 — Stage State And Context Discipline

The repo tells an agent *where it is* and *what to read*, not just *how to
work*. Stage position is durable and a single glance answers "where is this
project?"

Criteria:
- `STAGE.md` at repo root tracks Lane / Current stage / Last completed /
  Next gate, updated at every stage-boundary commit
  (`docs/decisions/0012`, `0013`).
- `self-review` lane is the default and runs all 13 stages
  (`docs/FEATURE_INTAKE.md`).
- `docs/CONTEXT_RULES.md` defines what to read per stage and lane.
- `.claude/hooks/context-monitor.sh` warns on token-budget thresholds.
- Traceability tokens (`US-NNN.REQ/SC/TC`) are defined and used
  (`docs/HARNESS.md` § Traceability Tokens).

Status: **Achieved.** STAGE.md, self-review lane, context-monitor, and tokens
are live; `CONTEXT_RULES.md` added in this distillation.

### H3 — Recorded Evidence And Friction Loop

The agent leaves structured evidence the next agent can trust, and friction
feeds back into harness growth instead of evaporating.

Criteria:
- `docs/TRACE_SPEC.md` defines a tiered trace shape and the session
  retrospective records it (`docs/playbooks/session-retrospective.md`).
- Friction is captured per the Growth Rule and lands in
  `docs/HARNESS_BACKLOG.md` when out of scope (`docs/HARNESS.md` § Growth Rule).
- Every stage-boundary commit carries its gate artifact, making the timeline
  auditable from `git log`.

Status: **Achieved (lightweight).** Trace spec + retrospective + backlog loop
exist. The trace is markdown, not a queryable store — sufficient for solo use.

### H4 — Mechanical Verification Gate

The harness does not just *observe* that work happened — it *checks* that the
work meets its contract before a task or stage can be called done.

Criteria:
- Stories / TEST_MATRIX rows can carry a **Verify** command and a **Last
  verified** result (`docs/TEST_MATRIX.md`, `docs/decisions/0014`).
- A **pre-close gate** stops "done" until the verify command was run and
  recorded, or the story packet explains why a proof column is empty
  (`docs/FEATURE_INTAKE.md` § Pre-Close Verification Gate).
- The Done Definition in `AGENTS.md` enforces "validation commands were run
  when they exist."

Status: **Achieved (client-side).** The gate convention and columns are in
place, and a git hook (`.githooks/` + `scripts/hooks/harness-verify-gate.sh`,
activated via `core.hooksPath`) enforces it mechanically on commit and push —
lint must pass and no `Result: fail` (or stage-close `never-run`) may be
committed (`docs/decisions/0014`). The one gap is that `git --no-verify` skips
client-side hooks, so the no-bypass guarantee for agents is instruction-level
(`AGENTS.md`); a server-side/CI backstop would close it.

## Current Position

**This fork sits at H4 (client-side enforcement).** Observation, context, and
mechanical verification layers are all in place. The remaining ceiling is
server-side enforcement (CI / pre-receive) to stop human `--no-verify` bypass —
deferred until that bypass is actually observed.

## What This Fork Deliberately Does NOT Pursue

The upstream ladder continues toward automated benchmark ingestion, trace
auto-scoring binaries, and an evolution loop driven by a compiled CLI + SQLite
store. Those serve a "harness as measurable product" goal. This fork is an
**internal delivery harness** — it stops at instruction-level verification on
purpose (`docs/decisions/0014`). Re-open this section only if the goal changes
from "deliver client projects" to "publish a measurable harness."
