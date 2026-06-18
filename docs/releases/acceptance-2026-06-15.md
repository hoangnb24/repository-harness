# VSF Data Profiler Acceptance Report

Date: 2026-06-15

## Scope

This acceptance pass checks VSF Data Profiler against the current DBML
multi-CSV streaming EDA contract. The original monolithic user spec is not kept
as a live repository artifact; the authoritative baseline is the derived product
contract and architecture decision:

- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`
- `docs/decisions/0008-vsf-profiler-python-cli-stack.md`
- story proof rows in `docs/TEST_MATRIX.md`

No new product scope was added. This pass fixed only documentation sync gaps
and recorded acceptance evidence.

## Acceptance Summary

| Area | Status | Evidence |
| --- | --- | --- |
| DBML plus multi-CSV local CLI | Pass | `make demo-small` regenerated `data/demo_small` and `outputs/demo_small`; run status `success`. |
| DuckDB streaming core without full pandas CSV loads | Pass | `tests/test_memory_guards.py` checks no production `pd.read_csv` and no direct `.fetchdf()` outside `duckdb_utils.fetch_bounded_df`. |
| Deterministic artifact contract | Pass | `outputs/demo_small` contains all required deterministic JSON/report/runtime/schema/chart/sample artifacts. |
| Optional fake LLM narrative | Pass | `vsf-profiler run ... --use-llm --llm-provider fake` wrote `l4_report.md` and `guardrail_report.json`. |
| LLM guardrails | Pass | `outputs/demo_small_l4/guardrail_report.json` status is `passed`, with checked numbers, checked refs, zero violations, and raw/unbounded sample flags set to false. |
| Real OpenAI L4 smoke | Pass with guarded fallback | `vsf-profiler run ... --use-llm --llm-provider openai` contacted the configured provider, wrote `l4_report.md` and `guardrail_report.json`, and recorded `provider=openai`, `status=fallback_used`, `fallback_reason=guardrail_failed`. |
| Reports link optional L4 artifact | Pass | `outputs/demo_small_l4/report.md` and `report.html` link to `l4_report.md` and `guardrail_report.json`. |
| CLI UX | Pass | `vsf-profiler run --help` documents `--use-llm`; README documents `--llm-provider fake` and `--llm-provider openai`. |
| Docs synchronization | Pass after fixes | README and v0.1 release note no longer contradict the static web prototype by saying "No web UI." |
| Existing deterministic path with LLM disabled | Pass | `outputs/demo_small` has no `l4_report.md`, no `guardrail_report.json`, and no `llm_narrative` runtime stage. |

## Default Demo Artifact Audit

Command:

```bash
PATH="/Users/jin/repository-harness/.venv/bin:$PATH" make demo-small
```

Observed result:

- `Issues found: 15`
- `run_summary.json` status: `success`
- sample CSV count: 15
- chart specs:
  - `charts/dataset_verdict_risk_summary.json`
  - `charts/influence_top_features.json`
  - `charts/issue_counts_by_severity.json`
  - `charts/issue_counts_by_type.json`
  - `charts/missingness_by_table.json`
  - `charts/missingness_top_columns.json`
  - `charts/relationship_fk_health.json`

Required top-level deterministic artifacts are present:

- `profile_summary.json`
- `issues.json`
- `influence.json`
- `schema_evaluation.json`
- `relationship_graph.json`
- `dataset_verdict.json`
- `schema_diagram.json`
- `schema_diagram.dbml`
- `run.log`
- `run_events.jsonl`
- `run_summary.json`
- `report.md`
- `report.html`
- `charts/`
- `samples/`

Optional L4 artifacts are absent in the default path, as expected.

## Fake LLM Artifact Audit

Command:

```bash
PATH="/Users/jin/repository-harness/.venv/bin:$PATH" vsf-profiler run \
  --dbml data/demo_small/schema.dbml \
  --csv-dir data/demo_small/csv \
  --rules data/demo_small/rules.yaml \
  --target order_reviews.review_score \
  --out outputs/demo_small_l4 \
  --use-llm \
  --llm-provider fake
```

Observed result:

- `Issues found: 15`
- `Wrote L4 report: outputs/demo_small_l4/l4_report.md`
- `guardrail_report.json` status: `passed`
- checked numeric claims: 3
- checked references: 2
- violations: 0
- `raw_csv_included`: `false`
- `unbounded_samples_included`: `false`

The L4 run includes the deterministic artifact set plus:

- `l4_report.md`
- `guardrail_report.json`

The runtime stage list includes `llm_narrative` only for this opt-in run.

## Real OpenAI L4 Smoke Audit

Command:

```bash
PATH="/Users/jin/repository-harness/.venv/bin:$PATH" vsf-profiler run \
  --dbml data/demo_small/schema.dbml \
  --csv-dir data/demo_small/csv \
  --rules data/demo_small/rules.yaml \
  --target order_reviews.review_score \
  --out outputs/demo_small_l4_openai_smoke \
  --use-llm \
  --llm-provider openai
