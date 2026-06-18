# Exec Plan

## Goal

Add deterministic per-table assessment and bounded business-impact reporting
across CLI artifacts, reports, local web dashboard, optional L4 context, and
guardrails.

## Scope

In scope:

- `table_assessments.json`
- CLI pipeline artifact generation and runtime registration
- deterministic report section
- web-runner artifact discovery and dashboard panel/drilldown
- L4 context and guardrail extension
- package/audit/docs/tests/Harness proof updates

Out of scope:

- raw CSV reads in dashboard
- hosted backend work
- automatic data repair
- external business ontology
- LLM-only scoring or unsupported causal/business claims

## Risk Classification

Risk flags:

- Public contracts: new canonical artifact/report/dashboard surface.
- Existing behavior: pipeline, audit, package, and tests are pinned.
- Multi-domain: deterministic artifacts, UI, L4 guardrails, docs, and Harness.
- Weak proof if table/business claims are not guardrailed.

Hard gates:

- None requiring human confirmation unless safe deterministic business impact
  cannot be verified from the artifact.

## Work Phases

1. Discovery of current pipeline/report/dashboard/guardrail seams.
2. Story and decision record.
3. Deterministic artifact builder and pipeline registration.
4. Report, package, audit, and web artifact exposure.
5. Dashboard panel and drilldown behavior.
6. L4 context and guardrail checks.
7. Focused tests, then full validation gates.
8. Harness matrix/story/decision/audit/trace evidence.

## Stop Conditions

Pause for human confirmation if:

- Business impact needs assumptions not inferable from table/schema names.
- Guardrails cannot verify a class of generated business-impact claim.
- Existing artifact names or CLI behavior would need to change.
- Dashboard implementation would require raw CSV reads or a frontend build step.
