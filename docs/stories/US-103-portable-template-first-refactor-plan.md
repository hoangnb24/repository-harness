# US-103 Portable Template-First Harness Refactor Plan

## Status

implemented

## Lane

normal

## Product Contract

Record the accepted, OpenAI-anchored direction for refactoring Repository
Harness into a portable template seed kit whose CLI stays outside ordinary
agent task execution.

## Relevant Product Docs

- `README.md`
- `docs/HARNESS.md`
- `docs/REFACTOR_PLAN.md`
- `docs/decisions/0003-generic-spec-intake-harness.md`
- `docs/decisions/0005-prebuilt-rust-harness-cli.md`
- `docs/decisions/0008-self-improving-harness-lifecycle.md`

## Acceptance Criteria

- The plan states the locked product decisions from the user interview.
- The plan distinguishes universal template structure from target-specific
  repository knowledge, tools, architecture, and validation.
- The documented ordinary-task path requires no Harness CLI command.
- The SQLite operational layer and its workflow commands have explicit V1
  dispositions.
- The plan defines installed shape, CLI scope, migration, phased delivery,
  verification, exit criteria, risks, deferred scope, and authorization
  boundary.
- The plan reuses the current documentation paths by default and requires zero
  cosmetic moves for a standard V0 migration.
- The plan includes a repository-native improvement loop without mandatory
  traces, friction synchronization, or proposal state.
- The plan turns proportional planning, executable invariants,
  agent-accessible feedback, and recurring maintenance into concrete
  target-native contracts rather than anchor-only statements.
- A dedicated implementation phase proves a small task avoids planning
  ceremony, a fresh agent resumes complex work, actionable invariants drive
  repair, agents directly inspect application feedback, failures become durable
  capabilities, and a second gardening run converges.
- These capabilities remain target-owned and do not expand the V1 core into a
  universal validation runner, observability platform, or scheduler.
- The planning change does not implement or publish V1 behavior.

## Design Notes

- Commands: future V1 surface is `install`, `update`, `migrate`, `audit`,
  `scaffold`, and `status`.
- Queries: none required for ordinary target-repository work.
- API: immutable template releases plus a committed install manifest.
- Tables: no operational database tables in V1 core.
- Domain rules: templates ask repository-specific questions; they do not ship
  generic semantic answers.
- UI surfaces: CLI terminal output and reviewable Markdown/Git changes only.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Not applicable to this planning-only documentation change. |
| Integration | Local link and documentation-contract inspection. |
| E2E | Confirm the plan covers fresh, brownfield, migration, and ordinary-agent workflows. |
| Platform | Confirm the plan retains Bash, PowerShell, and prebuilt release requirements. |
| Release | No release behavior changes in this story. |

Verification command:

```bash
test -s docs/REFACTOR_PLAN.md &&
rg -q '^## Implementation Phases' docs/REFACTOR_PLAN.md &&
rg -q '^## Migration And Compatibility' docs/REFACTOR_PLAN.md &&
rg -q '^## Target-Native Capability Contract' docs/REFACTOR_PLAN.md &&
rg -q '^### Phase 6: Instantiate Feedback And Maintenance Loops' docs/REFACTOR_PLAN.md &&
rg -q 'The second gardening run converges' docs/REFACTOR_PLAN.md &&
git diff --check
```

## Harness Delta

The plan proposes replacing the default V0 operational control plane with a
template-first V1 core. No proposed behavior is implemented by this story.

## Evidence

- User locked the simplified product anchor on 2026-07-16.
- Default source bootstrap failed because the local root database still contains
  Symphony-owned story state.
- Planning intake and story records were written through the supported isolated
  database path and semantic changeset `refactor_plan_v1`.
- Focused documentation contracts passed.
- `scripts/validate-premerge.sh` passed, including 90 Rust tests, clippy,
  coherence, replay, bootstrap, protocol, installer, documentation, task-effect,
  and release checks.
- Fresh story completion proof passed against `docs/REFACTOR_PLAN.md`.
- Existing-user review found that the first plan copied anchor terminology into
  new default folder names. The amended plan instead maps V1 roles to the
  repository's current paths and makes path stability a migration invariant.
- The amendment includes a concrete before/after path table: current V0
  knowledge paths remain unchanged, while only the provenance manifest is a
  required new tracked path.
- After the amendment, the focused documentation contract and
  `scripts/validate-premerge.sh` passed again, including 90 Rust tests plus
  installer, replay, documentation, and release checks.
- A fresh database replay of the original planning changeset plus the path-
  stability amendment reconstructed US-103 as implemented and retained the
  human correction record.
- User review found that principles 6 through 9 were present as statements but
  were not concrete enough in the implementation phases and release proof.
- The feedback-loop amendment adds a target-native capability contract and a
  dedicated Phase 6 for paired planning, actionable invariant repair, direct
  application feedback, held-out capability inheritance, and convergent
  recurring gardening.
- Focused US-103 verification and documentation contracts passed after the
  amendment.
- `scripts/validate-premerge.sh` passed after the amendment, including 90 Rust
  tests plus coherence, replay, bootstrap, protocol, installer, documentation,
  task-effect, and release checks.
- A fresh all-changeset rebuild exposed that the first feedback-loop changeset
  name sorted before the changeset that creates US-103, causing a foreign-key
  failure instead of silently leaving unreplayable evidence.
- The uncommitted changeset was renamed after its US-103 dependencies. A final
  fresh rebuild applied four changesets and 35 operations and reconstructed
  US-103 as implemented with the strengthened verification command.
