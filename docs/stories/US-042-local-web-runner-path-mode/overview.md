# Overview

## Current Behavior

The local web runner supports upload mode: browser-selected DBML, CSV, and
optional rules files are copied under `outputs/web_runs/<job_id>/input`, then a
background job calls the existing Python `run_pipeline()` and writes canonical
artifacts under `outputs/web_runs/<job_id>/artifacts`.

Upload mode is useful for demos and small-to-medium files, but it requires CSV
bytes to pass through the browser and the local HTTP request.

## Target Behavior

The web runner also offers Local path mode. Users type a DBML file path, CSV
directory path, optional rules file path, and optional target column in the
browser. The local `127.0.0.1` backend validates existence, type, extension, and
target shape, then starts a backend job that calls `run_pipeline()` directly
with those paths.

Generated artifacts, runtime streaming, and artifact URLs remain identical to
upload mode.

## Affected Users

- Local users profiling larger company-style CSV directories.
- Maintainers validating the web runner does not fork the Python pipeline.
- Demo users who still need upload mode to remain unchanged.

## Affected Product Docs

- `README.md`
- `docs/product/vsf-data-profiler.md`
- `docs/ARCHITECTURE.md`
- `docs/TEST_MATRIX.md`
- `docs/decisions/0012-local-path-mode-boundary.md`

## Non-Goals

- No hosted or network-accessible backend.
- No browser filesystem permission APIs or directory picker integration.
- No JavaScript profiling implementation.
- No CSV byte upload in path mode.
- No new LLM behavior.
- No artifact name or URL contract changes.
