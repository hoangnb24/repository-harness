# US-068 Generic Numeric Outlier Detection

## Status

implemented

## Lane

normal

## Product Contract

VSF Data Profiler detects numeric outliers generically during CSV plus DBML
Smart EDA profiling. Numeric column profiles include percentiles and IQR fence
evidence. Columns with values outside the IQR fence emit `NUMERIC_OUTLIER`
P3 review findings with bounded sample CSV evidence. Reports, package index,
PDF source Markdown, local dashboard, and chart specs expose the aggregate
outlier signal without domain-specific wording.

## Relevant Product Docs

- `README.md`
- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`
- `docs/demo/vsf-data-profiler.md`

## Acceptance Criteria

- Numeric profiles include `p25`, `p50`, `p75`, `p95`, `p99`, and an `outliers`
  object with method, q1, q3, IQR, fences, count, and rate.
- Outlier detection uses DuckDB SQL against CSV relations and does not add
  pandas full-file materialization or heavy plotting/statistics dependencies.
- `issues.json` emits `NUMERIC_OUTLIER` P3 findings only from profiled numeric
  IQR evidence and writes bounded sample rows.
- `charts/outliers_top_columns.json` is deterministic aggregate chart-spec
  evidence sourced from `profile_summary.json`.
- `report.md`, `report.html`, package `index.html`, optional package PDF source,
  and the web dashboard show numeric outlier summaries.
- The feature remains generic for data scientists: no business/domain-specific
  rules, labels, or actions are introduced.

## Design Notes

- Commands: existing `vsf-profiler run`, `vsf-profiler package`, and demo
  commands.
- Queries: DuckDB `quantile_cont`, IQR fence counts, and bounded sample queries.
- API: additive fields in `ColumnProfile`; additive chart key and run-summary
  artifact key.
- Tables: no persistent database tables.
- Domain rules: default numeric IQR review rule; optional z-score is deferred.
- UI surfaces: generated reports, package index, and local dashboard panel.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 1 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest -q tests/test_quality_rules.py tests/test_chart_specs.py tests/test_demo_small.py` |
| Integration | Full pytest plus artifact audit/package verification. |
| E2E | Dashboard E2E proves chart artifact visibility. |
| Platform | `ruff`, `node --check`, `make demo-full`, Olist output spot check, and Harness trace/decision verification. |
| Release | Not a release story. |

## Harness Delta

No Harness feature changes. Matrix, story, decision, and trace records are
updated for this product slice.

## Evidence

- Focused suite: `PATH="$PWD/.venv/bin:$PATH" pytest -q tests/test_quality_rules.py tests/test_chart_specs.py tests/test_demo_small.py` -> 7 passed.
- Full pytest: `PATH="$PWD/.venv/bin:$PATH" pytest -q` -> 93 passed, 3 skipped.
- Ruff: `PATH="$PWD/.venv/bin:$PATH" ruff check src tests scripts/verify_openai_smoke.py` -> passed.
- Node syntax: `node --check web/app.js && node --check playwright.config.js` -> passed.
- Dashboard E2E: `VSF_E2E_PORT=8766 npm run test:e2e:dashboard` -> 1 passed. Port 8765 was occupied by an existing web server from another local checkout, so the config used the env override.
- Full demo: `PATH="$PWD/.venv/bin:$PATH" VSF_E2E_PORT=8766 make demo-full` -> passed; artifact audit status passed with 0 violations; package index, package chart, report Markdown source for the PDF, and PDF file were produced.
- Olist: `PATH="$PWD/.venv/bin:$PATH" make demo-olist` -> passed with 22 issues; verification found 16 `NUMERIC_OUTLIER` findings, profile percentiles, `charts/outliers_top_columns.json`, and outlier sections in `report.md` and `report.html`.
- Materialization guard spot check: `rg -n "pd\\.read_csv|pandas\\.read_csv|fetchdf\\(" src tests scripts` found no production `read_csv` use and only the existing bounded `duckdb_utils.fetch_bounded_df()` plus guard tests.
- Harness: `scripts/bin/harness-cli story verify US-068` and `scripts/bin/harness-cli decision verify 0027` -> passed.
