# Validation

## Proof Strategy

Use unit tests for connector SQL/redaction/metadata, integration tests for
pipeline artifact generation and CSV compatibility, and a local Postgres test
that skips cleanly when no fixture URL/capability exists.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | URL redaction, selected table parsing, introspected schema mapping, connector metadata shape. |
| Integration | CSV demo unchanged; Postgres fixture run writes existing artifacts plus `connector_metadata.json`; no secret leaks in runtime/report surfaces. |
| E2E | Web artifact listing/dashboard includes `connector_metadata.json` when present. |
| Platform | Local Postgres fixture runs when configured, otherwise clean skip. |
| Performance | Connector extraction uses chunked fetches and no pandas full-table load. |
| Logs/Audit | Connection URL/password/API-key style values are redacted. |

## Fixtures

- `data/demo_small/schema.dbml`
- `VSF_POSTGRES_TEST_URL` for optional local Postgres integration.
- Harness tool registry `postgres` capability when available.

## Commands

```text
.venv/bin/pytest -q tests/test_postgres_connector.py tests/test_demo_small.py tests/test_web_runner.py tests/test_web_ui_static.py
.venv/bin/pytest -q
.venv/bin/ruff check src tests scripts/verify_openai_smoke.py
node --check web/app.js
make demo-small
scripts/bin/harness-cli story verify US-045
scripts/bin/harness-cli audit
```

## Acceptance Evidence

- `.venv/bin/pytest -q tests/test_postgres_connector.py tests/test_demo_small.py tests/test_web_runner.py tests/test_web_ui_static.py` -> 20 passed, 1 skipped.
- `.venv/bin/pytest -q` -> 52 passed, 1 skipped.
- `.venv/bin/ruff check src tests scripts/verify_openai_smoke.py` -> all checks passed.
- `node --check web/app.js` -> passed.
- `make demo-small` -> passed with 15 issues and existing CSV artifacts unchanged.
- CSV smoke with `VSF_PROFILER_POSTGRES_URL` set still used CSV mode and did not write `connector_metadata.json`.
- Postgres fixture test skipped cleanly because `VSF_POSTGRES_TEST_URL` was not configured and Harness had no present `postgres` tool capability.
- Fake connector pipeline test wrote `connector_metadata.json`, linked it in reports, exposed it through web-runner artifact/dashboard payloads, removed temporary connector extracts, and verified no raw connection URL or password leaked in JSON, JSONL, log, Markdown, or HTML surfaces.
- CLI help includes `--postgres-url`, `--postgres-url-env`, `--postgres-schema`, `--postgres-tables`, and `--postgres-chunk-rows`.
- `scripts/bin/harness-cli story verify US-045` -> passed.
- `scripts/bin/harness-cli decision verify 0015` -> passed.
