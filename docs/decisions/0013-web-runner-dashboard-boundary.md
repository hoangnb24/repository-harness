# 0013 Web Runner Dashboard Boundary

Date: 2026-06-16

## Status

Accepted

## Context

The VSF Data Profiler already writes deterministic chart specs and machine
artifacts. Users need an interactive browser dashboard after local web-runner
jobs, but the dashboard must not become a second profiling engine, fetch raw
CSV rows, depend on internet-hosted chart libraries, or break existing artifact
contracts.

## Decision

Add an interactive dashboard to the local web runner as an artifact consumer.
The backend exposes a dashboard artifact index under
`GET /api/jobs/<job_id>/dashboard`. The index contains only protected artifact
URLs for existing generated JSON files and chart specs. The browser fetches
those URLs, renders SVG/CSS charts with vanilla JavaScript, and keeps filter and
drilldown state client-side.

The dashboard may compute presentation-only grouping and filtering from parsed
artifact JSON. It must not reimplement profiling, validation, verdict,
relationship, influence, or LLM logic and must not read raw CSV files.

## Alternatives Considered

1. Add a frontend chart library through CDN. Rejected because the local runner
   must work offline without internet.
2. Generate dashboard-specific artifacts from the pipeline. Rejected for this
   slice because existing chart specs and machine artifacts are sufficient.
3. Read CSV samples or input directories from the browser. Rejected because the
   dashboard boundary is generated artifacts only.

## Consequences

Positive:

- Browser users get interactive filtering and drilldown without rerunning the
  profiler.
- The pipeline remains the only source of deterministic facts.
- Artifact URLs and path traversal protection remain centralized in the web
  runner.

Tradeoffs:

- Dashboard interactions are scoped to data present in existing artifacts.
- Complex chart types remain future work unless aggregate chart specs are
  extended deliberately.

## Follow-Up

- Consider richer aggregate chart specs if future users need additional
  interactive panels.
