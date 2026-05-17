# Phase 01 — Code Review Scoring Playbook

> **Independence note:** Authoring + execution in same session. Skeleton in
> body is canonical content; no external skim required.

## Context Links

- Parent plan: `plan.md`
- Decision: `docs/decisions/0005-roadmap-execution-direction.md` (Plan D
  ordering).
- Source pattern: ck:code-review — X/10 weighted rubric (Tier S4).
- Harness anchors:
  - `docs/HARNESS.md` § Traceability Tokens (TC tokens this playbook may
    cite in evidence rows).
  - `docs/FEATURE_INTAKE.md` § Lanes (per-tier application aligns with
    lane tiers).

## Overview

- **Priority:** First in Plan D — quality gate that subsequent phases
  may reference.
- **Status:** pending.
- **Brief:** Ship a portable X/10 review rubric (correctness 3 +
  security 2 + quality 2 + performance 1 + maintainability 1 + tests 1)
  with a pass/fail gate at ≥7, per-tier application, and an output
  template that cites composite tokens.

## Key Insights

- ClaudeKit's 3/2/2/1/1/1 weighting privileges correctness + security
  over polish — matches harness priorities (functional first; ship
  small, validate).
- Re-deriving weights without observed review evidence would be
  speculative — copy ClaudeKit's exact weights and document the
  decision so a later session can recalibrate when real review data
  exists.
- Pass/fail gate at ≥7 means a story with correctness=3 + security=2 +
  tests=1 (= 6) auto-fails — forcing at least one of quality /
  performance / maintainability to land.
- Per-tier rule mirrors Plan A token tier rule: tiny = optional,
  normal = required, high-risk = required + 2 reviewers minimum.

## Requirements

Functional:
- New playbook `docs/playbooks/code-review-scoring.md` covering:
  the 6 dimensions with weight + scoring criteria, pass/fail gate,
  per-tier application, output template (review report), evidence
  format that cites composite tokens.
- Register in `docs/playbooks/README.md` under "Structural framework"
  group (long-lived rubric, not a sequenced procedure).

Non-functional:
- Playbook under 160 lines.
- Weights documented as a decision inside the playbook (not buried in a
  footnote) so future agents see the rationale.
- No tool prescription (rubric is human-applied; automation out of scope
  per Plan D § Out Of Scope).

## Architecture

```text
docs/playbooks/
├── code-review-scoring.md        ← NEW
│   ├─ When to run (PR review; per-tier gating)
│   ├─ The 6 dimensions (weight + scoring criteria 0..weight)
│   ├─ Pass/fail gate (≥7 = pass; below = block merge)
│   ├─ Per-tier application (tiny / normal / high-risk)
│   ├─ Output report template (review header + 6 rows + verdict)
│   └─ Weight decision rationale (why 3/2/2/1/1/1)
└── README.md (updated)
```

## Related Code Files

To modify:
- `docs/playbooks/README.md` — add row in "Structural framework" group.

To create:
- `docs/playbooks/code-review-scoring.md`.

## Implementation Steps

1. Draft 6-dimension table with weight + scoring criteria.
2. Define pass/fail gate (≥7 = pass).
3. Define per-tier application aligned with Plan A token tier rule.
4. Define output report template citing composite tokens.
5. Add Weight Decision section documenting copy-from-ClaudeKit rationale.
6. Register in `docs/playbooks/README.md` (Structural framework group).
7. Grep verify: `grep -l "code-review-scoring" docs/playbooks/README.md`.
8. Commit.

## Open Question Resolution

**Q:** Copy ClaudeKit weights (3/2/2/1/1/1) or recalibrate?
**A:** Copy verbatim. No observed harness review data exists to justify
recalibration. ClaudeKit's weights privilege correctness + security
which matches harness "ship small, validate" priorities. Future
re-calibration follows the standard backlog → decision flow when
review reports accumulate signal.

## Plan E Overlap Check

- A1 XRE validate: validates *requirements*, not *implementation*. No
  overlap.
- A2 feature register: tracks which features exist, not their quality.
  No overlap.
- A3 QA video evidence: artifact capture from QA pass, separate from
  review scoring. No overlap.

No fold/punt action needed.

## Todo

- [ ] Draft playbook from skeleton.
- [ ] Register in README.
- [ ] Grep verify.
- [ ] Commit.

## Success Criteria

- File under 160 lines.
- All 6 dimensions present with weight + 3-line scoring criteria each.
- Pass/fail gate explicit (≥7).
- Per-tier table present.
- Weight decision rationale documented inline.
- Output report template uses composite token form (`US-NNN.REQ-MMM`,
  etc.).
- Registered in `docs/playbooks/README.md` under "Structural framework".

## Risk

Tiny. Docs only.

## Security Considerations

None.

## Next Steps

- Phase 02 may reference this rubric (E2E test pass = ≥7 review score
  on the test code itself).
- Future plans may add an automated scorer; out of scope per Plan D §
  Out Of Scope.
