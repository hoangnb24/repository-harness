# Architecture

VSF Data Profiler is a local-first data profiling system for many CSV tables
that are described by a DBML schema contract. The architecture is optimized for
large company-style datasets where loading every CSV into pandas is not
acceptable.

The core rule is: raw data is scanned through an external-memory engine, while
the application keeps only schema metadata, aggregate statistics, issue
evidence, bounded samples, runtime events, and report artifacts in memory.

## Architecture Status

This document separates **current MVP architecture** from **target architecture**.
That split is important because several desirable enterprise features are useful
roadmap items but should not become blockers for the local CLI MVP.

Current MVP scope:

- local CLI run over DBML plus CSV directory;
- DBML/CSV cataloging;
- DuckDB-based profiling and validation;
- issue catalog with bounded samples and suggested fixes;
- relationship checks from DBML foreign keys;
- bounded association analysis for an optional target column;
- deterministic Markdown/HTML reports;
- runtime visibility through console progress, logs, events, and run summary.

Target roadmap scope:

- richer graph validation;
- dataset verdict and risk scoring;
- chart specs and rendered charts;
- optional LLM narrative with guardrail validation;
- local web runner that calls the same application pipeline as the CLI.

## Goals

- Accept many CSV files plus one DBML schema contract.
- Use DBML tables, primary keys, foreign keys, and relationship declarations to
  build a dataset graph.
- Profile each table and column without full pandas loads.
- Validate schema, data quality rules, and cross-table relationships.
- Produce normalized, machine-readable findings that identify table, column,
  bad count, sample artifact, evidence SQL, severity, and suggested fix.
- Show the runtime execution flow while the profiler runs.
- Generate reproducible JSON, Markdown, HTML, and bounded sample artifacts.
- Optionally generate a Senior Data Scientist narrative from structured
  evidence only.
- Keep all raw data local unless the user explicitly opts into an external LLM.

## Non-Goals

- Do not mutate production databases or repair user data automatically.
- Do not require Spark, Kafka, or a hosted database for the local workflow.
- Do not send raw CSV rows to an LLM.
- Do not make causal-inference claims from profiling or association metrics.
- Do not use pandas/ydata/PyOD full-data pipelines for large input files.
- Do not build production database monitoring, backup validation, lock analysis,
  security audit, or enterprise lineage in the MVP.

## Product Surfaces

| Surface | Purpose | Status |
| --- | --- | --- |
| CLI | Run the full profiler and write artifacts to an output directory. | MVP. |
| Static reports | Let users inspect findings without running an app server. | MVP. |
| Runtime trace files | Make each run debuggable through log, JSONL events, and summary metadata. | MVP / near-term hardening. |
| Static web workspace | Upload DBML/CSV headers locally, map files to tables, and visualize DBML without running jobs. | Prototype, not required for MVP correctness. |
| Future local web runner | Start profiler jobs from the web UI through a local backend. | Roadmap. |
| Optional LLM report | Produce a narrative from evidence JSON after deterministic checks finish. | Roadmap. |

## High-Level Flow

### MVP run flow

```text
DBML + CSV directory + optional YAML rules + optional target column
  -> input boundary validation
  -> runtime context and run id creation
  -> DBML catalog and relationship graph
  -> CSV catalog and table mapping
  -> DuckDB external-memory scan layer
  -> table and column profiling
  -> DBML constraint checks
  -> YAML business-rule checks
  -> relationship validation
  -> bounded influence/correlation analysis when target is provided
  -> issue aggregation and recommended actions
  -> deterministic JSON, samples, Markdown, and HTML reports
  -> run.log, run_events.jsonl, and run_summary.json
```

### Target enrichment flow

```text
MVP artifacts
  -> schema evaluation artifact
  -> relationship graph artifact
  -> deterministic dataset verdict
  -> chart specs and rendered charts
  -> optional LLM narrative with guardrail validation
```

The deterministic pipeline owns all facts. The LLM layer is a presenter and must
not invent numbers, references, root causes, or remediation actions that are not
supported by evidence artifacts.

## Runtime Stack

