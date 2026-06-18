# Validation

## Proof Strategy

Use unit tests for doctor/audit behavior, focused integration tests for the
package and demo artifacts, and full local release-candidate commands for final
proof.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Doctor redacts OpenAI/Postgres secrets; audit reports missing artifacts, raw CSVs, and secret-like strings. |
| Integration | Demo output plus export package passes the final artifact audit. |
| E2E | Existing Playwright dashboard E2E runs when Playwright is installed. |
| Platform | `make demo-full` clean-skips optional Playwright when absent and runs it when present. |
| Performance | Basic smoke timing only through command completion. |
| Logs/Audit | Harness story verify, decision verify, and audit pass. |

## Fixtures

- `create_small_demo()` and `run_pipeline()`.
- `outputs/demo_small`.
- `outputs/demo_small_package`.
- Synthetic secret and raw CSV files for audit failure tests.

## Commands

```text
.venv/bin/pytest -q tests/test_doctor_and_artifact_audit.py tests/test_export_package.py tests/test_demo_small.py
.venv/bin/pytest -q
.venv/bin/ruff check src tests scripts/verify_openai_smoke.py scripts/verify_vsf_artifacts.py
node --check web/app.js
npm run test:e2e:dashboard
make demo-small
make demo-full
scripts/bin/harness-cli story verify US-050
scripts/bin/harness-cli decision verify 0020
scripts/bin/harness-cli audit
```

## Acceptance Evidence

- `.venv/bin/pytest -q tests/test_doctor_and_artifact_audit.py tests/test_export_package.py tests/test_demo_small.py`
  -> 14 passed.
- `.venv/bin/pytest -q` -> 64 passed, 2 skipped.
- `.venv/bin/ruff check src tests scripts/verify_openai_smoke.py scripts/verify_vsf_artifacts.py`
  -> passed.
- `node --check web/app.js` -> passed.
- `vsf-profiler doctor` -> required Python/import/DuckDB checks passed;
  optional Postgres env and OpenAI env skipped without leaking secrets; Node
  and Playwright detected.
- `make demo-small` -> wrote `outputs/demo_small/report.html` with 15 issues.
- `make demo-full` -> doctor passed, demo-small passed, export package and zip
  were written, artifact audit passed with 22 run artifacts, 24 package
  artifacts, 76 scanned text files, 39 zip entries, and 0 violations; Playwright
  dashboard E2E passed.
- `scripts/bin/harness-cli story verify US-050` -> passed.
- `scripts/bin/harness-cli decision verify 0020` -> passed.
