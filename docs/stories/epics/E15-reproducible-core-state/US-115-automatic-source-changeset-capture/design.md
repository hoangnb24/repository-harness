# Design

## Domain Model

A changeset run ID identifies one CLI process's semantic mutations. Caller-
supplied IDs remain authoritative. Otherwise source tracked-state mode creates
a time-sortable ID from Unix nanoseconds, process ID, and a process-local
sequence.

Source tracked-state mode is true only when:

- the repository contains the Harness workspace and `crates/harness-cli`;
- the target is the repository's default `harness.db`; and
- no explicit `HARNESS_RUN_ID` was supplied.

## Application Flow

```text
construct repository
  -> explicit run id exists: reuse it
  -> else default source database: generate one invocation id
  -> else: keep changeset capture disabled

typed write
  -> begin SQLite immediate transaction
  -> create semantic operations
  -> append header and operations under the invocation id
  -> commit database transaction
  -> on commit failure, truncate/remove the appended bytes
```

## Interface Contract

No new command or required environment variable is added. Existing commands
and output remain stable. Changeset files retain the current header-plus-typed-
operation JSONL envelope.

## Data Model

No schema migration is required. The change affects changeset run identity and
file creation only.

## UI / Platform Impact

Run IDs use filesystem-safe ASCII on macOS, Linux, and Windows. Source detection
uses paths already recognized by both bootstrap implementations.

## Observability

The generated filename and `changeset.header.run_id` provide the durable
invocation identity. No extra task lifecycle record is introduced.

## Alternatives Considered

1. Require `HARNESS_RUN_ID`. Rejected because omission is the current silent
   loss path.
2. Enable automatic capture in every installed consumer. Rejected because E15
   does not change consumer operational-state ownership.
3. Use one shared worktree log. Rejected because concurrent append and merge
   behavior is worse than unique files.

