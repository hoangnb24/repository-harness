# Glossary

## Current Workflow

### Agent

An AI coding collaborator operating directly in the repository and its
development environment.

### Harness

The repository knowledge, tools, constraints, and feedback loops that let agents
understand, operate, validate, and improve a product reliably.

### Repository Map

The small entry surface, led by `AGENTS.md`, that points agents toward current
product, design, plan, code, and validation truth.

### Product Contract

The current expected behavior of the product. Product documentation plus
executable tests and observable application behavior form the living contract.

### Ephemeral Plan

Working-context planning for a bounded change that can be completed safely in
the current session.

### Execution Plan

One evolving Git-native file under `docs/plans/active/` used when work spans
sessions, needs coordination or ordering, has meaningful dependencies, or
requires explicit recovery. A validated plan moves to `docs/plans/completed/`.

### Judgment Gate

A pause for human direction caused by ambiguous product intent, materially
different consequences, difficult recovery, weakened validation, or missing
authority. Sensitive terminology alone is not a gate.

### Mechanical Invariant

A repeatable rule enforced by code, schema, lint, test, or CI rather than by a
manual process reminder.

### Application Legibility

The ability of an agent to operate and inspect the real application through
development commands, user-facing interaction, logs, metrics, traces, and other
runtime signals.

### Observable Proof

Evidence produced by exercising the affected behavior, such as test output,
application interaction, screenshots, videos, logs, metrics, or recovery
rehearsal.

### Garbage Collection

Recurring targeted work that detects concrete repository drift or technical
debt and opens bounded fixes backed by mechanical proof.

## Compatibility Control Plane

The following terms describe optional historical CLI and SQLite capabilities.
They are not required by the default repository workflow.

### Durable Layer

The SQLite database and Rust CLI that store compatibility records such as
intakes, stories, decisions, backlog items, traces, tools, and interventions.

### Feature Intake

A compatibility classification record that maps a request to an input type and
tiny, normal, or high-risk lane.

### Story Packet

A legacy work artifact linked to a durable story row and proof matrix. New
complex work uses one execution plan by default.

### Test Matrix

The optional SQLite-backed story and proof-status view used by compatible
orchestrators and historical workflows.

### Trace

A manually supplied compatibility record describing an agent task. Git history,
test artifacts, runtime evidence, and plan progress are preferred default-path
evidence.

### Trace Quality Tier

The compatibility score assigned from the presence of trace fields.

### Context Score

The compatibility result from comparing a trace's reported file reads with
compiled historical context rules.

### Entropy Score

The compatibility audit score derived from incomplete or stale control-plane
records.

### Improvement Proposal

A compatibility recommendation generated from recorded friction,
interventions, and audit findings.

### Semantic Changeset

A typed JSONL operation log used to reconstruct and exchange compatible Harness
control-plane state.
