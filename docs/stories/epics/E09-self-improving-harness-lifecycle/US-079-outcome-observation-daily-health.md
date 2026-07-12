# US-079 Outcome Observation And Daily Improvement Health

## Status

implemented

## Lane

normal

## Product Contract

Harness distinguishes implementation proof from measured improvement outcome
and gives humans one read-only daily view of new proposals, accepted work,
pending outcome reviews, ineffective improvements, and recurrences.

## Relevant Product Docs

- `docs/stories/epics/E09-self-improving-harness-lifecycle/README.md`
- `docs/decisions/0008-self-improving-harness-lifecycle.md`
- `docs/HARNESS_MATURITY.md`
- `docs/IMPROVEMENT_PROTOCOL.md`
- `docs/HARNESS_AUDIT.md`

## Dependencies

- Blocked by: `US-078`.
- Blocks: none.

## Acceptance Criteria

- Story completion records resolution evidence without pretending the predicted
  operational impact has already been observed.
- `backlog outcome record --id <id> --status
  <confirmed|ineffective|reverted> --outcome <text> [--evidence <text>]` records
  one observation for an implemented occurrence; open work is refused.
- Every successful invocation appends one observation with the next per-backlog
  ordinal. The greatest ordinal is the current assessment, so a later
  `confirmed -> reverted` observation is valid without rewriting history.
- Outcome recording is replayable and never changes backlog status, completion
  proof, raw evidence, earlier observations, or legacy `actual_outcome`.
- An observation may be recorded before its schedule is due; the schedule is a
  reminder, not a mutation gate.
- `query improvement-health` combines:
  - audit entropy and actionable drift;
  - new and pending proposal decisions;
  - accepted work in progress;
  - implemented occurrences awaiting outcome observation;
  - confirmed, ineffective, or reverted outcomes;
  - regression and reconsideration candidates;
  - exact next operator actions.
- Repeated read-only health queries write nothing and return deterministic
  ordering.
- Health derives exact schedule state:
  - manual with no observation: `pending_manual`, listed but never overdue;
  - due timestamp not reached: `scheduled_not_due`;
  - due timestamp reached with no observation: `due`;
  - trace count below its target: `scheduled_not_due` with remaining count;
  - trace count reached with no observation: `due`;
  - one or more observations: current status from greatest ordinal;
  - null legacy schedule: `awaiting_observation_plan`, never guessed as overdue.
- Trace counting subtracts the persisted completion-time stable-trace count from
  the current number of uid-bearing trace rows. It never sorts opaque uids or
  uses timestamps. A current count below the baseline reports `schedule_error`
  with a rebuild/repair action instead of guessing.
- Audit treats a keyed implemented occurrence as having measured outcome only
  when at least one outcome-observation row exists. It continues to use
  `actual_outcome` solely for unkeyed legacy compatibility, so the new model does
  not create permanent false audit entropy.
- A neutral `legacy_recorded` observation created by `US-080` counts as preserved
  legacy outcome evidence and is displayed as such, not as confirmed impact. A
  later modern observation receives the next ordinal and becomes current.
- The command does not accept proposals, start external orchestrators, create regression work,
  or apply repairs.
- `docs/IMPROVEMENT_PROTOCOL.md` documents the daily loop and outcome distinction.

## Design Notes

- Commands: `backlog outcome record --id <id> --status
  <confirmed|ineffective|reverted> --outcome <text> [--evidence <text>]` and
  read-only `query improvement-health`.
- Queries: lifecycle state, outcome status/window, audit, proposals, and next
  actions.
- API: CLI only.
- Tables: schedule fields and append-only `backlog_outcome_observation` from
  migration 009 in `US-074`; this story adds no fallback schema without re-intake.
- Domain rules: passing proof means implemented; confirmed outcome means the
  predicted effect was later observed.
- UI surfaces: terminal only; no scheduled daemon.

## Non-Goals

- Do not run a daemon, cron job, or automatic outcome decision.
- Do not overwrite `actual_outcome` or earlier observation events.
- Do not accept proposals, start external orchestrators, or auto-create recurrence work.
- Do not add a generic event-sourcing framework or a rescheduling command.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Observation ordinal/current-state derivation, manual/due/trace-count schedule states, baseline errors, and next-action ordering. |
| Integration | Append confirmed/ineffective/reverted and confirmed-then-reverted observations; derive trace-count due state from persisted counts; reject open work; preserve/display legacy_recorded fields; same-time ordering; read-only hash proof. |
| E2E | Implement an improvement, capture its trace baseline, show not-due then due health, append evidence-backed outcome, and show updated health. |
| Platform | Outcome and health state match after changeset rebuild. |
| Release | Docs, help, workspace fmt/test/clippy, and local installer smoke pass. |

Planned story verification:

```bash
sh -c 'cargo test -p harness-cli -- --list | rg "improvement_health" && cargo test -p harness-cli improvement_health -- --nocapture && scripts/validate-changeset-rebuild.sh'
```

## Harness Delta

This story provides the practical day-to-day operating surface needed to move
from proposal memory toward measurable H5 improvement.

## Evidence

- Added typed `backlog outcome record` and read-only `query improvement-health`
  CLI surfaces with append-only semantic changeset replay.
- Focused `improvement_health` tests cover typed parsing, open-work refusal,
  confirmed/ineffective/reverted ordinal history, replay, current-state
  ordering, manual/date/trace-count schedules, baseline errors, preserved
  `legacy_recorded` outcome display, and byte-for-byte read-only queries.
- `cargo test --workspace` passed 158 tests.
- `cargo clippy --workspace -- -D warnings` and `cargo fmt --check` passed.
- The planned story verification passed and changeset rebuild restored 54
  external orchestrators story rows.
- A local release binary was checksum-verified by the installer; the fresh
  installed database initialized at schema 10 and returned improvement health
  with entropy 0 and no actionable drift.
