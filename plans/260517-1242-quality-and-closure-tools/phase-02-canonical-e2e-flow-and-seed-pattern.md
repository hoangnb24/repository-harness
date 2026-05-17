# Phase 02 — Canonical E2E Flow + Seed Data Pattern

> **Independence note:** Same-session authoring. Skeletons in body are
> canonical; no external skim required.

## Context Links

- Parent plan: `plan.md`
- Decision: `docs/decisions/0005-roadmap-execution-direction.md`.
- Source patterns: ck:e2e-flow + ck:seed-data (Tier S7, S8 in scan
  report).
- Harness anchors:
  - `docs/HARNESS.md` § Traceability Tokens (TC tokens cited per test).
  - `docs/TEST_MATRIX.md` (E2E rows reference flow playbook).
  - `docs/playbooks/scenario-taxonomy-playbook.md` (SC tokens feed E2E
    test design).

## Overview

- **Priority:** Second in Plan D — composes on phase-01 (review scoring
  applies to test code too).
- **Status:** pending.
- **Brief:** Ship two playbooks in one commit:
  - `canonical-e2e-flow-playbook.md` — phase-typed E2E test design
    (form / workflow / readonly / mixed). Each test cites TC token.
  - `seed-data-pattern.md` — deterministic FK-valid demo data shape.
    No locale data. No VN master data.

## Key Insights

- E2E tests recurringly fail to mirror real user flows because authors
  write step-by-step assertions, not journey-based assertions. Phase
  typing (form / workflow / readonly / mixed) forces authors to pick a
  shape before writing.
- Seed data is recurring friction: each story re-derives test fixtures
  ad-hoc, leading to FK violations and non-deterministic test order.
  The pattern ships the *shape* (FK-valid, deterministic IDs, scoped
  cleanup) — not actual master data.
- VN master data was explicitly rejected per roadmap report: harness
  ships locale-agnostic patterns; org owns locale-specific datasets.
- "DB seed only" recommendation (Plan D plan.md unresolved Q3): unit
  fixtures are framework-specific and out of harness scope.

## Requirements

Functional:
- New playbook `docs/playbooks/canonical-e2e-flow-playbook.md`:
  4 flow types with shape definition + sample skeleton; per-test TC
  token requirement; hand-off to TEST_MATRIX.
- New playbook `docs/playbooks/seed-data-pattern.md`:
  deterministic ID convention, FK-valid construction order, scoped
  cleanup, no-locale-data rule, DB-only scope.
- Register both in `docs/playbooks/README.md` under "Workflow recipe"
  group (E2E flow is a sequenced procedure; seed-data is a structural
  framework — register seed under "Structural framework").

Non-functional:
- E2E flow playbook under 160 lines.
- Seed data playbook under 120 lines.
- Single commit covers both files + README update.
- Zero `Vietnamese`, `VN`, `vi-VN`, or country-specific data references
  in either file.

## Architecture

```text
docs/playbooks/
├── canonical-e2e-flow-playbook.md     ← NEW (Workflow recipe)
│   ├─ When to run (per-story E2E phase)
│   ├─ 4 flow types (form / workflow / readonly / mixed)
│   ├─ Per-type skeleton (steps, assertions, TC-token line)
│   ├─ Cap rule (≤ 1 user journey per E2E file)
│   └─ Hand-off to TEST_MATRIX
├── seed-data-pattern.md               ← NEW (Structural framework)
│   ├─ When to use (any DB-backed test needing data)
│   ├─ Deterministic ID convention
│   ├─ FK-valid construction order
│   ├─ Scoped cleanup (no test pollution)
│   ├─ No-locale-data rule (explicit)
│   └─ Scope: DB seed only (NOT unit fixtures)
└── README.md (updated — 2 rows added)
```

## Related Code Files

To modify:
- `docs/playbooks/README.md` — 2 entries.

To create:
- `docs/playbooks/canonical-e2e-flow-playbook.md`.
- `docs/playbooks/seed-data-pattern.md`.

## Implementation Steps

1. Draft canonical-e2e-flow-playbook.md with 4 flow type definitions +
   skeletons.
2. Draft seed-data-pattern.md with ID convention + FK-order rule +
   cleanup + no-locale rule.
3. Register both in README (correct groups).
4. Grep verify: `grep -lE "(canonical-e2e-flow|seed-data-pattern)" docs/playbooks/README.md`
   returns README. Grep for forbidden strings:
   `grep -iE "Vietnamese|\bVN\b|vi-VN" docs/playbooks/canonical-e2e-flow-playbook.md docs/playbooks/seed-data-pattern.md`
   returns empty.
5. Single commit.

## Open Question Resolution

**Q3 (Plan D plan.md):** Seed-data pattern scope — DB only or also
fixture files? **A:** DB only. Fixtures are framework-specific
(Jest snapshots, pytest fixtures, etc.) and belong in framework docs.

## Plan E Overlap Check

- A1 XRE validate: requirements-side, not test-side. No overlap.
- A3 QA video evidence: post-test artifact capture. Could *consume*
  canonical-e2e-flow output (the journey IS the video script) but
  doesn't replace it. Note in playbook § Related; no fold/punt.

## Todo

- [ ] Draft canonical-e2e-flow-playbook.md.
- [ ] Draft seed-data-pattern.md.
- [ ] Register both in README.
- [ ] Grep verify (existence + no-locale).
- [ ] Single commit.

## Success Criteria

- Both files exist; LoC caps respected (E2E ≤ 160, seed ≤ 120).
- E2E playbook: 4 flow types documented; each has skeleton citing TC
  token.
- Seed playbook: ID convention, FK-order rule, cleanup, no-locale-data
  rule all present.
- README registers both under correct groups.
- No `Vietnamese` / `VN` / `vi-VN` strings in either file.
- Single commit covers both.

## Risk

Tiny. Docs only.

## Security Considerations

Seed data playbook must warn: seed data is for DEV/TEST environments
only; never seed production. Add one-line warning.

## Next Steps

- Phase 03 may reference these playbooks in project-closure-story
  documentation index.
- Plan E A3 (QA video evidence) consumes canonical-e2e-flow output if
  Plan E runs.
