# Context Retrieval Rules

Agents need a map, not a preloaded manual. Start from `AGENTS.md`, follow the
nearest relevant index, and retrieve only enough product, design, plan, code,
and validation truth to act safely.

The canonical task flow is `docs/WORKFLOW.md`.

## Authority Before Retrieval

| Requested outcome | Mutation authority | Starting context |
| --- | --- | --- |
| Answer, explanation, review, diagnosis, plan, or status | Read-only | `AGENTS.md`, named material, then the smallest adjacent evidence needed to answer. |
| Bounded change | Repository changes within the request | `AGENTS.md`, `docs/WORKFLOW.md`, affected product/design material, implementation, and existing proof. |
| Durable planned change | Repository changes within the request plus one active plan | Bounded-change context plus the active plan and relevant lasting decisions. |

Discovery does not expand authority. Finding a defect during a review does not
authorize fixing it.

## Progressive Disclosure

### Understand The Outcome

Read:

- the user request;
- the nearest product contract or current behavior description;
- the affected code or observable surface; and
- existing tests or validation commands.

Stop when the intended outcome, affected boundary, and plausible proof are
clear. Do not read unrelated historical stories or phase documents.

### Plan The Change

For bounded work, keep the plan in working context.

For durable work, read and update one file in `docs/plans/active/`. Retrieve
architecture and decisions only when they constrain the approach. Historical
plans are references, not current instructions.

### Implement

Read the files being changed and enough adjacent code to preserve local
patterns. Expand context when an actual boundary is crossed, not because a lane
requires a generic document bundle.

### Validate

Read the requested behavior, existing tests, repository-required checks, and
the active plan's validation section when one exists. Prefer proof that directly
exercises the behavior.

### Report

Inspect the final diff and validation output. Report the verified outcome,
important changed surfaces, limitations, and anything intentionally not
attempted. No manual trace specification is required.

## Retrieval Triggers

| Trigger | Additional context |
| --- | --- |
| Database schema, durable records, or migrations | Relevant schema, storage code, recovery procedure, and applicable decisions. |
| Public API or user-visible behavior | Product contract, consumers, compatibility tests, and end-to-end proof. |
| Authentication, authorization, privacy, or security | Existing policy, trust boundaries, negative tests, and recovery or incident guidance. |
| External provider behavior | Provider contract, failure modes, local adapters, and integration proof. Do not escalate solely because a provider is mentioned. |
| Architecture or dependency direction | `docs/ARCHITECTURE.md`, applicable decisions, and mechanical structure checks. |
| Installer or release behavior | `scripts/README.md`, installers, manifests, release decisions, and platform tests. |
| Complex or multi-session work | One active execution plan and its directly relevant sources. |
| Missing or stale repository knowledge | Correct the bounded source or identify a targeted documentation check; do not create a manual trace merely to record the gap. |

## Context Budget

The mandatory entry context is `AGENTS.md` plus `docs/WORKFLOW.md`, targeting
under approximately 1,000 words. Everything else is task-selected.

Use targeted `rg` searches, indexes, generated references, and project tools.
Do not preload compatibility manuals, completed plans, historical stories,
review evidence, or database state unless the task targets them.

## Completion Check

Before editing:

- The observable outcome is understood.
- Relevant product or design truth has been identified.
- Durable planning and human judgment needs have been considered independently.
- A behavior-appropriate proof path is known or its absence is explicit.

Before reporting:

- The final diff has been inspected.
- Relevant validation output has been inspected.
- Product, architecture, decision, and active-plan truth remains current.
- Claims do not exceed the available evidence.

## Compatibility Context

SQLite intake, story, matrix, trace, scoring, audit, proposal, and changeset
documents are retrieved only when a task explicitly targets the compatibility
control plane or an external orchestrator requires them. Their presence in the
repository does not make them default context.