| Concern | Choice | Rationale |
| --- | --- | --- |
| CLI | Typer | Small local command surface with typed options. |
| Query engine | DuckDB | Reads CSV directly and can aggregate/join without loading full files into Python memory. |
| Domain contracts | Pydantic | Stable JSON contracts and validation for reports. |
| Rules config | YAML | Human-editable business rules. |
| Reports | Jinja2 Markdown/HTML templates | Deterministic, testable output. |
| Runtime logging | Python logging + JSONL events; optional Rich console | Human-readable progress plus machine-readable run trace. |
| Web prototype | Plain HTML/CSS/JavaScript | Local-first DBML/CSV mapping without a build step. |
| pandas | Bounded samples only | Allowed only after an explicit `LIMIT`, reservoir sample, or row/column guard. |
| LLM provider | Optional adapter | The core profiler must run without internet or model credentials. |

## Layering

```text
interfaces
  CLI, static web, report templates

application
  run orchestration, runtime tracing, artifact writing, severity aggregation,
  optional LLM dispatch

domain
  schema catalog, table catalog, profiles, issues, graph, verdict, report and
  runtime models

infrastructure
  DuckDB relations, DBML parser, YAML loader, file system, logging sinks,
  optional LLM client
```

Dependency rule: domain models do not import DuckDB, Typer, web UI code, report
templates, logging sinks, or LLM clients. Infrastructure adapters convert
external data into domain models before application logic consumes it.

The CLI should stay thin. If orchestration grows, move pipeline coordination out
of `cli.py` into an application runner such as `runner.py` so CLI and future web
runner can share the same implementation.

## Current Module Map

| Module | Responsibility | Architecture role |
| --- | --- | --- |
| `src/vsf_profiler/cli.py` | CLI options and command entrypoints. | Interface. |
| `src/vsf_profiler/models.py` | Pydantic/dataclass contracts for profiles, issues, reports, and runtime summary. | Domain. |
| `src/vsf_profiler/dbml_parser.py` | Pragmatic DBML parsing. | Infrastructure adapter producing domain catalog data. |
| `src/vsf_profiler/csv_catalog.py` | CSV discovery and DBML table mapping. | Application/domain boundary. |
| `src/vsf_profiler/duckdb_utils.py` | DuckDB connection, settings, safe identifier quoting, and CSV relation creation. | Infrastructure. |
| `src/vsf_profiler/profiler.py` | Table and column statistics through DuckDB SQL. | Application service. |
| `src/vsf_profiler/quality_rules.py` | DBML and YAML rule checks. | Application service. |
| `src/vsf_profiler/relationship_checker.py` | FK, anti-join, parent duplicate, and join coverage checks. | Application service. |
| `src/vsf_profiler/issue_catalog.py` | Normalized issue creation, severity defaults, evidence paths, and suggested fixes. | Domain/application service. |
| `src/vsf_profiler/influence_analyzer.py` | Bounded association analysis for a target column. | Application service with strict memory guards. |
| `src/vsf_profiler/report_generator.py` | Deterministic Markdown and HTML reports. | Interface presenter. |
| `src/vsf_profiler/runtime.py` | Run context, stage timing, run events, and run summary contract. | Application/domain support. |
| `src/vsf_profiler/logging_utils.py` | Console logging, `run.log`, and JSONL event sinks. | Infrastructure. |
| `src/vsf_profiler/demo_data.py` | Small synthetic dataset with injected issues. | Demo/test support. |
| `src/vsf_profiler/schema_diagram.py` | DBML diagram payload and dbdiagram link generation. | Report artifact service / roadmap if not implemented. |
| `web/` | Local browser workspace for DBML/CSV mapping. | Static interface / prototype. |

## Domain Model

The domain should converge on these stable concepts:

- `RunSummary`: run id, input paths, output paths, tool versions, resource
  limits, start/finish timestamps, status, stage timings, and artifact list.
- `RunEvent`: machine-readable runtime event for stage start/finish, table
  profiling, issue discovery, artifact writing, warnings, and failures.
- `SchemaCatalog`: DBML tables, columns, types, primary keys, unique
  constraints, not-null constraints, foreign keys, and relationship metadata.
- `CsvCatalog`: discovered files, headers, inferred dialect, mapped table,
  missing tables, extra files, and duplicate candidate mappings.
- `TableProfile`: row count, column count, duplicate key metrics, and scan
  metadata.
- `ColumnProfile`: null count, distinct count, inferred semantic type, numeric
  stats, string stats, date stats, top values, and quality flags.
- `Issue`: normalized finding with type, severity, table, columns, bad count,
  affected percent, evidence SQL, sample artifact, suggested fix, and
  provenance.
