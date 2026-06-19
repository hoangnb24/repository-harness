# 0029 Local Web Database Mode Secret Boundary

Date: 2026-06-19

## Status

Accepted

## Context

The CLI already supports Postgres and MySQL/MariaDB connectors through a
redacted `TabularSourceConnector` boundary. The local web runner previously
supported upload and local path modes only. Adding database mode introduces a
browser form and local HTTP endpoint that receive database credentials, so the
credential boundary must be explicit.

## Decision

Add Database mode only to the local `127.0.0.1` web runner. The browser may
submit a raw Postgres or MySQL/MariaDB connection URL to `/api/database-jobs`,
but the raw URL is used only in process to construct the existing connector.
The backend persists only redacted database input manifests, returns only source
type summaries in job payloads, and relies on connector metadata/runtime
redaction for generated artifacts.

Database mode calls the existing `run_pipeline()` with
`source_connector=PostgresConnector` or `source_connector=MySQLConnector`.
Connector temporary extracts remain implementation details and are removed by
existing cleanup before the run completes. Generated `schema_diagram.dbml`,
`schema_parse_report.json`, `connector_metadata.json`, `run_events.jsonl`,
`run_summary.json`, reports, and dashboard views keep their existing artifact
contracts.

## Alternatives Considered

1. Require database credentials through environment variables only. Rejected
   for the web runner because the user asked for a first-class UI mode; the
   local-only endpoint can safely accept a raw URL without persisting it.
2. Return redacted connection URLs in job payloads. Rejected because source
   type is enough for the browser job summary and avoids another credential
   surface.
3. Persist connector extracts for inspection. Rejected because raw full-table
   extracts are not generated artifacts and must not be bundled or exposed as
   normal artifact links.

## Consequences

Positive:

- Web users can profile real local Postgres/MySQL tables without leaving the
  console.
- Connector schema introspection generates DBML/schema evidence and reports
  without duplicating the profiling engine.
- Credential redaction remains testable across manifests, runtime artifacts,
  reports, and dashboard payloads.

Tradeoffs:

- Database mode depends on optional connector dependencies and local database
  reachability.
- The UI cannot discover table names before connecting; the table list remains
  user-entered for this slice.

## Follow-Up

- Add optional schema/table discovery only if it can preserve the same local
  credential boundary and redaction guarantees.
