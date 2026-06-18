# 0024 Table Assessment and Business Impact Boundary

Date: 2026-06-16

## Status

Accepted

## Context

VSF Data Profiler can already compute dataset-level readiness, issues,
relationship health, charts, lineage, and guarded optional L4 narrative. The
next requested layer is per-table assessment plus likely business impact. That
can help users prioritize tables, but it is risky if “business impact” becomes
an unsupported domain claim or a causal statement.

## Decision

Treat business impact as a deterministic, evidence-bound classification:

- Generate `table_assessments.json` as a canonical additive artifact.
- Derive table role, health score, readiness, issue counts, affected columns,
  relationship risks, and next actions from existing structured artifacts.
- Derive business impact only from transparent table/schema name tokens.
- Store the matched tokens and rationale in each assessment.
- Do not claim actual business outcomes, monetary impact, customer behavior, or
  root cause.
- Allow optional L4 narrative to summarize per-table findings only from
  `table_assessments.json`.
- Reject unsupported business-impact labels/categories and table-specific
  impact mismatches in guardrails.

## Alternatives Considered

1. Ask the LLM to infer business impact from issue text. Rejected because it
   would be non-deterministic and not bounded to structured evidence.
2. Add an external business ontology service. Rejected because v0.2 is
   local-first and has no provider/config contract for ontology data.
3. Omit business impact entirely. Rejected because a bounded category can be
   useful when it is clearly labeled as name-token inference.

## Consequences

Positive:

- Every table gets a deterministic readiness and impact summary.
- L4 narrative has a verifiable per-table evidence source.
- Dashboard users can filter and drill into table-level risk without raw CSV
  reads.

Tradeoffs:

- Impact categories are intentionally coarse and may be `general_analytics`
  when names do not match safe tokens.
- The artifact is not a substitute for domain-owner business prioritization.

## Verification

```text
.venv/bin/pytest -q tests/test_table_assessments.py tests/test_llm_narrative.py tests/test_demo_small.py tests/test_web_runner.py tests/test_web_ui_static.py
rg -q 'table_assessments.json' README.md docs/product/vsf-data-profiler.md docs/ARCHITECTURE.md docs/releases/v0.2-rc.md
scripts/bin/harness-cli decision verify 0024
```
