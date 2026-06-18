# Validation

## Proof Strategy

Prove the feature by running the normal deterministic pipeline and confirming
`table_assessments.json` is generated, linked, packaged, audited, rendered in
reports/dashboard, and used safely by optional L4 narrative guardrails.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Table scoring, role inference, business-impact mapping, relationship risk extraction. |
| Integration | Demo pipeline writes one assessment per profiled table; runtime artifact paths include `table_assessments`. |
| E2E | Local web-runner dashboard shows table assessment panel and table drilldown from artifact URLs. |
| Platform | Upload/path web modes keep generated artifact URLs and local-only server behavior. |
| Performance | No pandas full-file load or JavaScript profiler logic is introduced. |
| Logs/Audit | Artifact audit, package export, L4 guardrail report, story/decision verification, and Harness audit pass. |

## Fixtures

- Synthetic demo data from `create_small_demo`.
- Fake L4 provider outputs for supported and unsupported business-impact
  claims.
- Existing dashboard Playwright fixture using local path mode.

## Commands

```text
.venv/bin/pytest -q tests/test_table_assessments.py tests/test_llm_narrative.py tests/test_demo_small.py tests/test_web_runner.py tests/test_web_ui_static.py
.venv/bin/pytest -q
.venv/bin/ruff check src tests scripts/verify_openai_smoke.py scripts/verify_vsf_artifacts.py scripts/benchmark_large_dataset.py
node --check web/app.js
npm run test:e2e:dashboard
make demo-small
make demo-full
make benchmark-small
make postgres-smoke
make mysql-smoke
scripts/bin/harness-cli story verify US-055
scripts/bin/harness-cli decision verify 0024
scripts/bin/harness-cli audit
```

## Acceptance Evidence

| Check | Result |
| --- | --- |
| Focused assessment/LLM/demo/web suite | `.venv/bin/pytest -q tests/test_table_assessments.py tests/test_llm_narrative.py tests/test_demo_small.py tests/test_web_runner.py tests/test_web_ui_static.py` -> 26 passed |
| Package/audit/lineage suite | `.venv/bin/pytest -q tests/test_export_package.py tests/test_doctor_and_artifact_audit.py tests/test_lineage_graph.py` -> 14 passed |
| Full pytest | `.venv/bin/pytest -q` -> 79 passed, 3 skipped |
| Ruff | `.venv/bin/ruff check src tests scripts/verify_openai_smoke.py scripts/verify_vsf_artifacts.py scripts/benchmark_large_dataset.py` -> passed |
| Dashboard syntax and E2E | `node --check web/app.js` -> passed; `npm run test:e2e:dashboard` -> 1 passed |
| Demo paths | `make demo-small`, `make demo-full`, and `make benchmark-small` -> passed |
| Optional database smokes | `make postgres-smoke` and `make mysql-smoke` -> skipped cleanly without fixture URLs |
| Harness | `scripts/bin/harness-cli story verify US-055` -> passed; `scripts/bin/harness-cli decision verify 0024` -> passed |

`make demo-small` now writes `outputs/demo_small/table_assessments.json` with
one assessment per profiled table. Reports, package export, artifact audit, and
the local web dashboard expose the additive artifact without renaming existing
outputs.
