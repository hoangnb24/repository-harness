# Harness

Harness makes a repository legible and operable to coding agents so humans can
specify intent and agents can execute reliable work with minimal supervision.

The app is what users touch. The harness is the repository knowledge, tools,
constraints, and feedback loops that let agents understand and improve it.

The canonical task flow is in `docs/WORKFLOW.md`.

## Mental Model

```text
human intent
  -> small repository map
  -> relevant product and design truth
  -> real code, application, and development tools
  -> implementation inside mechanical boundaries
  -> executable or observable validation
  -> Git-visible result and durable decisions when warranted
  -> targeted cleanup when repeated problems become enforceable rules
```

Human time and attention are the scarce resources. Harness capabilities should
reduce repeated explanation, manual reproduction, review, or recovery. A
capability that produces more process records without improving execution or
proof is not part of the default path.

## Core Responsibilities

### Repository Map

`AGENTS.md` is a compact table of contents and authority boundary. It points to
the workflow and repository truth; it does not attempt to contain every rule.

### Repository Knowledge

Knowledge that agents need should be versioned and discoverable:

- product behavior in the README and `docs/product/`;
- architecture in `docs/ARCHITECTURE.md`;
- lasting decisions in `docs/decisions/`;
- active and completed complex work in `docs/plans/`;
- development and compatibility commands in `scripts/README.md`; and
- executable truth in code, tests, CI, schemas, and generated references.

Prefer an index and progressive disclosure over a monolithic manual.

### Application Legibility

The highest-value Harness tools let an agent operate the real system: start an
isolated instance, reproduce a bug, drive user-visible behavior, inspect logs
and metrics, run focused checks, and observe the result. Installed consumers
define stack-specific commands as their applications emerge.

Harness must not fabricate generic commands and claim they passed. When a
validation or observability capability is missing, report the concrete gap.

### Mechanical Invariants

Encode important, repeatable boundaries in tests, linters, schemas, and CI.
Enforce architecture and correctness constraints while leaving local
implementation choices flexible.

Good invariants include dependency direction, boundary parsing, structured
logging, schema integrity, naming rules, file-size limits, and platform-specific
reliability requirements when the project actually needs them. Error messages
should tell an agent how to remediate the violation.

### Durable Planning

Bounded changes use ephemeral plans. Complex or multi-session work uses one
evolving plan under `docs/plans/active/`. The plan carries progress, task-local
decisions, validation, and recovery. Move it to `docs/plans/completed/` only
after recording the result.

Promote a decision into `docs/decisions/` only when future work needs to inherit
it independently of the plan.

### Garbage Collection

Repeated defects should become targeted repository improvements: a clearer
index, an application-facing tool, a mechanical rule, or a bounded cleanup.
Prefer recurring agents that find concrete violations and open focused fixes
over a self-referential backlog of process metadata.

## Default Request Flows

### Read-Only

Answers, explanations, reviews, diagnoses, plans, and status reports inspect
only the material needed for an evidence-backed response. They do not edit files
or mutate Harness state.

### Bounded Change

Restate the observable outcome, read the relevant repository truth, inspect the
affected implementation and proof, make the change, run behavior-appropriate
validation, and report the result. No Harness CLI operation is required.

### Durable Planned Change

Create or resume one active plan, update it as evidence changes the approach,
implement in coherent groups, validate the outcome, promote lasting decisions,
and move the completed plan to history.

### Human Judgment

Pause only when intent is ambiguous, alternatives have materially different
product consequences, the action is difficult to recover, validation would be
weakened, or the requested authority is insufficient.

## Source Hierarchy

```text
explicit user intent and accepted product direction
  -> current product contract
  -> current architecture and durable decisions
  -> active execution plan for complex work
  -> implementation, tests, schemas, CI, and observable runtime behavior
  -> completed plans and historical evidence
```

When sources conflict, prefer current accepted behavior and executable evidence
over historical plans or compatibility records. Correct or clearly demote stale
material instead of adding another parallel truth.

## Completion

A change is complete when:

- the requested behavior exists or the blocker is explicit;
- relevant repository truth is current;
- suitable executable or observable proof has passed, or missing proof is
  disclosed without overstating the result;
- the active plan is current when the work required one; and
- the final report identifies the outcome, important changed surfaces,
  validation, limitations, and unattempted work.

Git diffs, tests, CI, application interaction, screenshots, logs, metrics, and
plan progress are evidence. Manually filled process fields are commentary.

## Optional Compatibility Control Plane

The implemented Rust CLI and SQLite layer remain available for historical state
and external orchestration. They support intake, stories, proof matrices,
decisions, traces, tools, interventions, audits, proposals, snapshots, and
semantic changesets.

These capabilities are not the default workflow. Use them only when explicitly
requested, when maintaining that compatibility surface, or when an external
orchestrator's versioned contract requires them. Existing schemas and state
remain supported during the workflow-decoupling compatibility window.

Reference material for that surface includes:

- `docs/FEATURE_INTAKE.md`;
- `docs/TEST_MATRIX.md`;
- `docs/TRACE_SPEC.md`;
- `docs/HARNESS_AUDIT.md`;
- `docs/HARNESS_MATURITY.md`;
- `docs/IMPROVEMENT_PROTOCOL.md`;
- `docs/TOOL_REGISTRY.md`; and
- `docs/contracts/harness-orchestration-v1.md`.

Compatibility documentation cannot make those operations mandatory for an
ordinary repository task.

## Consumer Boundary

Installing Harness does not select a consumer application's stack, create fake
product domains, or invent validation commands. A consumer starts with the
repository map, workflow, documentation structure, compatibility tooling, and
templates. Product knowledge and executable capabilities are added only from
real accepted work.
