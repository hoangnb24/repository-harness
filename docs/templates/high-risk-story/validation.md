# Validation

## Proof Strategy

Explain what must pass before the story is done.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | |
| Integration | |
| E2E | |
| Platform | |
| Performance | |
| Logs/Audit | |

## Subject And Conditions

- Subject identity: `<revision or artifact digest being validated>`
- Condition identity: `<starting state, fixtures, environment, permissions, and checks>`
- Target owner: `<person, team, or repository role>`

## Validation Ladder

Run the smallest relevant target-owned check first and stop on the first
failure. A later broad pass does not erase an earlier failed boundary check.

| Order | Target-owned check | Applies when | Expected result | Failure route |
| --- | --- | --- | --- | --- |
| 1 | `<fast local check>` | | | |
| 2 | `<focused behavior check>` | | | |
| 3 | `<broader repository check>` | | | |
| 4 | `<platform or release check>` | | | |

## Target-Owned Invariants

| Invariant | Owner | Check | Seeded or natural failure | Remediation | Exception path |
| --- | --- | --- | --- | --- | --- |
| `<rule>` | `<target owner>` | `<command or inspection>` | | | |

## Direct Feedback Routes

| Surface | Owner | Direct route | Success signal | Unavailable behavior |
| --- | --- | --- | --- | --- |
| `<surface>` | `<target owner>` | `<command, path, or interface>` | | `<record unavailable and use named fallback>` |

## Repeated Corrections

If a correction repeats, record the trigger, target owner, durable home,
discovery route, validation, and retirement rule. The durable home may be an
instruction, example, check, test, script, review rule, or another
repository-native capability. Conversation history is not sufficient proof.

## Gardening Contract

| Scope | Owner | Trigger or cadence | Runner | Bounded change policy | Validation | Convergence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `<paths or concern>` | `<target owner>` | | | | | `<second equivalent run finds no repeat drift>` |

## Fixtures

List deterministic users, accounts, records, provider responses, or other
fixtures needed for repeatable proof.

## Commands

Add commands after scripts exist.

```text
TBD
```

## Acceptance Evidence

Add results after verification.
