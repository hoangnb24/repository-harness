# US-035 VSF Extended Relationship Validation

## Status

implemented

## Lane

normal

## Product Contract

VSF Data Profiler supports richer DBML relationship declarations and validates
them through DuckDB SQL without changing existing artifact names. Relationship
artifacts expose clear cardinality and status for one-to-one, one-to-many,
many-to-one, composite foreign keys, invalid parent duplicates, and inferred
many-to-many junction tables.

## Relevant Product Docs

- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`

## Acceptance Criteria

- DBML parsing supports `Ref:` direction variants `>`, `<`, and `-`.
- Composite foreign keys are represented in the relationship model when DBML
  declares composite endpoints.
- Relationship validation stays DuckDB/SQL based and covers parent duplicates,
  orphan keys, null FK components, join coverage, and one-to-one child
  duplicate checks.
- Many-to-many junction-table patterns are detected and exposed in schema and
  graph artifacts.
- `schema_evaluation.json` and `relationship_graph.json` include the richer
  relationship fields while preserving existing artifact names.
- Reports summarize relationship cardinality and relationship status.
- Existing artifacts remain compatible.
- The implementation does not add LLM, pandas/ydata/PyOD, automatic repair,
  or new chart types.

## Design Notes

- Commands: `vsf-profiler run`, `make demo-small`.
- Queries: relationship validation continues to use DuckDB aggregate, grouped
  duplicate, and anti-join SQL.
- API: preserve singular `child_column`/`parent_column` fields for compatibility
  while adding `child_columns`/`parent_columns` for composite relationships.
- Tables: no product database schema changes.
- Domain rules: graph source/target remain child-to-parent for compatibility;
  DBML operator and declared cardinality make original declaration semantics
  explicit.
- UI surfaces: reports summarize graph cardinality/status.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Parser and relationship fixtures cover 1:1, 1:N, N:1, invalid parent duplicate, composite FK, and junction detection. |
| Integration | Demo pipeline still writes existing artifacts, schema evaluation, relationship graph, chart specs, verdict, and reports. |
| E2E | Not applicable; no browser workflow change. |
| Platform | CLI demo still passes with existing artifact names. |
| Release | Full pytest, Ruff, demo-small, and story verify pass before close. |

## Harness Delta

No harness behavior changes are expected.

## Evidence

- `.venv/bin/pytest -q tests/test_dbml_parser.py tests/test_relationship_checker.py tests/test_schema_artifacts.py tests/test_demo_small.py` -> 10 passed.
- `.venv/bin/pytest -q` -> 26 passed.
- `.venv/bin/ruff check src tests` -> all checks passed.
- `PATH="/Users/jin/repository-harness/.venv/bin:$PATH" make demo-small` -> wrote existing demo artifacts and reported 15 issues.
- Generated `outputs/demo_small/relationship_graph.json` includes cardinality counts, declared/observed cardinality, source/target column arrays, statuses, and junction/many-to-many summary fields.
- Generated `outputs/demo_small/schema_evaluation.json` includes relationship cardinality counts, composite relationship count, and junction-table count.
- Generated Markdown and HTML reports summarize relationship cardinality/status and junction-table counts.
- `scripts/bin/harness-cli story verify US-035` -> pass; 10 focused tests passed.
