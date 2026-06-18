# Overview

## Current Behavior

VSF Data Profiler profiles CSV directories against a DBML schema. Users with
Postgres data must export tables to CSV manually before running the profiler.

## Target Behavior

Users can run the profiler against selected Postgres tables by providing a
connection URL or environment variable, schema/table selection, and an output
directory. DBML remains optional for Postgres mode; when absent, the profiler
introspects Postgres metadata and builds a compatible schema catalog.

The core profiling, quality, relationship, verdict, chart, report, and LLM
paths remain the existing Python/DuckDB pipeline. Connector mode writes an
additive `connector_metadata.json` artifact and redacts secret-bearing values
from logs, events, summaries, reports, and web artifact payloads.

## Affected Users

- CLI users profiling Postgres tables without manual CSV export.
- Maintainers preserving streaming-safe profiling boundaries.
- Local web-runner users reviewing generated connector artifacts if a web job
  writes them in the future.

## Affected Product Docs

- `README.md`
- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`
- `docs/TEST_MATRIX.md`
- `docs/decisions/0015-postgres-connector-boundary.md`

## Non-Goals

- No MySQL, SQL Server, BigQuery, Snowflake, or other connectors.
- No hosted backend or long-running distributed execution.
- No enterprise lineage integrations.
- No raw data previews beyond existing bounded sample artifacts.
- No pandas full-table loading.
