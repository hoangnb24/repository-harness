# Exec Plan

## Goal

Turn the current VSF feature set into a v0.2 release-candidate workflow with
one-command demo, environment diagnostics, artifact audit, release docs, and
validation proof.

## Scope

In scope:

- `make demo-full`.
- `vsf-profiler doctor`.
- Final artifact audit script.
- v0.2 RC release notes.
- Tests for doctor redaction and artifact audit pass/fail behavior.
- Harness story, decision, matrix, and trace updates.

Out of scope:

- New product features.
- Hosted deployment.
- New database connectors.
- PDF generation.
- Performance benchmarking beyond smoke timing.

## Risk Classification

Risk flags:

- Audit/security: doctor and audit must not leak secrets.
- Public contracts: new CLI command, make target, and release docs.
- Existing behavior: existing commands and artifact names must remain
  backward-compatible.
- Cross-platform: local environment checks vary by machine.
- Multi-domain: CLI, scripts, docs, tests, and Harness records change.

Hard gates:

- Audit/security.

## Work Phases

1. Discovery.
2. Harness story and decision.
3. Doctor command.
4. Artifact audit script.
5. Demo-full target and release docs.
6. Focused and full validation.
7. Harness trace and audit.

## Stop Conditions

Pause for human confirmation if:

- Optional checks would need to become hard requirements.
- Existing artifact names or CLI behavior would need to change.
- Doctor or audit would need to print secrets to be useful.
