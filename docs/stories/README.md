# Stories

> **Compatibility and historical reference.** New bounded work uses an
> ephemeral plan. New complex work uses one file under `docs/plans/active/`.
> Story packets remain for existing CLI state, orchestration consumers, and
> retained implementation history.

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
