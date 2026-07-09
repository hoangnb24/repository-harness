# Command Center Redesign Design

## Direction

Use the approved A direction: Command Center. The UI should feel like a dense
local operations controller, not a marketing dashboard or dark terminal clone.

## Scope

- Keep the existing React, Tailwind, and local shadcn-style primitives.
- Preserve all existing API calls, board states, task detail behavior, and tests.
- Redesign the main shell, summary strip, board cards, and sidebar styling.
- Avoid new dependencies, new routes, dark mode, and backend changes.

## Design Contract

The first viewport presents one compact command surface:

- Product identity and current operating state.
- Search and refresh controls.
- Active-run and review/sync cues.
- Six board columns visible on desktop and reachable early on mobile.

The board remains primary. Detail stays modal because current workflow and
tests depend on preserving board context, but it should read as an evidence
workbench rather than a decorative popup.

## Validation

Add one failing Playwright assertion before implementation for the Command
Center shell. Then run build, e2e, desktop smoke, Rust workspace tests, fmt,
clippy, and diff checks.
