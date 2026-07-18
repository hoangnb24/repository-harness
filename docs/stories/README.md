# Stories

Stories are work packets. They turn product intent into bounded implementation
and validation work.

## Active V1 Story

- `docs/stories/US-111-v1-phase6-capability-evaluation/overview.md` is in
  progress at the authority/template framework slice. Live candidate cards and
  Phase 6 acceptance remain pending; Phases 7-8 are not started.

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
