# Design

## Domain Model

`TableAssessment` is an additive deterministic machine artifact entry derived
from existing structured outputs:

- table profile from `profile_summary.json`;
- issue rows from `issues.json`;
- FK status and junction-table metadata from `relationship_graph.json`;
- dataset-level severity normalization from the existing verdict rules.

Each assessment includes:

- `table`
- `role`: `fact`, `dimension`, `bridge`, `event`, `reference`, or `unknown`
- `health_score`: `0..100`
- `readiness`: `READY`, `WARN`, or `NOT_READY`
- `issue_counts_by_severity`
- `issue_counts_by_type`
- `affected_columns`
- `relationship_risks`
- `business_impact`
- `evidence_artifacts`
- `recommended_next_actions`

Business impact is a classification, not a factual business outcome. It is
derived from safe table/schema name tokens such as `customer`, `order`,
`payment`, `product`, `review`, `seller`, `status`, and `event`. The artifact
stores the matched token and rationale so the evidence is visible.

## Application Flow

The existing `run_pipeline()` flow remains authoritative:

1. Parse/catalog/profile/check data with DuckDB.
2. Build existing machine artifacts.
3. Build `table_assessments.json` from the existing structured objects.
4. Register the artifact in runtime summaries and web artifact payloads.
5. Render reports from the same deterministic context.
6. When `--use-llm` is enabled, include table assessments in the L4 context and
   guardrail evidence.

No profiling logic moves to JavaScript. The dashboard consumes only generated
artifact URLs.

## Interface Contract

`table_assessments.json` is canonical and additive. Existing artifact names,
URLs, chart names, CLI flags, and report names are preserved.

The web-runner dashboard endpoint includes `table_assessments.json` in required
dashboard artifact URLs. The browser fetches it the same way it fetches
`issues.json`, `dataset_verdict.json`, and graph artifacts.

The optional L4 source-artifact list includes `table_assessments.json`. Any
business impact claim must match categories/labels present in that artifact,
and table-specific impact claims must match the table’s own assessment.

## Data Model

No database migrations. The only data contract change is the additive JSON
artifact and related report/dashboard presentation.

## UI / Platform Impact

The dashboard adds a compact operational panel showing table readiness,
health score, role, and impact category. Existing severity/type/table filters
continue to drive issue rows and table drilldown. Artifact links include
`table_assessments.json`.

## Observability

`run_summary.json` includes the `table_assessments` artifact path. Runtime
events include the artifact write through existing recorder behavior. Artifact
audit/package checks include the new canonical artifact.

## Alternatives Considered

1. Let the LLM infer business impact directly. Rejected because the claim would
   not be deterministic or reliably guardrail-verifiable.
2. Add a full domain ontology. Rejected because the current product has no
   domain configuration surface and the story requires safe heuristics only.
3. Add a chart spec for table assessments. Deferred because the dashboard can
   render directly from the additive artifact without changing chart contracts.
