# VSF Data Profiler Product Contract

## Product

VSF Data Profiler is a local-first Smart EDA tool for data scientists. The MVP
workflow profiles a folder of related CSV files against a DBML/schema contract,
applies optional data-quality rules, can run association-based influence
analysis for an optional target column, detects generic numeric outliers, and
writes deterministic reports plus machine-readable evidence artifacts.

DuckDB is an internal execution detail used for bounded local scans. Users
interact with CSV folders, schema files, optional rules, optional target
columns, and generated artifacts.

## Core MVP Contract

The core CLI accepts:

- A DBML/schema file.
- A directory of related CSV files.
- An optional YAML rules file.
- An optional target column in `table.column` format.
- An output directory.

The core CLI produces:

- `profile_summary.json`
- `issues.json`
- `influence.json`
- `schema_parse_report.json`
- `schema_evaluation.json`
- `relationship_graph.json`
- `dataset_verdict.json`
- `table_assessments.json`
- `schema_diagram.json`
- `schema_diagram.dbml`
- `run.log`
- `run_events.jsonl`
- `run_summary.json`
- JSON chart specs under `charts/`
- `report.md`
- `report.html`
- bounded issue sample CSV files under `samples/`

`dataset_verdict.json` remains the artifact name for compatibility. In user
copy it represents EDA/data-quality readiness: readiness label, risk score, top
blockers, affected tables, and data-quality next steps.

`table_assessments.json` remains the artifact name for compatibility. It
contains one deterministic row per profiled table: role, health score,
readiness, issue counts, affected columns, relationship risks, a name-token
analysis-impact category stored in the existing `business_impact` field, and
data-quality next steps.

## Optional Advanced Surfaces

These capabilities are implemented and test-covered, but they are not required
to understand or run the MVP Smart EDA workflow:

- `vsf-profiler web` local-only runner on `127.0.0.1`, including browser upload
  mode, local path mode, first-class Postgres/MySQL/MariaDB database mode,
  generated-results previews, dashboard filters, graph views, and artifact
  links.
- Static Vercel deployment for browser-side DBML/CSV preflight only. It does
  not run Python/DuckDB jobs.
- Postgres and MySQL/MariaDB connector modes for selected local database
  tables through the CLI or local web runner, writing additive
  `connector_metadata.json`, generating schema/DBML evidence from
  introspection, and removing temporary raw extracts after a run.
- `lineage_graph.json` and optional lineage graph presentation in reports,
  packages, and the local dashboard.
- `vsf-profiler package` export of an existing output directory into an offline
  package with `index.html`, `export_manifest.json`, copied generated
  artifacts, bounded sample evidence, optional zip, and optional
  `analysis_report.pdf`.
- `vsf-profiler doctor`, `make demo-full`, `scripts/verify_vsf_artifacts.py`,
  and benchmark commands used for release-candidate validation.
- Optional guarded L4 Data Scientist EDA narrative. When `--use-llm` is set,
  `l4_report.md` and `guardrail_report.json` are generated from structured
  artifacts only. Providers are `fake` for local validation and `openai` for
  opt-in API usage.
- Olist support as an optional relational CSV sample that depends on Kaggle
  credentials. Olist is not the product identity.

## Required Capabilities

- Parse a practical DBML subset: tables, columns, types, `Project`, `Enum`,
  `TableGroup`, quoted identifiers, schema-qualified names, notes, settings,
  defaults, `pk`, `not null`, `unique`, inline refs, short `Ref:` syntax,
  `Ref` blocks, composite primary keys, and composite unique indexes from
  `indexes { (...) [...] }`.
- Generate `schema_parse_report.json` with parsed object counts, parser
  diagnostics, warnings, and unsupported constructs so unsupported DBML syntax
  is explicit instead of silently ignored.
- Map CSV files to DBML table names by exact file stem first, then
  conservative schema/header inference when confidence is high and the top
  candidate is clearly better than alternatives.
- Support explicit manual table-to-CSV mapping overrides through backend run
  configuration without renaming columns, mutating data, or weakening schema
  checks.
- Detect missing, ambiguous, and extra CSV files with mapping candidate
  evidence.
- Profile CSV data with DuckDB without loading entire input files into pandas.
- Add numeric percentiles (`p25`, `p50`, `p75`, `p95`, `p99`) and default IQR
  outlier evidence to numeric column profiles using DuckDB SQL.
