# Stories

Stories are work packets. They turn product intent into bounded implementation
and validation work.

No story packets are active yet.

## Normal Story

Use `docs/templates/story.md` for normal feature work.

Suggested path:

```text
docs/stories/epics/E01-domain-name/US-001-short-story-title.md
```

## High-Risk Story

Use `docs/templates/high-risk-story/` when the feature intake classifies work as
high-risk.

Suggested path:

```text
docs/stories/epics/E02-risky-domain/US-012-risky-story-title/
  execplan.md
  overview.md
  design.md
  validation.md
```

## Status Flow

```text
planned -> in_progress -> implemented
                  |
                  v
               changed
                  |
                  v
               retired
```

## Story Selection

When multiple stories are `planned`, follow the **Ordering Rule** in
`backlog.md`: lowest sequence number among epics whose dependencies are
satisfied. Within an epic, take stories in `US-NNN` numeric order
unless the story packet explicitly notes a dependency on another story.

## Examples

Reference stories live under `docs/stories/examples/`. They demonstrate story shape and are NOT active work — ignore them when starting a new project.

## Sync Requirement

Whenever a story's `Status` changes, the corresponding row in
`docs/TEST_MATRIX.md` must be updated in the same change. The two are
the same fact in two views — drift between them silently invalidates
the proof column.
