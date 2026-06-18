# Overview

## Current Behavior

The web workspace is a static local-first preflight UI. It can parse DBML in
JavaScript, inspect CSV headers, map CSV stems to DBML tables, and open a
dbdiagram.io visualization. It does not run the Python DuckDB profiler from the
browser.

## Target Behavior

The browser can upload a DBML file, multiple CSV files, and an optional rules
file to a local `127.0.0.1` backend. The backend runs the existing Python
pipeline, streams runtime progress from `run_events.jsonl`, and exposes the
generated artifacts for inspection.

## Affected Users

- Local demo users who want to run the full profiler from a browser.
- Maintainers validating that the web path uses the canonical Python pipeline.

## Affected Product Docs

- `README.md`
- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`
- `docs/TEST_MATRIX.md`
- `docs/decisions/0011-local-web-runner-boundary.md`

## Non-Goals

- No JavaScript port of profiling logic.
- No large company-data path mode in this slice.
- No hosted production backend.
- No artifact name changes.
- No unbounded pandas full-file loading.
