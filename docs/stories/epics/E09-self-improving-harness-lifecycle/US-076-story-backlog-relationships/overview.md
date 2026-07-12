# Overview

## Status

planned

## Lane

high-risk

## Product Contract

Stories declare explicit replayable relationships to stable backlog occurrences,
and only one designated resolver has closure authority for each occurrence.

## Current Behavior

Stories and Harness improvement backlog items are independent durable records.
Free-form notes cannot prove which story resolves an item, which stories are only
related, or which story is authorized to close it.

## Target Behavior

Humans and agents can create replayable `resolves` and `references`
relationships. One backlog occurrence has at most one designated resolver, while
any number of stories may reference it for context. Queries explain the complete
relationship without raw SQL.

## Affected Users

- Humans approving Harness improvement work.
- Agents shaping and implementing stories.
- external consumers applying relationship changesets.
- Reviewers inspecting closure authority.

## Affected Product Docs

- `docs/stories/epics/E09-self-improving-harness-lifecycle/README.md`
- `docs/decisions/0008-self-improving-harness-lifecycle.md`
- `docs/HARNESS.md`
- `docs/TOOL_REGISTRY.md`

## Dependencies

- Blocked by: `US-074`.
- Blocks: `US-077`.

## Acceptance Criteria

- A supported CLI command creates and removes `resolves` or `references` links.
- Both story and backlog occurrence must exist; missing targets fail atomically.
- A `resolves` target must currently be `accepted`. A `references` target may be
  open or closed because it carries no closure authority.
- An `implemented` or `retired` story cannot receive or change a resolver link.
- One story/backlog pair cannot carry both relationship types.
- At most one story resolves one backlog occurrence; additional related stories
  use references.
- One story may resolve several backlog occurrences.
- Creating a link never changes story status or closes backlog work.
- Adding, removing, or changing a resolver link clears the story's prior
  verification result so stale proof cannot authorize later closure.
- Human-facing commands may accept a local backlog id, but semantic operations
  and stored relationships use stable backlog uid.
- Link creation/removal is idempotent and replayable across separate changesets.
- Resolver links may be removed or replaced only while the story is nonterminal
  and the backlog occurrence is still accepted. After implemented closure, the
  resolver link is immutable. Reference links remain removable because they
  never carry closure authority.
- Detailed queries show resolver, references, proposal key, predecessor, and
  later resolution evidence without raw SQL.
- Any attempt to remove/change a closed resolver link fails and never rewrites
  historical closure provenance.

## Non-Goals

- Do not close backlog items in this story.
- Do not change story status.
- Do not infer links from titles or notes.
- Do not model implicit all-of completion across several resolver stories.
- Do not create links to unkeyed legacy rows; the command reports `requires
  legacy reconciliation`.
