# Overview

## Current Behavior

`harness-symphony work list` reads Harness stories and classifies whether a
story is runnable from its status and verification command. It does not know
about task dependencies, task hierarchy, active Symphony runs, PR review state,
or sync completion.

## Target Behavior

Symphony exposes a dependency-aware board model for Web UI callers. The model
lists every Harness story, direct blockers, tasks unblocked by each story,
cycle problems, and the board state that a local controller should show.

## Affected Users

- Non-technical task owners selecting safe work from the board.
- Technical maintainers inspecting the same board derivation from the CLI and
  future local API.

## Affected Product Docs

- `docs/product/symphony-web-ui-controller.md`

## Non-Goals

- Serving the browser UI.
- Starting runs from the browser.
- Streaming Codex events.
- Creating or editing tasks in the Web UI.
