# Validation

## Proof Strategy

The story is complete only when automated tests still prove deterministic and
fake-provider behavior, and a real OpenAI Olist run proves provider output is
accepted by unchanged guardrails with no fallback or leaks.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | L4 context, payload, guardrail pass/fallback behavior. |
| Integration | Fake-provider L4 smoke, OpenAI missing/bad provider fallback, Olist OpenAI run. |
| E2E | Report Markdown/HTML show OpenAI L4 narrative and passed state. |
| Platform | `make demo-full`, `python scripts/verify_openai_smoke.py`, secret scan. |
| Performance | Olist smoke completes within local demo expectations. |
| Logs/Audit | Scan generated outputs for API key, `Authorization:`, `Bearer`, `sk-`, raw CSV markers, and prompt leakage. |

## Fixtures

- `data/olist/`
- `examples/olist/schema.dbml`
- `examples/olist/rules.yaml`
- target `olist_order_reviews_dataset.review_score`
- local ignored `.env` with `OPENAI_API_KEY`

## Commands

```text
.venv/bin/pytest -q tests/test_llm_narrative.py
.venv/bin/ruff check src/vsf_profiler/llm_narrative.py tests/test_llm_narrative.py
.venv/bin/pytest -q
.venv/bin/ruff check src tests scripts/verify_openai_smoke.py
PATH="/Users/jin/repository-harness/.venv/bin:$PATH" make demo-full
PATH="/Users/jin/repository-harness/.venv/bin:$PATH" vsf-profiler run --dbml examples/olist/schema.dbml --csv-dir data/olist --rules examples/olist/rules.yaml --target olist_order_reviews_dataset.review_score --out outputs/olist_l4_openai_smoke --use-llm --llm-provider openai
.venv/bin/python scripts/verify_openai_smoke.py
scripts/bin/harness-cli audit
```

## Acceptance Evidence

- Pre-patch Olist reproduction:
  `outputs/olist_l4_openai_current/guardrail_report.json` had
  `provider=openai`, `status=fallback_used`,
  `fallback_reason=guardrail_failed`, and violations for unsupported
  `health_score`, `relationship_risk_count`, and `because` claims.
- `.venv/bin/pytest -q tests/test_llm_narrative.py` -> 20 passed.
- `.venv/bin/ruff check src/vsf_profiler/llm_narrative.py tests/test_llm_narrative.py scripts/verify_openai_smoke.py` -> passed.
- `.venv/bin/pytest -q` -> 92 passed, 3 skipped.
- `.venv/bin/ruff check src tests scripts/verify_openai_smoke.py` -> passed.
- `PATH="/Users/jin/repository-harness/.venv/bin:$PATH" make demo-full` ->
  doctor ok, artifact audit passed with 0 violations, and Playwright dashboard
  E2E passed.
- `PATH="/Users/jin/repository-harness/.venv/bin:$PATH" vsf-profiler run --dbml data/demo_small/schema.dbml --csv-dir data/demo_small/csv --rules data/demo_small/rules.yaml --target order_reviews.review_score --out outputs/demo_small_l4_openai_smoke --use-llm --llm-provider openai` -> wrote `l4_report.md`.
- `.venv/bin/python scripts/verify_openai_smoke.py` ->
  `openai_smoke_verification=passed`, `guardrail_status=passed`,
  `fallback_reason=<none>`, and `violation_count=0`.
- `PATH="/Users/jin/repository-harness/.venv/bin:$PATH" vsf-profiler run --dbml examples/olist/schema.dbml --csv-dir data/olist --rules examples/olist/rules.yaml --target olist_order_reviews_dataset.review_score --out outputs/olist_l4_openai_smoke --use-llm --llm-provider openai` -> wrote `l4_report.md` and reports for 9 tables, 52 columns, 1,550,922 rows, and 6 issues.
- `outputs/olist_l4_openai_smoke/guardrail_report.json` has
  `provider=openai`, `status=passed`, `fallback_reason=""`,
  `violation_count=0`, `violations=[]`, `raw_csv_included=false`, and
  `unbounded_samples_included=false`.
- `outputs/olist_l4_openai_smoke/report.md` and `report.html` show L4
  guardrail status `passed`, provider `openai`, and the guarded provider
  narrative preview.
- Secret marker scan across `outputs/demo_small_l4_openai_smoke` and
  `outputs/olist_l4_openai_smoke` text outputs checked 48 files and found no
  `OPENAI_API_KEY`, `Authorization:`, `Bearer`, or `sk-` markers.
