# Repository Workflow

This is the canonical default workflow for humans and agents. The repository is
the system of record: product behavior, architecture, active plans, decisions,
code, tests, and observable application behavior carry the work.

The objective is reliable agent execution with as little human attention and
process overhead as the task permits.

## Repository Map

- `AGENTS.md`: small entry map and authority boundary.
- `README.md` and `docs/product/`: current product behavior.
- `docs/ARCHITECTURE.md` and `docs/decisions/`: structural constraints and
  lasting decisions.
- `docs/plans/active/`: complex work currently in progress.
- `docs/plans/completed/`: completed execution history worth retaining.
- Project code, tests, CI, and runtime signals: executable and observable truth.
- `scripts/README.md`: upstream Harness development and compatibility commands.

Use `docs/README.md` for the expanded documentation map. Prefer targeted search
and the nearest relevant index over loading unrelated history.

## Select The Work Shape

Answer three questions independently. Do not use one risk label to decide all
three.

### Does The Work Need Durable Memory?

Use an ephemeral plan for bounded work that can be completed safely in the
current session.

Create or update one execution plan in `docs/plans/active/` when work:

- is likely to span sessions;
- coordinates multiple agents or contributors;
- has meaningful dependencies or an important sequence;
- requires an explicit recovery procedure; or
- would be unsafe or expensive to resume from the final diff alone.

Use `docs/templates/exec-plan.md`. Keep progress and task-local decisions in the
same file. Do not create parallel story, design, validation, and trace documents
for the same work unless one has independent long-term value.

### Does The Work Need Human Judgment?

Pause and request direction when:

- product intent is ambiguous;
- valid alternatives have materially different product consequences;
- the action is irreversible or difficult to recover;
- validation, security, or compatibility requirements would be weakened; or
- the requested work does not authorize the necessary action.

Sensitive subject matter is not an automatic pause when the expected behavior
and authority are already explicit. Fixing an authorization bypass with an
existing contract can proceed; creating a new administrator deletion power
requires product judgment.

### What Proves The Behavior?

Choose proof from the affected behavior:

- focused tests for local rules;
- integration tests for persistence and service boundaries;
- end-to-end interaction for user-visible behavior;
- recovery rehearsal for migrations and destructive operations; and
- runtime measurements for reliability or performance claims.

Harness rows, proof flags, trace tiers, context scores, and entropy scores do not
prove product behavior by themselves.

## Task Flows

### Read-Only Request

For an answer, explanation, review, diagnosis, plan, or status report:

1. Read `AGENTS.md` and only the material needed for the response.
2. Use read-only inspection commands when useful.
3. Do not edit files or mutate Harness state.
4. Stop when concrete repository evidence supports the answer.

Discovery never grants authority to fix what it finds.

### Bounded Change

1. Restate the observable outcome.
2. Read the relevant product or design material, affected code, adjacent
   patterns, and existing tests.
3. Make the smallest coherent change that satisfies the outcome.
4. Run focused proof plus repository-required checks.
5. Report the outcome, important changed surfaces, proof, and known limitations.

No bootstrap, intake, story, matrix, trace, scoring, audit, or proposal command
is required.

### Durable Planned Change

1. Create or resume one plan in `docs/plans/active/`.
2. Record outcome, context, approach, risks, recovery, progress, decisions, and
   validation in that file.
3. Implement in coherent, independently verifiable groups.
4. Update progress and decisions as reality changes.
5. Run the plan's focused and repository-wide proof.
6. Promote lasting product or architecture decisions into `docs/decisions/`.
7. Record the final result and move the plan to `docs/plans/completed/`.

The plan is working memory, not a prediction frozen at intake. Update it when
evidence changes the approach.

## Completion Standard

A change is complete only when:

- the requested outcome exists or the blocker is explicit;
- relevant product and design truth remains current;
- behavior-appropriate proof has passed, or missing proof is disclosed without
  overstating completion;
- durable plan progress and result are current when a plan was required; and
- the final report separates verified facts, limitations, and unattempted work.

Git history, pull-request discussion, test artifacts, screenshots, videos,
logs, metrics, and plan progress are preferred evidence because they arise from
the work. Manual descriptions may add context but do not replace observed proof.

## Compatibility Control Plane

The Rust CLI and SQLite durable layer remain supported for historical state and
optional external orchestration. Their intake, story, matrix, trace, scoring,
audit, intervention, proposal, snapshot, and changeset commands are not part of
the default repository workflow.

Use those commands only when a user explicitly requests them, a maintenance task
targets that compatibility surface, or an external orchestrator's documented
contract requires them. Compatibility documents are references, not authority
to reintroduce mandatory control-plane writes.
