# Run Ready Story From Board Card Design

## Direction

Add a direct start affordance to Ready cards so operators can run Codex without
opening detail first. Keep it a guarded shortcut over the existing start flow.

## Scope

- Show `Run with Codex` only on Ready cards.
- Confirm before calling the start endpoint.
- Reuse `POST /api/tasks/<story-id>/start`.
- Refresh board state after start.
- Disable when proof is missing or another run is active.
- Do not change backend execution, PR, review, merge, or sync behavior.

## Architecture

`main.tsx` keeps start state and confirmation. `BoardGrid` receives active-run
and start callbacks. `TaskCard` becomes a small container with one button for
opening detail and one button for direct run, avoiding nested interactive
controls.

## Validation

- RED: Playwright cannot find `Run US-076 with Codex`.
- GREEN: clicking direct run confirms, posts to start endpoint, refreshes board,
  and does not open detail.
- Full proof: build, e2e, desktop smoke, design detector, diff check.
