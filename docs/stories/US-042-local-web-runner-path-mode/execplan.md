# Exec Plan

## Goal

Add Local path mode to the VSF Data Profiler web runner so browser users can
start full Python/DuckDB pipeline jobs from local DBML, CSV directory, and
optional rules paths without uploading CSV contents through the browser.

## Scope

In scope:

- Backend path job API that validates local paths before starting.
- Path-mode execution through the existing `run_pipeline()`.
- Existing upload-mode behavior preserved.
- Shared runtime progress and artifact rendering for upload and path jobs.
- Static UI mode switch with plain text path inputs.
- Tests for success, validation failures, path traversal protection, and static
  UI behavior.
- Product docs, story packet, durable decision, and matrix update.

Out of scope:

- Hosted runner or non-local bind addresses.
- Directory picker APIs or browser filesystem permissions.
- New profiling engine or JavaScript port.
- New LLM behavior.
- Artifact contract changes.

## Risk Classification

Risk flags:

- Audit/security.
- Public contracts.
- Existing behavior.
- Cross-platform.
- Weak proof.

Hard gates:

- Server must remain bound to `127.0.0.1`.
- Path mode must call `run_pipeline()`.
- Upload mode must remain available.
- Artifact serving must stay confined to job output directories.
- Path validation must happen before the job starts.

## Work Phases

1. Discovery and Harness intake.
2. Story and decision record.
3. Backend tests for path jobs and validation failures.
4. Backend implementation.
5. UI mode controls and static assertions.
6. Focused tests and smoke runs.
7. Full validation and Harness trace.

## Stop Conditions

Pause for human confirmation if:

- Path mode requires binding anywhere other than `127.0.0.1`.
- A separate profiling engine is needed.
- Browser filesystem permissions are required.
- Existing artifact names or CLI behavior need to change.
- Required validation conflicts with legitimate demo paths.
