# Design

## Domain Model

New benchmark support adds:

- `BenchmarkDataset`: generated DBML, rules, CSV directory, table row counts,
  total rows, deterministic seed, and generator settings.
- `PerformanceGuardReport`: benchmark output with run status, stage timings,
  peak RSS memory, artifact sizes, package/audit status, materialization guard
  scan results, and influence limit evidence.

The benchmark report is a benchmark artifact, not a new deterministic profiler
artifact required from every normal `vsf-profiler run`.

## Application Flow

1. Generate deterministic relational CSVs and matching DBML/rules into a
   benchmark work directory.
2. Run the existing `run_pipeline()` against the generated local CSV directory.
3. Pass explicit influence analysis row and feature limits to the pipeline.
4. Read `run_summary.json`, `run_events.jsonl`, `profile_summary.json`, and
   `influence.json`.
5. Create an export package and zip through `create_analysis_package()`.
6. Run the existing artifact audit against the run/package/zip.
7. Scan source files for forbidden production `pandas.read_csv` and unguarded
   `.fetchdf()` usage.
8. Write `performance_guard_report.json` under the profiler output directory.

## Interface Contract

New script:

```bash
python scripts/benchmark_large_dataset.py \
  --work-dir outputs/benchmark_ci \
  --rows 600 \
  --tables 7 \
  --max-analysis-rows 120 \
  --max-feature-columns 4 \
  --force
```

Optional larger local run:

```bash
python scripts/benchmark_large_dataset.py \
  --work-dir outputs/benchmark_large \
  --rows 50000 \
  --tables 8 \
  --max-analysis-rows 5000 \
  --max-feature-columns 10 \
  --force
```

New make targets:

```bash
make benchmark-small
make benchmark-large
```

`performance_guard_report.json` uses `status: passed | failed` and includes
violations when limits, package generation, artifact audit, or materialization
guards fail.

## Data Model

No durable application data model changes. Generated benchmark data lives under
the selected work directory and can be deleted safely.

## UI / Platform Impact

No browser UI changes. The benchmark validates existing report, chart, package,
and artifact outputs.

## Observability

The benchmark report records:

- total and per-table generated rows;
- run wall time and stage timings from `run_summary.json`;
- run event count from `run_events.jsonl`;
- peak RSS memory when the platform supports it;
- generated artifact sizes;
- influence row and feature limit configuration plus observed result notes;
- chart/report/package/audit success flags;
- materialization guard scan results.

## Alternatives Considered

1. Add a hosted benchmark dashboard. Rejected because the story is local proof,
   not SaaS observability.
2. Add a second profiling engine for benchmarks. Rejected because benchmark
   proof must exercise the existing Python/DuckDB pipeline.
3. Make `performance_guard_report.json` a required artifact for every profiler
   run. Rejected to keep normal run contracts backward-compatible.