- `RelationshipCheck`: FK health, orphan count, null FK count, duplicate parent
  count, join coverage, cardinality, and confidence.
- `DataGraph`: tables as nodes and relationships as edges, including edge type,
  cardinality, constraint source, and validation status.
- `InfluenceResult`: association metrics for a target column with explicit
  non-causality wording.
- `DatasetVerdict`: overall readiness, risk score, top blockers, warnings, and
  recommended next actions.
- `NarrativeReport`: optional LLM output plus guardrail validation status.

`RunSummary` is the MVP runtime contract. `RunManifest` may be introduced later
as a richer superset, but it should not replace current artifact names without a
compatibility path.

The legacy `tanlong` branch may contain useful ontology ideas for findings,
schema evaluation, verdict, graph edges, issue clusters, and guardrail reports.
Those concepts should be ported as contracts, not as pandas execution logic.

## Input Boundaries

All untrusted input is parsed at the boundary:

- CLI paths must be resolved and validated before pipeline execution.
- DBML text must be parsed into a `SchemaCatalog`.
- CSV files must be cataloged before any scan.
- CSV headers and DBML table names must be normalized consistently.
- YAML rules must be validated into typed rule objects.
- Target columns must use `table.column` format and must exist after mapping.
- LLM provider config must be optional and isolated from deterministic runs.

The pipeline should fail fast for invalid control inputs such as unreadable
DBML, malformed YAML, missing CSV directories, invalid target column names, or
unwritable output directories. Data-quality failures inside valid input files
should be reported as issues rather than crashing the run whenever possible.

Security-sensitive boundary rule: table names, column names, and file paths from
DBML/CSV input are untrusted. SQL generation must quote identifiers through a
single utility and avoid raw string interpolation of unescaped identifiers.

## DBML and Schema Graph

The DBML parser is the contract parser for the dataset graph.

MVP required support:

- tables and columns;
- column types;
- `pk`, `not null`, and `unique`;
- composite primary keys from `indexes { (...) [pk] }` when available;
- inline refs such as `ref: > parent.id`;
- short `Ref:` syntax.

Roadmap support:

- one-to-one relationship declarations;
- many-to-many relationships, represented either explicitly or inferred through
  junction tables;
- composite foreign keys;
- full DBML grammar compatibility through a parser adapter.

Current implementation covers a pragmatic subset. The next parser iteration
should either adopt a complete DBML parser behind the same `SchemaCatalog`
contract or extend the current parser without leaking parser-specific objects
into the rest of the application.

Graph construction should not trust DBML blindly. It should combine declared
constraints with observed data checks:

- Does the parent key exist?
- Is the parent key unique at runtime?
- Is the child FK nullable?
- Are there orphan child keys?
- Is the relationship cardinality consistent with DBML?
- Does a bridge table look like a valid many-to-many junction?

## CSV Catalog and Mapping

CSV files map to DBML tables by normalized file stem by default. The catalog
also records:

- missing CSV files for DBML tables;
- extra CSV files not described in DBML;
- duplicate candidate mappings;
- headers read from each file;
- header-to-column mismatches;
- file size and modification metadata when available.

The static web UI may let users override mappings manually. A future local web
runner should pass those mappings to the CLI/backend as explicit run config
rather than relying only on file stems.

## External-Memory Data Access

DuckDB is the scan layer. CSV files are exposed as DuckDB relations, and all
large-data operations are expressed as SQL aggregates, joins, anti-joins, or
bounded samples.

Rules:

- Do not call `pandas.read_csv()` on user CSV files in production profiling
  code.
- Do not call `.fetchdf()` without an explicit row and column cap.
- Keep raw row samples small and write them to artifact files.
- Prefer aggregate tables, sketches, and SQL windows over Python collections.
- Parent-key checks must not materialize large key sets in Python.
- Cross-table joins must run through DuckDB with explicit join strategy and
  output limits.
- Quote all identifiers with a shared utility; never concatenate untrusted table
  or column names into SQL directly.
- Use DuckDB resource options for large runs: memory limit, temp directory, and
  thread count where configured.

Resource controls should be first-class run options:

- DuckDB memory limit;
- DuckDB temp directory;
- max sample rows per issue;
- max analysis rows for bounded influence analysis;
- max feature columns for influence analysis;
- exact vs approximate distinct-count mode;
- fail-fast vs best-effort mode.

## Profiling

Profiling is table-local and column-local before cross-table checks begin.

Table-level metrics:

