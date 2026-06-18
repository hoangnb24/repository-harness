# Validation

## Proof Strategy

Use parser unit fixtures for grammar coverage and diagnostics, integration
tests for pipeline artifact generation/report links, and demo/web tests for
backward compatibility.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Current demo DBML, realistic DBML constructs, malformed DBML, unsupported nonfatal constructs, quoted/schema-qualified identifiers, composite primary/unique indexes, inline refs, and `Ref` blocks. |
| Integration | `run_pipeline` writes `schema_parse_report.json`, runtime registers it, reports link it, and canonical artifacts keep existing names. |
| E2E | Web runner upload/path jobs expose `schema_parse_report.json` in artifact URLs/dashboard sources. |
| Platform | `make demo-small` remains local and offline. |
| Performance | Parser remains metadata-only and does not read CSV contents. |
| Logs/Audit | Runtime parse stage reports diagnostic and unsupported construct counts. |

## Fixtures

- `data/demo_small/schema.dbml`
- Realistic DBML fixture embedded in parser tests.
- Malformed DBML fixture with unclosed blocks or invalid relationship
  endpoints.
- Unsupported-but-nonfatal fixture with DBML constructs outside profiler
  semantics.

## Commands

```text
.venv/bin/pytest -q tests/test_dbml_parser.py tests/test_schema_artifacts.py tests/test_demo_small.py tests/test_web_runner.py tests/test_web_ui_static.py
.venv/bin/pytest -q
.venv/bin/ruff check src tests scripts/verify_openai_smoke.py
node --check web/app.js
make demo-small
scripts/bin/harness-cli story verify US-044
scripts/bin/harness-cli audit
```

## Acceptance Evidence

- `.venv/bin/pytest -q tests/test_dbml_parser.py tests/test_schema_artifacts.py tests/test_demo_small.py tests/test_web_runner.py tests/test_web_ui_static.py` -> 22 passed.
- `.venv/bin/pytest -q` -> 46 passed.
- `.venv/bin/ruff check src tests scripts/verify_openai_smoke.py` -> all checks passed.
- `node --check web/app.js` -> passed.
- `make demo-small` -> passed with 15 issues and existing deterministic artifact names preserved.
- Demo `outputs/demo_small/schema_parse_report.json` was generated with `status=parsed`, `tables=7`, `columns=27`, `relationships=6`, `warnings=0`, and `unsupported=0`.
- Demo `report.md` and `report.html` both link `schema_parse_report.json` and include Schema Parse Diagnostics.
- Parser unit coverage includes current inline/composite refs, realistic `Project`/`Enum`/`TableGroup`/quoted/schema-qualified/index/default/note syntax, unsupported nonfatal constructs, native many-to-many reporting, and malformed unclosed table failure.
- Web-runner backend tests prove upload/path jobs expose `schema_parse_report.json` through canonical artifact listings and dashboard artifact URLs.
- `scripts/bin/harness-cli story verify US-044` -> passed.
- `scripts/bin/harness-cli decision verify 0014` -> passed.
