# US-070 Layer 4 Smart EDA Report Pattern Integration

## Status

implemented

## Lane

normal

## Product Contract

VSF Data Profiler integrates useful Layer 4 report patterns from the external
Senior Data Scientist reference as presentation behavior only. The generated
Markdown, HTML, package, dashboard, and optional L4 narrative should provide a
richer generic Smart EDA review with executive readiness, feature or column
usability, table-by-table health, column issue blocks, relationship/schema
context, and existing chart-spec references.

The current CSV folder plus DBML/schema architecture remains the contract.
DuckDB profiling, bounded materialization, artifact filenames, and optional L4
guardrails stay intact.

## Relevant Product Docs

- `README.md`
- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`
- `docs/stories/US-067-smart-eda-mvp-framing/`
- `docs/stories/US-068-generic-numeric-outlier-detection.md`
- `docs/stories/US-069-schema-aware-csv-auto-mapping.md`

## Acceptance Criteria

- Deterministic `report.md` and `report.html` include a feature or column
  usability summary derived from existing structured artifacts.
- Reports include table-by-table health reviews with role, readiness, health,
  issue counts, affected columns, relationship risks, and an advisory next
  step.
- Reports include column issue blocks grouped by table and column, with
  severity, evidence, ML/analysis consequence, and advisory next step.
- Relationship, schema, influence, and chart-spec references remain sourced
  from existing artifacts only.
- Optional `l4_report.md` uses the same structured artifacts and guardrails and
  remains useful with the fake provider or deterministic fallback.
- Package and local dashboard report links continue to expose the same artifact
  names and do not require raw CSV data, PNG generation, ydata-profiling,
  FastAPI, schema inference without DBML, or full anomaly-row exports.
- Output remains generic for data scientists and does not introduce
  business/revenue/customer-churn recommendations, unsupported numbers, causal
  wording, raw CSV snippets, secrets, or unbounded samples.

## Design Notes

- Commands: existing `vsf-profiler run`, `vsf-profiler package`, demo commands,
  and local dashboard artifact rendering.
- Queries: no new database queries beyond existing DuckDB profiling artifacts.
- API: no public CLI, artifact filename, route, or JSON key renames.
- Tables: no persistent database tables or migrations.
- Domain rules: derive report sections from `profile_summary`, `issues`,
  `schema_evaluation`, `relationship_graph`, `dataset_verdict`,
  `table_assessments`, `charts`, and `influence`.
- UI surfaces: generated reports, optional L4 report, package index, and local
  dashboard links/preview.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-070 --unit 1 --integration 1 --e2e 1 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest -q tests/test_llm_narrative.py tests/test_chart_specs.py tests/test_demo_small.py tests/test_export_package.py tests/test_web_ui_static.py` |
| Integration | Full `pytest -q`, package/report assertions, and `make demo-small`. |
| E2E | Existing dashboard/static tests prove report/package/L4 artifact links remain visible. |
| Platform | Ruff for touched Python paths, `node --check web/app.js`, `git diff --check`, generated report scans. |
| Release | Not a release story. |

## Harness Delta

No Harness behavior changes are planned. The story, durable matrix evidence,
and trace record the integration and validation proof.

## Evidence

- Commit-readiness review hardening:
  fixed the L4 feature-usability summary so it counts all profiled columns
  while still bounding preview rows; replaced remaining negative-value
  "amount" wording with generic numeric wording; hardened the dashboard
  generated-results preview so column-usability cards and artifact names wrap
  cleanly in narrow panels; added dashboard E2E assertions and screenshots for
  the Column usability preview.
- Playwright visual review:
  screenshots captured under `outputs/us070_visual_review/` for report,
  package, and dashboard generated-results surfaces on desktop and mobile.
  Static report/package captures had no console errors and no page-level
  horizontal overflow at 1440px or 390px widths; dashboard generated-results
  desktop/mobile screenshots show the Column usability card without clipped
  labels after the CSS hardening.
- In-task focused suite:
  `PATH="$PWD/.venv/bin:$PATH" pytest -q tests/test_llm_narrative.py tests/test_demo_small.py tests/test_export_package.py tests/test_web_ui_static.py`
  -> 33 passed.
- Focused story suite:
  `PATH="$PWD/.venv/bin:$PATH" pytest -q tests/test_llm_narrative.py tests/test_chart_specs.py tests/test_demo_small.py tests/test_export_package.py tests/test_web_ui_static.py`
  -> 35 passed.
- Story verification: `scripts/bin/harness-cli story verify US-070` -> passed
  with the same 35-test focused suite.
- Full pytest: `PATH="$PWD/.venv/bin:$PATH" pytest -q` -> 99 passed, 3 skipped.
- Ruff:
  `PATH="$PWD/.venv/bin:$PATH" ruff check src/vsf_profiler/report_generator.py src/vsf_profiler/llm_narrative.py src/vsf_profiler/issue_catalog.py src/vsf_profiler/export_package.py tests/test_llm_narrative.py tests/test_demo_small.py tests/test_export_package.py`
  -> passed.
- Node syntax: `node --check web/app.js` -> passed.
- Whitespace: `git diff --check` -> passed.
- Demo: `PATH="$PWD/.venv/bin:$PATH" make demo-small` -> passed with
  15 issues and regenerated `outputs/demo_small/report.md` and `report.html`.
- Optional fake L4 run:
  `PATH="$PWD/.venv/bin:$PATH" vsf-profiler run --dbml data/demo_small/schema.dbml --csv-dir data/demo_small/csv --rules data/demo_small/rules.yaml --target order_reviews.review_score --out outputs/demo_small_l4 --use-llm --llm-provider fake`
  -> wrote `l4_report.md`; `guardrail_report.json` has status `passed`,
  provider `fake`, violation_count `0`, raw_csv_included `false`, and
  unbounded_samples_included `false`.
- Package export:
  `PATH="$PWD/.venv/bin:$PATH" vsf-profiler package --input outputs/demo_small --output outputs/demo_small_package --zip --force`
  -> wrote package directory, `export_manifest.json`, `index.html`, and zip.
- Artifact audit:
  `PATH="$PWD/.venv/bin:$PATH" python3 scripts/verify_vsf_artifacts.py --run-dir outputs/demo_small --package-dir outputs/demo_small_package --zip-path outputs/demo_small_package.zip`
  -> passed with 0 violations.
- Dashboard E2E: default port 8765 was occupied; rerun with
  `PATH="$PWD/.venv/bin:$PATH" VSF_E2E_PORT=8766 npm run test:e2e:dashboard`
  -> 1 passed and wrote generated-results screenshots under
  `outputs/us070_visual_review/`.
- Generated report/package scans confirmed `Feature/Column Usability Summary`,
  `Table-by-Table Health Review`, `Column Issue Blocks`,
  `ML/Analysis Consequence`, chart references, package report links, and L4
  guardrail links are present.
- Banned-wording scan over `outputs/demo_small`, `outputs/demo_small_l4`, and
  `outputs/demo_small_package` report surfaces found no
  customer-churn/revenue/profitability, business-rule/process, probable-cause,
  suggested-fix, causal, raw-row, raw-CSV, secret, or token assignment matches.
