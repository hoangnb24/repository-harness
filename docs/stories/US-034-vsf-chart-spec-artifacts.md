# US-034 VSF Chart Spec Artifacts

## Status

implemented

## Lane

normal

## Product Contract

VSF Data Profiler writes deterministic chart-spec JSON files under `charts/`
from existing aggregate machine artifacts and renders a Visual Summary section
in Markdown/HTML reports. Chart specs do not read raw CSV data, do not use
pandas, and do not add rendering dependencies such as matplotlib or seaborn.

## Relevant Product Docs

- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`

## Acceptance Criteria

- The CLI creates `charts/` in the output directory.
- Chart-spec JSON files cover issue counts by severity and type, top missingness
  by table/column, relationship FK health, dataset verdict risk summary, and
  influence top features when influence features exist.
- Chart specs are deterministic and are derived only from
  `profile_summary.json`, `issues.json`, `relationship_graph.json`,
  `dataset_verdict.json`, and `influence.json` payloads.
- Markdown and HTML reports include a Visual Summary or Charts section based on
  the chart specs.
- Existing artifact names remain compatible.
- The implementation does not add LLM behavior, matplotlib/seaborn, composite
  FK, or many-to-many validation.

## Design Notes

- Commands: `vsf-profiler run`, `make demo-small`.
- Queries: chart generation consumes already-built aggregate payloads in memory,
  matching the JSON machine artifacts.
- API: chart builder lives under `src/vsf_profiler`.
- Tables: no product data model changes.
- Domain rules: chart specs are JSON payloads with stable `artifact`, `version`,
  `chart_id`, `chart_type`, `title`, `data`, and `source_artifacts` fields.
- UI surfaces: static Markdown and HTML reports summarize chart data; HTML uses
  simple CSS bars only.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Fixed aggregate fixtures prove deterministic chart spec contents. |
| Integration | Demo pipeline writes `charts/*.json`, reports include Visual Summary, and runtime summary lists chart artifacts. |
| E2E | Not applicable; no browser workflow change. |
| Platform | CLI demo still writes existing artifacts plus chart specs. |
| Release | Full pytest, Ruff, demo-small, and story verify pass before close. |

## Harness Delta

No harness behavior changes are expected.

## Evidence

- `.venv/bin/pytest -q tests/test_chart_specs.py tests/test_demo_small.py`
  -> `5 passed`.
- `.venv/bin/pytest -q` -> `24 passed`.
- `.venv/bin/ruff check src tests` -> passed.
- `PATH="/Users/jin/repository-harness/.venv/bin:$PATH" make demo-small` -> wrote
  `outputs/demo_small/report.html` and found 15 issues.
- `outputs/demo_small/charts/` contains deterministic JSON specs for
  `dataset_verdict_risk_summary`, `influence_top_features`,
  `issue_counts_by_severity`, `issue_counts_by_type`, `missingness_by_table`,
  `missingness_top_columns`, and `relationship_fk_health`.
- Chart specs list only approved source artifacts:
  `profile_summary.json`, `issues.json`, `relationship_graph.json`,
  `dataset_verdict.json`, and `influence.json`.
- `report.md` and `report.html` include a Visual Summary section and link chart
  specs under `charts/`.
- `run_summary.json` includes chart spec artifact paths.
- `scripts/bin/harness-cli story verify US-034` -> passed.
