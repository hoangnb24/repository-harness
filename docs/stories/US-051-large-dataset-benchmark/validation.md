# Validation

## Proof Strategy

Use unit tests for deterministic generation and materialization scan behavior,
an integration test for a small benchmark report, and full local commands for
release/demo compatibility.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Generator deterministic metadata and row counts; source scan catches no production `pandas.read_csv` or unguarded `.fetchdf()`. |
| Integration | CI-safe benchmark writes `performance_guard_report.json` with row counts, stage timings, peak memory, artifact sizes, influence limits, package success, and audit status. |
| E2E | `make demo-full` still passes and Playwright dashboard E2E remains intact when available. |
| Platform | Peak RSS is recorded when supported; report marks support status explicitly. |
| Performance | CI-safe benchmark passes conservative checks; optional larger local benchmark command is documented. |
| Logs/Audit | Story verify, decision verify, artifact audit, and Harness audit pass. |

## Fixtures

- Synthetic benchmark dataset generated into `tmp_path` for tests.
- `outputs/benchmark_ci` for local CI-safe benchmark command.
- Existing `data/demo_small` and `outputs/demo_small` for compatibility proof.

## Commands

```text
.venv/bin/pytest -q tests/test_large_benchmark.py tests/test_memory_guards.py tests/test_export_package.py tests/test_demo_small.py
.venv/bin/pytest -q
.venv/bin/ruff check src tests scripts/verify_openai_smoke.py scripts/verify_vsf_artifacts.py scripts/benchmark_large_dataset.py
.venv/bin/python scripts/benchmark_large_dataset.py --work-dir outputs/benchmark_ci --rows 600 --tables 7 --max-analysis-rows 120 --max-feature-columns 4 --force
vsf-profiler doctor
make demo-small
make demo-full
scripts/bin/harness-cli story verify US-051
scripts/bin/harness-cli decision verify 0021
scripts/bin/harness-cli audit
```

## Acceptance Evidence

- `.venv/bin/pytest -q tests/test_large_benchmark.py tests/test_memory_guards.py tests/test_export_package.py tests/test_demo_small.py`
  -> 16 passed.
- `.venv/bin/pytest -q` -> 68 passed, 2 skipped.
- `.venv/bin/ruff check src tests scripts/verify_openai_smoke.py scripts/verify_vsf_artifacts.py scripts/benchmark_large_dataset.py`
  -> passed.
- `node --check web/app.js` -> passed.
- `vsf-profiler doctor` -> required checks passed; optional Postgres and
  OpenAI env checks skipped without secret output; Node and Playwright detected.
- `make demo-small` -> passed with 15 issues.
- `make demo-full` -> passed; package and zip written; artifact audit passed
  with 0 violations; Playwright dashboard E2E passed.
- `make benchmark-small` -> passed and wrote
  `outputs/benchmark_ci/run/performance_guard_report.json`.
- CI-safe benchmark report evidence: status `passed`, 2,565 generated rows
  across 7 tables, 8 runtime stages, peak RSS recorded, influence capped at
  120 rows and 4 features, package success, artifact audit `passed`,
  materialization guards `passed`, and 0 violations.
- Direct artifact audit on `outputs/benchmark_ci/run`,
  `outputs/benchmark_ci/package`, and `outputs/benchmark_ci/package.zip`
  -> passed with 0 violations.
- Larger local smoke
  `.venv/bin/python scripts/benchmark_large_dataset.py --work-dir outputs/benchmark_local_smoke --rows 2000 --tables 8 --max-analysis-rows 300 --max-feature-columns 5 --force`
  -> passed with 10,550 generated rows across 8 tables, peak RSS recorded,
  influence capped at 300 rows, package success, and artifact audit `passed`.
- `scripts/bin/harness-cli story verify US-051` -> passed.
- `scripts/bin/harness-cli decision verify 0021` -> passed.
