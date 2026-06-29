# US-001 Add Brainstorm Workflow

## Status

implemented

## Lane

normal

## Product Contract

The harness supports a pre-intake brainstorm workflow for early idea
exploration. Brainstorm output is provisional until the user selects a direction
and the selected work passes through feature intake.

## Relevant Product Docs

- `docs/BRAINSTORM.md`
- `docs/HARNESS.md`
- `docs/FEATURE_INTAKE.md`
- `docs/templates/brainstorm.md`

## Acceptance Criteria

- Brainstorming has a documented position before feature intake.
- The workflow explains when brainstorm notes are provisional and when selected
  ideas become intake-ready work.
- A reusable brainstorm template exists for captured exploration.
- The documentation map points future agents to the brainstorm workflow.

## Design Notes

- Commands: no new CLI command.
- Queries: no new durable query.
- API: none.
- Tables: none.
- Domain rules: brainstorm notes are not product truth until selected and routed
  through feature intake.
- UI surfaces: none.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Documentation review only; no executable unit layer exists. |
| Integration | Harness CLI accepts the story record and matrix update. |
| E2E | Not applicable. |
| Platform | Not applicable. |
| Release | Not applicable. |

## Harness Delta

Added `docs/BRAINSTORM.md`, `docs/templates/brainstorm.md`, and links from the
main harness docs so future exploratory work has a durable shape.

## Evidence

- `scripts/bin/harness-cli story add --id US-001 --title "Add brainstorm workflow" --lane normal`
- `scripts/bin/harness-cli story update --id US-001 --status implemented --unit 1 --integration 1 --e2e 0 --platform 0 --evidence "Docs-only validation: reviewed brainstorm workflow, template, docs map, context rules, and durable matrix update."`
- `scripts/bin/harness-cli story update --id US-001 --verify "test -f docs/BRAINSTORM.md"`
- `scripts/bin/harness-cli story verify US-001`
