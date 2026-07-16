# Validation

## Proof Strategy

Verify that the plan contains every required contract heading, names the
isolated bridge rather than a permanent V1 migrate command, and has no
contradictory migrate/audit/Phase 6/Phase 7 prose. This is document proof only.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Exact required plan headings and V1 command boundary are present. |
| Integration | Plan, Decision 0011, and the four packet files agree on the bridge decision and planning-only scope. |
| E2E | Inspect migration, audit, Phase 6, and Phase 7 occurrences for the ordered delivery and release-only protocol. |
| Platform | No executable platform behavior changes; plan retains future platform proof. |
| Performance | Not applicable to planning artifacts. |
| Logs/Audit | No V1 operational state or product telemetry is created. Intake #3 and story US-104 are existing external V0 evidence in .harness/refactor-plan.db; orchestration records Decision 0011 and the final trace. |

## Fixtures

- Current docs/REFACTOR_PLAN.md.
- Decision 0011 and this four-file packet.
- The repository diff.

## Commands

~~~bash
set -e
plan=docs/REFACTOR_PLAN.md
for heading in \
  'Anchor Evidence Classification' \
  'Role And Asset State Model' \
  'CLI Identity And Compatibility' \
  'Legacy V0 Conversion And Recovery' \
  'Pilot Evaluation Protocol'
do
  rg -q "^## $heading$" "$plan"
done
rg -q 'harness-v0-migrate' "$plan"
! rg -n 'harness[[:space:]]migrate' "$plan"
rg -n -i 'migrate|audit|phase 6|phase 7' "$plan"
test -s docs/decisions/0011-time-bounded-v0-conversion.md
for file in overview.md design.md execplan.md validation.md
do
  test -s "docs/stories/US-104-refactor-plan-execution-contracts/$file"
done
git diff --check
~~~

## Acceptance Evidence

Record the exact command results in the completion response. Do not claim
implementation, release, V1 database, or product-telemetry proof from this
planning-only change. The externally recorded V0 decision and final trace are
workflow evidence, not V1 product proof; the writing agent runs no Harness
commands.
