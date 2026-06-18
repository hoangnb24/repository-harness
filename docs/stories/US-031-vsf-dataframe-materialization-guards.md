# US-031 VSF Dataframe Materialization Guards

## Status

implemented

## Lane

normal

## Product Contract

VSF Data Profiler may use pandas only for explicitly bounded analysis frames.
Production code must not load full user CSV files into pandas or call DuckDB
`.fetchdf()` without a reusable row and column guard.

## Relevant Product Docs

- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`

## Acceptance Criteria

- Repo audit covers `.fetchdf()`, pandas imports, and `read_csv` usage.
- DuckDB-to-pandas materialization goes through a reusable
  `fetch_bounded_df(...)` helper with explicit row and column limits.
- Influence analysis enforces `max_analysis_rows` and max feature columns for
  generic and Olist paths.
- Tests fail if production code calls `.fetchdf()` outside the guard helper or
  calls `pandas.read_csv` / `pd.read_csv`.
- A synthetic large-ish CSV fixture proves influence analysis uses bounded
  DuckDB materialization rather than full pandas CSV loading.
- Existing output artifact names and runtime artifacts remain unchanged.

## Design Notes

- Commands: `vsf-profiler run`, `make demo-small`.
- Queries: DuckDB remains the scan layer; pandas receives bounded result
  frames only.
- API: `src/vsf_profiler/duckdb_utils.py` owns the materialization guard.
- Tables: no product data model changes.
- Domain rules: influence analysis remains association-only.
- UI surfaces: no report layout change expected.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Guard helper and static materialization tests. |
| Integration | Large-ish fixture influence test and demo run. |
| E2E | Not applicable; no browser workflow change. |
| Platform | CLI demo still writes existing and runtime artifacts. |
| Release | Not applicable. |

## Harness Delta

No harness behavior changes are expected.

## Evidence

- `rg -n "fetchdf\\(|pandas\\.read_csv|pd\\.read_csv|import pandas|from pandas" src tests`
  showed the only production `.fetchdf()` call is inside
  `src/vsf_profiler/duckdb_utils.py`, and pandas imports are limited to
  `duckdb_utils.py` and `influence_analyzer.py`.
- A wider repo audit excluding `.venv`, `data/`, and `outputs/` found no other
  production usage; remaining matches are tests, docs, or `manual_add/`
  reference text.
- `.venv/bin/pytest -q tests/test_memory_guards.py tests/test_demo_small.py` ->
  `7 passed`.
- `.venv/bin/pytest -q` -> `17 passed`.
- `.venv/bin/ruff check src tests` -> passed.
- `PATH="/Users/jin/repository-harness/.venv/bin:$PATH" make demo-small` -> wrote
  `outputs/demo_small/report.html` and found 15 issues.
- `outputs/demo_small/` still contains `profile_summary.json`, `issues.json`,
  `influence.json`, `schema_diagram.json`, `schema_diagram.dbml`, `report.md`,
  `report.html`, `samples/`, `run.log`, `run_events.jsonl`, and
  `run_summary.json`.
- `outputs/demo_small/influence.json` includes bounded-frame notes for max
  analysis rows and max feature columns.
