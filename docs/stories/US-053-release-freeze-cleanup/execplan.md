# Exec Plan

## Goal

Prepare a clean v0.2 local release-candidate handoff without adding new product
features or changing deterministic artifacts.

## Scope

In scope:

- Release wording in README, architecture, product, demo, and release docs.
- Static Vercel preflight versus local runner boundary.
- v0.2 RC package metadata.
- `.gitignore` and `.vercelignore` release hygiene.
- Harness story, decision, matrix, and final evidence.

Out of scope:

- Profiling, connector, dashboard, PDF, LLM, or artifact-contract changes.
- Hosted backend design.
- Commit/push operations.
- Deleting ambiguous user-created files.

## Risk Classification

Risk flags:

- Release/deployment boundary wording can mislead users if inconsistent.
- Workspace cleanup can accidentally remove user work if done broadly.

Hard gates:

- Preserve existing artifact names and CLI/web behavior.
- Keep Vercel static-only and full runner local-only on `127.0.0.1`.
- Run release validation commands and record any clean skips explicitly.

## Work Phases

1. Read Harness and VSF release context.
2. Audit working tree and generated/local files.
3. Patch release docs, package metadata, and ignore rules.
4. Add Harness story, decision, and matrix row.
5. Run focused syntax/doc checks, full tests, release demos, smokes, story and
   decision verify, and Harness audit.
6. Record final evidence and perform a requirement-by-requirement audit.

## Stop Conditions

Pause for human confirmation if:

- Vercel is intended to host a Python/DuckDB backend.
- Version metadata conflicts with a published package convention.
- Cleanup requires deleting ambiguous user-created files.
- Required gates fail for reasons unrelated to US-053 and need a product
  decision.
