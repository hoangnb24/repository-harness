# Overview

## Current Behavior

VSF Data Profiler supports CSV inputs, local path/web upload modes, and an
optional Postgres connector that adapts selected database tables into the
existing DuckDB profiling pipeline. Export packages can include generated run
artifacts, bounded samples, a static index, a manifest, and an optional zip, but
not a PDF report.

## Target Behavior

US-052 adds two additive capabilities:

- optional MySQL/MariaDB connector mode using the existing
  `TabularSourceConnector` boundary and `run_pipeline()`;
- optional `vsf-profiler package --pdf` export that renders
  `analysis_report.pdf` from existing report/package artifacts without rerunning
  profiling.

Normal CSV, Postgres, web runner, dashboard, lineage, benchmark, LLM, and
deterministic artifact behavior remains backward-compatible.

## Affected Users

- Local users profiling MySQL/MariaDB tables without a manual CSV export.
- Reviewers who need a portable PDF alongside the offline package.
- Maintainers auditing connector redaction and package boundaries.

## Affected Product Docs

- `README.md`
- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`
- `docs/releases/v0.2-rc.md`
- `docs/TEST_MATRIX.md`

## Non-Goals

- No hosted database connector service.
- No production database mutations outside disposable smoke-test fixtures.
- No replacement profiling engine.
- No raw CSV or connector temporary extract inclusion in packages.
- No frontend PDF rendering pipeline or external CDN dependency.
