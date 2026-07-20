# Decisions

Decision records explain why important product, architecture, or harness choices
were made.

Use `docs/templates/decision.md` when adding a new decision.

After adding or updating a markdown decision file, also add or refresh the
durable decision row:

```bash
scripts/bin/harness-cli decision add \
  --id 0008-auth-boundary \
  --title "Auth Boundary" \
  --doc docs/decisions/0008-auth-boundary.md
```

Trace fields such as `--decisions` summarize task-level choices. They do not
count as the Harness decision log.

## Reusable Decision Index

These decisions are part of the installed Harness contract. Source-only
maintenance decisions remain in this repository without entering the consumer
payload.

| Decision | Status | Title |
| --- | --- | --- |
| [0001](./0001-harness-first-development.md) | Accepted | Harness-First Development |
| [0002](./0002-post-spec-product-lifecycle.md) | Accepted | Seed Specification Product Lifecycle |
| [0003](./0003-generic-spec-intake-harness.md) | Accepted | Generic Spec Intake Harness |
| [0004](./0004-sqlite-durable-layer.md) | Accepted | SQLite Durable Layer |
| [0005](./0005-prebuilt-rust-harness-cli.md) | Accepted | Prebuilt Rust Harness CLI |
| [0006](./0006-phase-4-benchmark-triage.md) | Accepted | Phase 4 Benchmark Triage |
| [0007](./0007-improvement-proposal-rules.md) | Accepted | Improvement Proposal Rules |
| [0011](./0011-reproducible-core-state.md) | Accepted | Reproducible Core State |


Add a decision when:

- A locked technical choice changes.
- A product rule changes meaningfully.
- A validation requirement is added, removed, or weakened.
- A high-risk feature chooses one design over another.
- Auth, authorization, data ownership, audit/security, or API behavior changes.
- The source-of-truth hierarchy changes.
