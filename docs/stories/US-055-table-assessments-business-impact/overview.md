# Overview

## Current Behavior

VSF Data Profiler produces dataset-level readiness through
`dataset_verdict.json`, issue details through `issues.json`, relationship
status through `relationship_graph.json`, and dashboard/report views over those
artifacts. It does not yet produce a deterministic one-row-per-table assessment
that combines table role, readiness, relationship risk, and a bounded business
impact category.

Optional L4 narrative generation can summarize structured artifacts with
guardrail checks, but it has no table-assessment evidence source and no
table-specific business-impact guardrail.

## Target Behavior

US-055 adds an additive deterministic artifact:

- `table_assessments.json` is generated for every normal run.
- Each profiled table has one assessment with role, health score, readiness,
  issue counts, affected columns, relationship risks, bounded business impact,
  evidence artifact references, and next actions.
- Business impact is inferred only from transparent table/schema name tokens,
  with no external ontology, hidden domain assumptions, or causal claims.
- Markdown/HTML reports show a “Per-Table Assessment” section and link the new
  artifact.
- The local web-runner dashboard loads `table_assessments.json` from generated
  artifact URLs, renders a compact panel, and uses existing filters/drilldown
  mechanics for table selections.
- Optional L4 context can summarize table assessments only from
  `table_assessments.json`, and guardrails reject unsupported table/business
  impact claims.

## Affected Users

- Local data analysts reviewing readiness table by table.
- Maintainers validating release artifacts and dashboard contracts.
- Reviewers checking that optional L4 output stays evidence-bound.

## Affected Product Docs

- `README.md`
- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`
- `docs/releases/v0.2-rc.md`
- `docs/TEST_MATRIX.md`
- `docs/decisions/0024-table-assessment-business-impact-boundary.md`

## Non-Goals

- No automatic remediation.
- No hosted backend or raw CSV dashboard reads.
- No LLM-only scoring or business-impact invention.
- No external business ontology service.
- No artifact renames or changes to existing deterministic artifact names.
