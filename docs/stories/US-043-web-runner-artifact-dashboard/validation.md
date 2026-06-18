# Validation

## Proof Strategy

Prove that the dashboard is a pure artifact consumer: backend tests cover the
dashboard index and path safety; static UI tests cover the dashboard controls
and absence of profiler/raw CSV logic; local HTTP smoke covers upload-mode and
local-path-mode jobs populating dashboard artifacts.
Browser E2E additionally proves the local-path flow renders the dashboard in
Chromium and fetches protected artifact URLs rather than raw CSV files.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | chart specs remain deterministic and aggregate-only. |
| Integration | dashboard endpoint lists canonical machine artifacts and chart specs by protected artifact URLs. |
| E2E | upload and local path jobs complete, dashboard artifact index is fetchable, chart artifacts are reachable, and Playwright verifies the browser dashboard flow. |
| Platform | web server stays bound to `127.0.0.1`. |
| Performance | filters update client-side without rerunning profiler. |
| Logs/Audit | no raw CSV paths are fetched by dashboard JS; runtime artifacts remain source of progress. |

## Fixtures

- `data/demo_small/schema.dbml`
- `data/demo_small/csv`
- `data/demo_small/rules.yaml`
- target `order_reviews.review_score`

## Commands

```text
.venv/bin/pytest -q tests/test_chart_specs.py tests/test_web_runner.py tests/test_web_ui_static.py tests/test_demo_small.py
.venv/bin/pytest -q
.venv/bin/ruff check src tests scripts/verify_openai_smoke.py
node --check web/app.js
npm run test:e2e:dashboard
make demo-small
PATH="/Users/jin/repository-harness/.venv/bin:$PATH" vsf-profiler web --port 8765
scripts/bin/harness-cli story verify US-043
scripts/bin/harness-cli audit
```

## Acceptance Evidence

- `.venv/bin/pytest -q tests/test_chart_specs.py tests/test_web_runner.py tests/test_web_ui_static.py tests/test_demo_small.py` -> 16 passed.
- `.venv/bin/pytest -q` -> 43 passed.
- `.venv/bin/ruff check src tests scripts/verify_openai_smoke.py` -> all checks passed.
- `node --check web/app.js && node --check playwright.config.js && node --check tests/e2e/web-dashboard.spec.js` -> passed.
- `npm run test:e2e:dashboard` -> 1 passed in Chromium. The browser test used local path mode, waited for `Run complete`, verified dashboard panels and artifact links, exercised severity filtering/drilldown, and confirmed the dashboard made no non-sample raw CSV artifact requests.
- `make demo-small` -> passed with 15 issues and canonical artifacts.
- `vsf-profiler web --port 8765` bound to `127.0.0.1`; `/api/health` returned `{"status":"ok","host":"127.0.0.1"}`.
- Upload-mode HTTP smoke succeeded with demo DBML/CSV/rules, dashboard `missing_artifacts=[]`, 7 chart artifacts, report link `report.html`, and reachable chart specs for severity, type, missingness, FK health, and influence.
- Local-path-mode HTTP smoke succeeded with `dbml_path=data/demo_small/schema.dbml`, `csv_dir=data/demo_small/csv`, `rules_path=data/demo_small/rules.yaml`, and `target=order_reviews.review_score`; dashboard `missing_artifacts=[]`, 7 chart artifacts, and reachable sample artifact links.
- Static UI and source checks confirmed dashboard filter handlers rerender client state only, use `/api/jobs/<job_id>/dashboard` plus artifact URLs, and do not fetch raw `.csv` files.
- Browser plugin `iab` remained unavailable in this session, but Playwright Chromium was installed and used for browser verification.
- `scripts/bin/harness-cli story verify US-043` -> passed.
- `scripts/bin/harness-cli decision verify 0013` -> passed.
