# Documentation Map

The repository is the system of record. Start with a small map and follow only
the sources relevant to the task.

## Current Workflow

- `WORKFLOW.md`: canonical read-only, bounded-change, durable-plan, judgment,
  validation, and completion behavior.
- `HARNESS.md`: Harness goals, responsibilities, source hierarchy, and consumer
  boundary.
- `CONTEXT_RULES.md`: progressive retrieval and task-triggered context.

## Product And Design Truth

- Root `README.md`: upstream Harness product and distribution contract.
- `product/`: consumer product behavior derived from real accepted intent.
- `ARCHITECTURE.md`: architecture discovery, boundaries, and structural rules.
- `decisions/`: indexed lasting product and architecture decisions.
- `GLOSSARY.md`: current and compatibility terminology.

## Work And Operations

- `plans/active/`: complex work currently in progress.
- `plans/completed/`: retained execution history.
- `templates/exec-plan.md`: the single default durable-plan template.
- `WORKTREE_CONFLICTS.md`: source-state conflict diagnosis and recovery.
- `scripts/README.md`: upstream development, validation, installer, release,
  snapshot, and compatibility commands.
- `contracts/`: versioned contracts for optional external orchestrators.

## Compatibility References

The implemented Rust CLI and SQLite control plane remain supported, but their
lifecycle is not the default repository workflow:

- `FEATURE_INTAKE.md`
- `TEST_MATRIX.md`
- `TRACE_SPEC.md`
- `HARNESS_AUDIT.md`
- `HARNESS_BACKLOG.md`
- `HARNESS_COMPONENTS.md`
- `HARNESS_MATURITY.md`
- `IMPROVEMENT_PROTOCOL.md`
- `TOOL_REGISTRY.md`
- `stories/` and the legacy story templates

These documents may be needed for historical state, CLI maintenance, or
external orchestration. They cannot make control-plane writes mandatory for an
ordinary task.

## Consumer Boundary

The upstream repository implements the Harness CLI, installers, tests, and
release automation. Installed consumers receive the generic workflow and
knowledge structure but do not receive a fabricated application stack, product
contract, or validation suite.
