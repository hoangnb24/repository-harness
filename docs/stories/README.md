# Stories

Stories are work packets. They turn product intent into bounded implementation
and validation work.

## Active V1 Story

- `docs/stories/US-112-v1-phase7-portability-release-proof/overview.md` is in
  progress after owner acceptance of the Phase 6 framework. Phase 7 engineering
  is open, but the deferred live P0-P7 evidence, Phase 7 acceptance, release
  promotion, and Phase 8 remain closed.

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
