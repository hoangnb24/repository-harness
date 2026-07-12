# Exec Plan

## Goal

Close every review finding without weakening the accepted E09 lifecycle.

## Scope

In scope:

- F-001 through F-006 and F-009 through F-013.
- Baseline observations B-001 and B-002.
- Focused tests, committed rebuild proof, docs, and review closure evidence.

Out of scope:

- Unrelated backlog items and UI redesign.

## Risk Classification

Risk flags:

- Database schema and migration.
- Semantic replay compatibility.
- Cross-command lifecycle and orchestrator behavior.

Hard gates:

- No lossy replay timestamps or order boundaries.
- No deletion of historical evidence.
- Full workspace tests, clippy, formatting, changeset rebuild, and audit parity.

## Work Phases

1. Add story and deterministic regression fixtures.
2. Fix replay timestamps and resolver ordering.
3. Fix audit/proposal decisions and Unicode/RFC3339 handling.
4. Align external orchestrators and living docs.
5. Repair committed US-074 proof and strengthen rebuild validation.
6. Run completion audit and close every ledger item.

## Stop Conditions

Pause only if a correction requires changing the accepted lifecycle contract,
deleting historical evidence, or weakening validation.
