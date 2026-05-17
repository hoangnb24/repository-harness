# Plan D — Quality + Closure Tools

**Date:** 2026-05-17 · **Branch:** main · **Status:** completed 2026-05-17

**Plan status:** completed 2026-05-17. All 7 grep validation checks passed.

## Goal

Recover three Tier S items the original decision 0004 silently dropped, plus
ship a per-project closure shape distinct from Plan C's per-release closure.

Output is four artifacts that make quality measurable, tests reproducible,
project handoff portable, and current-state legible.

## Triggers (per decision 0005 § 1)

Sequential after Plan C. Execute when:

- Plan C is committed and validated.
- No higher-priority work has surfaced (e.g. Plan B trigger has fired —
  in that case run Plan B first per the original sequence).

## Source Context

- `docs/decisions/0005-roadmap-execution-direction.md` — Plan D ordering
  (sequential after C).
- `plans/reports/roadmap-260517-1234-claudekit-custom-port-roadmap.md` —
  Plan D scope and "silent dropout" recovery rationale.
- `plans/reports/xia-260517-1130-claudekit-custom-skill-scan.md` — Tier S4,
  S7, S8 source analysis.

## Phases (drafted at execution time)

Phase file detail intentionally deferred per decision 0005 § Alternatives 3.
Sketch below is for visibility.

| # | Phase | Output | Status |
|---|-------|--------|--------|
| 1 | [Code review scoring playbook](phase-01-code-review-scoring-playbook.md) | `docs/playbooks/code-review-scoring.md` — X/10 rubric (3+2+2+1+1+1). Pass gate ≥7. ClaudeKit weights copied verbatim; recalibration deferred. | completed (commit `a05143e`) |
| 2 | [Canonical E2E flow + seed data pattern](phase-02-canonical-e2e-flow-and-seed-pattern.md) | `docs/playbooks/canonical-e2e-flow-playbook.md` (4 flow types) + `docs/playbooks/seed-data-pattern.md` (DB seed only, no locale data). | completed (commit `9785fdc`) |
| 3 | [Project closure story template](phase-03-project-closure-story-template.md) | `docs/templates/project-closure-story/` — 4 files mirroring delivery-closure-story shape, scoped to end-of-project handover. | completed (commit `0846f5f`) |
| 4 | [Project status snapshot playbook](phase-04-project-status-snapshot-playbook.md) | `docs/playbooks/project-status-snapshot.md` — read-only agent-read snapshot. Playbook, NOT script (decision 0005 § 6). | completed (commit `e437b30`) |

**Estimated effort when work begins:** ~5-8h.

## Dependencies

- Plan A complete (uses REQ / SC / TC tokens).
- Plan C complete (delivery-closure-story exists so project-closure-story
  can distinguish per-release vs per-project closure).
- Plan B optional (synergistic but not blocking — Plan D's prod-related
  hooks can reference Plan B playbooks when Plan B exists).

## Risk

Tiny. All four phases are docs / templates only. No installer touch, no
agent behaviour change until adopted by a story.

## Success Criteria (will apply when triggered)

- `docs/playbooks/code-review-scoring.md` exists, registered.
- `docs/playbooks/canonical-e2e-flow-playbook.md` exists, registered.
- `docs/playbooks/seed-data-pattern.md` exists, registered.
- `docs/templates/project-closure-story/` exists with 4 files mirroring
  `delivery-closure-story/` shape proportions.
- `docs/playbooks/project-status-snapshot.md` exists, registered.
- `docs/FEATURE_INTAKE.md` registers both closure shapes (delivery + project).
- All shipped artifacts use composite token placeholders consistent with
  Plan A.

## Out Of Scope

- VN master data in seed-data-pattern (rejected outright per roadmap).
- Python implementation of project-status (rejected per decision 0005 § 6 —
  playbook is the right shape until proven otherwise).
- Test framework prescription (Playwright, Jest, etc. — team owns test
  infrastructure).
- Code review automation (X/10 rubric is human-applied; scoring agent
  optional and out of scope).
- Hypercare / monitoring (Plan B).

## Plan D vs Plan E Boundary

Plan E (Tier A patterns) overlaps with Plan D on two surfaces:

- A1 XRE validate mode → potentially a "requirements validation" playbook.
- A3 QA video evidence → potentially merges into Plan D phase 2.

When working on Plan D, check Plan E scope before adding scope. If a Plan
D phase grows to include a Plan E item, document the overlap in the phase
file and either fold or punt to Plan E.

## Unresolved Questions (will resolve at execution time)

1. Project status snapshot output format: markdown report only, or also
   a one-line summary the agent can echo at session start?
2. Code review scoring rubric weights: do we copy ClaudeKit's
   3/2/2/1/1/1 exactly, or recalibrate based on observed harness work
   priorities?
3. Seed data pattern: does it cover only DB seed, or also fixture files
   for unit tests? Recommend DB seed only — fixtures are framework-specific
   and out of harness scope.
