# US-116 Mutable Entity Revision Guards

## Current Behavior

Automatic changesets preserve branch operations, but replayed updates still use
unconditional SQL. Two worktrees can both update the same story from the same
starting state and whichever changeset sorts last silently wins.

## Target Behavior

Mutable story, decision, backlog, tool, and audit-episode rows carry monotonic
revisions. New mutating operations record the revision observed before the
write. Replay applies the operation only when the stored revision matches and
otherwise returns a structured conflict naming the entity, expected revision,
actual revision, and changeset.

Append-only intake, trace, intervention, observation, and evidence records keep
stable-identity semantics. Relationship add/remove operations remain explicit
set operations and retain their existing idempotent validation.

## Affected Users

- Agents merging Harness changes from independent worktrees.
- Maintainers diagnosing a replay failure.

## Affected Product Docs

- `docs/stories/epics/E15-reproducible-core-state/README.md`
- `docs/decisions/0011-reproducible-core-state.md`
- `scripts/README.md`

## Non-Goals

- Choosing a winner or rewriting a branch changeset automatically.
- Guarding immutable append-only records with a global database revision.
- Publishing or materializing the canonical snapshot.

