# US-032 VSF Schema Evaluation and Relationship Graph

## Status

implemented

## Lane

normal

## Product Contract

VSF Data Profiler writes `schema_evaluation.json` and
`relationship_graph.json` alongside existing artifacts. The new files expose
DBML-vs-CSV conformance and validated relationship graph facts without changing
the DuckDB profiling/checking core or renaming existing outputs.

## Relevant Product Docs

- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`

## Acceptance Criteria

- `schema_evaluation.json` captures DBML tables, CSV mappings, missing/extra
  tables, missing/extra columns, primary-key and foreign-key metadata, and
  schema issue references.
- `relationship_graph.json` captures table nodes and relationship edges with FK
  status, orphan counts, parent duplicate counts, join coverage, and issue/sample
  evidence links where available.
- Existing artifacts remain compatible: `profile_summary.json`, `issues.json`,
  `influence.json`, `schema_diagram.json`, `schema_diagram.dbml`, `report.md`,
  `report.html`, runtime artifacts, and `samples/`.
- Reports link or summarize the new artifacts.
- The implementation does not add LLM, charts, verdict scoring, composite FK,
  many-to-many validation, or pandas execution logic.

## Design Notes

- Commands: `vsf-profiler run`, `make demo-small`.
- Queries: relationship facts continue to come from the existing DuckDB/SQL
  relationship checker.
- API: artifact builders live under `src/vsf_profiler`.
- Tables: no product data model changes.
- Domain rules: direct one-column FK relationships only in this slice.
- UI surfaces: static Markdown and HTML reports list the new artifacts.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Artifact builder tests for schema conformance and graph edges. |
| Integration | Demo pipeline writes both JSON files and reports link them. |
| E2E | Not applicable; no browser workflow change. |
| Platform | CLI demo still writes existing and runtime artifacts. |
| Release | Not applicable. |

## Harness Delta

No harness behavior changes are expected.

## Evidence

- Legacy tanlong ontology/schema/graph references were read from
  `/Users/jin/Auto-Data-Profiling-Smart-EDA-Report-Tool/src/ontology/models.py`,
  `src/engines/schema_engine.py`, `src/engines/graph_engine.py`, and
  `src/evaluation/schema_relationships.py`; only contract ideas were reused.
- `.venv/bin/pytest -q tests/test_schema_artifacts.py tests/test_demo_small.py tests/test_relationship_checker.py`
  -> `6 passed`.
- `.venv/bin/pytest -q` -> `19 passed`.
- `.venv/bin/ruff check src tests` -> passed.
- `PATH="/Users/jin/repository-harness/.venv/bin:$PATH" make demo-small` -> wrote
  `outputs/demo_small/report.html` and found 15 issues.
- `outputs/demo_small/` contains all existing artifacts plus
  `schema_evaluation.json` and `relationship_graph.json`.
- `schema_evaluation.json` records 7 DBML tables, 7 mapped tables, table/column
  conformance, PK/FK metadata, and schema issue references.
- `relationship_graph.json` records 7 nodes, 6 direct FK edges, FK status,
  orphan counts, parent duplicate counts, join coverage, and issue/sample
  evidence links. It also includes tanlong-inspired compatibility fields such
  as explicit FK type, cardinality/role labels, confidence, warnings, and
  non-unique parent table names without adding new relationship validation.
- `report.md` and `report.html` link `schema_evaluation.json` and
  `relationship_graph.json`.
