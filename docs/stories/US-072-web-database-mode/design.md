# Design

## Domain Model

`database` becomes a local web-runner input mode. It adapts a selected
Postgres or MySQL/MariaDB database source into the existing
`TabularSourceConnector` boundary. The connector supplies schema metadata and a
temporary DuckDB-readable catalog. The profiler still owns profiling, quality
checks, relationship checks, influence analysis, readiness artifacts, reports,
and runtime events.

## Application Flow

1. Browser posts `/api/database-jobs` with source type, connection URL,
   schema/database, optional tables, chunk rows, optional rules path, optional
   target column, and optional L4 mode.
2. The local backend validates source type, URL scheme, chunk size, rules path,
   target format, and L4 options.
3. The backend writes `database_inputs.json` with a redacted URL only.
4. The backend constructs `PostgresConnector` or `MySQLConnector` and calls
   `run_pipeline(dbml_path=None, csv_dir=None, source_connector=...)`.
5. Runtime events stream through the existing SSE endpoint. Generated artifacts
   and dashboard payloads use existing artifact routes.

## Interface Contract

Request:

```json
{
  "source_type": "postgres",
  "connection_url": "postgresql://user:password@127.0.0.1:5432/app",
  "schema": "public",
  "tables": "customers,orders",
  "chunk_rows": 10000,
  "rules_path": "data/demo_small/rules.yaml",
  "target": "orders.order_total",
  "use_llm": false,
  "llm_provider": null
}
```

Response: same job payload as `/api/jobs` and `/api/path-jobs`, with
`input_mode: "database"` and a `database.source_type` summary. Raw connection
URLs are never returned.

## Data Model

No database migrations. Job state remains in memory. Job input manifests remain
under ignored `outputs/web_runs/<id>/input/`. Connector temporary CSV extracts
remain under `outputs/web_runs/<id>/artifacts/.connector_extracts/` during the
run and are removed before completion by the existing connector cleanup.

## UI / Platform Impact

The runner mode segmented control gains a Database tab. The database form uses
compact operational controls: source type, connection URL, schema/database,
table list, chunk rows, rules path, target column, and the shared L4 toggle.
The console remains local-first and dense; no marketing or landing-page surface
is introduced.

## Observability

Database mode uses existing `run.log`, `run_events.jsonl`, `run_summary.json`,
runtime stage list, generated-results preview, and dashboard artifact links.
Connector metadata records source type, scanned tables, extraction status,
warnings, chunk rows, redaction status, and a redacted connection URL.

## Alternatives Considered

1. Add a second web-only profiling path. Rejected because it would duplicate
   CLI connector behavior and weaken artifact parity.
2. Persist connector extracts for user download. Rejected because the product
   contract excludes raw source CSV files and temporary extracts from packages
   and generated artifacts.
3. Require users to create DBML manually for database mode. Rejected because
   existing connector introspection already generates schema evidence and
   `schema_diagram.dbml`.
