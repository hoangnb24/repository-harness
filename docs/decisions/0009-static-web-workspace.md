# 0009 Static Web Workspace

Date: 2026-06-15

## Status

Accepted

## Context

VSF Data Profiler started as a CLI and static report generator. The next demo
need is a website-like workspace where users can upload a DBML file and related
CSV files, visualize the schema, and link uploaded CSV files to DBML tables.

## Decision

Implement the first web surface as a static local-first prototype under `web/`
using plain HTML, CSS, and JavaScript.

The web UI:

- Reads DBML and CSV files in the browser.
- Parses the DBML subset client-side for table, PK, FK, and relationship
  display.
- Reads only CSV headers for mapping.
- Auto-links file stems to DBML table names.
- Allows manual CSV-to-table overrides.
- Generates dbdiagram.io embed URLs for DBML visualization.
- Does not upload files to a backend.

## Consequences

Positive:

- The demo is easy to run with `python3 -m http.server`.
- No frontend build tool or backend server is required for the first UI pass.
- Sensitive CSV files stay local during mapping/visualization.

Tradeoffs:

- This is not yet wired to the Python profiling pipeline.
- Large DBML files can create long dbdiagram URLs.
- Browser visual validation depends on an available browser surface.

## Follow-Up

- Add an API/backend bridge when users need the web UI to run the full profiler.
- Persist mapping choices if multi-step web workflows become part of v0.2.
