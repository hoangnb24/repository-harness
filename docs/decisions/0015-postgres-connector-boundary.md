# 0015 Postgres Connector Boundary

## Status

Accepted

## Context

VSF Data Profiler currently scans CSV files with DuckDB and keeps all profiling
logic in Python/DuckDB services. US-045 adds Postgres as the first database
source. This introduces credential handling, external systems, and a new input
mode, so the connector boundary needs a durable decision.

## Decision

Add a connector abstraction that adapts non-CSV tabular sources into the
existing `Schema` plus `CsvCatalog` pipeline. The first `PostgresConnector`
introspects selected tables and streams data in chunks into temporary
DuckDB-readable CSV extracts. The existing DuckDB profiling, quality,
relationship, influence, verdict, chart, report, and LLM stages continue to own
all profiling behavior.

`connector_metadata.json` is additive and contains only metadata: source type,
tables scanned, row-count estimates, introspection/extraction status, warnings,
and redaction status. Full raw extracts are temporary implementation details
and are removed after the run.

Connection URLs, passwords, tokens, API keys, and auth material must be
redacted at runtime boundaries. CLI users should prefer `--postgres-url-env` to
avoid putting secrets in shell history, while `--postgres-url` remains
available for local testing.

## Consequences

- Existing CSV + DBML mode remains the default path.
- Postgres mode can run without DBML by introspecting table/column/key/FK
  metadata.
- The connector does not introduce pandas full-table loading.
- Postgres integration tests can skip cleanly when no local fixture is
  configured.
- Web support is limited to artifact listing/dashboard surfacing unless a
  future slice adds a secret-safe local credential UI.

## Verification

```text
.venv/bin/pytest -q tests/test_postgres_connector.py tests/test_demo_small.py tests/test_web_runner.py tests/test_web_ui_static.py
node --check web/app.js
```
