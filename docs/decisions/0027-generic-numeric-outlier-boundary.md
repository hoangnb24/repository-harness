# 0027 Generic Numeric Outlier Boundary

Date: 2026-06-18

## Status

Accepted

## Context

The Smart EDA MVP should help data scientists review arbitrary CSV plus
DBML/schema datasets. Outlier detection is useful EDA evidence, but it can
easily become domain-specific if rules assume business meaning, revenue,
orders, customers, or a particular dataset.

## Decision

Add generic numeric outlier detection as an aggregate profiling capability.
Numeric profiles store percentiles and default IQR fence evidence. Quality
checks emit additive `NUMERIC_OUTLIER` P3 review findings from that evidence
with bounded sample rows. Reports, package index, package PDF source Markdown,
chart specs, and local dashboard surfaces expose numeric outlier summaries.

Keep the implementation inside the DuckDB CSV scan path. Do not add unbounded
pandas reads, full-dataframe materialization, plotting dependencies, or
domain-specific labels/actions.

## Alternatives Considered

1. Use YAML rules only. Rejected because the MVP should provide automatic EDA
   signals before users know which columns deserve custom rules.
2. Add domain-specific anomaly rules for the demo dataset. Rejected because
   the product must work for arbitrary datasets and fields.
3. Add a separate `outliers.json` artifact. Deferred because additive evidence
   in `profile_summary.json` plus `charts/outliers_top_columns.json` satisfies
   review and report needs without expanding the core artifact set.

## Consequences

Positive:

- Numeric outlier evidence is available in machine artifacts, issue evidence,
  reports, packages, and dashboard review.
- The feature aligns with generic EDA framing and does not require a target
  column or business context.

Tradeoffs:

- IQR can flag identifier-like numeric columns or heavy-tailed valid values, so
  findings are P3 review signals rather than readiness blockers.
- Optional z-score support remains future work.

## Follow-Up

- Consider opt-in z-score configuration only if it can remain generic and
  artifact-compatible.