```

Observed result:

- `Issues found: 15`
- `Wrote L4 report: outputs/demo_small_l4_openai_smoke/l4_report.md`
- `guardrail_report.json` provider: `openai`
- `guardrail_report.json` status: `fallback_used`
- fallback reason: `guardrail_failed`
- checked numeric claims: 10
- checked references: 13
- violations: 5 (`numeric_claim` and `reference`)
- `raw_csv_included`: `false`
- `unbounded_samples_included`: `false`
- runtime `llm_narrative` stage duration: about 5.969 seconds

The real provider returned a candidate narrative, but guardrail validation
rejected unsupported evidence. The system therefore wrote the deterministic
fallback narrative and preserved a clear guardrail audit trail.

Repeatable local verification:

```bash
.venv/bin/python scripts/verify_openai_smoke.py
```

Observed result:

- `openai_smoke_verification=passed`
- `guardrail_status=fallback_used`
- `fallback_reason=guardrail_failed`

The verifier checks:

- `l4_report.md` and `guardrail_report.json` exist.
- Guardrail provider is `openai`.
- Guardrail status is `passed` or `fallback_used`.
- Baseline `outputs/demo_small` deterministic core artifact hashes did not
  change after the OpenAI run.
- The OpenAI output directory's deterministic core artifacts match the
  baseline hashes.
- Runtime logs/events, reports, L4 report, and guardrail report do not contain
  the actual API key, `OPENAI_API_KEY`, authorization headers, `Bearer`, `sk-`,
  or exact raw CSV data rows.
- Runtime logs/events do not contain prompt context markers such as
  `privacy_contract`, `source_artifacts`, or `top_issues`.

`run_events.jsonl` records normal runtime input metadata, including the input
CSV directory path. It does not record raw CSV rows or the LLM prompt body.

## Guardrail and Memory Evidence

The current guard surface is:

- `src/vsf_profiler/duckdb_utils.py` imports pandas and contains the only
  production `.fetchdf()` call inside `fetch_bounded_df`.
- `src/vsf_profiler/influence_analyzer.py` imports pandas only for bounded
  analysis frames.
- No production file contains `pd.read_csv` or `pandas.read_csv`.

Executable proof:

```bash
.venv/bin/pytest -q tests/test_memory_guards.py tests/test_llm_narrative.py
```

## Gaps Found And Fixed

| Gap | Resolution |
| --- | --- |
| README listed the static web UI as MVP but also said "No web UI" under non-goals. | Changed non-goal to "No hosted production web UI or backend job runner." |
| `docs/releases/v0.1.md` had the same web UI contradiction and an obsolete note about missing Harness durable trace support. | Updated known limitations to describe the static browser workspace as a prototype and removed the obsolete Harness note. |

## Backlog-Only Gaps

No acceptance-blocking gaps remain in the current product contract.

The following are intentional future scope, not acceptance gaps:

- external LLM provider integrations beyond OpenAI;
- UI polish beyond the current static web prototype;
- hosted production web runner/backend;
- complete DBML grammar compatibility beyond the pragmatic supported subset.

## Final Gate

Observed final validation:

| Command | Result |
| --- | --- |
| `.venv/bin/pytest -q` | Pass, 31 tests. |
| `.venv/bin/ruff check src tests` | Pass, all checks clean. |
| `PATH="/Users/jin/repository-harness/.venv/bin:$PATH" make demo-small` | Pass, default artifacts and 15 issues. |
| `PATH="/Users/jin/repository-harness/.venv/bin:$PATH" vsf-profiler run --dbml data/demo_small/schema.dbml --csv-dir data/demo_small/csv --rules data/demo_small/rules.yaml --target order_reviews.review_score --out outputs/demo_small_l4 --use-llm --llm-provider fake` | Pass, L4 artifacts generated. |
| `PATH="/Users/jin/repository-harness/.venv/bin:$PATH" vsf-profiler run --dbml data/demo_small/schema.dbml --csv-dir data/demo_small/csv --rules data/demo_small/rules.yaml --target order_reviews.review_score --out outputs/demo_small_l4_openai_smoke --use-llm --llm-provider openai` | Pass with guarded fallback, L4 artifacts generated. |
| `.venv/bin/python scripts/verify_openai_smoke.py` | Pass, guarded OpenAI smoke artifacts verified. |
| `scripts/bin/harness-cli story verify US-037` | Pass, 12 focused tests. |
| `scripts/bin/harness-cli audit` | Pass after Trace #16, entropy score 0/100. |
