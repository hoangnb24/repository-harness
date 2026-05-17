# UAT Plan — <story id>

## Scope

REQ tokens covered: `US-NNN.REQ-001`, `US-NNN.REQ-002`, ...
SC tokens covered: `US-NNN.SC-001`, `US-NNN.SC-002`, ...

REQ tokens explicitly NOT covered in this pass: list with reason
(e.g. "deferred to release N+1, see `02-signoff.md` § Exclusions").

## Journey

Step-by-step user journey through the surface being accepted. Numbered
so test cases can cite step numbers.

1. Actor logs in as <role>.
2. Actor navigates to <screen>.
3. Actor performs <action>.
4. Actor verifies <expected result>.
5. ...

## Test Cases

| TC ID | Path | Steps | Expected | Result |
| --- | --- | --- | --- | --- |
| US-NNN.TC-001 | Happy | 1-5 | <expected> | pass |
| US-NNN.TC-002 | Edge — empty input (covers `US-NNN.SC-001`) | 1-3 | reject with 400 | pass |
| US-NNN.TC-003 | Edge — unauthorized actor (covers `US-NNN.SC-003`) | 1-2 | reject with 403 | fail |

Each test cites its SC token in the Path column when applicable.
Failures must link to a follow-up entry in `overview.md` § Open
Follow-Ups.

## Cap

Recommended ≤ 40 test cases per UAT pass. If more is needed, split
into multiple UAT passes (e.g. one per epic phase) rather than
letting the table balloon.

## Environment

| Item | Value |
| --- | --- |
| Build / commit | <git sha or release tag> |
| Environment | staging / pre-prod / prod-like |
| Test data source | <fixture set, anonymized prod dump, fresh seed, etc.> |
| Observers | <names or roles witnessing the pass> |
