# US-036 VSF Optional LLM Narrative Guardrails

## Status

implemented

## Lane

normal

## Product Contract

VSF Data Profiler can optionally generate a Senior Data Scientist narrative
from existing structured artifacts only. The path is opt-in through `--use-llm`,
does not send raw CSV data or unbounded samples, validates the narrative against
deterministic evidence, writes `l4_report.md` and `guardrail_report.json` when
the path runs, and preserves existing deterministic artifacts when disabled.

## Relevant Product Docs

- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`

## Acceptance Criteria

- `--use-llm` is required before the narrative path runs.
- Missing provider configuration produces deterministic fallback behavior
  rather than failing the main profiling run.
- Tests use a fake provider and never call a real LLM API.
- LLM input is built only from structured artifacts:
  `profile_summary.json`, `issues.json`, `schema_evaluation.json`,
  `relationship_graph.json`, `dataset_verdict.json`, `charts/*.json`, and
  `influence.json`.
- Raw CSV files and unbounded sample rows are never loaded into or sent through
  the narrative path.
- Guardrails verify numeric claims, table/column/issue references, and
  unsupported causal wording.
- Guardrail failure writes `guardrail_report.json` with `failed` status or uses
  deterministic fallback narrative with `fallback_used` status.
- `report.md` and `report.html` link to `l4_report.md` when the artifact exists.

## Design Notes

- Commands: add `--use-llm`; support fake provider through test/local config.
- Queries: no new raw-data SQL for narrative generation.
- API: add an internal provider adapter interface; no real network provider in
  this story.
- Tables: no product database schema changes.
- Domain rules: deterministic artifacts own all facts; narrative is presenter
  text and may not invent numbers, references, or causal claims.
- UI surfaces: deterministic reports expose links to optional L4 artifacts only
  when present.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Guardrail tests cover allowed/disallowed numeric claims, refs, and causal wording. |
| Integration | Fake-provider pipeline writes `l4_report.md` and `guardrail_report.json`; disabled pipeline does not run LLM path. |
| E2E | Not applicable; no browser workflow change. |
| Platform | `make demo-small` still passes without enabling LLM and preserves deterministic artifacts. |
| Release | Full pytest, Ruff, demo-small, story verify, and harness audit pass before close. |

## Harness Delta

No harness behavior changes are expected. The inactive `llm-provider`
capability is recorded as an intentional degraded path.

## Evidence

- `.venv/bin/pytest -q tests/test_llm_narrative.py` -> 5 passed.
- `scripts/bin/harness-cli story verify US-036` -> 8 passed and story verification passed.
- `.venv/bin/pytest -q` -> 31 passed.
- `.venv/bin/ruff check src tests` -> all checks passed.
- `PATH="/Users/jin/repository-harness/.venv/bin:$PATH" make demo-small` -> default deterministic run wrote existing artifacts and 15 issues without `l4_report.md` or `guardrail_report.json`.
- `PATH="/Users/jin/repository-harness/.venv/bin:$PATH" vsf-profiler run --dbml data/demo_small/schema.dbml --csv-dir data/demo_small/csv --rules data/demo_small/rules.yaml --target order_reviews.review_score --out outputs/demo_small_l4 --use-llm --llm-provider fake` -> wrote `l4_report.md`, `guardrail_report.json`, and reports linking both.
- `outputs/demo_small_l4/guardrail_report.json` status is `passed`, provider is `fake`, `raw_csv_included` is `false`, `unbounded_samples_included` is `false`, and checked numbers/refs are recorded with no violations.
