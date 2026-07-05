# E08 Symphony Web UI Controller

## Goal

Build the local browser controller described in
`docs/product/symphony-web-ui-controller.md` without creating a second source of
truth for Harness or Symphony state.

## Product Contract

The Web UI is a local-only controller over existing Harness stories and
Symphony runs. It must derive task hierarchy, dependency blocking, board state,
run progress, review readiness, PR state, and sync state from Harness and
Symphony records.

## Stories

1. `US-047` - Dependency-aware board state foundation.
2. `US-048` - Local web backend command and API contract.
3. `US-049` - Browser board and task detail UI.
4. `US-050` - Run start, active-run enforcement, and Codex event streaming.
5. `US-051` - Review surface for result artifacts, changesets, PR state, and
   logs.
6. `US-052` - Sync approval flow and Done transition.
7. `US-053` - Browser E2E validation for the MVP workflow.
8. `US-054` - Task hierarchy rendering.
9. `US-055` - PR merged gate before sync.
10. `US-056` - Simplified Kanban-first controller reference revamp.
11. `US-057` - Dependency graph sidebar view.
12. `US-058` - Scrollable board columns.
13. `US-059` - Electron desktop shell.
14. `US-060` - Human-readable chat logs.
15. `US-061` - FrankenTUI app server log TUI.
16. `US-062` - Confetti close effect for the task detail popup.
17. `US-063` - Small completion alert when an active task finishes.
18. `US-064` - Ready work story delete action.
19. `US-065` - Unlimited Codex app-server task runtime.
20. `US-066` - Needs Attention failure explanation.
21. `US-067` - Needs Attention recovery action.
22. `US-068` - Bounded work item cards.
23. `US-069` - Web UI design principles and validation.

## Exit Criteria

- `harness-symphony web` serves a local unauthenticated browser UI.
- The UI shows all Harness stories with Ready, Blocked, In Progress, Review,
  Needs Attention, and Done states derived from durable data.
- A user can start exactly one ready task, watch live Codex App Server events,
  review completed artifacts and PR state, approve sync after merge, and see
  the task move to Done.
- A user can delete unwanted Ready work from the active board without hard
  deleting durable Harness history.
- Codex App Server tasks are not failed by a fixed wall-clock timeout while
  still surfacing real terminal failures and validation errors.
- Needs Attention tasks show a concise failure reason, evidence artifacts, and
  a suggested next action from the Web UI.
- Needs Attention tasks offer guarded retry or PR-retry recovery controls when
  the backend classifies the latest failure as recoverable.
- Work-item cards stay bounded inside board columns and put full content in the
  task detail popup.
- Future Web UI work follows an explicit lightweight controller design contract
  backed by build, Playwright, screenshot, and optional design-lint validation.
- Dependency cycles are detected and shown as task breakdown problems.
- Browser-level validation proves the board, task detail, event stream, review,
  and sync workflows.
- The same controller can be rebuilt into an Electron desktop shell without
  changing Harness or Symphony state ownership.
- Technical maintainers can optionally inspect local app-server logs from a
  terminal TUI without replacing the browser or Electron review surfaces.
