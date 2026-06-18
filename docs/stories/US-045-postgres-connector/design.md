# Design

## Domain Model

`TabularConnector` is the input adapter boundary for sources that are not
already a CSV directory. The first implementation is `PostgresConnector`.

Connector output is intentionally shaped like the existing CSV pipeline:

- `Schema`: parsed DBML schema or introspected Postgres schema.
- `CsvCatalog`: table mappings pointing at temporary DuckDB-readable extracts.
- `connector_metadata.json`: source type, selected tables, extract status,
  introspection status, row-count estimates, warnings, and redaction status.

## Application Flow

1. CLI determines source mode: CSV or Postgres.
2. CSV mode follows the existing DBML + CSV directory path.
3. Postgres mode resolves the connection URL from `--postgres-url` or
   `--postgres-url-env`.
4. The connector introspects selected tables and constraints.
5. If DBML is absent, the connector builds `Schema` from introspection.
6. The connector streams selected rows in chunks into temporary local CSV
   extracts for DuckDB scans.
7. Existing profiling, quality, relationship, verdict, chart, report, and
   optional LLM stages run unchanged against that catalog.
8. Temporary connector extracts are removed after the run.
9. `connector_metadata.json` is written and linked with other artifacts.

## Interface Contract

Additive CLI options:

- `--postgres-url`
- `--postgres-url-env`
- `--postgres-schema`
- `--postgres-tables`
- `--postgres-chunk-rows`

Existing CSV options continue to work. `--csv-dir` remains required only for
CSV mode.

Additive artifact:

```json
{
  "artifact": "connector_metadata",
  "version": 1,
  "source_type": "postgres",
  "connection": {"url": "[redacted]"},
  "tables": [],
  "warnings": []
}
```

## Data Model

No persistent database schema changes. Temporary extracts are local files under
the run output directory and are deleted after profiling. Artifacts store only
metadata and bounded sample files produced by the existing issue catalog.

## UI / Platform Impact

The local web runner remains local-only. It can list and link
`connector_metadata.json` when present, but Postgres credential entry is not
required for this slice.

## Observability

Runtime stages record connector source type, selected table count, extracted
row count, warning count, and redaction status. Secret-bearing values are
redacted by runtime sanitization and connector metadata generation.

## Alternatives Considered

1. Use DuckDB's Postgres scanner directly. Deferred because extension
   availability varies by environment and the existing CSV scan path is already
   streaming-safe and well-tested.
2. Load full Postgres tables into pandas. Rejected by the product constraint.
3. Persist full connector extracts as user-visible artifacts. Rejected because
   raw data previews should remain bounded to sample artifacts.
