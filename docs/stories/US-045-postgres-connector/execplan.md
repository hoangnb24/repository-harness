# Exec Plan

## Goal

Add the first tabular source connector for Postgres while preserving the
existing CSV/DBML run contract and streaming-safe DuckDB pipeline.

## Scope

In scope:

- Connector abstraction.
- Postgres connector with introspection and chunked extraction.
- CLI options for connection URL/env var, schema, selected tables, and chunk
  size.
- Optional DBML handling; introspected schema when DBML is absent.
- Additive `connector_metadata.json`.
- Secret redaction in runtime/report/web surfaces.
- Tests for CSV compatibility, metadata, redaction, skip behavior when
  Postgres is unavailable, and no pandas full-table loading.

Out of scope:

- Other databases.
- Hosted jobs, auth, or production connector management.
- Enterprise lineage.
- Raw table previews.

## Risk Classification

Risk flags:

- Audit/security.
- External systems.
- Public contracts.
- Data model.
- Existing behavior.
- Weak proof.

Hard gates:

- No secrets in artifacts, events, summaries, reports, dashboard payloads, or
  errors.
- Existing artifact names and CSV mode behavior remain compatible.
- Postgres tests skip cleanly when no local fixture is present.

## Work Phases

1. Intake, story, and decision.
2. Tests for connector metadata/redaction and CSV compatibility.
3. Connector abstraction and Postgres implementation.
4. Pipeline and CLI integration.
5. Report/web artifact surfacing.
6. Focused tests and full validation.
7. Harness proof update and trace.

## Stop Conditions

Pause for human confirmation if:

- The implementation would require loading full tables into pandas.
- Existing artifact names or CLI CSV behavior would need to break.
- Web support would expose secrets or require hosted backend behavior.
- Postgres validation cannot cleanly skip when no fixture is available.
