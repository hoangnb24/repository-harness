# Validation

## Proof Strategy

This story is validation-only. The proof is an actual OpenAI run plus local
artifact checks that confirm guarded fallback behavior, privacy constraints,
and deterministic artifact stability.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Existing L4 unit tests are inherited from US-038; no new unit behavior. |
| Integration | Default demo run and real OpenAI L4 run on the existing demo dataset. |
| E2E | Not applicable; no browser workflow. |
| Platform | Local CLI uses `.env` without printing or committing the key. |
| Performance | Smoke-only; no benchmark claim. |
| Logs/Audit | Scan logs/events/reports/L4/guardrail artifacts for key, auth header, secret markers, and exact raw CSV rows. |

## Fixtures

- `data/demo_small/schema.dbml`
- `data/demo_small/csv/`
- `data/demo_small/rules.yaml`
- target `order_reviews.review_score`
- local ignored `.env` with `OPENAI_API_KEY`

## Commands

```text
PATH="/Users/jin/repository-harness/.venv/bin:$PATH" make demo-small
PATH="/Users/jin/repository-harness/.venv/bin:$PATH" vsf-profiler run --dbml data/demo_small/schema.dbml --csv-dir data/demo_small/csv --rules data/demo_small/rules.yaml --target order_reviews.review_score --out outputs/demo_small_l4_openai_smoke --use-llm --llm-provider openai
.venv/bin/python scripts/verify_openai_smoke.py
```

## Acceptance Evidence

- `PATH="/Users/jin/repository-harness/.venv/bin:$PATH" make demo-small` ->
  baseline demo passed with 15 issues.
- Baseline `outputs/demo_small` had all required deterministic artifacts, 15
  sample CSV files, 7 chart specs, and no `l4_report.md` or
  `guardrail_report.json`.
- `outputs/demo_small_deterministic_manifest_before_openai.json` captured
  baseline deterministic core artifact hashes before the OpenAI run.
- `PATH="/Users/jin/repository-harness/.venv/bin:$PATH" vsf-profiler run --dbml data/demo_small/schema.dbml --csv-dir data/demo_small/csv --rules data/demo_small/rules.yaml --target order_reviews.review_score --out outputs/demo_small_l4_openai_smoke --use-llm --llm-provider openai` ->
  completed with 15 issues and wrote `l4_report.md`.
- `outputs/demo_small_l4_openai_smoke/guardrail_report.json` has
  `provider=openai`, `status=fallback_used`,
  `fallback_reason=guardrail_failed`, checked numbers = 10, checked refs = 13,
  violations = 5, `raw_csv_included=false`, and
  `unbounded_samples_included=false`.
- `outputs/demo_small_l4_openai_smoke/l4_report.md` contains the deterministic
  fallback narrative, showing the guardrail rejected provider output rather
  than accepting unsupported claims.
- `outputs/demo_small_l4_openai_smoke/report.md` and `report.html` link to
  `l4_report.md` and `guardrail_report.json`.
- `outputs/demo_small_l4_openai_smoke/run_events.jsonl` records
  `provider=openai`, `guardrail_status=fallback_used`, and the L4 artifact
  paths.
- `.venv/bin/python scripts/verify_openai_smoke.py` -> passed with
  `openai_smoke_verification=passed`, `guardrail_status=fallback_used`, and
  `fallback_reason=guardrail_failed`.
- The verifier found no API key, `OPENAI_API_KEY`, authorization header,
  `Bearer`, `sk-`, exact raw CSV row, or prompt context marker leak in the
  checked runtime/report/L4/guardrail surfaces.
- The verifier found no baseline deterministic artifact hash changes after the
  OpenAI run and no deterministic core artifact differences in the OpenAI
  output directory.
