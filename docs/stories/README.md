# Stories

Stories are work packets. They turn product intent into bounded implementation
and validation work.

## Active V1 Stories

- `docs/stories/US-113-proportional-v1-release-gate/overview.md` aligns release
  acceptance with Decision 0017's smaller evidence set.
- `docs/stories/US-112-v1-phase7-portability-release-proof/overview.md` remains
  the platform engineering packet; only platforms with native smoke proof may
  be claimed as supported.

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
