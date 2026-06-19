# US-071 Web Runner Demo Presets and LLM Toggle

## Status

implemented

## Lane

normal

## Product Contract

The local web runner lets a user choose the small synthetic demo or the optional
full Olist CSV sample from the runner UI. The same runner UI lets the user keep
L4 narrative generation off by default or opt into fake/OpenAI L4 report
generation for the next backend run.

## Relevant Product Docs

- `docs/product/vsf-data-profiler.md`
- `docs/demo/vsf-data-profiler.md`
- `docs/stories/US-064-l4-config-ux-smoke/overview.md`
- `docs/stories/US-070-layer-4-smart-eda-report-patterns.md`

## Acceptance Criteria

- Runner UI exposes small demo and full Olist presets that prefill DBML path,
  CSV directory, rules path, target column, and browser preflight DBML/CSV
  state.
- Runner UI exposes L4 report modes: off, fake, and OpenAI. Off remains the
  default.
- Upload and path job requests carry `use_llm` and `llm_provider` only through
  the local backend; old clients that omit the fields still run without L4.
- Path job manifests and runtime summaries record the chosen L4 mode.
- Dashboard/report artifact behavior remains generated-artifact-only; no raw
  CSV fetch or JavaScript profiler execution is introduced.

## Design Notes

- Commands: existing `vsf-profiler web`, `vsf-profiler run`, `make demo-small`,
  and optional `make demo-olist`.
- API: additive `use_llm` boolean and `llm_provider` string on `/api/jobs` and
  `/api/path-jobs`.
- UI surfaces: runner panel preset segmented control and L4 report segmented
  control.
- Domain rules: L4 generation remains optional and guarded; fake provider is
  local-only validation, OpenAI uses existing local `.env`/environment config.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-071 --unit 1 --integration 1 --e2e 1 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest -q tests/test_web_ui_static.py tests/test_web_runner.py` |
| Integration | `make demo-small`, `git diff --check` |
| E2E | `VSF_E2E_PORT=8766 npm run test:e2e:dashboard` |
| Platform | `ruff check src/vsf_profiler/web_runner.py tests/test_web_runner.py`, `node --check web/app.js tests/e2e/web-dashboard.spec.js` |
| Release | Story verify after proof commands pass. |

## Harness Delta

No harness policy changes.

## Evidence

- Focused backend/static proof:
  `PATH="$PWD/.venv/bin:$PATH" pytest -q tests/test_web_ui_static.py tests/test_web_runner.py`
  -> 16 passed.
- Full suite:
  `PATH="$PWD/.venv/bin:$PATH" pytest -q` -> 100 passed, 3 skipped.
- JavaScript syntax:
  `node --check web/app.js` and
  `node --check tests/e2e/web-dashboard.spec.js` -> passed.
- Python style:
  `PATH="$PWD/.venv/bin:$PATH" ruff check src/vsf_profiler/web_runner.py tests/test_web_runner.py`
  -> passed.
- Whitespace:
  `git diff --check` -> passed.
- Demo:
  `PATH="$PWD/.venv/bin:$PATH" make demo-small` -> passed with 15 issues.
- Playwright visual/state proof:
  `VSF_E2E_PORT=8766 PATH="$PWD/.venv/bin:$PATH" npm run test:e2e:dashboard`
  -> 1 passed. The E2E clicks Full Olist, verifies Olist paths and 9/9
  mapped tables, toggles fake L4 mode, returns to LLM off, then runs the small
  deterministic path job and loads the dashboard from generated artifacts.
