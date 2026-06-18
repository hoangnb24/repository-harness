# US-062 Declutter Dashboard Graph View with Progressive Disclosure

## Status

implemented

## Lane

normal

## Product Contract

The web dashboard Graph view remains a browser-side presenter over existing
generated artifacts. It should default to a readable table-level overview and
reveal columns, runtime/artifacts, and relationship-node detail only through
focused selection or explicit controls. Backend routes, artifact names, and
graph JSON contracts remain unchanged.

## Relevant Product Docs

- `README.md`
- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`
- `.interface-design/system.md`

## Acceptance Criteria

- Default Graph state is low-noise: table-level nodes, direct table
  relationships, no column nodes, no runtime/artifact fan-out, and no visible
  edge labels unless selected or hovered.
- Graph controls include Overview, Focus, Full, Show columns,
  Show runtime/artifacts, Invalid/warning only, and Reset graph view.
- Selecting a graph node highlights direct neighbors, fades unrelated
  nodes/edges, and shows only direct evidence artifacts and matching issues in
  the graph drilldown.
- Relationship mode defaults to table-to-table FK edges and shows
  relationship nodes only in Full mode.
- Lineage mode defaults to source -> table -> artifact-summary lanes and hides
  stage/artifact fan-out unless the runtime/artifact toggle or Full mode is
  active.
- Keyboard activation for graph nodes remains available.
- No backend API, artifact contract, raw CSV read, CDN, build tooling, or graph
  layout dependency is added.

## Design Notes

- Commands: no new CLI or backend command.
- Queries: reuse existing web-runner artifact URLs and loaded artifact JSON.
- API: no new backend route.
- Tables: none.
- Domain rules: Python/DuckDB artifacts remain authoritative; the graph view is
  presentation only.
- UI surfaces: Dashboard Graph view in the local web runner.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-062 --unit 1 --integration 1 --e2e 1 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | Static UI assertions for graph controls, renderer functions, and no raw CSV/backend changes. |
| Integration | Focused pytest for web UI, web runner, and demo artifact compatibility. |
| E2E | Playwright asserts default overview, toggles, selection highlighting, and relationship full mode. |
| Platform | `node --check`, full pytest, Ruff, `make demo-full`, and screenshots if feasible. |
| Release | Harness story verify and audit. |

## Harness Delta

- Durable intake recorded as change request #48.
- Durable story recorded as US-062.
- `.interface-design/system.md` receives the reusable progressive graph pattern.

## Evidence

- `node --check web/app.js` -> passed.
- `.venv/bin/pytest -q tests/test_web_ui_static.py tests/test_web_runner.py tests/test_demo_small.py`
  -> 15 passed.
- `npm run test:e2e:dashboard` -> 1 passed; asserts low-noise lineage
  overview, no default column/runtime/individual artifact nodes, focus mode,
  reset, invalid/warning filter, relationship Full mode, selection dimming,
  direct-neighbor drilldown, and unchanged raw-CSV boundary.
- `.venv/bin/pytest -q` -> 79 passed, 3 skipped.
- `.venv/bin/ruff check src tests scripts/verify_openai_smoke.py scripts/verify_vsf_artifacts.py scripts/benchmark_large_dataset.py`
  -> passed.
- `PATH="$PWD/.venv/bin:$PATH" make demo-full` -> passed; artifact audit
  reported 0 violations and bundled Playwright passed.
- Graph screenshots captured with Playwright:
  `outputs/graph_progressive_screenshots/lineage-overview.png` and
  `outputs/graph_progressive_screenshots/relationship-full.png`.
- `scripts/bin/harness-cli story verify US-062` -> passed.
- `scripts/bin/harness-cli audit` -> entropy score 0/100.
