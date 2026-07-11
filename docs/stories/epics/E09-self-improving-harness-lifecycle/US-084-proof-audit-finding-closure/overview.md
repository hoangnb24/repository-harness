# US-084 Proof-Audit Finding Closure

## Current Behavior

The branch review records five open proof-integrity findings, F-018 through
F-022. Mixed resolver state is not replay-tested, validator selection has no
shell contract tests, later verification is not exercised end to end, closure
trace lists are malformed, and proof timestamp checks accept arbitrary text.

## Target Behavior

Each scenario is executable and fails for the original defect. Rebuild proof
requires a valid canonical timestamp, later verification replaces earlier
proof, validator binary selection is testable, mixed resolver behavior matches
after semantic replay, and the latest closure trace is clean detailed evidence.

## Non-Goals

- Deleting malformed historical traces.
- Freezing verification timestamps.
- Inventing precise order for legacy-only events.
