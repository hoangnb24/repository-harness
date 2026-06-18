# Overview

## Current Behavior

VSF Data Profiler uses DuckDB scans and bounded dataframe materialization, and
tests already reject production `pandas.read_csv` and unguarded `.fetchdf()`
usage. The repo does not yet have a repeatable large-dataset benchmark artifact
that proves those constraints on a larger deterministic multi-table dataset.

## Target Behavior

The repo provides a repeatable large-dataset benchmark path:

- deterministic synthetic relational CSV generation configurable by rows and
  table count;
- a `scripts/benchmark_large_dataset.py` command for CI-safe and larger local
  runs;
- `performance_guard_report.json` with row counts, stage runtimes, peak RSS
  memory where supported, artifact sizes, influence row/feature limits,
  chart/report/package success, artifact audit status, and materialization
  guard scan results;
- docs explaining the small CI command and optional larger local command.

## Affected Users

- Maintainer validating release readiness on larger local data.
- Reviewer checking whether the streaming/DuckDB architecture claim has
  executable evidence.
- Agent continuing benchmark or performance-hardening work.

## Affected Product Docs

- `README.md`
- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`
- `docs/TEST_MATRIX.md`
- `docs/releases/v0.2-rc.md`

## Non-Goals

- No distributed compute.
- No Spark, Dask, or Ray integration.
- No hosted benchmark dashboard.
- No exact cross-machine SLA.
- No new database connector type.
