# US-XXX Story Title

## Status

planned

## Lane

tiny | normal | high-risk

## Product Contract

Describe the behavior this story must make true.

## Relevant Product Docs

- `docs/product/...`

## Planning Triggers

- No plan: describe the bounded conditions that permit direct work.
- Lightweight plan: name the target-owned checklist and its trigger.
- Resumable plan: name the target-owned durable path and its interruption,
  coordination, or risk trigger.

Do not create a plan solely to satisfy an external tool.

## Acceptance Criteria

- Criterion 1.
- Criterion 2.
- Criterion 3.

## Design Notes

- Commands:
- Queries:
- API:
- Tables:
- Domain rules:
- UI surfaces:

## Validation

When the target actually uses the V0 Harness durable layer, update its durable
proof status with numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 0 --platform 0`.

Otherwise, do not require that command or durable layer. Use the target's own
proof route and record its evidence in the table below.

| Layer | Expected proof |
| --- | --- |
| Unit | |
| Integration | |
| E2E | |
| Platform | |
| Release | |

### Validation Ladder

Run the smallest relevant target-owned check first and stop on failure.

| Order | Check | Applies when | Expected result | Failure route |
| --- | --- | --- | --- | --- |
| 1 | `<fast local check>` | | | |
| 2 | `<focused behavior check>` | | | |
| 3 | `<broader repository check>` | | | |
| 4 | `<platform or release check>` | | | |

## Harness Delta

This section is optional and conditional. Complete it only when the target uses
Harness or explicitly selects a Harness change; otherwise write `Not
applicable` and use the target-owned capability section below.

When applicable, document any harness updates made or proposed because of this
story.

## Target-Owned Capability Contracts

- Invariant: name the target owner, runnable check, bounded remediation, and
  exception path.
- Feedback: name the target owner, direct route, success signal, and explicit
  behavior when the surface is unavailable.
- Repeated correction: name the trigger, target-owned durable home, discovery
  route, validation, and retirement rule.
- Gardening: name the bounded scope, target owner, trigger or cadence, runner,
  allowed-change policy, validation, and second-run convergence expectation.

Conversation history alone is not a durable capability.

## Resume Capsule

- Objective:
- Completed:
- Remaining:
- Exact next action: `<one command, inspection, or edit with its target>`
- Validation ladder: `<ordered target-owned checks and stop-on-failure rule>`
- Decisions and assumptions:
- Blockers and owners:
- Working state: `<revision, changed paths, and required environment facts>`

## Evidence

Add commands, reports, screenshots, or links after validation exists.
