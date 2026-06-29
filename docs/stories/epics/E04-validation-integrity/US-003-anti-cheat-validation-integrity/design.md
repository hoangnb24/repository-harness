# Design

## Domain Model

Validation integrity protects the surfaces that decide whether work is done:

- Protected policy files.
- Story proof and matrix evidence.
- Test, fixture, snapshot, and coverage files.
- CI workflow files.
- Agent-written traces and externally generated proof.

## Application Flow

1. Intake classifies validation-integrity changes as high-risk.
2. Story planning identifies whether protected surfaces, tests, or CI change.
3. Implementation updates policy and proof surfaces.
4. `scripts/validation-integrity-check.py` verifies static guardrails and diff
   evidence.
5. CI runs the same script after a remote exists.
6. Trace records the validation-integrity result and any skipped checks.

## Interface Contract

- Local command: `python3 scripts/validation-integrity-check.py --auto`
- CI command: `python3 scripts/validation-integrity-check.py --base origin/main`
- Durable story verify command: `python3 scripts/validation-integrity-check.py --auto`

## Data Model

No database schema change. Existing `story`, `decision`, `backlog`, and `trace`
records store state and evidence.

## UI / Platform Impact

- Adds GitHub CODEOWNERS and pull request template.
- Adds GitHub Actions workflow for future remote CI.
- Keeps bootstrap mode for the current no-commit local repository.

## Observability

Trace records should name validation integrity checks, protected file changes,
test/proof changes, CI URL or local command, and any bootstrap exception.

## Alternatives Considered

1. Documentation-only policy. Rejected because the user requested physical
   guardrails.
2. CLI schema changes. Deferred because a stack-neutral script gives immediate
   coverage without changing Rust CLI internals.
3. Hard fail on placeholder CODEOWNERS during bootstrap. Rejected because this
   repository does not yet have a remote owner or baseline commit.