- row count;
- column count;
- duplicate full-row count when enabled;
- primary-key duplicate count;
- scan warnings;
- missing/extra column counts.

Column-level metrics:

- non-null count and null count;
- null percent;
- exact or approximate distinct count;
- top values with counts;
- inferred type family;
- min, max, mean, standard deviation for numeric-looking columns;
- min and max for date/time-looking columns;
- min, max, and average length for strings;
- invalid parse count for expected numeric/date/boolean columns.

For very high-cardinality columns, profiling should avoid keeping full value
histograms in memory. The report should show bounded top-k values and a clear
note when distinct counts are approximate.

## Quality Checks

Quality checks come from three sources:

- DBML constraints: required fields, primary keys, unique columns, foreign keys,
  and type expectations.
- YAML business rules: range checks, accepted values, regex, date ordering, and
  SQL expressions.
- Built-in heuristics: empty strings, placeholder tokens, constant columns, high
  missingness, high cardinality, invalid dates, invalid numbers, duplicate rows,
  and suspicious identifiers.

Every issue must carry evidence:

- stable issue type;
- severity;
- table and columns;
- bad row count;
- affected percentage when meaningful;
- evidence SQL or deterministic rule reference;
- bounded sample artifact path;
- probable cause when deterministic;
- suggested fix;
- provenance showing whether it came from DBML, YAML, built-in heuristics, or
  graph validation.

The issue catalog should stay machine-readable and stable even when report
wording changes.

## Relationship Validation

Relationship checks run after table profiles and DBML graph construction.

MVP required checks:

- FK child null count;
- orphan FK count through anti-join;
- parent duplicate key count;
- child join coverage.

Roadmap checks:

- parent coverage;
- runtime cardinality classification;
- declared-vs-observed cardinality mismatch;
- many-to-many bridge-table validation;
- composite FK validation.

Relationship validation should emit both issue records and graph-edge status.
For example, an edge can be declared in DBML but marked `invalid` because the
parent key is not unique or because orphan keys exceed the configured threshold.

## Influence and Cross-Table Analysis

Influence analysis is association analysis, not causality analysis.

Allowed implementation pattern:

- select a target column in `table.column` format;
- build a bounded analysis relation in DuckDB;
- include direct table features and selected parent-table features through safe
  joins;
- aggregate one-to-many child features before joining to the target grain;
- enforce max rows, max columns, and max joined output size;
- compute association metrics with SQL or bounded in-memory frames;
- label every result as association only.

The default behavior should still produce a successful run when no target is
provided. In that case `influence.json` should record `skipped` with a clear
reason rather than crashing the pipeline.

The legacy `tanlong` branch may contain useful ideas for safe joins, fact-table
selection, and cross-table correlation. Those ideas must be rewritten to use
DuckDB relations and bounded samples instead of pandas merges.

## Charts

Charts are generated from aggregate outputs, not raw full datasets.

MVP report may work without charts. Recommended roadmap chart artifacts:

- missingness bar chart per table;
- top issue counts by severity and type;
- top-k categorical distributions;
- numeric histograms from SQL bins;
- relationship graph diagram data;
- FK health summary;
- influence ranking chart.

The stable artifact should be chart data or a chart spec first. PNG/SVG/HTML
rendering can be layered on top so the report remains reproducible in headless
environments.

## Severity and Verdict

Severity should be deterministic and explainable.

MVP severity may be rule-default based:

- P0: the run or core dataset contract is blocked;
- P1: critical data quality or relationship issue likely to break analytics;
- P2: medium data quality issue that needs cleanup or confirmation;
- P3: warning, outlier, or review-needed finding.

Target verdict inputs:

- issue type;
- bad count and affected percent;
- DBML constraint criticality;
- relationship role;
- target-column relevance;
- configurable thresholds;
- compound issue patterns.

Target verdict outputs:

- issue severity;
- table-level risk;
- relationship-level risk;
- dataset-level readiness verdict such as `READY`, `WARN`, or `NOT_READY`;
- top blockers and suggested next actions.

The severity and verdict model from the legacy `tanlong` branch is a useful
product-behavior reference. It should be adapted to the current issue model and
tested with deterministic fixtures.

## Runtime Execution and Observability

Each run should show and record the same execution stages:

1. Parse DBML schema.
2. Catalog CSV files and table mappings.
3. Profile CSV tables and columns.
4. Run data quality checks.
5. Check relationships.
6. Run influence analysis or record why it was skipped.
7. Generate artifacts and reports.

