# Execution Plan

1. Add MySQL/MariaDB connector constants, table refs, URL/table parsing, schema
   introspection, chunked extraction, schema report generation, and redaction.
2. Wire CLI options for `--mysql-url`, `--mysql-url-env`, `--mysql-schema`,
   `--mysql-tables`, and `--mysql-chunk-rows`, mutually exclusive with
   Postgres.
3. Add optional `mysql` dependency extra and `make mysql-smoke`.
4. Add package PDF generation, manifest metadata, package index link, CLI flag,
   and audit validation.
5. Extend doctor output for MySQL readiness and the local PDF backend.
6. Add fake-provider/unit tests, live MySQL skip/pass smoke, package PDF tests,
   and audit tests.
7. Update docs, release notes, test matrix, story, and decision records.
8. Run focused, full, demo, benchmark, smoke, Harness verify, and audit proof.
