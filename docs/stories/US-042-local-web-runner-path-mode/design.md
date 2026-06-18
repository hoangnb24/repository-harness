# Design

## Domain Model

Path-mode jobs reuse the existing `WebRunJob` model and add an `input_mode`
field:

- `upload`: browser-uploaded files copied under the job input directory.
- `path`: browser-entered local paths validated by the backend and passed
  directly to `run_pipeline()`.

The job output contract remains `outputs/web_runs/<job_id>/artifacts`.
Generated artifacts are still the source of truth.

## Application Flow

1. User starts `vsf-profiler web`.
2. Browser switches to Local path mode and submits JSON with `dbml_path`,
   `csv_dir`, optional `rules_path`, and optional `target`.
3. Backend validates:
   - DBML path exists, is a file, and has `.dbml` extension.
   - CSV path exists, is a directory, and contains at least one `.csv` file.
   - Rules path, when present, exists, is a file, and has `.yaml` or `.yml`
     extension.
   - Target, when present, has `table.column` shape.
4. Backend creates a job output directory without copying CSV contents.
5. Backend starts the same background worker used by upload mode and calls
   `run_pipeline()`.
6. Browser subscribes to the existing SSE event endpoint and renders artifacts
   from the existing job payload.

## Interface Contract

Existing upload endpoint remains unchanged:

- `POST /api/jobs` with multipart form data.

New path endpoint:

- `POST /api/path-jobs` with JSON body:

```json
{
  "dbml_path": "data/demo_small/schema.dbml",
  "csv_dir": "data/demo_small/csv",
  "rules_path": "data/demo_small/rules.yaml",
  "target": "order_reviews.review_score"
}
```

Successful response is the same job payload as upload mode and uses the same
artifact/event URLs:

- `GET /api/jobs/<job_id>`
- `GET /api/jobs/<job_id>/events`
- `GET /api/jobs/<job_id>/artifacts`
- `GET /api/jobs/<job_id>/artifacts/<artifact_path>`

Validation failures return HTTP 400 with `{ "error": "..." }`.

Artifact serving continues to reject paths outside the job output directory.

## Data Model

No database schema changes. Path-mode jobs may write a small path manifest under
the ignored job input directory, but CSV contents are not copied.

## UI / Platform Impact

The runner panel becomes two explicit modes:

- Upload mode for browser-selected demo/small-medium files.
- Local path mode for paths visible to the local Python process.

Both modes keep runtime stages and artifact lists in the same panel.

## Observability

Runtime observability remains `run_events.jsonl`, `run_summary.json`, job
payload status, and generated report links. Path-mode validation errors are
returned before a job starts.

## Alternatives Considered

1. Overload `POST /api/jobs` for multipart and JSON. Rejected to keep the upload
   contract stable and path mode explicit.
2. Browser directory picker APIs. Rejected because this local runner only needs
   plain text paths and should avoid browser filesystem permissions.
3. Copy local path CSVs into the job directory. Rejected because path mode exists
   to avoid moving CSV bytes through the browser or duplicate storage.
