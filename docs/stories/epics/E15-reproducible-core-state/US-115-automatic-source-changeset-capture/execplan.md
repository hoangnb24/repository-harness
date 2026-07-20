# Exec Plan

## Goal

Make every normal typed source mutation Git-visible without requiring a caller-
managed run lifecycle.

## Scope

In scope:

- Source/default-database detection.
- One automatically generated run ID per CLI invocation.
- Existing semantic operation and rollback behavior.
- Source, consumer, isolated-database, and uniqueness tests.
- Contract documentation.

Out of scope:

- Revision guards, snapshot activation, worktree recovery, and CI compaction.

## Risk Classification

Risk flags:

- Data model.
- Public contracts.
- Existing behavior.
- Cross-platform.

Hard gates:

- Durable-state loss or duplication.

## Work Phases

1. Add failing tests for source auto-capture and consumer isolation.
2. Generate an invocation run ID only for the default source database.
3. Prove unique files, typed JSONL, and failed-write rollback.
4. Update the CLI and Harness contracts.
5. Run targeted and workspace validation.
6. Record trace and complete `US-115` before starting `US-116`.

## Stop Conditions

Pause if:

- capture requires changing installed consumer defaults;
- a typed mutating command cannot produce semantic operations;
- validation would require weakening existing replay or rollback proof; or
- the design expands into task lifecycle commands.

