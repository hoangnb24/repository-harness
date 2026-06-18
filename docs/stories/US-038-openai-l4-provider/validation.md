# Validation

## Planned Proof

| Layer | Expected proof |
| --- | --- |
| Unit | OpenAI provider request construction and response parsing use fake transport; guardrails still reject unsupported claims. |
| Integration | Fake LLM run writes `l4_report.md` and passed `guardrail_report.json`; missing-key OpenAI run writes fallback artifacts. |
| E2E | Not applicable; no browser workflow change. |
| Platform | Default `make demo-small` remains deterministic and offline. |
| Release | Full pytest, Ruff, demo-small, fake LLM, missing-key OpenAI fallback, story verify, Harness audit, and trace pass. |

## Evidence

- `.venv/bin/pytest -q tests/test_llm_narrative.py` -> 8 passed.
- `.venv/bin/pytest -q` -> 34 passed.
- `.venv/bin/ruff check src tests` -> all checks passed.
- `PATH="/Users/jin/repository-harness/.venv/bin:$PATH" make demo-small` ->
  default deterministic run passed with 15 issues and no L4 artifacts.
- `PATH="/Users/jin/repository-harness/.venv/bin:$PATH" vsf-profiler run --dbml data/demo_small/schema.dbml --csv-dir data/demo_small/csv --rules data/demo_small/rules.yaml --target order_reviews.review_score --out outputs/demo_small_l4 --use-llm --llm-provider fake` ->
  wrote `l4_report.md`, `guardrail_report.json`, and report links.
- `outputs/demo_small_l4/guardrail_report.json` status is `passed`, provider
  is `fake`, checked numbers = 3, checked refs = 2, and violations = 0.
- `OPENAI_API_KEY= PATH="/Users/jin/repository-harness/.venv/bin:$PATH" vsf-profiler run --dbml data/demo_small/schema.dbml --csv-dir data/demo_small/csv --rules data/demo_small/rules.yaml --target order_reviews.review_score --out outputs/demo_small_l4_openai_missing --use-llm --llm-provider openai` ->
  wrote deterministic fallback `l4_report.md`, `guardrail_report.json`, and
  report links without making an API call.
- `outputs/demo_small_l4_openai_missing/guardrail_report.json` status is
  `fallback_used`, fallback reason is `provider_config_missing`, checked
  numbers = 10, checked refs = 13, and raw CSV flags are false.
- `scripts/bin/harness-cli story verify US-038` -> pass.
- `scripts/bin/harness-cli decision verify 0010` -> pass.
