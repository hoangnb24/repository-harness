# 0028 Schema-Aware CSV Mapping Boundary

Date: 2026-06-18

## Status

Accepted

## Context

VSF Data Profiler historically mapped CSV files to DBML tables only by exact
filename stem. Real CSV exports often use source-specific names while retaining
schema-compatible headers. Mapping by headers can reduce setup friction, but a
wrong automatic match would make every downstream profiling artifact misleading.

## Decision

Keep exact filename-stem mapping as the highest-priority path. Add backend-owned
schema/header inference only as a fallback for unmapped tables, with conservative
confidence and margin thresholds. Record mapping candidates and selected mapping
evidence in generated artifacts. Treat ambiguous candidates as unmapped unless a
user supplies an explicit manual override mapping file or web-run override.

Manual overrides are accepted as run configuration, not as data repair. They
force table-to-CSV mapping but do not rename CSV columns, mutate data, or relax
schema/data-quality checks.

## Alternatives Considered

1. Keep exact-stem mapping only. This preserves safety but forces users to
   rename files even when headers strongly identify the intended table.
2. Let the browser preflight UI own smart mapping. This would make CLI and local
   path jobs inconsistent and would duplicate product logic in JavaScript.
3. Auto-select the highest-scoring candidate regardless of margin. This improves
   convenience but risks silent wrong-table profiling when multiple exports share
   common identifier columns.

## Consequences

Positive:

- CLI and web runner share the same mapping semantics.
- Users can review why a CSV was selected or left unresolved.
- Existing exact-name workflows keep their current behavior.

Tradeoffs:

- Some valid but weak matches remain unmapped until users provide an override.
- The additive artifact evidence expands `schema_evaluation.json` and diagram
  payloads, so report/dashboard presenters need to tolerate new fields.

## Follow-Up

- Tune thresholds only from validation evidence or explicit product feedback.
