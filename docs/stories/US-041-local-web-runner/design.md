# Design

## Domain Model

The web runner introduces a local job concept:

- `job_id`: generated local id for an uploaded run.
- `status`: `queued`, `running`, `succeeded`, or `failed`.
- `input_dir`: ignored local directory containing uploaded DBML/CSV/rules.
- `out_dir`: ignored local directory containing canonical profiler artifacts.

The profiler artifacts remain the source of truth. Runtime stage display comes
from `run_events.jsonl` and `run_summary.json`.

## Application Flow

1. User opens `vsf-profiler web`.
2. Browser uploads DBML, CSV files, optional rules, and optional target.
3. Backend stores inputs under `outputs/web_runs/<job_id>/input`.
4. Backend starts a thread that calls `run_pipeline()`.
5. Browser subscribes to server-sent events sourced from `run_events.jsonl`.
6. Browser polls job metadata and artifact links.
7. Browser opens generated `report.html` or JSON artifacts from the local
   backend.

## Interface Contract

Commands:

- `vsf-profiler web --port 8765`

HTTP:

- `GET /api/health`
- `POST /api/jobs`
- `GET /api/jobs/<job_id>`
- `GET /api/jobs/<job_id>/events`
- `GET /api/jobs/<job_id>/artifacts`
- `GET /api/jobs/<job_id>/artifacts/<artifact_path>`

## Data Model

No database schema changes. Uploaded files and generated artifacts live under
ignored `outputs/web_runs/`.

## UI / Platform Impact

The existing web workspace gains a runner panel. Upload/preflight remains in
the browser, but full profiling is done by the local Python backend.

## Observability

Job progress is visible through:

- `run_events.jsonl`
- `run_summary.json`
- generated report links
- job error message if the pipeline fails

## Alternatives Considered

1. JavaScript profiling implementation. Rejected.
2. Network-accessible backend bind. Rejected.
3. Hosted job runner. Rejected for v0.1 local-first scope.
