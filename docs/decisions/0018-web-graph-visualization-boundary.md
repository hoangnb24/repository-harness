# 0018 Web Graph Visualization Boundary

Date: 2026-06-16

## Status

Accepted

## Context

The profiler now writes `lineage_graph.json` and `relationship_graph.json` as
machine artifacts, and the web-runner dashboard already fetches canonical
artifacts through protected local URLs. Users need a browser graph view, but
the dashboard must not become a profiler, lineage inference engine, raw CSV
reader, or external metadata publisher.

## Decision

Add graph visualization to the local web-runner dashboard as a client-side
artifact view. The browser may fetch and render `lineage_graph.json` and
`relationship_graph.json` only through `/api/jobs/<job_id>/artifacts/...` URLs
returned by the existing dashboard endpoint.

The graph renderer may filter, lay out, and drill into generated node and edge
metadata. It must not read raw CSV files, construct local filesystem paths,
infer new lineage semantics, call external services, or change canonical
artifact names. Backend path traversal protection remains the artifact-serving
boundary.

## Alternatives Considered

1. Add a dedicated graph API. Rejected because the existing artifact endpoint
   already provides the needed protected local contract.
2. Use a graph rendering package or CDN. Rejected because the local runner
   should remain dependency-light and offline-capable.
3. Recompute lineage or FK relationships in JavaScript. Rejected because the
   existing Python/DuckDB pipeline owns all profiling facts.

## Consequences

Positive:

- CLI and web outputs stay aligned through the same generated artifacts.
- Upload mode, local path mode, and Postgres connector mode can share the same
  dashboard graph renderer.
- Raw data and secret boundaries remain centralized in existing artifacts and
  artifact serving.

Tradeoffs:

- The graph layout is a deterministic operational map, not a full graph-catalog
  experience.
- Very large schemas may need future UI summarization, but this slice keeps the
  renderer bounded to generated artifact JSON.

## Follow-Up

- Consider richer graph search only after artifact contracts prove the required
  metadata without raw data reads.

## Verification

```text
.venv/bin/pytest -q tests/test_web_runner.py tests/test_web_ui_static.py tests/test_demo_small.py
node --check web/app.js
npm run test:e2e:dashboard
```