Console output should show stage start, stage success/failure, duration, and key
metrics. File outputs should include:

- `run.log`: detailed human-readable log;
- `run_events.jsonl`: machine-readable event stream;
- `run_summary.json`: final run status, input/output paths, stage timings,
  totals, and issue counts by severity.

Runtime events should include at least:

- `run_started`;
- `stage_started`;
- `stage_finished`;
- `stage_failed`;
- `table_profile_started`;
- `table_profile_finished`;
- `issue_found`;
- `artifact_written`;
- `run_finished`;
- `run_failed`.

Logs must not print full raw rows, secrets, credentials, or unbounded sample
values. They may include table name, column name, issue type, severity,
`bad_count`, `bad_rate`, and sample artifact path.

## LLM Narrative

The LLM layer is optional and runs after deterministic artifacts are complete.

LLM input may include:

- profile summary JSON;
- issue summaries;
- schema evaluation;
- relationship graph summary;
- verdict;
- chart summaries;
- sample row snippets only when explicitly allowed and bounded.

LLM input must not include:

- full CSV data;
- secrets;
- credentials;
- unbounded sample rows;
- unsupported numbers or claims.

The narrative role is "Senior Data Scientist". The output should explain:

- dataset health;
- important table and column findings;
- relationship risks;
- likely downstream modeling or analytics impact;
- prioritized remediation steps;
- caveats and non-causal interpretation.

Guardrail validation should run after generation:

- verify numeric claims against allowed evidence;
- verify issue/table/column references;
- reject causal wording unless explicitly supported;
- retry once with guardrail feedback when configured;
- fall back to deterministic narrative if validation fails.

## Reports and Artifacts

The output directory is the run contract.

### MVP artifacts

| Artifact | Purpose |
| --- | --- |
| `profile_summary.json` | Table and column statistics. |
| `issues.json` | Normalized data-quality, schema, and relationship findings. |
| `influence.json` | Target-column association analysis or skipped status. |
| `samples/` | Bounded evidence rows for findings. |
| `report.md` | Deterministic human-readable report. |
| `report.html` | Static HTML report. |
| `run.log` | Human-readable run log. |
| `run_events.jsonl` | Machine-readable runtime event stream. |
| `run_summary.json` | Inputs, outputs, config, timings, stage status, and issue counts. |

### Roadmap artifacts

| Artifact | Purpose |
| --- | --- |
| `run_manifest.json` | Richer superset of `run_summary.json` with versions and artifact inventory. |
| `schema_evaluation.json` | Schema conformance and graph validation details. |
| `relationship_graph.json` | Nodes, edges, cardinality, and validation status. |
| `dataset_verdict.json` | Readiness verdict, risk score, blockers, and recommendations. |
| `charts/` | Chart specs, chart data, and optional rendered images. |
| `schema_diagram.json` | Diagram metadata and dbdiagram link. |
| `schema_diagram.dbml` | DBML used for diagram rendering. |
| `l4_report.md` | Optional LLM narrative. |
| `guardrail_report.json` | Optional LLM validation result. |

Backward compatibility matters: existing artifact names should keep working while
richer artifacts are added.

## Web Architecture

The current web UI, when present, is intentionally static and local-first:

- reads DBML files in the browser;
- reads only CSV headers;
- maps CSV files to DBML tables;
- displays PK/FK relationships;
- generates a dbdiagram.io link;
- does not upload raw files to a backend.

A future local web runner should be an explicit second surface:

```text
browser workspace
  -> local backend job API
  -> same application pipeline used by CLI
  -> output artifacts
  -> browser report viewer
```

The web runner must not create a separate profiling implementation. CLI and web
must share the same application services and domain models.

## Performance Strategy

The system should scale by scanning and aggregating, not by retaining rows.

| Workload | Strategy |
| --- | --- |
| Row counts | DuckDB `COUNT(*)` over CSV relation. |
| Null counts | SQL conditional aggregates. |
| Distinct counts | Exact `COUNT(DISTINCT)` by default, approximate mode for very large columns. |
| Top values | SQL `GROUP BY` with `ORDER BY count DESC LIMIT k`. |
| PK duplicates | SQL grouped count on key columns. |
| FK orphans | SQL anti-join or `NOT EXISTS`. |
| Parent duplicate keys | SQL grouped count on parent key. |
| Composite FK | Roadmap SQL join over all key columns. |
| Many-to-many validation | Roadmap SQL checks over bridge-table key pairs. |
| Issue samples | SQL query with `LIMIT sample_size`, written to CSV. |
| Influence | SQL feature extraction plus bounded sample frame. |
| Charts | SQL aggregate bins and top-k datasets. |

