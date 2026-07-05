# US-069 Web UI Design Principles And Validation

## Status

planned

## Lane

normal

## Product Contract

The Symphony Web UI should have a lightweight component and design-principles
contract that guides future controller work without becoming a heavyweight
design-system project. Local shadcn-style primitives remain the component
foundation; Impeccable or equivalent design tooling may be used as a review and
anti-drift layer.

## Relevant Product Docs

- `docs/product/symphony-web-ui-controller.md`

## Acceptance Criteria

- A lightweight Web UI design contract exists for the Symphony controller.
- The contract defines the controller as a dense product/tool UI, not a
  marketing surface.
- The contract states when to use local shadcn-style primitives and when to
  extract product-specific components.
- The contract captures board/card/detail principles: bounded summaries,
  full detail in popups or panels, no nested card-heavy page sections, stable
  status tones, accessible focus states, and responsive overflow constraints.
- The contract documents how Impeccable can help: design vocabulary, audit,
  polish, anti-pattern detection, and optional CLI/browser review.
- The validation path includes existing build and Playwright checks, plus a
  clean skip or documented gap when design-validation tooling is not registered
  or installed.

## Design Notes

- Commands: `harness-symphony web`, Vite build, Playwright E2E, optional
  `npx impeccable detect crates/harness-symphony/web-ui/src/` if available.
- Queries: no runtime data query changes.
- API: no new API shape.
- Tables: no new tables.
- Domain rules: design guidance only; Harness and Symphony remain the state
  owners.
- UI surfaces: Web UI component primitives, task board, task detail popup,
  review/log surfaces, and future Electron shell builds.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-069 --unit 1 --integration 1 --e2e 1 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | Documentation and component references are internally consistent. |
| Integration | Web UI build still succeeds after any component extraction or token changes. |
| E2E | Existing Playwright board/detail coverage still passes, with new checks only if the story changes rendered UI. |
| Platform | Screenshot review or equivalent visual proof demonstrates that the principles fit the controller on desktop and mobile. |
| Release | Not required. |

## Harness Delta

This story may add a reusable design-validation capability recommendation to
the Harness tool registry docs or backlog if Impeccable adoption requires a
new repeatable workflow.

## Evidence

Add commands, reports, screenshots, or links after validation exists.
