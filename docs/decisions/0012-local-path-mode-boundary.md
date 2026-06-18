# 0012 Local Path Mode Boundary

Date: 2026-06-15

## Status

Accepted

## Context

Upload mode lets the local web runner execute the existing Python pipeline, but
it sends CSV bytes through the browser request and stores a copied input set
under the job directory. Larger local datasets need a browser workflow that
does not upload CSV contents while preserving the local-first security posture
and canonical artifact contract.

## Decision

Add an explicit Local path mode to the `127.0.0.1` web runner. The browser
submits plain text local paths to a new JSON endpoint, `POST /api/path-jobs`.
The backend validates that the DBML file, CSV directory, optional rules file,
and optional target have acceptable shapes before creating a job.

Path-mode jobs call the existing `run_pipeline()` with the submitted local
paths and write outputs under `outputs/web_runs/<job_id>/artifacts`. They do
not copy CSV contents into the job input directory and do not add new LLM
behavior. Upload mode remains the demo/small-medium browser-file workflow.

Artifact serving remains constrained to each job output directory. Browser
submitted input paths are treated as local trusted-by-user paths for execution,
not as paths that may be served back through artifact URLs.

## Alternatives Considered

1. Extend upload mode with directory picker APIs. Rejected because it adds
   browser filesystem permissions and still does not improve the backend
   pipeline boundary.
2. Reuse `POST /api/jobs` for JSON path jobs. Rejected because a separate
   endpoint keeps upload mode and path mode explicit and easier to test.
3. Copy all path-mode CSV files into the job directory. Rejected because it
   duplicates large local data and defeats the reason for path mode.

## Consequences

Positive:

- Larger local datasets can be run from the browser without uploading CSV bytes.
- The web runner continues to use the canonical Python pipeline and artifacts.
- Upload and path modes have separate contracts and UI states.

Tradeoffs:

- Users must type paths that are valid from the local server process working
  directory.
- Path mode is local-only and not suitable for hosted deployment.

## Follow-Up

- Add job cleanup or retention controls if local path mode leads to many saved
  web-run artifacts.
