# Validation

## Proof Strategy

Use fake connector tests for deterministic backend proof, static UI assertions
for markup/API wiring, Playwright for visual form behavior, and existing full
suite checks to prove CSV upload/path modes remain intact.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Database job validates source, URL, schema/table fields, target, L4 options, and redacts connection URLs. |
| Integration | Fake Postgres/MySQL connector jobs write canonical artifacts, connector metadata, generated DBML, runtime summary, and delete temporary extracts. |
| E2E | Local web UI exposes Database mode, preserves the shared L4 toggle, enables run button only when a connection URL is present, and does not clip labels. |
| Platform | Ruff, node syntax checks, `git diff --check`, localhost-only server behavior. |
| Logs/Audit | Secret markers absent from generated JSON, JSONL, logs, reports, HTML, and job payloads. |

## Fixtures

- Existing small demo CSV fixture for regression runs.
- Fake database connector classes in tests with deterministic table schemas and
  rows.
- Dummy local connection URLs with secret markers for redaction tests.

## Commands

```text
PATH="$PWD/.venv/bin:$PATH" pytest -q tests/test_web_runner.py tests/test_web_ui_static.py
PATH="$PWD/.venv/bin:$PATH" pytest -q
PATH="$PWD/.venv/bin:$PATH" ruff check src/vsf_profiler/web_runner.py tests/test_web_runner.py
node --check web/app.js
node --check tests/e2e/web-dashboard.spec.js
git diff --check
PATH="$PWD/.venv/bin:$PATH" make demo-small
VSF_E2E_PORT=8766 PATH="$PWD/.venv/bin:$PATH" npm run test:e2e:dashboard
scripts/bin/harness-cli story verify US-072
```

## Acceptance Evidence

- Focused backend/static proof:
  `PATH="$PWD/.venv/bin:$PATH" pytest -q tests/test_web_runner.py tests/test_web_ui_static.py`
  -> 19 passed.
- Full suite:
  `PATH="$PWD/.venv/bin:$PATH" pytest -q` -> 103 passed, 3 skipped.
- Python style:
  `PATH="$PWD/.venv/bin:$PATH" ruff check src/vsf_profiler/web_runner.py tests/test_web_runner.py`
  -> passed.
- JavaScript syntax:
  `node --check web/app.js` and
  `node --check tests/e2e/web-dashboard.spec.js` -> passed.
- Whitespace:
  `git diff --check` -> passed.
- Demo smoke:
  `PATH="$PWD/.venv/bin:$PATH" make demo-small` -> passed with 15 issues.
- Playwright visual/state proof:
  `VSF_E2E_PORT=8766 PATH="$PWD/.venv/bin:$PATH" npm run test:e2e:dashboard`
  -> 1 passed. Screenshots captured under `outputs/us072_database_mode/` for
  desktop and mobile Database mode forms.
- Story verification:
  `scripts/bin/harness-cli story verify US-072` -> pass.
