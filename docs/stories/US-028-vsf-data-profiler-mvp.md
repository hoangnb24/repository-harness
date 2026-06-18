# US-028 VSF Data Profiler MVP

## Status

implemented

## Lane

normal

## Product Contract

Build the first runnable VSF Data Profiler CLI that ingests DBML plus CSV files,
profiles the dataset, detects schema/data/relationship issues, performs
association-based influence analysis, and writes JSON plus Markdown/HTML
reports.

## Relevant Product Docs

- `docs/product/vsf-data-profiler.md`

## Acceptance Criteria

- `pip install -e ".[dev]"` installs the CLI and test dependencies.
- `make demo-small` creates the synthetic demo and writes all required output
  artifacts under `outputs/demo_small/`.
- `outputs/demo_small/issues.json` includes the required injected issue types.
- `outputs/demo_small/schema_diagram.json` and `schema_diagram.dbml` exist and
  include DBML table, PK/FK, relationship, dbdiagram link, and CSV mapping data.
- Every issue includes table, columns, bad_count, severity, suggested_fix, and
  evidence_sql.
- Production code does not call `pandas.read_csv` on full CSV files without a
  sample, limit, or chunking guard.
- `pytest -q` passes.

## Design Notes

- Commands: Typer CLI entrypoint `vsf-profiler`.
- Queries: DuckDB reads CSV files directly with `read_csv_auto`.
- API: internal Python modules under `src/vsf_profiler`.
- Tables: input tables are CSV files mapped by file stem.
- Domain rules: DBML constraints and optional YAML rules produce normalized
  issue catalog entries.
- UI surfaces: CLI and static reports only.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Parser, rule, relationship, and demo tests through `pytest -q`. |
| Integration | `make demo-small` runs end-to-end and writes required artifacts. |
| E2E | Not applicable; no browser workflow in MVP. |
| Platform | Local Python 3.11+ CLI install via editable package. |
| Release | Not applicable for MVP. |

## Harness Delta

The prebuilt `scripts/bin/harness-cli` binary is absent and `cargo` is not
available, so durable intake/story/trace rows cannot be written in this
environment. This story file and the product doc carry the local evidence
fallback.

## Evidence

- `.venv/bin/ruff check src tests` -> passed.
- `.venv/bin/pytest -q` -> `10 passed`.
- `PATH="/Users/jin/repository-harness/.venv/bin:$PATH" make demo-small` -> wrote
  `outputs/demo_small/report.html` and found 15 issues.
- Generated issue types include `DUPLICATE_PRIMARY_KEY`, `ORPHAN_FOREIGN_KEY`,
  `VALUE_OUT_OF_RANGE`, `NEGATIVE_VALUE_NOT_ALLOWED`, `DATE_ORDER_INVALID`, and
  `REQUIRED_FIELD_NULL`.
- Clean environment setup with `python` failed on this macOS environment because
  no system `python` alias exists. Clean setup with `python3 -m venv .venv`,
  editable install, and `make demo-small` passed.
- Report HTML opened with macOS `open`; static HTML checklist confirmed title,
  dataset overview, table/column/row metrics, DBML diagram section, CSV mapping,
  PK/FK relationship display, top issues, issue metadata, suggested fixes,
  influence analysis, association-not-causation wording, and sample links.
- `make download-olist` downloaded the public Olist dataset in this environment.
- `make demo-olist` passed after real-world CSV compatibility fixes; it scanned
  9 tables, generated relationship issues, produced review-score influence
  features, and wrote `outputs/olist_demo/report.html`.
- DBML diagram feature validated in `make demo-small`: generated
  `schema_diagram.dbml`, `schema_diagram.json`, a dbdiagram.io embed link,
  CSV-to-table mapping, 7 mapped synthetic tables, and 6 relationships.
- DBML diagram feature validated in `make demo-olist`: generated a dbdiagram.io
  link of 3733 characters, mapped 9 Olist tables, and listed 7 relationships.
- Static web UI prototype added under `web/` for local DBML upload, multi-CSV
  upload, CSV-to-table linking, PK/FK review, and dbdiagram.io preview.
