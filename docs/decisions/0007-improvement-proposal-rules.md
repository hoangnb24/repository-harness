# 0007 Improvement Proposal Rules

Date: 2026-06-04

## Status

Accepted for the optional compatibility proposal command. It does not govern
the default repository workflow under
`0019-repository-centered-default-workflow.md`.

## Context

Phase 5 adds `harness-cli propose`, which changes the harness evolution model.
The command must be useful without becoming an unchecked source of scope creep
or circular recommendations.

## Decision

Improvement proposals are advisory, rule-based, and evidence-backed. The command
may summarize repeated friction, repeated interventions, and audit drift. It may
create `proposed` backlog items only when `--commit` is supplied.

Every proposal must include:

- affected Harness component,
- concrete evidence,
- predicted impact,
- risk lane,
- suggested action,
- validation plan,
- confidence level.

High-risk proposal implementation still requires human review and a durable
decision record when it changes source hierarchy, architecture direction,
validation requirements, or risk policy.

## Alternatives Considered

1. Generate free-form LLM recommendations. Rejected because Phase 5 needs a
   deterministic and auditable evolution role.
2. Automatically apply proposed changes. Rejected because the harness must not
   rewrite its own policy without review.
3. Only report audit findings. Rejected because H5 requires proposed
   improvements, not just drift detection.

## Consequences

Positive:

- Repeated operational patterns can become backlog items.
- Proposal output is explainable and testable.
- Human review remains the gate for risky harness changes.

Tradeoffs:

- Rule-based grouping can miss semantically similar phrasing.
- Audit-based proposals may be housekeeping rather than strategic evolution.

## Follow-Up

- Use benchmark runs and closed backlog outcomes to improve proposal quality in
  later phases.
