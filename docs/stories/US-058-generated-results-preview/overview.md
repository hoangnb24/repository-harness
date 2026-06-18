# US-058 Generated Results Preview

## Status

implemented

## Lane

normal

## Product Contract

The local web runner's post-run artifact area should help users understand the
generated run results before they open raw artifact files. After upload-mode or
local-path-mode jobs finish, the runner must preview existing generated
artifacts such as dataset verdict, issue counts, table impact, runtime summary,
and report links, while preserving all raw JSON/report artifact links and
artifact URLs.

## Relevant Product Docs

- `README.md`
- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`

## Acceptance Criteria

- The runner panel is labeled as Generated results rather than only Generated
  artifacts.
- Generated results preview cards are derived only from existing generated
  artifact URLs and already-loaded dashboard JSON artifacts.
- Previewed results include dataset verdict, issue counts, table impact,
  runtime summary, and report links when those artifacts exist.
- Raw JSON/report artifact links remain available with existing artifact names
  and URLs.
- The browser dashboard does not fetch raw source CSV files or implement
  profiler logic.
- Upload mode and local path mode continue to use existing backend job routes.

## Design Notes

- Commands: no new CLI or backend commands.
- Queries: use the existing `/api/jobs/<job_id>/dashboard` artifact index.
- API: no backend contract changes.
- Tables: none.
- Domain rules: generated facts remain owned by Python/DuckDB artifacts.
- UI surfaces: local web runner runtime panel and dashboard artifact area.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-058 --unit 1 --integration 1 --e2e 1 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | Static UI assertions for Generated results markers and no JS profiler/raw CSV fetches. |
| Integration | Focused pytest for web runner/static/demo behavior. |
| E2E | Playwright dashboard run asserts preview cards and raw artifact links. |
| Platform | `node --check`, full pytest, Ruff, and `make demo-full`. |
| Release | Harness story verify and audit. |

## Harness Delta

No Harness policy change expected.

## Evidence

- `node --check web/app.js` -> passed.
- `.venv/bin/pytest -q tests/test_web_ui_static.py tests/test_web_runner.py tests/test_demo_small.py` -> 15 passed.
- `.venv/bin/pytest -q` -> 79 passed, 3 skipped.
- `.venv/bin/ruff check src tests scripts/verify_openai_smoke.py scripts/verify_vsf_artifacts.py scripts/benchmark_large_dataset.py` -> passed.
- `npm run test:e2e:dashboard` -> 1 passed; asserts Generated results previews for dataset verdict, issue counts, table impact, runtime summary, report links, and raw artifact links.
- `make demo-full` -> passed; doctor, demo run, package export, PDF export, artifact audit with 0 violations, and dashboard E2E passed.
- Live `vsf-profiler web --port 8765` path-mode smoke on `127.0.0.1` confirmed the Generated results panel includes verdict, issue counts, table impact, runtime summary, report links, and raw links.
- Browser plugin `iab` was unavailable in this session, so live verification used local Playwright against the running server.
- `scripts/bin/harness-cli story verify US-058` -> passed.
- `scripts/bin/harness-cli audit` -> entropy score 0/100.
