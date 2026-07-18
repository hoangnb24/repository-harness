# Phase 5 Pilot Baseline Validation Report

Completion time: `2026-07-18T07:34:03Z`.

## Final locked card commands

| Card | Command | Exit | Result |
| --- | --- | ---: | --- |
| P0 | `git diff --no-ext-diff --check` | 0 | pass |
| P1 | inapplicable | n/a | concrete finding present |
| P2 | `npm run build` | 0 | pass |
| P3 | `npm test -- --run benchmark/orchestrator/test` | 0 | 20 files, 91 tests passed |
| P4 | `npm test -- --run benchmark/orchestrator/test/task-manifest.test.ts` | 0 | 3/3 passed |
| P5 | `npm test -- --run benchmark/orchestrator/test/score-adherence.test.ts` | 0 | 4/4 passed |
| P6 | `npm test -- --run benchmark/orchestrator/test/phase5-capability-inheritance.test.ts` | 0 | 1/1 passed late; card remains failed on timeout |
| P7 | `git diff --no-ext-diff --check` | 0 | pass |

Additional gates:

- `npm run build`: exit 0.
- `npm run typecheck:orchestrator`: exit 0.
- `npm run lint:orchestrator`: exit 0, 1/1 architecture test passed.
- `git diff --no-ext-diff --check`: exit 0.

## Preserved negative results

`npm test -- --run` exited 1: all 20 orchestrator files passed (91 tests), but
`src/bookmarks.test.ts` could not load the `better-sqlite3` native binding and
skipped 27 tests. Dependency setup intentionally used
`npm ci --ignore-scripts` before the final environment lock; rebuilding the
native addon after the lock would change the environment, so it was not done.

The following final native Harness commands each exited 127 because
`scripts/bin/harness-cli` is absent:

- `story verify-all`
- `query matrix`
- `audit`
- `trace --summary "Completed Phase 5 pilot benchmark baseline" --outcome partial`

Cause and effect: repository-native orchestrator proof is strong and passes,
but product integration proof and Harness durable evidence cannot be claimed.
The missing native addon and missing Harness binary remain explicit blockers.
