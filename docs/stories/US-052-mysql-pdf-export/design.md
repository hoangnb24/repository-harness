# Design

## Connector Boundary

MySQL/MariaDB is implemented as another `TabularSourceConnector`. It mirrors the
Postgres connector contract:

- CLI/env config produces a connector instance.
- DBML can be supplied by the user; otherwise the connector introspects
  table/column/key/FK metadata and generates `schema_parse_report.json`.
- Selected rows are streamed in chunks through the Python database driver into
  temporary DuckDB-readable CSV extracts.
- The core profiler still scans through DuckDB and writes the existing
  deterministic artifacts.
- Temporary extracts live under `.connector_extracts/mysql` and are removed in
  `run_pipeline()` cleanup.
- Connector metadata is additive and redacted through `connector_metadata.json`.

The optional dependency is `pymysql` under the `mysql` extra. Unit tests use a
fake connector and do not require PyMySQL. The live acceptance smoke only runs
when `VSF_MYSQL_TEST_URL` and the optional dependency are available.

## PDF Boundary

PDF export is package-only. `vsf-profiler package --pdf` renders
`analysis_report.pdf` from the already-copied Markdown report in the package
directory. Profiling is not rerun, and normal run output directories do not
gain a PDF artifact.

The PDF writer is local and dependency-free. It emits an uncompressed PDF so the
existing redaction scan can inspect its text. The package manifest records:

- path;
- SHA-256 checksum;
- generator;
- backend;
- creation timestamp;
- redaction status.

The artifact audit validates the PDF manifest entry and zip inclusion when the
manifest declares that a PDF was created.

## Security and Data Boundary

- Browser dashboard behavior remains artifact-only and does not read raw CSV.
- Connector temp extracts are not package artifacts and are deleted after runs.
- Connection URLs, passwords, tokens, and API keys are redacted in runtime,
  lineage, report, package, and audit surfaces.
- The PDF is generated from existing report artifacts, not from source CSVs or
  unbounded database samples.
