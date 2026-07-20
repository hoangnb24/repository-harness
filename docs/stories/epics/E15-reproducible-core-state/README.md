# E15 Reproducible Core State

## Status

Complete. `US-114` through `US-119` are implemented with passing proof as of
2026-07-20.

## Intake

- Current local intake: `#222` (numeric ids can remap after rebuild).
- Durable planning run: `run_20260720_e15_reproducible_core_state`.
- Planning lane: `normal`.
- Implementation lane: assigned per story; state-format and bootstrap changes are
  `high-risk`.

## Outcome And Evidence

A fresh source clone and every source worktree can reconstruct the same Harness
core state using only tracked repository artifacts. Normal mutating CLI commands
durably capture their semantic operations without a separate task lifecycle.

A disposable source checkout with no writable database or prebuilt CLI now
bootstraps from the tracked snapshot plus JSONL and matches the expected durable
state. Real worktrees preserve independent changes, while two stale edits to
the same entity stop with an actionable conflict instead of silently
overwriting one another.

## Starting Problem

The source repository's authoritative planning history previously lived only
in an ignored, owner-local `harness.db`. Although the repository tracked
semantic changesets, writing one depended on the caller supplying
`HARNESS_RUN_ID`.

That causes a direct failure chain:

1. An agent mutates `harness.db` without the environment variable.
2. The database changes, but no tracked JSONL operation is created.
3. A fresh clone or another worktree cannot observe that change.
4. Bootstrap refuses to create a missing source database, so the clone cannot
   reconstruct the project control plane from Git.

Tracking the live SQLite file would replace this with binary merge conflicts,
WAL concerns, and noisy unrelated changes. E15 therefore keeps writable
databases local and makes the reproducible inputs tracked.

## Target Mechanism

```text
tracked verified snapshot + tracked typed JSONL changesets
                         |
                         v
        bootstrap copies and replays into each worktree
                         |
                         v
             ignored writable local harness.db

normal mutating harness-cli command
        -> commits its SQLite transaction
        -> automatically emits one uniquely named changeset
        -> records typed operations in the existing JSONL envelope
```

The CLI process performing the mutation owns changeset creation. Agents keep
using commands such as `story add`, `story update`, and `trace`; they do not
manually open, finish, seal, or author changeset files.

For mutable entities, operations carry the revision they observed. For example,
if two branches both update story `US-200` from revision `3`, the first merged
operation advances it to `4`. Replaying the second operation sees `expected=3`
and `actual=4`, stops, and names the entity and changeset. An agent then inspects
both intents, rebases, removes only its own stale unmerged generated changeset,
and reruns the high-level command against revision `4`. Harness detects the
conflict; it does not invent the resolution.

Independent operations continue to replay normally. Append-only records use
stable unique identity rather than an unnecessary shared revision lock.

## Work Items

| Story | Lane | Outcome | Depends on |
| --- | --- | --- | --- |
| `US-114` Define Reproducible Core State Epic | normal | Record the minimal mechanism, execution order, proof, and scope boundary. | none |
| `US-115` Automatic Source Changeset Capture | high-risk | In source tracked-state mode, every successful mutating CLI invocation automatically writes one unique, rollback-safe JSONL changeset using the existing typed operation structure. Consumer defaults remain unchanged. | `US-114` |
| `US-116` Mutable Entity Revision Guards | high-risk | Replay rejects stale mutations with entity, expected revision, actual revision, and originating changeset; append-only operations retain stable-identity semantics. | `US-115` |
| `US-117` Verified Snapshot Materialization | high-risk | Publish a sanitized, read-only baseline and make source bootstrap materialize each worktree's ignored database from the baseline plus tracked changesets. | `US-116` |
| `US-118` Worktree Conflict Recovery | normal | Prove independent changes merge and document the agent recovery loop for genuine stale-revision conflicts, without an automatic reconciliation subsystem. | `US-117` |
| `US-119` CI Rebuild Gate And Snapshot Compaction | high-risk | Rebuild from tracked state in CI and define optional, infrequent snapshot replacement that preserves logical-state proof. | `US-118` |

