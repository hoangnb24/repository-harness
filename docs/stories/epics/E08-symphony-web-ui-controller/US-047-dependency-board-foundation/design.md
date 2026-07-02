# Design

## Domain Model

- `BoardItem`: one Harness story plus simple label, story status, lane, verify
  status, direct blockers, direct dependents, board state, and reason.
- `BoardState`: `Ready`, `Blocked`, `In Progress`, `Review`,
  `Needs Attention`, or `Done`.
- `DependencyEdge`: a Harness-owned edge where one story blocks another.

## Application Flow

1. Read Harness stories from `harness.db`.
2. Read optional Harness dependency edges from `story_dependency`.
3. Read Symphony run state from `.symphony/state.db`.
4. Detect dependency cycles before marking tasks runnable.
5. Derive board state:
   - active prepared/running run -> `In Progress`;
   - failed/cancelled/interrupted run -> `Needs Attention`;
   - completed run with PR URL and unsynced changes -> `Review`;
   - implemented story or synced completed run -> `Done`;
   - planned/in-progress story with incomplete blockers or dependency cycle ->
     `Blocked`;
   - otherwise planned/in-progress story -> `Ready`.

## Interface Contract

`harness-symphony work board` prints a table suitable for humans and for early
CLI smoke proof. `US-048` will expose the same model through local APIs for the
browser.

## Data Model

Add Harness migration `007-story-dependencies.sql`:

- `story_dependency(story_id, blocks_story_id)` stores a direct blocker edge.
- Both columns reference `story(id)`.
- Self-dependencies are rejected.
- Duplicate edges are rejected by the composite primary key.

The Web UI MVP does not need hierarchy storage in this story. Hierarchy remains
an explicit follow-up unless feature intake needs a parent-child model before
the browser slice.

## UI / Platform Impact

No browser UI yet. This story creates the backend board model that the local UI
will consume.

## Observability

Board derivation errors should produce direct CLI/API errors. Dependency cycles
are product planning problems and appear in item reasons, not as process
crashes.

## Alternatives Considered

1. Encode dependencies in story notes. Rejected because the Web UI needs typed
   direct blockers, reverse dependents, and cycle detection.
2. Store dependencies only in Symphony state. Rejected because the product
   contract says dependencies live in Harness and are produced during feature
   intake.
