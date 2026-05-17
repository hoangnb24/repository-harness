# Code Review Scoring Playbook

**Lifecycle:** experimental · **First use:** TBD · **Verified by:** none

> Six-dimension X/10 rubric with a pass/fail gate at ≥7. Human-applied
> per PR or per story.

## When To Run

- Before approving a pull request for merge.
- During high-risk story acceptance (per-tier rule below).
- When auditing recently merged work — the rubric works retroactively
  too.

Skip when the change is a typo fix, docs-only patch with no semantic
shift, or generated-file refresh (lockfile, build artifact). Document
the skip reason in the merge note.

## The Six Dimensions

| Dimension | Weight | Scoring criteria |
| --- | --- | --- |
| Correctness | 3 | 0 = breaks intended behavior; 1 = behaves correctly on happy path only; 2 = handles documented edge cases; 3 = handles all edge cases the story names + at least one unstated. |
| Security | 2 | 0 = introduces vulnerability or exposes secret; 1 = no new risk but does not harden existing surface; 2 = explicitly defends a previously-soft surface (input validation, auth check, audit trail). |
| Quality | 2 | 0 = unreadable / duplicates existing patterns; 1 = readable, follows existing patterns; 2 = simplifies or removes complexity beyond the immediate change. |
| Performance | 1 | 0 = visibly slower under documented load; 1 = no regression or measurable improvement. |
| Maintainability | 1 | 0 = adds dead code, unused abstractions, or tight coupling; 1 = leaves the surface easier to change next time. |
| Tests | 1 | 0 = no proof or weakens existing proof; 1 = adds proof for the new behavior at the appropriate level (unit / integration / E2E). |

Max total: **10**. Pass threshold: **≥7**. Fractional scores are
allowed (e.g. correctness 2.5) when one criterion is partial.

## Pass / Fail Gate

- **≥7:** pass. Merge approved.
- **<7:** block merge. Reviewer writes one-line remediation per
  failing dimension; author re-submits.

A floor rule: any dimension scoring **0** is an automatic block
regardless of total. A 0 is a regression, not a low score.

## Per-Tier Application

Matches Plan A's token tier rule (see `docs/HARNESS.md` § Traceability
Tokens).

| Lane | Application |
| --- | --- |
| Tiny | Optional. Reviewer may skip the rubric and approve by inspection. |
| Normal | Required. One reviewer applies the rubric; result attached to PR. |
| High-risk | Required. Two reviewers apply the rubric independently; merge requires both ≥7. |

## Output Report Template

```markdown
# Review — <PR id or commit short sha>

Story: `US-NNN-slug.md` (or "no story — tiny lane")
REQ tokens touched: `US-NNN.REQ-001`, `US-NNN.REQ-002`, ...
SC tokens proven: `US-NNN.SC-001`, ...

| Dimension | Weight | Score | Notes |
| --- | --- | --- | --- |
| Correctness | 3 | 3 | All `US-NNN.SC-*` cases verified, including `SC-004` not in story. |
| Security | 2 | 1 | No new risk; did not harden the auth path it touches. |
| Quality | 2 | 2 | Removed duplicate validator; net -30 LoC. |
| Performance | 1 | 1 | Bench-checked: same throughput. |
| Maintainability | 1 | 1 | Extracted helper; one fewer hardcoded path. |
| Tests | 1 | 1 | Added `US-NNN.TC-005` covering `SC-004`. |
| **Total** | **10** | **9** | |

**Verdict:** PASS (9 ≥ 7).
**Remediation (if any):** none.
```

## Weight Decision

Weights are `3 / 2 / 2 / 1 / 1 / 1` for correctness / security /
quality / performance / maintainability / tests. This privileges
correctness + security over polish, matching the harness "ship small,
validate" priority.

The weights are copied verbatim from the upstream rubric they were
ported from. They were NOT recalibrated for this harness because no
observed review data yet justifies a different distribution.
Recalibration follows the standard `docs/HARNESS_BACKLOG.md` →
decision flow when accumulated review reports surface a pattern
(e.g. correctness consistently scoring high while security is
consistently 1).

## Variant Section

(Append a Variant block when this rubric fails or partially works.
Do not delete the original dimensions or weights.)

## Related

- `docs/HARNESS.md` § Traceability Tokens — composite tokens cited in
  review reports.
- `docs/playbooks/scenario-taxonomy-playbook.md` — SC tokens that the
  Correctness dimension validates.
- `docs/playbooks/README.md` § Use Order — Variant convention.
- `docs/FEATURE_INTAKE.md` § Lanes — tier definitions referenced by
  per-tier application.
