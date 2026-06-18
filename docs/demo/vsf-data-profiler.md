# VSF Data Profiler Demo

This is the concise Smart EDA demo path. It uses the existing synthetic
relational CSV plus DBML dataset and does not require internet access.

## 5-10 Minute Demo Script

1. Setup and orient: VSF Data Profiler is a local Smart EDA CLI for profiling
   a CSV folder against a DBML/schema contract. It uses DuckDB internally for
   large-file-friendly scans and writes static Markdown/HTML plus
   machine-readable artifacts.
2. Run the core demo:
   `PATH="/Users/jin/repository-harness/.venv/bin:$PATH" make demo-small`
3. Open `outputs/demo_small/report.html`. Point out schema mapping,
   relationship checks, issue counts, visual summaries, EDA readiness, and
   execution flow.
4. Show the artifact directory:
   `find outputs/demo_small -maxdepth 2 -type f | sort`
5. Optionally run the fake LLM path to show deterministic guardrails without an API call.
6. Open `outputs/demo_small_l4/report.html`, then show `l4_report.md` and
   `guardrail_report.json`.
7. Run the OpenAI smoke path only when `.env` has `OPENAI_API_KEY`; it is
   optional provider validation, not the default demo.
8. Optionally start the local web runner and show that completed upload/path
   jobs populate the interactive dashboard from generated artifact URLs.
9. Close with the boundary: core CSV plus DBML Smart EDA works locally without
   internet; L4, database connectors, package/PDF export, benchmarks, and the
   web dashboard are optional advanced surfaces.

## Command Checklist

Default deterministic demo:

```bash
PATH="/Users/jin/repository-harness/.venv/bin:$PATH" make demo-small
open outputs/demo_small/report.html
```

Advanced validation demo:

```bash
PATH="/Users/jin/repository-harness/.venv/bin:$PATH" vsf-profiler doctor
PATH="/Users/jin/repository-harness/.venv/bin:$PATH" make demo-full
open outputs/demo_small_package/index.html
```

Fake LLM demo:

```bash
PATH="/Users/jin/repository-harness/.venv/bin:$PATH" vsf-profiler run \
  --dbml data/demo_small/schema.dbml \
  --csv-dir data/demo_small/csv \
  --rules data/demo_small/rules.yaml \
  --target order_reviews.review_score \
  --out outputs/demo_small_l4 \
  --use-llm \
  --llm-provider fake
open outputs/demo_small_l4/report.html
```

OpenAI smoke demo:

```bash
cp .env.example .env
# edit .env and set OPENAI_API_KEY; do not commit .env
PATH="/Users/jin/repository-harness/.venv/bin:$PATH" vsf-profiler run \
  --dbml data/demo_small/schema.dbml \
  --csv-dir data/demo_small/csv \
  --rules data/demo_small/rules.yaml \
  --target order_reviews.review_score \
  --out outputs/demo_small_l4_openai_smoke \
  --use-llm \
  --llm-provider openai
.venv/bin/python scripts/verify_openai_smoke.py
open outputs/demo_small_l4_openai_smoke/report.html
```

## Artifact Tour

| Artifact | Demo talking point |
| --- | --- |
| `profile_summary.json` | Table and column profiling from CSV scans, including row counts, nulls, distinct values, numeric percentiles, IQR outlier evidence, and type-oriented summaries. |
| `issues.json` | Normalized quality findings with severity, table/column refs, counts, evidence SQL, sample paths, evidence notes, and data-quality next steps, including generic `NUMERIC_OUTLIER` findings when numeric values exceed profiled IQR fences. |
| `connector_metadata.json` | Optional for connector runs. Records source type, tables scanned, row estimates, extraction status, warnings, and redaction status. |
| `schema_parse_report.json` | DBML parsed object counts, warnings, unsupported constructs, and parser diagnostics. |
| `schema_evaluation.json` | DBML-vs-CSV conformance summary, including mapping method/confidence/candidates, missing/ambiguous/extra table or column evidence, and schema issue references. |
| `relationship_graph.json` | Graph of tables and DBML relationships with observed FK health, cardinality, junction-table detection, and relationship issue links. |
| `dataset_verdict.json` | Compatibility artifact for deterministic EDA/data-quality readiness, risk score, top blockers, affected tables, and data-quality next steps. |
| `table_assessments.json` | One deterministic assessment per profiled table with role, health score, readiness, relationship risks, name-token analysis impact, evidence refs, and data-quality next steps. |
| `charts/*.json` | Deterministic chart specs for issue counts, missingness, numeric outliers, relationship FK health, risk, and influence top features. |
| `l4_report.md` | Optional Data Scientist EDA narrative generated only when `--use-llm` runs; may be provider output or deterministic fallback. |
| `guardrail_report.json` | Audit record for L4 validation: status, provider, fallback reason, checked numbers, checked refs, violations, and raw-data flags. |

The static `report.html` renders a deterministic Visual Summary from these
chart specs. The local web runner adds the interactive dashboard: filters,
chart-item drilldown, issue rows, and artifact/sample links all come from the
same generated artifacts and protected web-runner URLs.

## Demo Caveats

- The default run is fully deterministic and should not write `l4_report.md` or
  `guardrail_report.json`.
- `--llm-provider fake` is for local validation and should produce a passed
  guardrail report without calling a real API.
- `--llm-provider openai` is opt-in and uses local `.env` configuration. Do not
  commit `.env` or print API keys.
- OpenAI provider validation should pass the guardrails; `fallback_used`
  remains the safe behavior if a provider ever returns unsupported numbers or
  references.
- L4 prompts use structured artifacts only. Raw CSV rows and unbounded samples
  are not sent through the narrative path.

## v0.2 Local RC Summary

Core demo readiness is `make demo-small` plus the generated Smart EDA report.
Release-candidate validation additionally runs doctor, package/PDF export,
artifact audit, benchmark smoke, optional Postgres/MySQL smokes, fake LLM
validation, OpenAI smoke verification when configured, and local web-runner
upload/path/dashboard flows. The hosted Vercel surface remains static preflight
only; full jobs run through the local `127.0.0.1` runner.
