# 0026 Smart EDA MVP Framing

Date: 2026-06-18

## Status

Accepted

## Context

VSF Data Profiler's original MVP is a local CSV plus DBML/schema Smart EDA
workflow for data scientists. Later implemented features added connectors,
package/PDF export, lineage, benchmarks, a local dashboard, and optional L4
provider output. Public copy began to frame the default product as a Senior
Data Scientist or business-impact review platform, which obscured the core
workflow.

## Decision

Keep the core product contract as CSV folder plus DBML/schema plus optional
rules plus optional target column producing deterministic Smart EDA artifacts
and reports. Present connectors, package/PDF export, lineage, benchmarks,
dashboard review, Olist, and L4 provider usage as optional advanced surfaces.

Preserve compatibility artifact names and JSON keys, including
`dataset_verdict.json`, `table_assessments.json`, and `business_impact`, while
changing visible copy to EDA/data-quality readiness, table assessment, analysis
impact, and data-quality next steps.

## Alternatives Considered

1. Rename artifacts and JSON keys to match the new language. Rejected because
   existing tests, packages, dashboards, and downstream references depend on
   those contracts.
2. Remove advanced features from documentation. Rejected because the features
   are implemented; they should be described as optional rather than erased.

## Consequences

Positive:

- The README, product contract, reports, package index, dashboard, and L4
  prompt align with the MVP Smart EDA framing.
- Optional advanced work remains discoverable without becoming the default
  product identity.

Tradeoffs:

- Compatibility JSON keys still carry legacy names, so docs must explain that
  user-visible language intentionally differs from some artifact keys.

## Follow-Up

- Keep future feature docs explicit about core versus optional advanced scope.
