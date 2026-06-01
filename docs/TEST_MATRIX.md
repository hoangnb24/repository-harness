# Test Matrix

This file maps product behavior to proof.

No product behavior has been defined or implemented yet. Do not mark a row
implemented until tests or validation evidence exist.

## Status Values

| Status | Meaning |
| --- | --- |
| planned | Accepted as intended behavior, not implemented |
| in_progress | Actively being built |
| implemented | Implemented and proof exists |
| changed | Contract changed after earlier implementation |
| retired | No longer part of the product contract |

## Matrix

The Contract column must cite at least one composite token (`US-NNN.REQ-MMM`,
`US-NNN.SC-MMM`, or `US-NNN.TC-MMM`) — see `docs/HARNESS.md` § Traceability
Tokens. Tiny-lane rows may use inline narrative instead.

| Story | Contract | Unit | Integration | E2E | Platform | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TBD | Add rows when story packets are created. Example: `US-014.REQ-001 — manager updates role for a member` | no | no | no | no | planned | none |

## Evidence Rules

- Unit proof covers pure domain and application rules.
- Integration proof covers backend enforcement, data integrity, provider
  behavior, jobs, or service contracts.
- E2E proof covers user-visible browser flows.
- Platform proof covers only shell, deployment, mobile, desktop, or runtime
  behavior that cannot be proven in lower layers.
- A story can be implemented without every proof column if the story packet
  explains why.

## Verification Register

Each story that ships behavior carries a **runnable proof command** and the
**result of the last run**. This is the mechanical half of "done": the proof
columns above say *which kinds* of proof exist; this register says *the exact
command that re-checks the contract* and *when it last passed*. Adapted from
the upstream story-verify concept (`docs/decisions/0014-...`), markdown-first —
the command is run by a human or agent in the shell, not by a binary.

| Story | Verify command | Last verified | Result |
| --- | --- | --- | --- |
| TBD | The single command that re-proves this story (e.g. `npm test -- roles`, `pnpm e2e auth.spec`, or a manual `MANUAL:` step). | YYYY-MM-DD or `never` | pass / fail / never-run |

Rules:

- A story is not closeable until its Verify command was run and `Result` is
  `pass`, **or** the story packet explains why no command exists (pure-docs,
  design-only, or a `MANUAL:` checkpoint the human signed off).
- `Last verified` + `Result` update in the same commit that closes the story
  or its stage — drift between this register and the proof columns is a bug.
- For a `MANUAL:` verify step, the result is the human's signoff reference
  (UAT row, `delivery-closure-story/02-signoff.md`, or a checkpoint date).

See the enforcement rule in `docs/FEATURE_INTAKE.md` § Pre-Close Verification
Gate and the Done Definition in `AGENTS.md`.
