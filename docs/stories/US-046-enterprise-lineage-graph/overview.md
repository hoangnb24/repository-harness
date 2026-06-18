# Overview

## Current Behavior

VSF Data Profiler writes schema, relationship, verdict, chart, runtime, report,
and optional connector metadata artifacts. Users can inspect those files
individually, but there is no single artifact that explains source-to-schema,
schema-to-profile, runtime-stage, and report/artifact dependencies.

## Target Behavior

Each successful run writes an additive `lineage_graph.json` artifact that links
input sources, schema entities, relationships, profiler stages, and generated
artifacts. CSV/DBML mode and Postgres connector mode both use the same lineage
builder, with connector-derived source metadata redacted before it enters the
lineage graph.

Reports and the local web runner expose the lineage artifact through existing
artifact links and dashboard artifact discovery. The artifact is evidence-only:
it summarizes dependencies already proven by existing machine artifacts and
does not introduce external lineage/catalog integrations.

## Affected Users

- CLI users who need to explain which tables, columns, stages, and artifacts
  contributed to a profiling result.
- Local web-runner users reviewing completed jobs through artifact links.
- Maintainers preserving additive artifact contracts and redaction boundaries.

## Affected Product Docs

- `README.md`
- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`
- `docs/TEST_MATRIX.md`
- `docs/decisions/0016-enterprise-lineage-boundary.md`

## Non-Goals

- No dbt, Airflow, Superset, BI, or external catalog integrations.
- No database writes or metadata publishing.
- No column-level transform lineage beyond the current generated evidence.
- No raw CSV dashboard reads.
- No hosted lineage service.