## Dependency Map

```text
US-114 -> US-115 -> US-116 -> US-117 -> US-118 -> US-119
 plan       capture    guard      restore    recover    enforce
```

This sequence is intentionally serial. Publishing a snapshot before automatic
capture creates another loss window. Publishing it before revision guards lets
conflicting branch operations replay with last-writer-wins behavior.

## Candidate Paths

| Path | Advantage | Failure or cost | Decision |
| --- | --- | --- | --- |
| Track the writable `harness.db` | Few implementation changes | Binary conflicts, transient SQLite files, and unrelated write churn | Rejected |
| Publish a snapshot first | Fresh clones work sooner | Mutations made before automatic capture can still disappear; conflicts can still overwrite | Rejected unless an explicit write freeze is imposed |
| Capture, guard, then publish | No untracked-write gap at cutover; deterministic conflicts | Fresh-clone repair arrives after two foundations | Chosen |
| Replace SQLite with a full event-sourcing platform | One conceptual source of truth | Large migration and substantial control-plane ceremony | Rejected |

## Execution Plan

Execution followed the dependency chain: automatic capture, revision guards,
verified baseline/materialization, real-worktree recovery, then CI and guarded
compaction. Each story reached `implemented` with fresh proof before its
dependent story began.

## Epic Exit Criteria

- A source-mode mutation emits a valid changeset without `HARNESS_RUN_ID` or a
  separate begin/finish command.
- Failed SQLite transactions leave neither state mutations nor partial JSONL.
- A disposable clone with no local database bootstraps from tracked artifacts.
- Snapshot integrity and logical-state identity are checked before use.
- Existing changesets apply at most once, and changing the content of an
  already-applied changeset is rejected.
- Two worktrees that change different entities converge after merge and rebuild.
- Two stale updates to the same entity stop with a structured conflict; neither
  value silently wins.
- The documented agent recovery reruns normal domain commands and does not
  require a reconciliation event graph or a human unless intent is ambiguous.
- CI proves materialization and logical-state parity on supported bootstrap
  paths.
- Installed consumer repositories retain their current local operational-state
  behavior.

## Non-Goals

- Committing the live writable SQLite database.
- Sharing one writable database between worktrees.
- Requiring agents to author JSONL or manage run lifecycle commands.
- Building a generic event DAG or automatic semantic merge engine.
- Automatically choosing between conflicting product intents.
- Migrating consumer operational state into Git.
- Cleaning every historical data-quality issue as part of the snapshot cutover.
- Running snapshot compaction during ordinary tasks.

## Risks And Stop Conditions

- Stop snapshot publication if it contains secrets, machine-specific paths, or
  state that cannot be explained and sanitized without destructive rewriting.
- Stop replay migration if any mutating command lacks a typed semantic operation;
  silent fallback to raw database copying is not acceptable.
- Stop automatic recovery when conflict resolution requires choosing product
  intent, weakening a validation gate, or changing already-shared history.
- Preserve current consumer defaults unless a separate product decision expands
  the scope.

## Traceability And Reconciliation Triggers

| Claim | Required proof |
| --- | --- |
| No silent mutation loss | Mutation tests with no caller-supplied run id and rollback-failure fixtures |
| Deterministic conflict detection | Same-entity and independent-entity two-worktree fixtures |
| Reproducible source state | Fresh bootstrap, replay, SQLite integrity, and logical-hash comparison |
| No consumer regression | Installed-consumer bootstrap and mutation smoke tests |
| Maintainable history | CI rebuild plus one tested snapshot-replacement procedure |

Revisit the plan if revision guards require changing the whole changeset format,
if the sanitized baseline cannot be reviewed as a bounded artifact, or if
worktree recovery repeatedly requires manual database surgery. Those signals may
justify a different storage model; they do not justify silently adding ceremony
to the common path.

## Execution Boundary

The authorized serial boundary was fulfilled. No E15 story began before its
blocker was implemented with passing proof, and no parallel orchestration
system was added.
