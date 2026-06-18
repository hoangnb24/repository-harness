# Design

## Domain Model

The graph view is a browser view model derived from existing artifacts:

- `LineageGraphView`: nodes and edges from `lineage_graph.json`, grouped by
  source, schema, table, column, relationship, runtime stage, and artifact.
- `RelationshipGraphView`: table nodes and FK edges from
  `relationship_graph.json`, including status, cardinality, metrics, and
  evidence links.
- `GraphFilters`: existing dashboard severity/type/table filters plus a graph
  mode and graph scope.
- `GraphSelection`: clicked node metadata used for drilldown.

The existing Python/DuckDB pipeline remains the only source of profiling and
lineage facts.

## Application Flow

1. User starts an upload-mode, local-path-mode, or Postgres-backed web-runner
   job.
2. Existing SSE job payload marks the job as completed.
3. Browser requests `/api/jobs/<job_id>/dashboard`.
4. Browser fetches returned artifact URLs for chart specs and canonical machine
   artifacts, including `lineage_graph.json` and `relationship_graph.json`.
5. Browser renders the existing dashboard panels plus a deterministic SVG graph.
6. Graph mode and scope controls update client-side graph state only.
7. Node clicks update a graph drilldown with metadata and relevant artifact
   links without rerunning the profiler.

## Interface Contract

No backend route or artifact-name changes are required. The existing dashboard
payload continues to expose protected artifact URLs:

```json
{
  "artifact_urls": {
    "lineage_graph.json": "/api/jobs/<job_id>/artifacts/lineage_graph.json",
    "relationship_graph.json": "/api/jobs/<job_id>/artifacts/relationship_graph.json"
  }
}
```

The graph renderer must not construct local filesystem paths or fetch CSV
inputs. It uses only URLs returned by the web runner artifact endpoint.

## Data Model

No persistent database or artifact schema change. The browser stores graph view
state in memory and discards it on refresh.

## UI / Platform Impact

The dashboard gains a dense Visual Graph section below the existing chart
panels. It uses vanilla JavaScript, SVG, and existing CSS tokens. Controls are
plain buttons/selects with keyboard focus states, and graph nodes are
keyboardable SVG groups.

## Observability

The UI shows graph source status, node/edge counts, missing-artifact states, and
selected node metadata. Runtime truth remains `run_events.jsonl` and
`run_summary.json`; graph facts remain the generated JSON artifacts.

## Alternatives Considered

1. Add a graph visualization library. Rejected because the local runner should
   stay dependency-light and work without internet or a frontend build step.
2. Generate graph HTML server-side. Rejected because the requested behavior is
   interactive and can be safely derived from protected artifact URLs.
3. Derive lineage in JavaScript from raw CSV or runtime internals. Rejected
   because the pipeline already writes `lineage_graph.json`, and the dashboard
   must not become a profiler or raw data reader.
