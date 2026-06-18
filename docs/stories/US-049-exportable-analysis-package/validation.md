# Validation

## Proof Strategy

Use deterministic demo and synthetic package fixtures to verify the command
copies only allowed artifacts, writes stable checksums, renders offline index
links, excludes raw source data, detects secret leaks, and can produce a
deterministic zip archive.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | File discovery, checksums, raw CSV exclusion, secret scan, manifest fields. |
| Integration | Run demo pipeline then package output directory through API and CLI command. |
| E2E | Not required; package index is static and does not use the web runner. |
| Platform | Zip archive uses sorted entries and fixed timestamps for deterministic output. |
| Performance | Package command streams/copies files and does not load raw source dataframes. |
| Logs/Audit | Manifest redaction status passes; tests inject a secret marker and expect failure. |

## Fixtures

- `create_small_demo()` generated DBML/CSV/rules.
- `run_pipeline()` demo output directory.
- A synthetic raw CSV file beside generated artifacts to prove exclusion.
- A synthetic secret-bearing artifact to prove package rejection.

## Commands

```text
.venv/bin/pytest -q tests/test_export_package.py tests/test_demo_small.py
.venv/bin/pytest -q
.venv/bin/ruff check src tests scripts/verify_openai_smoke.py
node --check web/app.js
make demo-small
scripts/bin/harness-cli story verify US-049
scripts/bin/harness-cli decision verify 0019
scripts/bin/harness-cli audit
```

## Acceptance Evidence

- `.venv/bin/pytest -q tests/test_export_package.py tests/test_demo_small.py` -> 8 passed.
- `.venv/bin/pytest -q` -> 58 passed, 2 skipped.
- `.venv/bin/ruff check src tests scripts/verify_openai_smoke.py` -> passed.
- `node --check web/app.js` -> passed.
- `npm run test:e2e:dashboard` -> 1 passed.
- `make demo-small` -> passed and wrote `outputs/demo_small/report.html` with 15 issues.
- `vsf-profiler package --input outputs/demo_small --output outputs/demo_small_package --zip` -> wrote package directory, `export_manifest.json`, `index.html`, and `outputs/demo_small_package.zip`.
- Manifest inspection for the demo package:
  - `artifact=export_manifest`;
  - `redaction.status=passed`;
  - 38 manifest-listed package files plus zip archive containing the manifest;
  - required report, verdict, schema, relationship, lineage, chart, and runtime artifacts present;
  - 15 bounded `samples/*.csv` files included;
  - no raw CSV outside `samples/` included in package directory or zip.
- `make postgres-smoke` -> clean skip without `VSF_POSTGRES_TEST_URL`.
- `scripts/bin/harness-cli story verify US-049` -> pass.
- `scripts/bin/harness-cli decision verify 0019` -> pass.