Large-file regression tests should include synthetic data that exceeds normal
developer RAM expectations for pandas full-load workflows. The acceptance rule
is not raw speed alone; it is bounded memory and graceful degradation.

## Error Handling

Error handling distinguishes control-plane errors from data-quality findings.

Control-plane errors stop the run:

- missing DBML file;
- unreadable CSV directory;
- invalid YAML syntax;
- invalid target-column format;
- artifact output path cannot be created;
- DuckDB cannot initialize with configured resource options.

Data-plane issues become findings when the run can continue:

- missing CSV for a DBML table;
- extra CSV not in DBML;
- missing expected column;
- invalid values;
- FK violations;
- parse failures in expected numeric/date columns.

Best-effort mode may continue after non-critical table failures and mark the
affected tables as incomplete in `run_summary.json` and, later,
`run_manifest.json`.

Every stopped run should still attempt to write a failure `run_summary.json` and
`run.log` so users know which stage failed.

## Security and Privacy

- The default workflow is local.
- Raw data should not leave the user's machine.
- LLM use must be opt-in.
- LLM prompts should contain structured summaries, not full raw tables.
- Sample artifacts must be bounded and clearly listed.
- Future redaction/masking should happen before samples are written or sent to
  external providers.
- Environment variables and credentials must not be copied into reports.
- Logs must not include full raw rows, secrets, tokens, or credentials.
- SQL generation must quote identifiers and avoid unescaped user-controlled
  table/column names.

## Testing Strategy

MVP required tests:

- DBML parser unit tests for supported syntax.
- CSV catalog tests for stem mapping, missing files, extra files, and header
  mismatches.
- DuckDB profiling tests with deterministic small fixtures.
- Relationship tests for valid FK, orphan FK, duplicate parent, and nullable FK.
- YAML rule tests for range, accepted values, regex, and expression checks.
- End-to-end demo tests that assert artifact existence and representative issue
  types.
- Runtime logging tests that assert `run.log`, `run_events.jsonl`, and
  `run_summary.json` are created and include stage events.
- Large-data regression tests that fail if production code uses unbounded
  pandas CSV loading.

Roadmap tests:

- composite FK, one-to-one, one-to-many, and many-to-many cases;
- severity/verdict tests with fixed issue sets;
- guardrail tests for numeric validation, invalid references, and causal
  wording;
- static web tests for local file handling and no upload calls.

## Legacy `tanlong` Migration Guidance

The legacy `tanlong` branch should be treated as a product-behavior reference,
not as the execution engine for large data.

Keep and adapt:

- ontology contracts for data quality, schema evaluation, verdict, graph, and
  LLM reports;
- severity aggregation and threshold concepts;
- guardrail validation for narrative reports;
- LLM analyst/editor flow as an optional presenter layer;
- schema graph and cardinality ideas;
- cross-table safe-join concepts;
- web job-management ideas if a local backend is added.

Rewrite before porting:

- ingestion readers that call pandas full-file loaders;
- ydata-profiling full-frame profiling;
- PyOD/sklearn anomaly detection over full dataframes;
- missingness analysis over full dataframes;
- parent-key and FK checks that materialize large Python sets;
- pandas merge-based cross-table correlation.

Drop or isolate:

- any feature that requires full raw dataframes for normal operation;
- any LLM path that can introduce unsupported numeric claims;
- any chart generation that needs full raw columns in memory.

## Near-Term Implementation Slices

1. Add runtime execution flow artifacts: `run.log`, `run_events.jsonl`, and
   `run_summary.json`, and include an Execution Flow section in reports.
2. Harden current MVP contracts while preserving existing artifact names.
3. Add large-data memory regression tests and guarded `.fetchdf()` checks.
4. Introduce richer ontology JSON for schema evaluation and relationship graph
   without changing the MVP pipeline shape.
5. Add deterministic severity aggregation and dataset verdict.
6. Extend DBML parsing and relationship validation for one-to-one,
   many-to-many, and composite foreign keys.
7. Add chart-spec artifacts from aggregate data.
8. Add optional LLM narrative and guardrail validation.
