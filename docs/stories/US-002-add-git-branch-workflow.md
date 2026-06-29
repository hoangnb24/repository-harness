# US-002 Add Git Branch Workflow

## Status

implemented

## Lane

normal

## Product Contract

The harness defines a production-ready Git workflow for feature and update
work. After the initial baseline commit, normal and high-risk work must happen
on a story-linked branch before implementation starts.

## Relevant Product Docs

- `docs/GIT_WORKFLOW.md`
- `docs/HARNESS.md`
- `docs/FEATURE_INTAKE.md`
- `docs/CONTEXT_RULES.md`
- `docs/templates/story.md`
- `docs/TOOL_REGISTRY.md`

## Acceptance Criteria

- Git branch requirements are defined by lane.
- Branch naming, start-work, during-work, pre-merge, PR summary, protected-main,
  and hotfix rules are documented.
- Harness task loop and intake requirements point to the Git workflow.
- Story packets have a place to record branch and merge evidence.
- Version control can be discovered through the Harness tool registry.

## Design Notes

- Commands: `git status --short --branch`, `git switch -c`, `git diff --check`,
  `scripts/bin/harness-cli story verify-all`.
- Queries: `scripts/bin/harness-cli query tools --capability version-control --status present`.
- API: none.
- Tables: existing `tool`, `story`, and `trace` durable records.
- Domain rules: normal and high-risk implementation work must not happen
  directly on `main` after baseline commit.
- UI surfaces: none.

## Git Branch

- Branch used for this story: bootstrap exception on unborn `main`.
- Reason: the repository has no baseline commit yet, so production branch rules
  begin after the first commit.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Documentation review of workflow rules and links. |
| Integration | Register/check Git in the Harness tool registry and verify story command. |
| E2E | Not applicable. |
| Platform | Not applicable. |
| Release | Not applicable. |

## Harness Delta

Added a Git workflow surface and linked it into intake, task loop, context
selection, tool registry guidance, story packets, and project vocabulary.

## Evidence

- `scripts/bin/harness-cli story add --id US-002 --title "Add Git branch workflow" --lane normal --verify "test -f docs/GIT_WORKFLOW.md"`
- `scripts/bin/harness-cli story update --id US-002 --status implemented --unit 1 --integration 1 --e2e 0 --platform 0 --evidence "Docs and registry validation: Git workflow linked into Harness docs, git registered as version-control, story verification passes."`
- `scripts/bin/harness-cli tool register --name git --kind cli --capability version-control --command git --description "Version control for branch, status, commit, and merge workflows" --responsibility "Tool access"`
- `scripts/bin/harness-cli tool check --name git`
- `scripts/bin/harness-cli query tools --capability version-control --status present`
- `git diff --check`
- `scripts/bin/harness-cli backlog close --id 2 --status implemented --outcome "Implemented docs/GIT_WORKFLOW.md, linked it from Harness intake/context/story surfaces, registered git as version-control, and verified US-002 with story verify-all."`
