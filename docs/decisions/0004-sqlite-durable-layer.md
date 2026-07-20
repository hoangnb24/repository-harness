# 0004 SQLite Durable Layer

Date: 2026-05-22

## Status

Accepted as an optional compatibility control plane. Default-path authority is
superseded by `0019-repository-centered-default-workflow.md`.

## Context

Harness v0 stores all operational data in markdown files: `TEST_MATRIX.md` rows,
`HARNESS_BACKLOG.md` items, decision records, and story status. This works for
human reading but creates friction for agents:

- Editing markdown tables is error-prone and hard to validate.
- There is no structured way to query past intakes, traces, or friction reports.
- The harness has no observability foundation for future evolution.

Recent research on harness engineering (arXiv:2604.25850, arXiv:2605.13357,
arXiv:2603.28052) identifies observability and structured traces as the
foundation for harness improvement. All three approaches require queryable
operational data, not prose documents.

## Decision

Add a SQLite database (`harness.db`) and a thin CLI (`scripts/bin/harness-cli`) as the
durable layer for operational harness data.

The database stores:

- **Intake records**: classification of incoming work.
- **Stories**: work packets and their validation proof status (replaces manual
  `TEST_MATRIX.md` rows).
- **Decisions**: durable records with optional verification commands.
- **Backlog items**: harness improvement proposals with predicted and actual
  impact.
- **Traces**: agent execution records including actions, files, errors, outcome,
  and harness friction.

The schema is version-controlled under `scripts/schema/`. Writable database
files are `.gitignore`d because each project instance, source clone, and
worktree owns local operational state.

As amended by decision `0011`, this source repository reconstructs its core
control-plane state from a tracked verified SQLite snapshot plus typed JSONL
changesets. The tracked snapshot is read-only input; it is never the writable
database shared by worktrees. Installed consumers still initialize and retain
their own local operational data.

Policy docs (`HARNESS.md`, `FEATURE_INTAKE.md`, `ARCHITECTURE.md`) remain as
human-readable references. The database stores what agents produce, not what
they should do.

## Alternatives Considered

1. Keep everything in markdown. Rejected because it prevents structured queries,
   makes observability impossible, and forces agents to edit fragile tables.
2. Use JSON files. Rejected because concurrent writes are unsafe and queries
   require custom tooling.
3. Use a full database server. Rejected because it adds deployment complexity
   that does not match Harness v0 scope.

## Consequences

Positive:

- Agents record structured data instead of editing markdown tables.
- Intake, story, decision, backlog, and trace data is queryable.
- The harness has an observability foundation for future evolution.
- Schema migrations enable the durable layer to grow with the harness.

Tradeoffs:

- Requires `sqlite3` to be available in the environment.
- Writable databases are not version-controlled. The upstream source instance
  restores reviewed core state; installed consumers start with local empty
  state.
- Markdown docs and the database may drift if agents use one but not the other.

## Follow-Up

- Seed existing decisions (0001-0003) into the database during init.
- Add context engineering rules keyed by task type and risk lane.
- Add harness maturity ladder (H0-H4) once the durable layer proves useful.
