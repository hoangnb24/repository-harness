# Phase 1 Workflow Decoupling

Date: 2026-07-20

## Status

Completed and activated. Focused checks and the full pre-merge repository
contract pass.

## Anchor

Phase 1 is anchored to OpenAI's
[Harness engineering: leveraging Codex in an agent-first world](https://openai.com/index/harness-engineering/).

The anchor treats human time and attention as the scarce resource. It favors a
short repository map, structured in-repository knowledge, direct access to the
application and its development tools, durable execution plans for complex
work, mechanical enforcement of important invariants, and recurring targeted
garbage collection.

Phase 1 applies those principles by removing the mandatory operational ledger
from the default task path without deleting its implementation or historical
state.

## Outcome

Replace the database-centered default task lifecycle with repository-centered
workflows:

```text
bounded change
  -> small repository map
  -> relevant product, design, code, and tests
  -> implementation
  -> executable or observable proof
  -> concise outcome report

complex or multi-session change
  -> one Git-native active execution plan
  -> implementation with progress and decision updates
  -> executable or observable proof
  -> completed plan plus any lasting design decision
```

After Phase 1, ordinary bounded changes require no Harness CLI mutation.
Existing intake, story, trace, scoring, audit, proposal, SQLite, changeset, and
orchestration behavior remains available for compatibility but is not part of
the default repository workflow.

## Safety Invariants

Phase 1 must preserve these behaviors:

1. Answer, review, diagnosis, plan, explanation, and status requests remain
   read-only.
2. Agents determine the requested outcome and relevant repository truth before
   editing.
3. Completion requires behavior-appropriate executable or observable proof.
4. Agents pause when product intent is ambiguous, an action is difficult to
   recover, validation would be weakened, or additional authority is needed.
5. Complex work remains resumable through a Git-native execution plan.
6. Lasting product and architecture decisions remain repository-visible and
   indexed.
7. Existing databases, semantic changesets, CLI commands, and external
   orchestration contracts remain readable and compatible throughout Phase 1.

## Prior Behavior

The current change workflow requires bootstrap, durable intake, matrix
retrieval, lane-specific context, story and proof records for normal or
high-risk work, manual trace recording, and optional friction/backlog updates.
Several of these records measure whether an agent described the process rather
than whether the resulting application behavior is correct.

The same tiny/normal/high-risk lane also controls unrelated questions:

- whether work needs durable memory;
- whether human judgment is required;
- how much context should be read;
- which documents must be created; and
- what validation is appropriate.

This creates ceremony on bounded tasks and false equivalence between changes
that share a risk keyword but have different consequences.

## Target Work Selection

Phase 1 replaces the single lane with three independent questions.

### Durable Memory

Use an ephemeral plan for bounded, single-session work.

Create or update one file under `docs/plans/active/` when work:

- is likely to span sessions;
- requires coordination across agents or contributors;
- has meaningful dependencies or an important execution sequence;
- needs an explicit recovery procedure; or
- would be unsafe or expensive to resume from the diff alone.

### Human Judgment

Pause only when:

- product intent is ambiguous;
- valid alternatives have materially different product consequences;
- the action is irreversible or difficult to recover;
- validation, security, or compatibility requirements would be weakened; or
- the requested work does not authorize the necessary action.

Sensitive subject matter alone does not require a pause when the expected
behavior and authority are already explicit.

### Validation

Select proof from the affected behavior:

- focused tests for local rules;
- integration tests for persistence or service boundaries;
- end-to-end interaction for user-visible behavior;
- recovery rehearsal for migrations and destructive operations; and
- runtime measurements for reliability or performance claims.

Harness status fields and proof flags are not completion evidence by
themselves.

## Scope

### In Scope

- Replace the mandatory task lifecycle in `AGENTS.md` and the canonical Harness
  operating guidance.
- Introduce a compact repository-centered workflow and plan-selection rule.
- Establish `docs/plans/active/` and `docs/plans/completed/` as the durable work
  memory for complex tasks.
- Add one reusable execution-plan template.
- Mark database-centered lifecycle documents and commands as compatibility or
  legacy surfaces where they are no longer authoritative.
- Keep the small agent entrypoint, repository knowledge indexes, durable design
  decisions, proof-before-completion, and human judgment gates.
- Update Bash, PowerShell, Claude, installer, documentation-contract, and task
  evaluation surfaces so fresh installs expose the same default workflow.
- Define an explicit opt-in refresh path for existing installations.
- Validate the reduced workflow on representative read-only, bounded, complex,
  user-visible, and judgment-requiring tasks.

### Out of Scope

- Delete or rewrite existing SQLite databases.
- Remove CLI commands, schema migrations, semantic changesets, snapshots, or
  historical records.
- Break or migrate Symphony's orchestration protocol.
- Refactor the Rust CLI implementation.
- Build Phase 2 application-legibility capabilities such as browser control,
  worktree-local observability, or generated application maps.
- Move all historical evidence to a separate archive.
- Claim that optional control-plane features are permanently removed before a
  compatibility and usage window has passed.

## Control Transfer

Phase 1 removes obligations only after naming their repository-centered
replacement.

| Current control | Phase 1 replacement |
| --- | --- |
| Intake row | Requested outcome in working context or the active execution plan |
| Risk lane | Independent durable-memory, human-judgment, and validation decisions |
| Story status | Active/completed plan location and Git history |
| Proof matrix flags | Actual test, CI, application, or runtime evidence |
| Manual task trace | Git diff, PR history, test artifacts, and plan progress |
| Context score | Indexed repository knowledge plus link/freshness checks |
| Entropy audit | Repository-specific mechanical checks and targeted cleanup |
| Friction proposal | Direct bounded repair or ordinary technical-debt entry |
| Decision database row | Indexed, Git-native durable decision document |

## Workstreams

### 1. Authority And Source Hierarchy

- [x] Make the compact agent entrypoint and canonical workflow document the
      current authority.
- [x] Preserve the read-only request boundary.
- [x] State that compatibility documentation cannot reintroduce mandatory
      lifecycle steps.
- [x] Define how product, design, plan, generated, and historical documents are
      indexed and retrieved.

### 2. Default Workflows

- [x] Document the bounded-change flow.
- [x] Document the durable-plan flow.
- [x] Document the human-judgment overlay.
- [x] Replace lane-driven validation with behavior-driven proof selection.
- [x] Require concise final reporting of outcome, changed surfaces, proof, and
      unresolved limitations.

### 3. Durable Plan Structure

- [x] Add `docs/plans/README.md`.
- [x] Add `docs/plans/completed/`.
- [x] Add a single reusable execution-plan template.
- [x] Define the active-to-completed transition.
- [x] Define when a plan decision must be promoted into `docs/decisions/`.

### 4. Legacy And Compatibility Boundaries

- [x] Identify every document that presents intake, story, matrix, trace,
      scoring, audit, or proposal operations as mandatory.
- [x] Add clear compatibility banners or relocate historical guidance without
      deleting it.
- [x] Keep existing CLI behavior and machine contracts unchanged.
- [x] Confirm that external orchestration consumers retain their current paths.

### 5. Installation And Refresh

- [x] Make fresh installations use the repository-centered workflow by default.
- [x] Provide an explicit, backed-up refresh path for existing agent shims.
- [x] Keep existing databases and historical documents untouched during refresh.
- [x] Keep Bash, PowerShell, and Claude instruction surfaces equivalent.

### 6. Validation And Evaluation

- [x] Update documentation-contract tests to reject stale mandatory lifecycle
      instructions on the default path.
- [x] Preserve all existing CLI and orchestration compatibility tests.
- [x] Exercise one read-only task.
- [x] Exercise one bounded documentation change.
- [x] Exercise one bounded code fix with existing expected behavior.
- [x] Exercise one user-visible fix requiring application interaction.
- [x] Exercise one multi-session change using a durable plan.
- [x] Exercise one consequential ambiguous change that must pause for judgment.
- [x] Compare required Harness commands, initial Harness context, human
      intervention, validation quality, and false-completion behavior.

## Compatibility Strategy

Phase 1 follows these rules:

```text
stop requiring old writes
  -> keep old reads and commands
  -> validate the new default workflow
  -> migrate optional consumers later
  -> delete dead implementation only in a later decision
```

- Existing CLI releases and databases remain supported.
- No schema migration is introduced for workflow decoupling.
- No historical state is rewritten to resemble the new model.
- Fresh installations adopt the new default.
- Existing installations change only through an explicit refresh or upgrade.
- A compatibility failure blocks Phase 1 completion but does not authorize
  weakening the reduced workflow.

## Rollback

Before CLI or data removal exists, Phase 1 can be rolled back by restoring the
prior agent and operating instructions. Existing commands and durable state
remain intact, so rollback does not require reconstructing deleted data or
releasing a replacement database format.

Rollback is appropriate if representative tasks show:

- an increase in unsupported completion claims;
- loss of necessary coordination or resumability;
- repeated inability to find relevant repository truth;
- an external orchestration compatibility regression; or
- more human attention rather than less.

Rollback should restore only the minimum old obligation needed to address the
observed failure. It must not automatically restore the entire lifecycle.

## Acceptance Criteria

- A bounded change requires zero Harness CLI commands.
- Initial mandatory Harness context is no more than a compact repository map and
  workflow, targeting under approximately 1,000 words.
- Complex work uses one evolving active plan rather than parallel story,
  overview, design, execution, validation, trace, and decision records.
- Completion is supported by relevant executable or observable proof.
- Judgment gates depend on ambiguity, recoverability, validation strength, and
  authority rather than a risk-keyword count.
- Fresh Bash, PowerShell, and Claude installations expose the same default
  workflow.
- Existing CLI, database, changeset, release, and orchestration compatibility
  checks continue to pass.
- Existing durable state remains readable and is not rewritten.
- Default-path documentation contains no contradictory mandatory control-plane
  lifecycle.
- Representative task evaluation shows reduced Harness commands and context
  without increased false completion or human intervention.

## Validation

Implementation must identify focused commands as the affected files become
known. Final validation must include:

```text
documentation contract and stale-guidance checks
installer mode and agent-shim parity checks
representative task evaluations
existing orchestration protocol checks
existing pre-merge repository contract
Git diff and generated-artifact review
```

Passing Harness status or trace scores are explicitly not Phase 1 evidence.

## Decision Log

- 2026-07-20: OpenAI Harness Engineering is the anchor for the reduced workflow.
- 2026-07-20: Preserve repository knowledge, durable complex plans, mechanical
  invariants, application legibility, and targeted garbage collection.
- 2026-07-20: Remove the operational ledger from the default path before
  deleting any implementation or state.
- 2026-07-20: Use independent durable-memory, human-judgment, and validation
  decisions instead of one tiny/normal/high-risk lane.
- 2026-07-20: Record Phase 1 with one Git-native plan and decision, intentionally
  without intake, story, matrix, trace, backlog, or decision-database writes.
- 2026-07-20: Decision `0019-repository-centered-default-workflow` governs the
  target behavior. The current default does not change until implementation is
  completed and validated.
- 2026-07-20: Keep the compatibility CLI in the installer payload, but describe
  bootstrap and database use as explicit opt-in behavior.
- 2026-07-20: Evaluate the workflow with deterministic repository fixtures plus
  the existing control-plane task evaluation. The new fixture exercises real
  file mutation and a visible executable boundary without pretending to measure
  model quality.
- 2026-07-20: Run the full pre-merge contract from a fresh detached worktree so
  proof uses tracked state and does not overwrite a checkout-owned ignored
  database. All gates passed.
- 2026-07-20: Activate decision `0019` and retain the SQLite control plane as an
  explicit compatibility surface after the reduced workflow passed its
  acceptance and rollback checks.

## Progress

- [x] Review the existing repository and identify the seven principal weaknesses.
- [x] Read and adopt OpenAI Harness Engineering as the anchor.
- [x] Agree on the Phase 1 boundary and reduced workflow.
- [x] Record the durable direction in decision `0019`.
- [x] Implement the repository workflow, durable-plan lifecycle, documentation
      hierarchy, compatibility boundaries, and installer payload.
- [x] Validate representative tasks and focused compatibility paths.
- [x] Run the full pre-merge repository contract.
- [x] Move this plan to `docs/plans/completed/` with the final result.

## Result

Phase 1 is implemented, validated, and active. The default path now uses the
repository and Git-native plans without Harness CLI mutations, while the
existing CLI, SQLite state, changesets, protocol, installer upgrades, and
release behavior remain compatible.

Measured workflow comparison:

| Measure | Previous mandatory path | Phase 1 path | Effect |
| --- | ---: | ---: | --- |
| Initial Harness words | 2,413 | 997 | 59% less mandatory context |
| Harness commands for bounded scenarios | At least bootstrap, intake, matrix, story, and trace operations | 0 | Bookkeeping removed from bounded work |
| Ambiguous-task intervention | Required by a broad high-risk lane | 1 of 1 consequentially ambiguous scenarios | Judgment tied to consequence, not vocabulary |
| Durable artifacts for the complex fixture | Multiple lifecycle records and documents | 1 evolving execution plan | One resumable source of task truth |

Focused evidence passed:

```text
tests/installer/assert-agent-authority-contract.sh
tests/evals/test-repository-workflow.sh
tests/installer/assert-install-manifest-links.sh
tests/docs/test-doc-contracts.sh
tests/installer/test-install-harness-modes.sh
tests/evals/test-task-authority.sh
tests/protocol/smoke-native-artifact.sh target/debug/harness-cli
git diff --check
scripts/validate-premerge.sh (fresh detached worktree at 232e0e3)
```

The local environment does not provide `pwsh`; the PowerShell assertions are
covered statically here and remain part of the Windows pre-merge workflow. The
first full-gate attempt correctly found that this checkout's ignored
`harness.db` differed from the tracked core snapshot; that local database was
left untouched. A fresh detached worktree bootstrapped only from tracked state
and passed the complete repository contract.
