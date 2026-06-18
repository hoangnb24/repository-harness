# Validation

## Proof Strategy

The primary proof is a local path-mode job against `data/demo_small` that writes
the same canonical artifacts as upload mode through the existing pipeline, plus
tests that invalid paths fail before job execution and artifact path traversal
is rejected.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | target shape validation, file extension/type checks, artifact path safety. |
| Integration | path job succeeds with demo DBML/CSV/rules and writes canonical artifacts without copying CSV bytes. |
| E2E | local HTTP path-mode job streams runtime events and exposes artifact links. |
| Platform | `vsf-profiler web` continues to bind `127.0.0.1` only. |
| Performance | path mode avoids browser CSV upload/copy; no new large-data benchmark claim. |
| Logs/Audit | runtime display remains sourced from `run_events.jsonl` and `run_summary.json`. |

## Fixtures

- `data/demo_small/schema.dbml`
- `data/demo_small/csv`
- `data/demo_small/rules.yaml`
- target `order_reviews.review_score`

## Commands

```text
.venv/bin/pytest -q tests/test_web_runner.py tests/test_web_ui_static.py
.venv/bin/pytest -q
.venv/bin/ruff check src tests scripts/verify_openai_smoke.py
node --check web/app.js
PATH="/Users/jin/repository-harness/.venv/bin:$PATH" vsf-profiler web --port 8765
scripts/bin/harness-cli story verify US-042
scripts/bin/harness-cli audit
```

## Acceptance Evidence

- `.venv/bin/pytest -q tests/test_web_runner.py tests/test_web_ui_static.py`
  -> 9 passed.
- `.venv/bin/pytest -q` -> 41 passed.
- `.venv/bin/ruff check src tests scripts/verify_openai_smoke.py` -> passed.
- `node --check web/app.js` -> passed.
- `make demo-small` -> passed, wrote `outputs/demo_small/report.html`, and
  reported 15 issues.
- `PATH="/Users/jin/repository-harness/.venv/bin:$PATH" vsf-profiler web --port 8765`
  started the local backend at `http://127.0.0.1:8765`.
- `GET /api/health` returned `{"status": "ok", "host": "127.0.0.1"}`.
- Static UI smoke found `Upload mode`, `Local path mode`, `pathRunnerForm`,
  `run_events.jsonl`, and `run_summary.json`.
- `POST /api/path-jobs` with:
  - `dbml_path=data/demo_small/schema.dbml`
  - `csv_dir=data/demo_small/csv`
  - `rules_path=data/demo_small/rules.yaml`
  - `target=order_reviews.review_score`
  created job `run_20260615_170341_e2d7e8ea`, finished with
  `status=succeeded`, `input_mode=path`, 8 expected runtime stages, 20 artifact
  links, and no missing required artifacts.
- Runtime event validation found all expected stages in `run_events.jsonl`:
  `parse_dbml_schema`, `catalog_csv_files`, `profile_csv_tables`,
  `data_quality_checks`, `relationship_checks`, `influence_analysis`,
  `write_machine_artifacts`, and `render_reports`.
- SSE smoke against `/api/jobs/<job_id>/events` returned 17 matching stage-event
  lines before the local `curl` probe was terminated.
- Multipart upload-mode smoke created job `run_20260615_170507_6b8fe773`,
  finished with `status=succeeded`, `input_mode=upload`, 20 artifact links, and
  no missing required artifacts.
- Invalid path-mode submission returned HTTP 400 with
  `DBML path does not exist: data/demo_small/missing.dbml`.
- Encoded artifact traversal attempt
  `/api/jobs/<job_id>/artifacts/..%2Finput%2Fpath_inputs.json` returned HTTP
  400.
- `scripts/bin/harness-cli story verify US-042` -> pass.
- `scripts/bin/harness-cli decision verify 0012` -> pass.
- Browser plugin setup was attempted, but the in-app `iab` browser instance was
  unavailable in this session. HTTP/API smoke checks were used as fallback
  verification.
