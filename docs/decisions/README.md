# Decisions

Decision records preserve lasting product, architecture, data ownership,
security, compatibility, and validation choices that future work must inherit.

Use `docs/templates/decision.md`. Task-local implementation choices remain in
the active execution plan and do not require a separate decision.

The Git-native document and this index are authoritative for the default
workflow. The optional compatibility control plane may also carry a decision
row when an external orchestrator explicitly requires it.

## Reusable Decision Index

These decisions are part of the installed Harness contract. Source-only
maintenance decisions may remain in this repository without entering the
consumer payload.

| Decision | Status | Title |
| --- | --- | --- |
| [0001](./0001-harness-first-development.md) | Amended by 0019 | Harness-First Development |
| [0002](./0002-post-spec-product-lifecycle.md) | Superseded by 0003 | Seed Specification Product Lifecycle |
| [0003](./0003-generic-spec-intake-harness.md) | Amended by 0019 | Generic Spec Intake Harness |
| [0004](./0004-sqlite-durable-layer.md) | Compatibility | SQLite Durable Layer |
| [0005](./0005-prebuilt-rust-harness-cli.md) | Accepted | Prebuilt Rust Harness CLI |
| [0006](./0006-phase-4-benchmark-triage.md) | Compatibility | Phase 4 Benchmark Triage |
| [0007](./0007-improvement-proposal-rules.md) | Compatibility | Improvement Proposal Rules |
| [0011](./0011-reproducible-core-state.md) | Accepted | Reproducible Core State |
| [0019](./0019-repository-centered-default-workflow.md) | Accepted | Repository-Centered Default Workflow |

Add a decision when:

- A locked technical choice changes.
- Product behavior changes meaningfully and alternatives have different
  consequences.
- Data ownership, authorization, privacy, security, or public compatibility is
  decided.
- A validation requirement is added, removed, or weakened.
- The source-of-truth hierarchy or default workflow changes.

Do not add a decision merely because a task mentions a sensitive domain or uses
a durable execution plan.
