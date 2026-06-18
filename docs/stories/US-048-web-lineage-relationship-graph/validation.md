# Validation

## Proof Strategy

Prove the graph view through static markers, focused backend/UI tests, a real
local web-runner dashboard E2E path job, and full existing regression checks.
The E2E proof must also retain the raw-CSV request audit.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Static HTML/JS markers for graph controls, renderer functions, and no raw CSV fetch patterns. |
| Integration | Web runner dashboard endpoint still lists `lineage_graph.json` and `relationship_graph.json` artifact URLs. |
| E2E | Path-mode run renders graph nodes, switches to relationship mode, supports graph scope filtering, and node click drilldown. |
| Platform | `vsf-profiler web` remains local-only on `127.0.0.1`; Playwright uses local server only. |
| Performance | SVG renderer uses bounded artifact JSON and deterministic layout, no polling or raw data fetches. |
| Logs/Audit | Postgres smoke remains pass/skip; no secret/raw CSV fetch regressions. |

## Fixtures

- `data/demo_small/schema.dbml`
- `data/demo_small/csv`
- `data/demo_small/rules.yaml`
- `target=order_reviews.review_score`

## Commands

```text
.venv/bin/pytest -q tests/test_chart_specs.py tests/test_web_runner.py tests/test_web_ui_static.py tests/test_demo_small.py
.venv/bin/pytest -q
.venv/bin/ruff check src tests scripts/verify_openai_smoke.py
node --check web/app.js
make demo-small
npm run test:e2e:dashboard
make postgres-smoke
scripts/bin/harness-cli story verify US-048
scripts/bin/harness-cli audit
```

## Acceptance Evidence

- `.venv/bin/pytest -q tests/test_chart_specs.py tests/test_web_runner.py tests/test_web_ui_static.py tests/test_demo_small.py` -> 17 passed.
- `.venv/bin/pytest -q` -> 53 passed, 2 skipped.
- `.venv/bin/ruff check src tests scripts/verify_openai_smoke.py` -> passed.
- `node --check web/app.js` -> passed.
- `make demo-small` -> wrote `outputs/demo_small/report.html` with 15 issues.
- `make postgres-smoke` -> clean skip without `VSF_POSTGRES_TEST_URL`.
- `npm run test:e2e:dashboard` -> 1 passed; verified path-mode dashboard graph render, lineage node drilldown, relationship mode/scope, and no raw CSV artifact fetches.
- Local web API smoke on `127.0.0.1:8765`:
  - path job `run_20260616_054956_1b94fc57` succeeded with 8 started stages, 75 lineage nodes, and 6 relationship edges;
  - upload job `run_20260616_054957_e1834a84` succeeded;
  - both dashboard payloads exposed 16 generated artifact URLs, including `lineage_graph.json` and `relationship_graph.json`;
  - encoded artifact traversal attempt `..%2Finput%2Fschema.dbml` returned HTTP 400.
- `scripts/bin/harness-cli story verify US-048` -> pass.
- `scripts/bin/harness-cli decision verify 0018` -> pass.
