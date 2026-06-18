# Overview

## Current Behavior

The local web runner can start upload-mode and local-path-mode jobs, stream
runtime progress, list generated artifacts, and render an interactive dashboard
from chart specs plus machine artifacts. It links `lineage_graph.json` and
`relationship_graph.json`, but it does not visualize either graph in the
browser.

## Target Behavior

After a completed web-runner job, the dashboard includes an interactive graph
section backed only by generated artifact URLs. Users can switch between a
lineage graph and a focused relationship graph, filter the visible graph by
table/column/relationship/runtime/artifact scope, and click graph nodes to see
metadata, evidence artifacts, and related issue details.

## Affected Users

- Local analyst or data scientist reviewing DBML/CSV profiling output.
- Local operator validating Postgres connector profiling output.
- Agent or reviewer using the web runner as an acceptance proof surface.

## Affected Product Docs

- `README.md`
- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`

## Non-Goals

- No raw CSV reads from the dashboard after a run.
- No JavaScript port of profiling, relationship validation, or lineage
  inference.
- No hosted multi-user web app, auth, database connector expansion, or external
  lineage catalog.
- No new frontend build system, CDN, or heavy graph dependency.
