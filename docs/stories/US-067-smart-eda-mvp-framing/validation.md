# Validation

## Proof Strategy

Prove that the generated default report, L4 narrative path, package index, and
web copy use Smart EDA/readiness/table-assessment language while existing
artifact contracts still pass.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | L4 guardrails, table assessments, report/package string assertions. |
| Integration | `make demo-small`, package export, artifact audit. |
| E2E | Dashboard E2E when included in full validation. |
| Platform | `node --check web/app.js`; Harness audit. |
| Performance | Existing benchmark code unchanged; not rerun unless final ladder requires it. |
| Logs/Audit | `scripts/verify_openai_smoke.py` still checks no prompt/secret/raw-row leaks. |

## Fixtures

- `data/demo_small` synthetic relational CSV plus DBML sample.
- Optional OpenAI smoke output when `.env` is configured.

## Commands

```text
.venv/bin/pytest -q tests/test_llm_narrative.py tests/test_demo_small.py tests/test_export_package.py tests/test_web_ui_static.py tests/test_table_assessments.py
node --check web/app.js
make demo-small
vsf-profiler package --input outputs/demo_small --output outputs/demo_small_package --zip --force
python scripts/verify_vsf_artifacts.py --run-dir outputs/demo_small --package-dir outputs/demo_small_package --zip-path outputs/demo_small_package.zip
.venv/bin/pytest -q
.venv/bin/ruff check src tests scripts/verify_openai_smoke.py scripts/benchmark_large_dataset.py scripts/verify_vsf_artifacts.py
scripts/bin/harness-cli audit
```

## Acceptance Evidence

- `.venv/bin/pytest -q tests/test_llm_narrative.py tests/test_demo_small.py tests/test_export_package.py tests/test_web_ui_static.py tests/test_table_assessments.py` -> 35 passed.
- `scripts/bin/harness-cli story verify US-067` -> 35 passed and story verification pass.
- `.venv/bin/pytest -q` -> 92 passed, 3 skipped.
- `.venv/bin/ruff check src tests scripts/verify_openai_smoke.py scripts/benchmark_large_dataset.py scripts/verify_vsf_artifacts.py` -> passed.
- `node --check web/app.js` -> passed.
- `PATH="$PWD/.venv/bin:$PATH" make demo-small` -> passed with 15 issues.
- `PATH="$PWD/.venv/bin:$PATH" vsf-profiler package --input outputs/demo_small --output outputs/demo_small_package --zip --force` -> package directory, manifest, index, and zip written.
- `.venv/bin/python scripts/verify_vsf_artifacts.py --run-dir outputs/demo_small --package-dir outputs/demo_small_package --zip-path outputs/demo_small_package.zip` -> passed with 0 violations.
- Generated report/package scan found the new Smart EDA, EDA readiness, Table Assessment, Analysis Impact, and Data Quality Next Step wording, with no old visible Senior Data Scientist, business-impact, Table Impact, Dataset Verdict, Probable Cause, or Suggested Fix phrases.
- Trace #71 recorded at detailed tier; `scripts/bin/harness-cli audit` -> entropy score 0/100 with no orphaned, unverified, stale, or broken records.
