# US-056 Web Demo UX Redesign

## Status

implemented

## Lane

normal

## Product Contract

The local VSF Data Profiler web runner presents as a polished data-quality
console for demo and local use. The first screen makes the safe local run path
clear, keeps upload mode and local path mode separate, and explains that full
profiling runs only on `127.0.0.1`. After a job completes, the dashboard is the
primary review surface for verdict, risk, issues, table impact, graph views, and
artifact links.

The redesign is presentation-only. It preserves the existing backend routes,
artifact names, artifact URLs, upload mode, local path mode, chart/artifact data
sources, and Playwright job flow. It does not add a new chart engine, profiler
artifact, hosted backend, JavaScript profiler, or raw CSV dashboard reads.

## Relevant Product Docs

- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`
- `docs/releases/v0.2-rc.md`
- `.interface-design/system.md`

## Acceptance Criteria

- The first web-runner screen supports a clean demo path: check local backend,
  choose upload or local path mode, run the existing Python/DuckDB profiler, and
  watch runtime progress.
- The visual system is a restrained data-console system, not the prior
  cream/serif/gradient workspace style.
- `.interface-design/system.md` records the chosen VSF data-console direction,
  tokens, spacing, depth, typography, and reusable UI patterns.
- The post-run dashboard clearly exposes dataset verdict, risk, issue counts,
  table impact from `table_assessments.json`, graph exploration, drilldowns, and
  artifact links.
- Upload mode, local path mode, backend routes, generated artifact URLs,
  dashboard artifact fetches, and Playwright flow remain compatible.
- The Vercel static preflight boundary stays visible in copy without implying a
  hosted Python/DuckDB backend.
- Static UI tests and Playwright assertions cover the redesigned console,
  table impact section, and artifact-driven dashboard behavior.
- Desktop and mobile screenshots are captured as validation artifacts when
  local browser tooling is available.

## Design Notes

- Commands: keep `vsf-profiler web --port 8765`, upload job POST
  `/api/jobs`, path job POST `/api/path-jobs`, dashboard GET
  `/api/jobs/<job_id>/dashboard`, artifact GET URLs, and SSE event streaming.
- Queries: dashboard continues fetching canonical JSON and chart artifacts via
  artifact URLs only.
- API: unchanged.
- Tables: no data model changes.
- Domain rules: table impact is read from existing `table_assessments.json`;
  dashboard must not infer new business impact from raw rows.
- UI surfaces: `web/index.html`, `web/styles.css`, `web/app.js`, static UI
  tests, Playwright dashboard E2E, and product/release docs where demo wording
  needs to match the new UI.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-056 --unit 1 --integration 1 --e2e 1 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit/static | `.venv/bin/pytest -q tests/test_web_ui_static.py` |
| Integration | `.venv/bin/pytest -q tests/test_web_runner.py tests/test_demo_small.py` |
| E2E | `npm run test:e2e:dashboard` |
| Platform | `node --check web/app.js`; screenshots when browser tooling is available |
| Release | `.venv/bin/pytest -q`; Ruff; `make demo-full`; Harness story verify and audit |

## Harness Delta

No harness behavior changes are planned. The story exists because the slice
changes an implemented user-visible workflow and needs durable proof.

## Evidence

| Check | Result |
| --- | --- |
| Syntax | `node --check web/app.js` -> passed |
| Focused static/web/demo tests | `.venv/bin/pytest -q tests/test_web_ui_static.py tests/test_web_runner.py tests/test_demo_small.py` -> 15 passed |
| Dashboard E2E | `npm run test:e2e:dashboard` -> 1 passed |
| Full pytest | `.venv/bin/pytest -q` -> 79 passed, 3 skipped |
| Ruff | `.venv/bin/ruff check src tests scripts/verify_openai_smoke.py scripts/verify_vsf_artifacts.py scripts/benchmark_large_dataset.py` -> passed |
| Release demo | `make demo-full` -> passed, including doctor, demo-small, package/PDF/zip, artifact audit, and Playwright dashboard E2E |

Screenshots:

- `outputs/web_demo_ux_screenshots/desktop-dashboard.png`
- `outputs/web_demo_ux_screenshots/mobile-dashboard.png`

Browser note: the in-app Browser plugin reported `iab` unavailable in this
session, so the visual proof uses the repository Playwright flow and captured
screenshots.
