# US-029 Static DBML CSV Web Workspace

## Status

implemented

## Lane

normal

## Product Contract

Add a browser-based UI where users can upload a DBML file and related CSV files,
visualize the DBML schema, and link uploaded CSV files to DBML tables before
profiling.

## Relevant Product Docs

- `docs/product/vsf-data-profiler.md`

## Acceptance Criteria

- The UI exposes DBML upload and multi-CSV upload controls.
- The UI parses DBML tables, primary keys, foreign keys, and relationships in
  the browser.
- The UI reads CSV headers locally and auto-links CSV file stems to DBML table
  names.
- The UI allows manual CSV-to-table linking through select controls.
- The UI generates a dbdiagram.io embed link and iframe preview for the DBML.
- The UI shows mapped, missing CSV, and extra CSV states.
- The UI communicates that files are processed locally in the browser.
- Static tests, Python tests, and Ruff checks pass.

## Design Notes

- Surface: static web app under `web/`.
- Runtime: plain HTML, CSS, and JavaScript; no build step.
- Commands: `make web-demo` serves the UI at `http://localhost:8080`.
- Design direction: schema operations console with a relationship rail.
- Data handling: local-first client-side file reads; no `fetch` or
  `XMLHttpRequest` data upload.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Static tests verify required UI regions and local-first JavaScript. |
| Integration | `python3 -m http.server 8080 --directory web` serves HTML, CSS, and JS. |
| E2E | Browser plugin unavailable in this session; curl verified served assets. |
| Platform | `node --check web/app.js` passed when Node was available. |
| Release | Not applicable for MVP. |

## Harness Delta

The prebuilt `scripts/bin/harness-cli` binary is absent, so durable story rows
cannot be written in this environment. This story file carries the local
evidence fallback.

## Evidence

- `pytest -q` -> `12 passed`.
- `ruff check src tests` -> passed.
- `node --check web/app.js` -> passed.
- `curl -fsS http://localhost:8080/` returned the static workspace HTML.
- `curl -fsS http://localhost:8080/styles.css` returned design tokens.
- `curl -fsS http://localhost:8080/app.js` returned the client app.
- Production deploy completed on Vercel project `smart-eda`.
- `curl -LfsS https://smart-eda.vercel.app/` returned the expected workspace
  HTML markers.
- `vercel inspect smart-4hr0hw8qj-tan-longs-projects-77c881cd.vercel.app`
  reported production status `Ready` and alias `https://smart-eda.vercel.app`.
- Browser plugin check returned no available browser instances, so visual
  screenshot validation was not possible in this session.
