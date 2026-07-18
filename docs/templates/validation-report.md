# Validation Report

Date: YYYY-MM-DD

## Scope

What story or change was validated?

## Subject And Conditions

- Subject identity: `<revision or artifact digest being validated>`
- Condition identity: `<starting state, fixtures, environment, permissions, and checks>`
- Target owner: `<person, team, or repository role>`

## Commands Run

```text
command
```

## Results

| Check | Result | Notes |
| --- | --- | --- |
| Typecheck | not run | Command does not exist yet |
| Unit | not run | Command does not exist yet |
| Integration | not run | Command does not exist yet |
| E2E | not run | Command does not exist yet |
| Platform | not run | Command does not exist yet |
| Release | not run | Command does not exist yet |

## Validation Ladder

Run the smallest relevant target-owned check first and stop on failure.

| Order | Target-owned check | Applies when | Expected result | Actual result | Evidence or failure route |
| --- | --- | --- | --- | --- | --- |
| 1 | `<fast local check>` | | | not run | |
| 2 | `<focused behavior check>` | | | not run | |
| 3 | `<broader repository check>` | | | not run | |
| 4 | `<platform or release check>` | | | not run | |

## Invariant Results

| Invariant | Target owner | Check | Result | Remediation or approved exception |
| --- | --- | --- | --- | --- |
| `<rule>` | | | not run | |

## Feedback Routes

| Surface | Target owner | Direct route | Result | Evidence or unavailable reason |
| --- | --- | --- | --- | --- |
| `<tests, build, review, runtime, docs, deploy, or recovery>` | | | not run | |

Do not replace unavailable target feedback with an invented proxy. Record the
surface as unavailable and name the approved fallback, if one exists.

## Repeated-Correction And Gardening Check

- Repeated correction observed: `<yes or no>`
- Target-owned durable home: `<path/check or not applicable>`
- Discovery route for future work: `<map or index>`
- Gardening scope and owner: `<bounded scope and target owner>`
- Convergence result: `<second equivalent run finds no repeat drift, not run, or not applicable>`

## Evidence

Add report paths, screenshots, logs, or other artifacts.

## Gaps

List remaining risk or missing harness capability.
