# US-052 Goal: MySQL/MariaDB Connector and PDF Export

## Objective

Add an optional MySQL/MariaDB connector and PDF export path while preserving the
existing CSV, Postgres, web dashboard, lineage, package, benchmark, and artifact
contracts.

## Context To Read First

- `README.md`
- `docs/HARNESS.md`
- `docs/ARCHITECTURE.md`
- `docs/product/vsf-data-profiler.md`
- `docs/releases/v0.2-rc.md`
- `docs/TEST_MATRIX.md`
- `src/vsf_profiler/connectors.py`
- `src/vsf_profiler/cli.py`
- `src/vsf_profiler/doctor.py`
- `src/vsf_profiler/export_package.py`
- `src/vsf_profiler/artifact_audit.py`
- `src/vsf_profiler/lineage_graph.py`
- `src/vsf_profiler/report_generator.py`
- `src/vsf_profiler/web_runner.py`
- `tests/test_postgres_connector.py`
- `tests/test_postgres_acceptance.py`
- `tests/test_export_package.py`
- `tests/test_doctor_and_artifact_audit.py`
- `tests/e2e/web-dashboard.spec.js`
- `scripts/bin/harness-cli query matrix`

## Scope

- Add a MySQL/MariaDB connector under the existing tabular connector abstraction.
- Use a portable optional dependency, preferably PyMySQL unless repo inspection
  shows a better fit.
- Add CLI options:
  - `--mysql-url`
  - `--mysql-url-env`
  - `--mysql-schema` or database name
  - `--mysql-tables`
  - `--mysql-chunk-rows`
- Support DBML-supplied mode.
- Support no-DBML mode by introspecting schema metadata from MySQL/MariaDB.
- Extract rows in chunks into temporary DuckDB-readable files, then clean them up.
- Generate `connector_metadata.json` using the existing source metadata shape.
- Extend `lineage_graph.json`, reports, dashboard artifact discovery, export
  package, artifact audit, and doctor output for MySQL metadata.
- Add real MySQL acceptance smoke using `VSF_MYSQL_TEST_URL` or Harness
  capability, with clean skip when unavailable.
- Add PDF export for completed analysis output/package:
  - package output should optionally include a PDF report, for example
    `analysis_report.pdf`.
  - CLI should expose a clear path such as
    `vsf-profiler package --input ... --output ... --pdf`.
  - PDF must be generated from existing report/package artifacts, not by
    re-running profiling.
  - PDF export must not include raw source CSV data except already allowed
    bounded samples.
  - PDF export must pass the same secret/redaction scan as HTML/package
    artifacts.
- Add PDF export metadata to `export_manifest.json`, including file path,
  checksum, generator/backend, created_at, and redaction status.

## Constraints

- Preserve all existing artifact names and behavior.
- Do not break CSV mode, Postgres mode, local web runner, dashboard, lineage
  graph, benchmark, or export package.
- Do not load full tables into pandas.
- Do not fetch raw CSV files in the browser dashboard.
- Do not print or persist database passwords, connection URLs, tokens, API keys,
  or secret-like query params.
- Keep PDF generation local/offline.
- If PDF backend dependencies are optional, `vsf-profiler doctor` must report
  availability without failing required checks.
- Real MySQL tests must clean-skip when no database URL/capability exists.

## Out Of Scope

- Snowflake, BigQuery, SQL Server, Oracle, or other connectors.
- Hosted deployment.
- Auth or multi-user backend.
- PDF editing.
- External lineage catalog publishing.
- Cross-database joins.
- Query builder UI.

## Operating Rules

- Implement in small vertical slices:
  1. MySQL connector boundary and redaction.
  2. MySQL introspection and chunked extraction.
  3. Artifact/report/dashboard/package/lineage integration.
  4. PDF export path and manifest/audit integration.
  5. Docs, Harness story, decision, test matrix, and trace.
- Keep additive artifacts additive.
- Reuse existing Postgres connector patterns where possible.
- Reuse existing package, artifact audit, and redaction logic for PDF.
- Do not expand scope without pausing.

## Validation Loop

During work:

- Run focused connector tests after MySQL connector changes.
- Run focused package/PDF tests after export changes.
- Run doctor/artifact audit tests after redaction or capability changes.
- Run node checks after web/dashboard changes.

Final proof:

- `.venv/bin/pytest -q`
- `.venv/bin/ruff check src tests scripts/verify_openai_smoke.py scripts/benchmark_large_dataset.py scripts/verify_vsf_artifacts.py`
- `node --check web/app.js`
- `npm run test:e2e:dashboard`
- `vsf-profiler doctor`
- `make demo-small`
- `make demo-full`
- `make benchmark-small`
- `make postgres-smoke`, passing or clean-skipping according to environment
- MySQL acceptance smoke, passing with `VSF_MYSQL_TEST_URL` or clean-skipping
  without it
- Package command with `--pdf` creates PDF, manifest entry, and passes artifact
  audit
- `scripts/bin/harness-cli story verify US-052`
- `scripts/bin/harness-cli decision verify <new-decision-id if created>`
- `scripts/bin/harness-cli audit`

## Done When

- Existing CSV demo remains unchanged and passes.
- Existing Postgres behavior remains unchanged.
- MySQL/MariaDB connector works through the same pipeline boundary as Postgres.
- MySQL fake/unit tests pass.
- Real MySQL acceptance passes when `VSF_MYSQL_TEST_URL` is available, otherwise
  clean-skips with an explicit message.
- `connector_metadata.json`, `lineage_graph.json`, reports, dashboard, export
  package, and artifact audit support MySQL source metadata.
- PDF export produces a valid PDF artifact from an existing run/package.
- `export_manifest.json` records PDF checksum and redaction status.
- No raw source CSV, temp extract, or secret leakage is found in logs, reports,
  package, PDF, dashboard payloads, lineage, or connector metadata.
- Full validation and Harness audit pass.

## Pause If

- PDF generation requires a heavyweight system dependency that is not already
  documented or cleanly optional.
- MySQL introspection needs behavior that conflicts with the current schema/DBML
  contract.
- Secret redaction cannot be proven for PDF contents.
- Adding PDF export would require changing existing artifact names.
- Real connector tests cannot clean up temporary extracts safely.
