# 0014 DBML Parser Diagnostics Boundary

## Status

Accepted

## Context

VSF Data Profiler depends on DBML as the schema contract for table profiling,
quality checks, relationship validation, schema diagrams, and reports. The
current parser supports the MVP subset but silently ignores unsupported table
lines, which makes real-world DBML files hard to debug.

US-044 expands parser coverage and adds parse diagnostics. This changes the
input boundary and adds a public artifact, so the parser/report boundary needs
a durable decision.

## Decision

Keep `Schema` as the downstream contract and add an additive parser result that
contains both `Schema` and `schema_parse_report.json` payload data.

The parser may accept and record DBML metadata such as projects, enums, table
groups, notes, settings, defaults, and index metadata, but profiling and
relationship validation continue to consume only the normalized `Schema`
tables, columns, keys, uniqueness, and relationships.

Unsupported nonfatal DBML constructs must be reported in
`schema_parse_report.json`. Malformed DBML that prevents reliable parsing must
raise `DbmlParseError` with a concrete message.

## Consequences

- Existing callers using `parse_dbml(path) -> Schema` continue to work.
- The pipeline writes one new additive artifact: `schema_parse_report.json`.
- Reports and web-runner artifact listings can expose parser diagnostics
  without changing existing artifact names.
- DuckDB remains the relationship validation engine.
- The browser dashboard remains an artifact consumer and does not parse raw
  CSV rows or reimplement profiler logic.

## Verification

```text
.venv/bin/pytest -q tests/test_dbml_parser.py tests/test_schema_artifacts.py tests/test_demo_small.py tests/test_web_runner.py tests/test_web_ui_static.py
node --check web/app.js
```
