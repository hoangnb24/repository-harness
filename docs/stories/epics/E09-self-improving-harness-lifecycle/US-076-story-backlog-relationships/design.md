# Design

## Domain Model

- `StoryBacklogRelationship`: `resolves` or `references`.
- `resolves`: the one story authorized to close an accepted occurrence through
  explicit completion.
- `references`: related context with no closure authority.

## Application Flow

1. Resolve the human-readable local backlog id to stable `BacklogUid`.
2. Validate story and backlog occurrence exist and have stable identity.
3. For `resolves`, require an accepted occurrence and a non-terminal story.
4. Validate relationship and one-resolver constraint.
5. Write the relationship, invalidate prior story verification when resolver
   authority changes, and emit uid-based semantic operations atomically.
6. Query relationships by story or backlog occurrence.

## Interface Contract

Prefer an explicit relationship command instead of overloading story creation:

```bash
scripts/bin/harness-cli story backlog link \
  --story US-077 --backlog 12 --relationship resolves
scripts/bin/harness-cli story backlog unlink \
  --story US-077 --backlog 12
scripts/bin/harness-cli query backlog --id 12
```

The detailed backlog query shows stable uid, proposal key, status, resolver,
references, predecessor, and resolution evidence when available.

## Data Model

Migration `010-story-backlog-links.sql` owns this table and its indexes:

```text
story_backlog_link(
  story_id,
  backlog_uid,
  relationship,
  linked_at
)
```

- `(story_id, backlog_uid)` is unique.
- One partial uniqueness constraint permits only one `resolves` row per
  `backlog_uid`.
- Relationship values are constrained to `resolves` or `references`.
- Semantic operations serialize `backlog_uid`, never only a local integer id.
- A resolver mutation and verification invalidation share one transaction and
  replay in the same deterministic operation order.

## UI / Platform Impact

CLI only. No external product UI change is required.

## Observability

Link creation/removal appears in semantic changeset rendering. Once completion
closes an occurrence, its resolver link and recorded resolver story id are
immutable. Reference unlinking never rewrites historical closure.

## Alternatives Considered

1. Store backlog ids in story notes. Rejected because they are not validated or
   replay-safe.
2. Allow several resolver stories and close on the first pass. Rejected because
   partially finished multi-story work could close prematurely.
3. Infer all-of completion. Deferred until a real product need defines its
   semantics.
