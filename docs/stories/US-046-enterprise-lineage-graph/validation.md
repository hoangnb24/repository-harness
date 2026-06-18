# Validation

## Proof Strategy

Use unit/integration tests around the generated lineage artifact, then verify
the existing demo, connector, web-runner, and static UI paths still pass.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Lineage graph includes source/schema/table/column/relationship/stage/artifact nodes and typed dependency edges. |
| Integration | Demo CSV mode writes `lineage_graph.json`, report links it, and runtime summary registers it. Fake connector mode writes connector-source lineage without leaking secrets. |
| E2E | Web-runner artifact and dashboard payloads expose `lineage_graph.json`. |
| Platform | `make demo-small` still passes with existing artifact names plus additive lineage. |
| Performance | Lineage builder consumes bounded metadata artifacts only, not raw CSV files. |
| Logs/Audit | Connector URL/password/token values are redacted from lineage outputs. |

## Fixtures

- `data/demo_small/schema.dbml`
- Demo CSV files under `data/demo_small/csv`
- Fake connector from `tests/test_postgres_connector.py`

## Commands

```text
.venv/bin/pytest -q tests/test_lineage_graph.py tests/test_postgres_connector.py tests/test_demo_small.py tests/test_web_runner.py tests/test_web_ui_static.py
.venv/bin/pytest -q
.venv/bin/ruff check src tests scripts/verify_openai_smoke.py
node --check web/app.js
make demo-small
scripts/bin/harness-cli story verify US-046
scripts/bin/harness-cli decision verify 0016
scripts/bin/harness-cli audit
```

## Acceptance Evidence

- `.venv/bin/pytest -q tests/test_lineage_graph.py tests/test_postgres_connector.py tests/test_demo_small.py tests/test_web_runner.py tests/test_web_ui_static.py` -> 21 passed, 1 skipped.
- `.venv/bin/pytest -q` -> 53 passed, 1 skipped.
- `.venv/bin/ruff check src tests scripts/verify_openai_smoke.py` -> all checks passed.
- `node --check web/app.js` -> passed.
- `make demo-small` -> passed with 15 issues and additive `lineage_graph.json`.
- Demo lineage summary: 2 source systems, 7 tables, 27 columns, 6 relationships, 8 stages, 24 artifacts, 171 edges.
- Demo reports link `lineage_graph.json` in Markdown and HTML.
- Fake connector test writes connector-source lineage and verifies no raw connection URL or password leaks across JSON, JSONL, log, Markdown, and HTML outputs.
- `scripts/bin/harness-cli story verify US-046` -> passed.
- `scripts/bin/harness-cli decision verify 0016` -> passed.
