# Decisions

Decision records preserve lasting product, architecture, data ownership,
security, compatibility, and validation choices that future work must inherit.

Use `docs/templates/decision.md`. Task-local implementation choices remain in
the active execution plan and do not require a separate decision.

An installed consumer begins with no fabricated decisions. Add local decision
documents here as real choices are accepted, then index them in this file.

## Upstream Current Decisions

These source-repository decisions explain Harness itself; they are not installed
consumer product choices.

| Decision | Status | Title |
| --- | --- | --- |
| [0019](https://github.com/hoangnb24/repository-harness/blob/main/docs/decisions/0019-repository-centered-default-workflow.md) | Active | Repository-Centered Default Workflow |
| [0020](https://github.com/hoangnb24/repository-harness/blob/main/docs/decisions/0020-installation-profiles-and-knowledge-boundaries.md) | Active | Installation Profiles And Knowledge Boundaries |
| [0021](https://github.com/hoangnb24/repository-harness/blob/main/docs/decisions/0021-consumer-first-application-legibility-phase.md) | Active | Consumer-First Application Legibility Phase |
| [0022](https://github.com/hoangnb24/repository-harness/blob/main/docs/decisions/0022-control-plane-freeze-and-compatibility-runway.md) | Active | Control-Plane Freeze And Compatibility Runway |
| [0023](https://github.com/hoangnb24/repository-harness/blob/main/docs/decisions/0023-optional-consumer-ownership.md) | Active | Optional Consumer Ownership |
| [0024](https://github.com/hoangnb24/repository-harness/blob/main/docs/decisions/0024-rust-harness-core-maintenance-cli.md) | Accepted target | Rust Harness Core Maintenance CLI |
| [0025](https://github.com/hoangnb24/repository-harness/blob/main/docs/decisions/0025-latest-release-self-update-and-human-directed-conflicts.md) | Active | Latest-Release Self-Update And Human-Directed Conflicts |
| [0026](https://github.com/hoangnb24/repository-harness/blob/main/docs/decisions/0026-explicit-onboarding-skills-in-default-core.md) | Active | Explicit Onboarding Skills In Default Core |

## Compatibility Decisions

These decisions remain relevant only when maintaining the optional CLI,
SQLite, or orchestration surface.

| Decision | Status | Title |
| --- | --- | --- |
| [0004](https://github.com/hoangnb24/repository-harness/blob/main/docs/decisions/0004-sqlite-durable-layer.md) | Compatibility | SQLite Durable Layer |
| [0005](https://github.com/hoangnb24/repository-harness/blob/main/docs/decisions/0005-prebuilt-rust-harness-cli.md) | Compatibility | Prebuilt Rust Harness CLI |
| [0006](https://github.com/hoangnb24/repository-harness/blob/main/docs/decisions/0006-phase-4-benchmark-triage.md) | Compatibility | Phase 4 Benchmark Triage |
| [0007](https://github.com/hoangnb24/repository-harness/blob/main/docs/decisions/0007-improvement-proposal-rules.md) | Compatibility | Improvement Proposal Rules |
| [0011](https://github.com/hoangnb24/repository-harness/blob/main/docs/decisions/0011-reproducible-core-state.md) | Compatibility | Reproducible Core State |
| [0010](https://github.com/hoangnb24/repository-harness/blob/main/docs/decisions/0010-proof-before-cli-release-promotion.md) | Compatibility | Proof Before Harness CLI Release Promotion |

## Historical Decisions

These records explain superseded default behavior and remain available for
provenance rather than current instruction.

| Decision | Status | Title |
| --- | --- | --- |
| [0001](https://github.com/hoangnb24/repository-harness/blob/main/docs/decisions/0001-harness-first-development.md) | Amended by 0019 | Harness-First Development |
| [0002](https://github.com/hoangnb24/repository-harness/blob/main/docs/decisions/0002-post-spec-product-lifecycle.md) | Superseded by 0003 | Seed Specification Product Lifecycle |
| [0003](https://github.com/hoangnb24/repository-harness/blob/main/docs/decisions/0003-generic-spec-intake-harness.md) | Amended by 0019 | Generic Spec Intake Harness |
| [0008](https://github.com/hoangnb24/repository-harness/blob/main/docs/decisions/0008-self-improving-harness-lifecycle.md) | Superseded by 0019 and 0022 | Self-Improving Harness Lifecycle |
| [0009](https://github.com/hoangnb24/repository-harness/blob/main/docs/decisions/0009-separate-symphony-product-repository.md) | Completed migration | Separate Symphony Into Its Own Product Repository |

## Add A Decision When

- A locked technical choice changes.
- Product behavior changes meaningfully and alternatives have different
  consequences.
- Data ownership, authorization, privacy, security, or public compatibility is
  decided.
- A validation requirement is added, removed, or weakened.
- The source-of-truth hierarchy or default workflow changes.

Do not add a decision merely because a task mentions a sensitive domain or uses
a durable execution plan.
