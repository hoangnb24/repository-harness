# Validation

## Proof Strategy

Use unit tests for the MySQL connector contract and PDF package behavior, an
optional live MySQL smoke for a configured local database, and full release
commands to prove existing CSV/Postgres/web/package/benchmark behavior remains
compatible.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | MySQL table parsing, URL redaction, schema introspection mapping, DBML-supplied connector mode, PDF writer/package manifest fields. |
| Integration | `run_pipeline()` through fake MySQL connector writes canonical artifacts, `connector_metadata.json`, lineage, reports, and cleans extracts. |
| Acceptance | `tests/test_mysql_acceptance.py` runs against `VSF_MYSQL_TEST_URL` or skips explicitly. |
| Package/Audit | `vsf-profiler package --pdf` writes `analysis_report.pdf`; manifest and zip entries validate; redaction scan covers PDF bytes. |
| Regression | CSV mode is not hijacked by database env vars; Postgres tests still pass; web dashboard/artifact discovery remains artifact-only. |
| Harness | Story verify, decision verify, matrix update, and audit pass. |

## Commands

```text
.venv/bin/pytest -q tests/test_mysql_connector.py tests/test_mysql_acceptance.py tests/test_export_package.py tests/test_doctor_and_artifact_audit.py
.venv/bin/pytest -q
.venv/bin/ruff check src tests scripts/verify_openai_smoke.py scripts/verify_vsf_artifacts.py scripts/benchmark_large_dataset.py
node --check web/app.js
vsf-profiler doctor
make demo-small
make demo-full
make benchmark-small
make postgres-smoke
make mysql-smoke
scripts/bin/harness-cli story verify US-052
scripts/bin/harness-cli decision verify 0022
scripts/bin/harness-cli audit
```

## Acceptance Evidence

- `.venv/bin/pytest -q tests/test_mysql_connector.py tests/test_export_package.py tests/test_doctor_and_artifact_audit.py`
  -> 19 passed.
- `.venv/bin/pytest -q tests/test_mysql_acceptance.py` -> 1 skipped because
  `VSF_MYSQL_TEST_URL` is not configured and no MySQL tool capability is
  present.
- `.venv/bin/pytest -q` -> 76 passed, 3 skipped.
- `.venv/bin/ruff check src tests scripts/verify_openai_smoke.py scripts/verify_vsf_artifacts.py scripts/benchmark_large_dataset.py`
  -> passed.
- `node --check web/app.js` -> passed.
- `npm run test:e2e:dashboard` -> 1 passed.
- `vsf-profiler doctor` -> required checks passed; optional MySQL env skipped,
  PyMySQL package reported optional missing, and PDF backend reported ok.
- `make demo-small` -> passed with 15 issues.
- `make demo-full` -> passed; package wrote `analysis_report.pdf`, manifest,
  index, zip, artifact audit status `passed` with 0 violations, and Playwright
  dashboard E2E passed.
- `make benchmark-small` -> passed and wrote
  `outputs/benchmark_ci/run/performance_guard_report.json` with status
  `passed`.
- `make postgres-smoke` -> skipped cleanly without `VSF_POSTGRES_TEST_URL`.
- `make mysql-smoke` -> skipped cleanly without `VSF_MYSQL_TEST_URL`.
- `scripts/bin/harness-cli story verify US-052` -> passed with 19 focused
  tests.
- `scripts/bin/harness-cli decision verify 0022` -> passed.
- `scripts/bin/harness-cli audit` -> passed with entropy score 0/100.
- `scripts/bin/harness-cli score-trace --id 45` -> detailed tier met for the
  high-risk lane.
