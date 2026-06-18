# US-061 ERD-Style Local DBML Diagram Layout Polish

## Status

implemented

## Lane

normal

## Product Contract

The local web runner DBML diagram should be readable and demo-ready without
depending on dbdiagram.io. The renderer remains a browser-side presenter over
existing pre-run DBML/CSV state and post-run generated artifacts. It should use
deterministic ERD-style layering, compact table cards, orthogonal relationship
edges, fit controls, table/edge selection, and a detail panel with artifact
evidence while preserving all backend routes and artifact contracts.

## Relevant Product Docs

- `README.md`
- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`
- `.interface-design/system.md`

## Acceptance Criteria

- The local diagram uses stable ERD-style layers: reference/dimension tables,
  bridge/junction tables, fact/event hubs, and child tables are ordered by
  role, relationship degree, and table name.
- Table cards are compact by default, show table name, mapped/missing status,
  PK/FK/key columns, and a `+N columns` collapsed indicator.
- Expanded and non-key-column controls update the same local renderer without
  rerunning the profiler.
- Relationship lines use orthogonal elbow paths, muted default styling, warning
  colors only for problematic relationships, and labels only on hover/focus or
  selected state.
- Clicking or keyboard-selecting a table highlights direct neighbors and shows
  table detail with columns, relationships, counts, status, and artifact links.
- Clicking or keyboard-selecting a relationship shows edge detail with child
  and parent columns, status/cardinality, and artifact evidence.
- `Open dbdiagram` remains a secondary external action.
- No backend route, artifact name, raw CSV fetch, hosted backend, JS profiler
  port, or external build/CDN dependency is added.

## Design Notes

- Commands: no new CLI or backend command.
- Queries: reuse existing web-runner artifact URLs and loaded artifact JSON.
- API: no new backend route.
- Tables: none.
- Domain rules: local diagram is presentation only; Python/DuckDB artifacts
  remain authoritative after a run.
- UI surfaces: DBML diagram preview panel in the local web runner.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-061 --unit 1 --integration 1 --e2e 1 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | Static UI assertions for ERD controls, detail panel, renderer functions, and no raw CSV/backend changes. |
| Integration | Focused pytest for web UI, web runner, and demo artifact compatibility. |
| E2E | Playwright asserts pre-run and post-run ERD layout, controls, selection, and secondary dbdiagram link. |
| Platform | `node --check`, full pytest, Ruff, `make demo-full`, and screenshots if feasible. |
| Release | Harness story verify and audit. |

## Harness Delta

- Durable intake recorded as change request #47.
- Durable story recorded as US-061.
- `.interface-design/system.md` receives the reusable ERD diagram pattern.

## Evidence

- `node --check web/app.js` -> passed.
- `.venv/bin/pytest -q tests/test_web_ui_static.py tests/test_web_runner.py tests/test_demo_small.py`
  -> 15 passed.
- `npm run test:e2e:dashboard` -> 1 passed; asserts ERD controls, bridge
  role, selected table inspector, non-key column toggle, post-run relationship
  keyboard selection, evidence detail, and unchanged dbdiagram link.
- `.venv/bin/pytest -q` -> 79 passed, 3 skipped.
- `.venv/bin/ruff check src tests scripts/verify_openai_smoke.py scripts/verify_vsf_artifacts.py scripts/benchmark_large_dataset.py`
  -> passed.
- `PATH="$PWD/.venv/bin:$PATH" make demo-full` -> passed; doctor ok, demo run
  found 15 issues, package/PDF/zip outputs written, artifact audit passed with
  0 violations, and bundled Playwright E2E passed.
- Visual screenshots captured with Playwright fallback because Browser `iab`
  was unavailable: `outputs/erd_diagram_screenshots/desktop-diagram.png` and
  `outputs/erd_diagram_screenshots/mobile-diagram.png`.
- No backend route, artifact name, raw CSV fetch, hosted backend, JS profiler
  port, external CDN, build step, or graph-layout dependency was added.
