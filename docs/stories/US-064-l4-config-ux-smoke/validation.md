# Validation

## Planned Proof

| Layer | Proof |
| --- | --- |
| Unit | OpenAI provider rejects invalid model/base URL/timeout/token/API-key config without API calls. |
| Integration | Configured fake provider writes `l4_report.md` and passed `guardrail_report.json` from provider output. |
| UI Static | Web UI includes L4 generated-result preview, dashboard panel, drilldown, and optional artifact links. |
| Regression | Default deterministic run still omits L4 artifacts unless `--use-llm` is enabled. |

## Evidence

- `node --check web/app.js` -> passed.
- `.venv/bin/pytest -q tests/test_llm_narrative.py tests/test_web_ui_static.py tests/test_web_runner.py tests/test_demo_small.py` -> 35 passed.
- `npm run test:e2e:dashboard` -> 1 passed.
- `.venv/bin/pytest -q` -> 90 passed, 3 skipped.
- `.venv/bin/ruff check src tests scripts/verify_openai_smoke.py scripts/verify_vsf_artifacts.py scripts/benchmark_large_dataset.py` -> passed.
- `PATH="$PWD/.venv/bin:$PATH" make demo-full` -> passed; artifact audit passed with 0 violations and bundled Playwright dashboard E2E passed.
- `scripts/bin/harness-cli story verify US-064` -> passed.
