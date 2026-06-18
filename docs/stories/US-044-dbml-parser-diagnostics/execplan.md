# Exec Plan

## Goal

Implement broader DBML grammar support and explicit parser diagnostics for VSF
Data Profiler without changing existing deterministic artifact contracts.

## Scope

In scope:

- Parser support for practical DBML constructs: `Project`, `Enum`,
  `TableGroup`, indexes, composite primary/unique indexes, quoted identifiers,
  schema-qualified names, inline refs, `Ref` blocks, notes, settings, defaults,
  and relevant default values.
- `schema_parse_report.json`.
- Report and web-runner artifact links.
- Fixtures and tests for realistic DBML, malformed DBML, unsupported nonfatal
  constructs, composite keys, and demo compatibility.

Out of scope:

- Database connectors.
- Enterprise lineage integrations.
- JavaScript profiler port.
- pandas full-dataframe loading.
- raw CSV dashboard reads.

## Risk Classification

Risk flags:

- Public contracts.
- Existing behavior.
- Data model.
- Multi-domain.
- Weak proof.

Hard gates:

- Existing artifact names remain unchanged.
- Existing DuckDB relationship validation remains the relationship execution
  engine.
- Unsupported syntax produces explicit diagnostics instead of silent success.

## Work Phases

1. Record Harness intake, story, and decision.
2. Add parser result/report model and tests.
3. Extend DBML tokenizer/block parser while preserving existing callers.
4. Write `schema_parse_report.json` through the existing pipeline.
5. Surface diagnostics in reports and web-runner artifact listings.
6. Run focused parser/schema/demo/web tests.
7. Run full pytest, Ruff, `make demo-small`, Harness verify/audit, and trace.

## Stop Conditions

Pause for human confirmation if:

- Existing artifact names or CLI behavior would need to break.
- Relationship validation would need to move out of DuckDB.
- Parser semantics require interpreting DBML constructs as lineage or
  connector metadata.
- A browser dashboard would need to fetch raw CSV rows.