- Materialize DuckDB results into pandas only through bounded helpers with
  explicit row and column limits.
- Generate automatic checks from DBML constraints.
- Run optional YAML rules for range, accepted values, regex, and expressions.
- Validate foreign-key relationships with orphan, duplicate parent key, null
  FK, child duplicate checks for one-to-one relationships, composite FK joins,
  and join coverage metrics.
- Save issue evidence, bounded sample rows, evidence notes, and data-quality
  next steps.
- Emit `NUMERIC_OUTLIER` P3 review findings with bounded sample evidence when
  numeric values fall outside their profiled IQR fence.
- Generate schema evaluation artifacts with DBML-vs-CSV table/column
  conformance, mapping method/confidence/candidate evidence, PK/FK metadata,
  and schema issue references.
- Generate relationship graph artifacts with table nodes, FK edges, declared
  and observed cardinality, runtime FK metrics, statuses, junction-table
  detection, and issue/sample evidence links.
- Generate deterministic readiness, table assessment, and chart-spec artifacts
  from aggregate outputs.
- Include a top numeric outlier chart spec in `charts/outliers_top_columns.json`
  for reports, packages, and local dashboard review.
- Run association-based influence analysis for a supplied target column with
  explicit max analysis rows and max feature columns.
- Record runtime execution flow through a human-readable log, ordered JSONL
  events, and a summary with stage timings, issue counts, artifact paths, and
  skipped or failed stage details.
- Generate deterministic Markdown and HTML Smart EDA reports with executive
  scorecard, visual summaries from chart specs, table assessments, issue
  evidence, relationship/schema/optional-lineage summary, and explicit no-LLM
  or L4 guardrail state.

## Optional Capability Requirements

- Database connectors must redact connection strings, passwords, tokens, API
  keys, and auth material from runtime logs, events, summaries, reports,
  dashboard payloads, and errors.
- The local web-runner database mode may accept a raw connection URL only
  through the `127.0.0.1` backend request. Persisted input manifests, job
  payloads, generated artifacts, reports, and dashboard payloads must expose
  only redacted connection details or source type summaries.
- Real Postgres and MySQL/MariaDB smokes must skip explicitly when local test
  URLs are absent.
- The local web runner dashboard must consume generated artifacts only; it must
  not fetch raw CSV files or rerun profiler logic in JavaScript.
- The local web runner may prefill the small synthetic demo or optional Olist
  CSV sample, expose upload/path/database source modes, and opt into
  fake/OpenAI L4 report generation while keeping LLM disabled by default.
- Export packages must exclude raw source CSV files and connector temporary
  extracts. Bounded `samples/*.csv` evidence is the only CSV content allowed in
  packages.
- L4 narrative guardrails must reject unsupported numeric claims, references,
  analysis-impact claims, and causal wording. No raw CSV rows or unbounded
  samples may enter the L4 path.
- Tests must not make real LLM API calls.

## Non-Goals

- No hosted Python/DuckDB backend job runner.
- No requirement to use Postgres, MySQL/MariaDB, package export, PDF export,
  benchmark commands, web dashboard, or Olist for the core MVP workflow.
- No Spark, Kafka, realtime processing, or production database monitoring.
- No production database mutations.
- No external lineage catalog publishing or hosted metadata service.
- No automatic data repair.
- No causal-inference claims.
- No raw CSV rows or unbounded samples sent through the LLM narrative path.

## Demo Contract

`make demo-small` must run without internet and create a synthetic relational
CSV plus DBML dataset with known data defects. The resulting `issues.json` must
include:

- `DUPLICATE_PRIMARY_KEY`
- `ORPHAN_FOREIGN_KEY`
- `VALUE_OUT_OF_RANGE`
- `NEGATIVE_VALUE_NOT_ALLOWED`
- `DATE_ORDER_INVALID`
- `REQUIRED_FIELD_NULL`

Olist support is optional at runtime because it depends on Kaggle credentials,
but the CLI must provide clear download and run commands.

`make demo-full` is an advanced validation path: doctor checks, `make
demo-small`, package export with zip and PDF, final artifact audit, optional
Playwright dashboard E2E when installed, and key output path printing.

`make benchmark-small` must run a CI-safe benchmark. `make benchmark-large`
must run an optional larger local benchmark. Both write
`performance_guard_report.json`; the report is benchmark output and is not a
required artifact from every normal profiler run.
