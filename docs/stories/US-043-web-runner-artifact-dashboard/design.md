# Design

## Domain Model

The dashboard is a client-side view model derived from generated artifacts:

- `DashboardArtifacts`: URLs and parsed JSON for chart specs and canonical
  machine artifacts.
- `DashboardFilters`: selected severity, issue type, and table.
- `DashboardSelection`: active chart item used for drilldown.

The Python pipeline remains the only source of profiling facts.

## Application Flow

1. User starts an upload-mode or local-path-mode job.
2. Existing SSE job payload marks the job `succeeded`.
3. Browser requests `/api/jobs/<job_id>/dashboard`.
4. Browser fetches the returned artifact URLs for:
   - `charts/*.json`
   - `issues.json`
   - `profile_summary.json`
   - `relationship_graph.json`
   - `dataset_verdict.json`
   - `schema_evaluation.json`
   - `influence.json`
   - `run_summary.json`
5. Browser renders SVG/CSS panels for the available specs and artifacts.
6. Filter controls update the client-side view model only.
7. Chart-item clicks update the drilldown panel without rerunning the profiler.

## Interface Contract

Existing job and artifact routes remain unchanged.

New route:

- `GET /api/jobs/<job_id>/dashboard`

Response:

```json
{
  "job_id": "run_...",
  "status": "succeeded",
  "artifact_urls": {
    "issues.json": "/api/jobs/.../artifacts/issues.json",
    "charts/issue_counts_by_type.json": "/api/jobs/.../artifacts/charts/issue_counts_by_type.json"
  },
  "required_artifacts": ["issues.json", "..."],
  "chart_artifacts": ["charts/issue_counts_by_type.json"],
  "missing_artifacts": []
}
```

The endpoint lists only files already available through the protected artifact
resolver. It does not parse CSVs or expose input paths.

## Data Model

No database or artifact schema changes. Dashboard state is held in the browser
and discarded on page refresh.

## UI / Platform Impact

The web runner gains a dashboard panel below the runtime/artifact area. It uses
vanilla JS, SVG, and CSS with the existing warm technical design tokens.

## Observability

Dashboard loading state, missing optional artifact state, filter state, and
drilldown selection are visible in the UI. Runtime proof remains the existing
`run_events.jsonl` and `run_summary.json`.

## Alternatives Considered

1. Render dashboard charts server-side. Rejected because the requested behavior
   is interactive and can be derived safely from existing artifacts in the
   browser.
2. Fetch artifacts from local filesystem paths. Rejected because the dashboard
   must use web-runner artifact URLs and keep path traversal protection.
3. Add a charting library or CDN. Rejected because the local runner must work
   offline without build tooling.
