# US-115 Automatic Source Changeset Capture

## Current Behavior

Typed Harness writes append semantic JSONL only when the caller supplies
`HARNESS_RUN_ID`. A normal source mutation can update ignored `harness.db`
without creating any Git-visible record.

## Target Behavior

When a typed mutation targets the default database in a Harness CLI source
checkout, the CLI creates one unique changeset for that invocation if no run ID
was supplied. Existing explicit run IDs continue to work. Installed consumers
and isolated `HARNESS_DB_PATH` workflows retain their current opt-in behavior.

## Affected Users

- Repository maintainers and agents changing Harness control-plane state.
- Installed consumers, whose behavior must not change.

## Affected Product Docs

- `docs/stories/epics/E15-reproducible-core-state/README.md`
- `docs/HARNESS.md`
- `scripts/README.md`
- `docs/decisions/0011-reproducible-core-state.md`

## Non-Goals

- Publishing the canonical baseline snapshot.
- Adding entity revisions or automatic conflict resolution.
- Automatically tracking changesets in Git.
- Adding begin, finish, or seal commands.

