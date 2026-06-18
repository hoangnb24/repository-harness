# 0021 Large Benchmark Guardrail Boundary

Date: 2026-06-16

## Status

Accepted

## Context

VSF Data Profiler already has architectural and static-test evidence that CSV
profiling uses DuckDB and only materializes bounded analysis frames into
pandas. The next release-hardening gap is executable evidence on larger
multi-table data: row counts, runtime stages, memory, artifact sizes, and
guardrail status should be captured in a repeatable benchmark report.

## Decision

Add a local benchmark boundary rather than a second profiler:

- generate deterministic relational CSV/DBML/rules fixtures locally;
- run the existing `run_pipeline()` with explicit influence limits;
- package and audit the generated output through existing package/audit code;
- write `performance_guard_report.json` as benchmark output;
- keep normal profiler artifact names and required artifact contracts
  unchanged.

The benchmark report can be written next to profiler outputs, but normal
`vsf-profiler run` does not need to produce it. This keeps the benchmark proof
additive while preserving existing demo/report/package behavior.

## Alternatives Considered

1. Add Spark/Dask/Ray benchmark modes. Rejected because the current architecture
   is DuckDB-local and the story is proof of that boundary.
2. Enforce a universal wall-clock or memory SLA. Rejected because results vary
   by machine; the benchmark records facts and conservative guard status rather
   than a cross-machine promise.
3. Require every profiler run to write `performance_guard_report.json`.
   Rejected because benchmark evidence should not alter normal deterministic
   output contracts.

## Consequences

Positive:

- Large-data claims become inspectable through a generated report.
- CI-safe benchmark can run quickly while local users can scale rows upward.
- Existing pipeline/package/audit code paths are exercised instead of mocked.

Tradeoffs:

- The benchmark report is environment-specific, so it should be compared as
  evidence, not as a strict golden file.
- Peak RSS support depends on platform APIs.

## Follow-Up

- Add larger optional benchmark baselines after v0.2 RC stabilizes.

## Verification

```text
.venv/bin/pytest -q tests/test_large_benchmark.py tests/test_memory_guards.py tests/test_export_package.py tests/test_demo_small.py
.venv/bin/python scripts/benchmark_large_dataset.py --work-dir outputs/benchmark_ci --rows 600 --tables 7 --max-analysis-rows 120 --max-feature-columns 4 --force
make demo-full
```
