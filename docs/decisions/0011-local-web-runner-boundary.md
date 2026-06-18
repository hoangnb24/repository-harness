# 0011 Local Web Runner Boundary

Date: 2026-06-15

## Status

Accepted

## Context

VSF Data Profiler has a static browser workspace that parses DBML and CSV
headers for preflight mapping, but users also need a way to upload demo-sized
DBML/CSV/rules inputs and run the full Python DuckDB profiler from the browser.
The product constraints require preserving existing artifact names, avoiding a
JavaScript profiler port, and keeping raw data local.

## Decision

Add a local-only web runner served by the Python package. The server binds only
to `127.0.0.1`, accepts DBML, CSV files, optional rules, and an optional target
column, then writes uploaded inputs under an ignored `outputs/web_runs/<id>/`
directory.

Each job calls the existing `run_pipeline()` function. Output artifacts are
written under `outputs/web_runs/<id>/artifacts` with the same artifact names as
the CLI. The browser reads backend endpoints for job state, generated artifact
links, and runtime events derived from `run_events.jsonl` and `run_summary.json`.
The UI must not infer pipeline stages independently.

Upload mode is for demos and small-to-medium local files. Large company-data
path mode remains future work.

## Alternatives Considered

1. Port profiling logic to JavaScript. Rejected because it would duplicate the
   Python DuckDB pipeline and risk divergent behavior.
2. Bind a server on `0.0.0.0`. Rejected because the runner handles local data
   uploads and must stay local-only for this slice.
3. Rename web-runner artifacts. Rejected because reports, docs, and tests
   already rely on stable CLI artifact names.

## Consequences

Positive:

- Browser users can run the full existing profiler after upload.
- Runtime progress comes from canonical runtime artifacts.
- CLI artifact contracts remain unchanged.

Tradeoffs:

- Upload mode is intentionally not the large-data workflow.
- The local runner adds a small HTTP surface that needs security and path
  traversal checks.

## Follow-Up

- Local path mode for larger local datasets was added under
  `docs/decisions/0012-local-path-mode-boundary.md`.
- Add richer job retention controls if web-runner output grows.
