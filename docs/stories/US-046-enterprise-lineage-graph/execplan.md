# Exec Plan

## Goal

Add an additive enterprise lineage graph artifact that explains source,
schema, relationship, runtime-stage, and output-artifact dependencies for CSV
and connector runs.

## Scope

In scope:

- Add `lineage_graph.json`.
- Build lineage from existing structured artifacts and runtime traces.
- Include CSV and Postgres connector source nodes.
- Redact connector-derived secret-bearing values.
- Surface lineage in Markdown/HTML reports and web-runner artifact/dashboard
  links.
- Add tests for CSV lineage, fake connector lineage, dependencies, and
  redaction.

Out of scope:

- dbt, Airflow, Superset, BI, or hosted catalog integrations.
- Column-level transform lineage beyond current profiler artifacts.
- Database writes or external metadata publishing.
- Raw CSV dashboard reads.

## Risk Classification

Risk flags:

- Audit/security.
- Public contracts.
- Existing behavior.
- Multi-domain.
- Weak proof.

Hard gates:

- Existing artifact names remain compatible.
- No raw rows or unredacted connector secrets enter lineage artifacts,
  reports, events, or web payloads.
- CSV and connector modes both continue to use the existing Python/DuckDB
  pipeline.

## Work Phases

1. Intake, story, and lineage boundary decision.
2. Lineage artifact contract and tests.
3. Pipeline integration after deterministic machine artifacts are available.
4. Report and web-runner artifact surfacing.
5. Product docs and test matrix updates.
6. Focused and full validation.
7. Harness proof update and trace.

## Stop Conditions

Pause for human confirmation if:

- Existing artifact names or CSV/Postgres behavior would need to break.
- Lineage would require reading raw CSV rows outside the profiler pipeline.
- Secret redaction cannot be proven for connector-derived metadata.
- The implementation would require publishing to an external lineage catalog.
