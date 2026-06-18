# US-069 Schema-Aware CSV Auto-Mapping

## Status

implemented

## Lane

normal

## Product Contract

VSF Data Profiler maps CSV files to DBML tables by exact filename stem first,
then by conservative schema/header evidence when exact matching is unavailable.
The backend owns the real mapping logic for CLI, local web upload jobs, and
local path jobs. Manual mapping overrides can force table-to-CSV choices.
Ambiguous inferred matches remain unmapped and visible with candidate evidence.

## Relevant Product Docs

- `README.md`
- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`
- `docs/demo/vsf-data-profiler.md`

## Acceptance Criteria

- Exact filename behavior is preserved: table `customers` still maps to
  `customers.csv`.
- Each DBML table receives mapping candidates from available CSVs with filename,
  column overlap, primary-key match, foreign-key match, and extra-column
  penalty evidence.
- Non-exact CSVs auto-select only when confidence is high and the top candidate
  is clearly better than the next candidate.
- Ambiguous non-exact matches remain unmapped and expose candidates in
  `schema_evaluation.json`.
- Manual override mapping files work through CLI/backend and local web runner
  upload/path jobs.
- `schema_evaluation.json`, `schema_diagram.json`, reports, and dashboard
  preflight states show exact, inferred, manual, missing, and extra CSV states.
- Existing artifact filenames and DuckDB profiling behavior remain unchanged.
- No AI/LLM, schema evolution, fuzzy column renaming, or automatic data repair
  is introduced.

## Design Notes

- Commands: add optional `--mapping` for `vsf-profiler run`.
- Queries: no database schema changes.
- API: local web runner accepts mapping overrides in upload form data and path
  JSON payloads.
- Tables: no persistent tables.
- Domain rules: backend catalog stores mapping method, confidence, candidates,
  selected CSV, matched/missing/extra columns, and ambiguity evidence.
- UI surfaces: browser preflight dropdown overrides are sent to backend runs.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-069 --unit 1 --integration 1 --e2e 1 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest -q tests/test_schema_artifacts.py tests/test_web_ui_static.py tests/test_demo_small.py` |
| Integration | Full pytest and manual override CLI/backend tests. |
| E2E | Local web runner upload/path mapping override tests and dashboard/static checks. |
| Platform | `node --check web/app.js`, Ruff, `make demo-small`, artifact verifier, and Harness audit. |
| Release | Not a release story. |

## Harness Delta

No Harness feature changes expected. The story, durable matrix record, decision,
and trace should capture the product behavior and validation proof.

## Evidence

- Focused suite: `PATH="$PWD/.venv/bin:$PATH" pytest -q tests/test_schema_artifacts.py tests/test_web_runner.py tests/test_web_ui_static.py tests/test_demo_small.py` -> 24 passed.
- Full pytest: `PATH="$PWD/.venv/bin:$PATH" pytest -q` -> 99 passed, 3 skipped.
- Ruff: `PATH="$PWD/.venv/bin:$PATH" ruff check src tests scripts/verify_openai_smoke.py scripts/benchmark_large_dataset.py scripts/verify_vsf_artifacts.py` -> passed.
- Node syntax: `node --check web/app.js` -> passed.
- Whitespace: `git diff --check` -> passed.
- Demo: `PATH="$PWD/.venv/bin:$PATH" make demo-small` -> passed with 15 issues.
- Artifact audit: `.venv/bin/python scripts/verify_vsf_artifacts.py --run-dir outputs/demo_small` -> passed with 0 violations.
- Demo exact-name preservation: `outputs/demo_small/schema_evaluation.json` reports `mapping_method_counts={"exact": 7}`.
- Harness: `scripts/bin/harness-cli story verify US-069` and `scripts/bin/harness-cli decision verify 0028` -> passed.
