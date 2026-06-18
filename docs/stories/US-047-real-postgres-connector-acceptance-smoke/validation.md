# Validation

## Proof Strategy

Use a live Postgres fixture when `VSF_POSTGRES_TEST_URL` is configured. In
environments without Postgres or a Harness-registered Docker/Postgres
capability, prove the skip path and keep the rest of the suite green.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Existing connector URL parsing, redaction, and introspection mapping remain covered. |
| Integration | Real Postgres smoke creates a disposable schema, runs introspection and DBML modes, verifies artifacts, issues, lineage, reports, cleanup, and redaction. |
| E2E | Web-runner artifact and dashboard payload discovery works against connector-produced artifacts. |
| Platform | `VSF_POSTGRES_TEST_URL` runs the smoke; unavailable Postgres/Docker produces an explicit skip. |
| Performance | Smoke uses `postgres_chunk_rows=2` with more than two rows to exercise chunked fetches. |
| Logs/Audit | No full URL, password, token, or secret-like string leaks into JSON, JSONL, log, Markdown, HTML, or dashboard payloads. |

## Fixtures

- Local Postgres database pointed to by `VSF_POSTGRES_TEST_URL`.
- Optional Docker command documented in README to start a disposable local
  Postgres container before setting `VSF_POSTGRES_TEST_URL`.

## Commands

```text
.venv/bin/pytest -q tests/test_postgres_acceptance.py
.venv/bin/pytest -q tests/test_postgres_acceptance.py tests/test_postgres_connector.py tests/test_demo_small.py tests/test_web_runner.py tests/test_web_ui_static.py
.venv/bin/pytest -q
.venv/bin/ruff check src tests scripts/verify_openai_smoke.py
node --check web/app.js
make postgres-smoke
make demo-small
scripts/bin/harness-cli story verify US-047
scripts/bin/harness-cli decision verify 0017
scripts/bin/harness-cli audit
```

## Acceptance Evidence

- Live disposable Homebrew Postgres cluster with
  `VSF_POSTGRES_TEST_URL=postgresql://postgres:us-047-secret@127.0.0.1:<port>/postgres`:
  `.venv/bin/pytest -q tests/test_postgres_acceptance.py -rs` -> 1 passed.
- Live disposable Homebrew Postgres cluster with the same secret-bearing URL:
  `make postgres-smoke` -> 1 passed.
- `.venv/bin/pytest -q tests/test_postgres_acceptance.py -rs` -> 1 skipped with an explicit message because `VSF_POSTGRES_TEST_URL` is not configured and no Harness-present Postgres/Docker fixture is wired for this run.
- `.venv/bin/pytest -q tests/test_postgres_acceptance.py tests/test_postgres_connector.py tests/test_demo_small.py tests/test_web_runner.py tests/test_web_ui_static.py -rs` -> 20 passed, 2 skipped.
- `.venv/bin/pytest -q` -> 53 passed, 2 skipped.
- `.venv/bin/ruff check src tests scripts/verify_openai_smoke.py` -> all checks passed.
- `node --check web/app.js` -> passed.
- `make demo-small` -> passed with 15 issues.
- `scripts/bin/harness-cli story verify US-047` -> passed through the explicit no-Postgres skip path.
- `scripts/bin/harness-cli decision verify 0017` -> passed through the explicit no-Postgres skip path.
