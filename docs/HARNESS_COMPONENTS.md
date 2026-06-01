# Harness Components

Coverage audit: maps every harness surface in **this** fork to the
11-responsibility framework for agent harnesses (Runtime Substrate, arXiv
2605.13357). The framework is generic — it describes what *any* agent harness
must cover, not anything upstream-specific. Use this table to spot which
responsibilities are still thin.

Status values:
- **Covered** — an explicit file, gate, or convention handles it.
- **Partial** — some support exists, but it is manual, incomplete, or not yet
  proven on a real project.
- **Missing** — no meaningful support yet.

> This fork is markdown + hooks + subagent, no compiled CLI or database.
> "Tool access" and "Observability" therefore look different from upstream:
> the durable store is the file tree + git history, not a SQLite table.

## Responsibility Map

| # | Responsibility | Status | Harness Surface | Gap |
| --- | --- | --- | --- | --- |
| 1 | Task specification | Covered | `docs/FEATURE_INTAKE.md` (input types + lanes), `docs/WORKFLOW.md` (13 stages), `docs/templates/story.md`, `docs/templates/high-risk-story/*`, intake/discovery/gap-analysis templates | Story packets must stay synced with `docs/product/*` once a real project starts. |
| 2 | Context selection | Covered | `AGENTS.md` reading order, `docs/CONTEXT_RULES.md` (phase × stage × lane), `.claude/hooks/context-monitor.sh` (token budget) | Reading lists are advisory; nothing measures over-reading. |
| 3 | Tool access | Partial | `scripts/install-harness.sh`, `.claude/hooks/*`, `.claude/agents/stage-runner.md`, `/stage-next` command, optional `/ck:*` skills (Independence Principle) | No machine-readable tool registry or permission profile — by design for solo use. |
| 4 | Project memory | Covered | `docs/decisions/*`, `docs/HARNESS_BACKLOG.md`, `docs/playbooks/*` (cross-project memory), `docs/stories/*`, `git log`, `STAGE.md` | No staleness check; old playbooks rely on the Lifecycle line for freshness. |
| 5 | Task state | Covered | `STAGE.md` (current stage), `docs/TEST_MATRIX.md` (proof status), story status, stage-boundary commits (`0012`) | No lifecycle alarm if a project stalls mid-stage. |
| 6 | Observability | Partial | `docs/TRACE_SPEC.md` (trace shape), `docs/playbooks/session-retrospective.md`, stage-boundary commits as an audit timeline, Telegram delivery hooks | Traces are markdown, not queryable; no dashboard. Acceptable for solo scale. |
| 7 | Failure attribution | Partial | `session-retrospective.md` (friction → root cause → recurrence), `HARNESS_BACKLOG.md`, this component map | Attribution is manual; no automated link from a failed gate to a component. |
| 8 | Verification | Covered | `docs/TEST_MATRIX.md` (Verify + Last verified columns, `0014`), `docs/FEATURE_INTAKE.md` § Pre-Close Verification Gate, stage 9/10 gates in `docs/WORKFLOW.md`, `AGENTS.md` Done Definition | Gate is instruction-enforced, not tool-enforced (deliberate, `0014`). |
| 9 | Permissions | Partial | `AGENTS.md` § Harness Change Policy (update-directly vs ask-first lists), Manual Checkpoint signaling, `~/.claude/rules/*` | Policy is instruction-level; no enforced allowlist. |
| 10 | Entropy auditing | Partial | `docs/HARNESS_BACKLOG.md` + Growth Rule, Playbook Lifecycle (`experimental`→`verified`→`deprecated`), `docs/HARNESS_MATURITY.md`, STAGE.md drift-is-a-bug rule | No automated stale-doc or drift detector. |
| 11 | Intervention recording | Covered | `docs/decisions/*`, `MANUAL_CHECKPOINT` blocks, change-request log template, session retrospectives | Human checkpoints are captured; not separated into a distinct review-event schema (not needed solo). |

## Coverage Summary

- **Covered:** 6/11 (task spec, context selection, project memory, task state,
  verification, intervention recording)
- **Partial:** 5/11 (tool access, observability, failure attribution,
  permissions, entropy auditing)
- **Missing:** 0/11

The five Partials are all "manual / instruction-level rather than enforced."
For a solo human-as-customer harness that is the intended shape — enforcement
binaries are the upstream "harness as product" path this fork declined
(`docs/decisions/0014`). The honest gaps worth watching:

1. **Entropy auditing** — no drift/stale detector. Mitigated today by the
   Playbook Lifecycle line and the "STAGE.md drift is a bug" rule, both manual.
2. **Failure attribution** — when a gate fails, nothing points to which
   component caused it. The retrospective is the only link.

Re-audit this map whenever a new stage, hook, or template is added — every
tracked harness file should map to at least one responsibility.
