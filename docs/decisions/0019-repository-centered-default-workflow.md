# 0019 Repository-Centered Default Workflow

Date: 2026-07-20

## Status

Accepted and active. Phase 1 implementation and the full pre-merge repository
contract completed on 2026-07-20.

## Context

The prior Harness default required agents making repository changes to
bootstrap a SQLite control plane, record intake, retrieve a durable proof
matrix, create or update story state for normal and high-risk work, record a
manual trace, and optionally score context, audit entropy, or create improvement
proposals.

This machinery makes Harness operations reproducible, but it directs agent and
human attention toward proving the bookkeeping itself. Manual traces and context
scores primarily evaluate agent-provided descriptions. Story proof flags and
verification status can show that a configured command passed without showing
that it proves the requested product behavior. The same risk lane also controls
durable memory, approval, context, documentation, and proof despite those being
independent engineering decisions.

OpenAI's
[Harness engineering: leveraging Codex in an agent-first world](https://openai.com/index/harness-engineering/)
provides the anchor for a different default. It treats human attention as the
scarce resource and emphasizes a short repository map, structured repository
knowledge, direct use of development and application tools, first-class
execution plans for complex work, mechanically enforced invariants, observable
validation, and recurring targeted cleanup.

## Decision

Harness adopts a repository-centered default workflow.

1. `AGENTS.md` remains a small map to product, design, plan, operation, and
   validation truth. It is not a comprehensive operating manual.
2. Bounded work uses an ephemeral plan and requires no Harness CLI mutation.
3. Complex, multi-session, dependency-sensitive, coordinated, or recovery-heavy
   work uses one evolving Git-native execution plan under `docs/plans/active/`.
4. The need for durable memory, human judgment, and validation strength are
   decided independently rather than through a single tiny/normal/high-risk
   lane.
5. Agents pause for human direction when product intent is ambiguous, an action
   is difficult to recover, validation would be weakened, or additional
   authority is required. Sensitive terminology alone is not an automatic
   approval gate when expected behavior is explicit.
6. Completion is supported by relevant executable or observable product
   evidence. Harness rows, proof flags, trace tiers, context scores, and entropy
   scores are not completion evidence by themselves.
7. Lasting product and architecture decisions remain indexed Git-native
   documents. Task-local choices remain in the execution plan.
8. Intake, story, matrix, trace, scoring, audit, proposal, SQLite, changeset, and
   orchestration capabilities remain compatible during Phase 1 but are removed
   from the default workflow.
9. Existing durable state is preserved and readable. Phase 1 introduces no
   destructive migration, schema change, or CLI removal.
10. Fresh installations adopt the repository-centered default. Existing
    installations change only through an explicit backed-up refresh or upgrade.

The source implementation is recorded in
`docs/plans/completed/phase-1-workflow-decoupling.md`.

This decision and its plan are intentionally recorded only as Git-native
artifacts. They do not create intake, story, matrix, trace, backlog, or decision
database records. This is the approved transition exception that begins using
the target durable-state model before the old default is changed.

## Alternatives Considered

1. **Keep the mandatory lifecycle and reduce its number of fields.** Rejected
   because the primary problem is the control plane's position in every task,
   not only the amount of data entered.
2. **Delete the CLI, SQLite state, and changesets immediately.** Rejected because
   it would strand historical data, remove rollback, and risk breaking external
   orchestration consumers before the reduced workflow is proven.
3. **Remove durable planning entirely.** Rejected because complex work must
   remain resumable and repository-legible across sessions and agents.
4. **Create a smaller replacement task database.** Rejected because it would
   preserve dual truth and rebuild ceremony before demonstrating that a task
   database is needed.
5. **Use the reduced workflow only for tiny changes.** Rejected because bounded
   normal work is where mandatory lifecycle overhead is most common and least
   justified.

## Consequences

Positive:

- Bounded work can move directly from repository context to implementation and
  real proof.
- Human and agent attention shifts from self-reported process compliance to
  application legibility, mechanical constraints, and observable outcomes.
- Complex work retains durable progress, recovery, and decision memory without
  parallel story, trace, and database records.
- Phase 1 is reversible because existing implementation and state remain
  intact.
- External consumers receive an explicit compatibility window rather than an
  abrupt removal.

Tradeoffs:

- Compatibility documents continue to describe the prior lifecycle and must
  retain clear boundaries so they do not regain default authority.
- Repositories with weak native tests or application observability will expose
  real proof gaps previously obscured by Harness proof metadata.
- Active work and completion queries will no longer have one universal SQLite
  representation on the default path.
- Optional orchestration and evaluation consumers will require an explicit
  extension boundary in a later phase.
- Maintainers must resist adding replacement ceremony before representative
  tasks demonstrate a concrete need.

## Follow-Up

- Invest next in Phase 2 application legibility: worktree-local
  execution, direct application interaction, logs, metrics, and focused
  validation discovery.
- Decide later whether orchestration, observability evaluation, and historical
  control-plane compatibility become separate optional packages.
- Delete control-plane implementation only under a later decision supported by
  a compatibility and usage window.
