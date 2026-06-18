# Validation

## Proof Strategy

Combine backend integration tests, static UI assertions, CLI/server smoke, and
browser verification. The core proof is that uploaded demo files produce the
same canonical artifact names through the existing Python pipeline.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | filename sanitization, artifact path safety, and artifact listing. |
| Integration | uploaded demo DBML/CSV/rules job succeeds and writes canonical artifacts. |
| E2E | browser opens local web runner, sees upload/runner controls and progress UI. |
| Platform | `vsf-profiler web` binds `127.0.0.1` only. |
| Performance | Upload mode scoped to demo/small-medium files; no benchmark claim. |
| Logs/Audit | Runtime display uses `run_events.jsonl`/`run_summary.json`. |

## Fixtures

- synthetic demo from `create_small_demo()`
- local ignored `outputs/web_runs/`

## Commands

```text
.venv/bin/pytest -q tests/test_web_runner.py tests/test_web_ui_static.py
.venv/bin/ruff check src tests scripts/verify_openai_smoke.py
PATH="/Users/jin/repository-harness/.venv/bin:$PATH" vsf-profiler web --port 8765
```

## Acceptance Evidence

- `.venv/bin/pytest -q tests/test_web_runner.py tests/test_web_ui_static.py`
  -> 5 passed.
- `node --check web/app.js` -> passed.
- `.venv/bin/ruff check src tests scripts/verify_openai_smoke.py` -> passed.
- `.venv/bin/pytest -q` -> 37 passed.
- `vsf-profiler web --help` documents `--port` and states the server always
  binds `127.0.0.1`.
- `PATH="/Users/jin/repository-harness/.venv/bin:$PATH" vsf-profiler web --port 8765`
  started the local backend at `http://127.0.0.1:8765`.
- `curl http://127.0.0.1:8765/api/health` returned
  `{"status": "ok", "host": "127.0.0.1"}`.
- `curl http://127.0.0.1:8765/` served the runner UI with `runnerForm`,
  `Run Python profiler`, `run_events.jsonl`, and `run_summary.json` markers.
- HTTP multipart upload of `data/demo_small/schema.dbml`, all demo CSV files,
  `data/demo_small/rules.yaml`, and target `order_reviews.review_score`
  created job `run_20260615_135631_7fbcea3d`.
- The HTTP-uploaded job finished with `status=succeeded`, no job error, 8
  runtime stages, 20 artifact links, and no missing required artifacts among
  `profile_summary.json`, `issues.json`, `schema_evaluation.json`,
  `relationship_graph.json`, `dataset_verdict.json`, `run_events.jsonl`,
  `run_summary.json`, and `report.html`.
- Browser plugin setup was attempted, but the in-app `iab` browser instance was
  unavailable in this session. HTTP and API smoke checks were used as fallback
  verification.
