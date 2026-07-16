# Exec Plan

## Goal

Make the accepted V1 refactor plan execution-contract complete while changing
planning artifacts only.

## Scope

In scope:

- Reconcile docs/REFACTOR_PLAN.md with the five-model review.
- Add accepted Decision 0011.
- Create this required high-risk packet from the repository templates.

Out of scope:

- Every surface outside the three owned surfaces named in overview.md.
- V1 operational state, product telemetry, and all implementation or release
  operations.
- Bootstrap, Harness CLI/database/changeset commands by the writing agent.
  Intake #3 and story US-104 are already recorded externally in
  .harness/refactor-plan.db; the orchestrator records Decision 0011 and the
  final trace there.

## Risk Classification

Risk flags:

- Data model and migration contract.
- Audit/security boundary.
- Public CLI and release compatibility contract.
- Existing behavior and weak proof.
- Multi-domain documentation contract.

Hard gates:

- Data migration and audit behavior.

## Work Phases

1. Read the required instructions, templates, plan, story, and decisions.
2. Replace conflicting plan prose with one role, CLI, bridge, phase, and pilot
   contract.
3. Record the accepted migration decision without changing earlier history.
4. Add the planning-only high-risk packet.
5. Run the focused document checks, contradiction inspection, and diff check.
6. Leave current-V0 decision and final-trace recording to external
   orchestration; do not run Harness commands as the writing agent.

## Stop Conditions

Pause for human confirmation if:

- The accepted decision changes from a time-bounded bridge to permanent V1
  conversion behavior.
- A requested edit would change code, release artifacts, databases, changesets,
  US-103, or another unowned surface.
- Compatibility-window dates or bridge input ranges must be committed as
  implementation facts rather than planning requirements.
