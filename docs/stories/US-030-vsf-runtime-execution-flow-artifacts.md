# US-030 VSF Runtime Execution Flow Artifacts

## Status

implemented

## Lane

normal

## Product Contract

Every VSF Data Profiler CLI run writes reusable runtime execution artifacts:
`run.log`, `run_events.jsonl`, and `run_summary.json`. Reports include an
Execution Flow section based on the same stage metadata.

## Relevant Product Docs

- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`

## Acceptance Criteria

- A successful CLI profiling run writes `run.log`, `run_events.jsonl`, and
  `run_summary.json` without removing or renaming existing artifacts.
- `run_summary.json` includes run status, input paths, output paths, stage
  timings, issue counts, artifact paths, and skipped or failed stage details
  when applicable.
- `run_events.jsonl` includes ordered `run_started`, `stage_started`,
  `stage_finished` or `stage_failed`, `artifact_written`, and `run_finished` or
  `run_failed` events.
- Markdown and HTML reports include an Execution Flow section.
- Runtime logs do not include full raw rows, secrets, credentials, or unbounded
  sample values.

## Design Notes

- Commands: `vsf-profiler run`, `make demo-small`.
- Queries: unchanged DuckDB-based profiling pipeline.
- API: reusable runtime support under `src/vsf_profiler/runtime.py`.
- Tables: no data model changes.
- Domain rules: runtime events record bounded metadata only.
- UI surfaces: static Markdown and HTML reports.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Runtime artifact contract tests over demo fixtures. |
| Integration | `make demo-small` writes runtime artifacts and report sections. |
| E2E | Not applicable; no browser workflow change. |
| Platform | CLI run from installed entrypoint writes artifacts to disk. |
| Release | Not applicable. |

## Harness Delta

No harness behavior changes are expected.

## Evidence

- `.venv/bin/pytest -q tests/test_demo_small.py tests/test_schema_validation.py` -> `7 passed`.
- `.venv/bin/pytest -q` -> `13 passed`.
- `.venv/bin/ruff check src tests` -> passed.
- `PATH="/Users/jin/repository-harness/.venv/bin:$PATH" make demo-small` -> wrote
  `outputs/demo_small/report.html` and found 15 issues.
- `outputs/demo_small/` contains existing JSON/report artifacts plus `run.log`,
  `run_events.jsonl`, and `run_summary.json`.
- `outputs/demo_small/run_summary.json` records `status=success`, input paths,
  output directory, 15 total issues, issue counts by severity/type, artifact
  paths, completed stage timings, and no failed/skipped stages for the targeted
  demo run.
- `outputs/demo_small/run_events.jsonl` starts with `run_started`, ends with
  `run_finished`, has ordered sequences, and includes `stage_started`,
  `stage_finished`, and `artifact_written` events.
- `outputs/demo_small/report.md` and `outputs/demo_small/report.html` include
  an Execution Flow section.
- Tests also cover no-target skipped influence metadata and a failure path that
  writes `run.log`, `run_events.jsonl`, and failed `run_summary.json` without
  masking the original `FileNotFoundError`.
