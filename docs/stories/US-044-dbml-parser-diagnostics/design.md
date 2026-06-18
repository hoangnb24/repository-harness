# Design

## Domain Model

`Schema` remains the downstream contract for profiling, quality checks,
relationship checks, graph artifacts, and reports.

`SchemaParseReport` is an additive machine artifact with:

- parse status and parser version;
- object counts for projects, enums, table groups, tables, columns,
  indexes, relationships, notes, defaults, and settings;
- diagnostics grouped by severity (`info`, `warning`, `error`);
- unsupported constructs with line numbers and snippets when available;
- DBML object summaries useful for debugging parser coverage.

## Application Flow

1. Read DBML text at the input boundary.
2. Parse it into `Schema` plus `SchemaParseReport`.
3. Fail fast only on malformed constructs that prevent reliable table or
   relationship parsing.
4. Continue on unsupported-but-nonfatal syntax while recording explicit
   diagnostics.
5. Write `schema_parse_report.json` with other machine artifacts.
6. Link parse diagnostics from Markdown/HTML reports and web-runner artifact
   listings.

## Interface Contract

Existing CLI options, web-runner routes, and deterministic artifact names stay
unchanged.

New additive artifact:

```json
{
  "artifact": "schema_parse_report",
  "version": 1,
  "status": "parsed_with_warnings",
  "source": {"path": "schema.dbml"},
  "counts": {"tables": 7, "columns": 42, "relationships": 6},
  "diagnostics": [],
  "unsupported_constructs": []
}
```

`parse_dbml(path)` continues to return `Schema` for existing callers.
Callers that need diagnostics use an additive parser result API.

## Data Model

No database or migration changes. Pydantic models may be added for structured
parse diagnostics if useful, but the report artifact is JSON-compatible and
backward-compatible.

## UI / Platform Impact

Reports add a compact Schema Parse Diagnostics section. The local web runner
adds `schema_parse_report.json` to canonical artifact listings and dashboard
artifact sources. The browser does not parse DBML for profiler facts after a
run.

## Observability

The parse stage records table count, relationship count, diagnostic count, and
unsupported construct count in runtime details. The parse report gives durable
evidence for ignored syntax.

## Alternatives Considered

1. Adopt a third-party full DBML parser. Deferred because the local MVP has no
   parser dependency today and needs controlled compatibility with the existing
   `Schema` model.
2. Replace `Schema` with parser-native objects. Rejected because it would
   ripple through profiling, relationship validation, reports, and chart
   artifacts.
3. Treat every unsupported construct as fatal. Rejected because real-world DBML
   often contains presentation metadata that should not block profiling.
