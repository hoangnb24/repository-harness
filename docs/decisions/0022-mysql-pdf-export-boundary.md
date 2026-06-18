# 0022 MySQL Connector and Package PDF Export Boundary

Date: 2026-06-16

## Status

Accepted

## Context

VSF Data Profiler already adapts Postgres tables into the existing
Python/DuckDB pipeline through `TabularSourceConnector`, and already packages
completed runs into offline bundles. US-052 needs MySQL/MariaDB support and PDF
export without creating a second profiling engine, leaking secrets, or changing
normal deterministic run artifacts.

## Decision

Add both capabilities as additive adapters:

- implement MySQL/MariaDB as a `TabularSourceConnector` using optional PyMySQL;
- stream selected database rows in bounded chunks into temporary local CSV
  extracts that DuckDB can scan;
- generate the same `connector_metadata.json`, schema parse report, lineage,
  report, dashboard, and cleanup behavior as existing connector runs;
- add `vsf-profiler package --pdf` as a package-only operation that renders
  `analysis_report.pdf` from existing package/report artifacts;
- include PDF checksum/generator/backend/redaction metadata in
  `export_manifest.json`;
- keep normal `vsf-profiler run` artifact names and package behavior
  backward-compatible unless `--pdf` is requested.

## Alternatives Considered

1. Build a MySQL-specific profiling path. Rejected because it would duplicate
   core behavior and weaken existing DuckDB/materialization guarantees.
2. Require a heavyweight PDF dependency. Rejected because the package flow must
   stay local/offline and optional; a simple deterministic PDF backend is enough
   for report handoff.
3. Generate PDF during every profiler run. Rejected because US-052 asks for
   optional package export and existing deterministic run artifacts should not
   change.

## Consequences

Positive:

- MySQL/MariaDB gets the same connector metadata, lineage, reporting, and
  cleanup guarantees as Postgres.
- PDF export is inspectable through the package manifest and audit.
- Existing CSV, Postgres, web, benchmark, and LLM paths remain additive.

Tradeoffs:

- The built-in PDF is intentionally simple and text-first.
- Live MySQL proof depends on local `VSF_MYSQL_TEST_URL`; otherwise the smoke
  skips explicitly.

## Verification

```text
.venv/bin/pytest -q tests/test_mysql_connector.py tests/test_mysql_acceptance.py tests/test_export_package.py tests/test_doctor_and_artifact_audit.py
.venv/bin/pytest -q
.venv/bin/ruff check src tests scripts/verify_openai_smoke.py scripts/verify_vsf_artifacts.py scripts/benchmark_large_dataset.py
node --check web/app.js
make demo-full
make benchmark-small
make mysql-smoke
```
