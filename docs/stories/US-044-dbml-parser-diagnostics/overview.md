# Overview

## Current Behavior

The VSF Data Profiler parses a pragmatic DBML subset with regular expressions.
It supports tables, columns, basic column attributes, inline refs, short
`Ref:` declarations, and composite primary keys from `indexes { (...) [pk] }`.
Unsupported table lines are currently skipped, which makes real-world DBML
hard to diagnose when constructs are not represented in downstream schema
artifacts.

## Target Behavior

The parser accepts broader real-world DBML syntax while keeping the existing
`Schema` contract intact. It should parse useful schema facts from `Project`,
`Enum`, `TableGroup`, table aliases, quoted identifiers, schema-qualified table
names, column notes/settings/default values, index settings, inline refs, and
`Ref` blocks where those constructs affect profiling or relationship
validation.

Unsupported or ignored constructs must be reported explicitly in
`schema_parse_report.json` with counts, warnings, diagnostics, and source
locations where practical. Malformed DBML should fail with a clear parser error
instead of succeeding silently.

## Affected Users

- Local CLI users running company DBML files.
- Web-runner users reviewing parser diagnostics after a completed job.
- Maintainers extending schema parsing without changing relationship
  validation semantics.

## Affected Product Docs

- `README.md`
- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`
- `docs/TEST_MATRIX.md`
- `docs/decisions/0014-dbml-parser-diagnostics-boundary.md`

## Non-Goals

- No database connectors or enterprise lineage integrations.
- No JavaScript profiler port.
- No pandas full-dataframe loading.
- No raw CSV dashboard reads.
- No changes to existing deterministic artifact names or relationship checker
  execution strategy.
