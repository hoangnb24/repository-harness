# Design

## Domain Model

The core domain language is Smart EDA and data-quality readiness:

- `dataset_verdict.json` stays the compatibility artifact for readiness label,
  risk score, blockers, and data-quality next steps.
- `table_assessments.json` stays the compatibility artifact for per-table
  readiness, health, role, relationship risks, and analysis impact.
- The existing `business_impact` JSON key remains to preserve downstream
  contracts, but generated labels and visible copy describe analysis impact.

## Application Flow

The deterministic pipeline continues to own all facts. The L4 provider prompt
asks for an optional Data Scientist EDA narrative and still requires the
provider to return the guardrail-safe draft exactly.

## Interface Contract

Artifact filenames, CLI commands, web routes, API payloads, and JSON keys are
unchanged. Visible report/web/package headings change from business/verdict
framing to Smart EDA/readiness/table assessment framing.

## Data Model

No migrations or persistence changes.

## UI / Platform Impact

The local web runner keeps its existing IDs and JavaScript function names for
compatibility, but visible labels move to Smart EDA, EDA readiness, Table
Assessment, analysis impact, and data-quality next steps.

## Observability

Validation evidence remains local command output plus a Harness trace. No new
runtime logs or metrics are introduced.

## Alternatives Considered

1. Rename JSON keys such as `business_impact` and `dataset_verdict`. Rejected
   because existing tests, packages, dashboards, and artifact consumers rely on
   stable artifact contracts.
2. Remove advanced features from docs. Rejected because they are implemented
   and still useful; the safer correction is to mark them optional.
