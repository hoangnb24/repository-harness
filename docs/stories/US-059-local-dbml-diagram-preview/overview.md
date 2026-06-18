# US-059 Reliable Local DBML Diagram Preview

## Status

implemented

## Lane

normal

## Product Contract

The VSF local web runner should show a reliable local schema diagram before and
after profiler runs. The visible diagram must not depend on a dbdiagram.io
iframe. The external dbdiagram.io URL remains available as a secondary action,
while the local preview renders table nodes, PK/FK columns, CSV mapping status,
relationship edges, and post-run parse diagnostics from existing browser state
and generated artifacts.

## Relevant Product Docs

- `README.md`
- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`

## Acceptance Criteria

- The DBML diagram panel renders a local table/relationship preview before a
  run from browser DBML/CSV preflight state.
- After a completed backend job, the diagram prefers existing generated
  `schema_diagram.json`, `relationship_graph.json`, and
  `schema_parse_report.json` artifacts through existing artifact URLs.
- The local diagram shows table nodes, PK/FK columns, CSV mapping status, and
  relationship edges.
- `Open dbdiagram` remains a secondary external link generated from DBML or the
  generated schema diagram artifact.
- Empty, parse-error, and too-large diagram states are explicit and do not show
  a broken iframe.
- No backend route, artifact name, profiler behavior, raw CSV read, or JS
  profiler port is added.

## Design Notes

- Commands: no new CLI or backend command.
- Queries: reuse existing web-runner artifact URLs.
- API: no new backend route.
- Tables: none.
- Domain rules: local preview is presentation only; Python/DuckDB artifacts
  remain authoritative after a run.
- UI surfaces: DBML diagram preview panel in the local web runner.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-059 --unit 1 --integration 1 --e2e 1 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | Static UI tests for local diagram DOM markers and no raw CSV/profile JS port. |
| Integration | Focused pytest for web UI, web runner, and demo artifact compatibility. |
| E2E | Playwright asserts pre-run local diagram and post-run artifact-backed diagram. |
| Platform | `node --check`, full pytest, Ruff, and `make demo-full`. |
| Release | Harness story verify and audit. |

## Harness Delta

No Harness policy change expected.

## Evidence

- `node --check web/app.js` -> passed.
- `.venv/bin/pytest -q tests/test_web_ui_static.py tests/test_web_runner.py tests/test_demo_small.py` -> 15 passed.
- `npm run test:e2e:dashboard` -> 1 passed; asserts pre-run local diagram and post-run artifact-backed diagram.
- `.venv/bin/pytest -q` -> 79 passed, 3 skipped.
- `.venv/bin/ruff check src tests scripts/verify_openai_smoke.py scripts/verify_vsf_artifacts.py scripts/benchmark_large_dataset.py` -> passed.
- `make demo-full` -> passed; doctor, demo run, package/PDF export, artifact audit with 0 violations, and dashboard E2E passed.
- Live `vsf-profiler web --port 8765` path-mode smoke on `127.0.0.1` confirmed local preflight diagram, hidden iframe, generated-artifact diagram source, parse diagnostics, and relationship status labels.
- Browser plugin `iab` was unavailable in this session, so live verification used local Playwright against the running server.
- `scripts/bin/harness-cli story verify US-059` -> passed.
- `scripts/bin/harness-cli audit` -> entropy score 0/100.
