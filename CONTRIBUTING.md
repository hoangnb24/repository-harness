# Contributing

The best contributions make repositories easier for agents and humans to
understand without adding a parallel control plane.

## Useful Contributions

- A real agent failure caused by missing repository authority.
- A smaller or clearer repository rule that prevents a demonstrated mistake.
- Installer, updater, merge, checksum, rollback, or recovery hardening.
- A consumer example that measures undocumented human intervention.
- A documentation or validation improvement backed by a concrete task.

## Before Editing

1. Read `AGENTS.md` and `docs/WORKFLOW.md`.
2. Identify the repository authority for externally observable behavior.
3. Use a durable plan only when the work spans sessions, coordinates people,
   has meaningful dependencies, or needs recovery memory.
4. Keep the change at one product owner.
5. Select proof that observes the changed behavior.

## Context Budget

`scripts/context-budget.tsv` is the single source of size limits for text
agents load repeatedly: the entry blocks, skill descriptions, and skill
bodies. Raising a limit is deliberate: change the number and its reason in the
same pull request and explain why shortening was not possible. Grandfathered
skill limits may only decrease.

## Pull Request

Describe:

```markdown
## Outcome

## Important changes

## Validation

## Compatibility, recovery, and remaining risks
```

Run:

```bash
scripts/validate-premerge.sh
```

## Product Boundary

This repository owns:

- the repository protocol and installed guidance;
- the Rust `harness` installer/updater;
- installation, update, conflict, recovery, and release proof.

Consumer repositories own their product behavior, application runtime, fixtures,
credentials, observability, interface automation, and end-to-end validation.

Do not add a task database, story lifecycle, trace score, generic orchestrator,
application stack, or product-specific policy without a new accepted product
decision.

Protocol v1 and `harness-cli` are end-of-life. Historical fixes belong on a
pinned historical branch or fork, not in the current product.
