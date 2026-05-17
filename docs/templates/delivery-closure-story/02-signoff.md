# Signoff — <story id>

## Approver — Client Side

- Name: <name>
- Role: <role>
- Date: YYYY-MM-DD
- Signature mechanism: <email approval / e-signature / written reply>

## Approver — Delivery Side

- Name: <name>
- Role: <role>
- Date: YYYY-MM-DD

## REQ Coverage

| REQ ID | One-line description | Evidence link |
| --- | --- | --- |
| US-NNN.REQ-001 | <one-line description> | `01-uat-plan.md#US-NNN.TC-001` |
| US-NNN.REQ-002 | <one-line description> | `01-uat-plan.md#US-NNN.TC-003` |

Every REQ must have at least one evidence link. Open evidence gaps
block signoff.

## Exclusions

REQ tokens explicitly OUT of this signoff (e.g. deferred to next
release). Each exclusion cites the decision doc that defers it.

| Excluded REQ | Reason | Deferred to | Decision link |
| --- | --- | --- | --- |
| US-NNN.REQ-005 | Out of scope this release | <release tag> | `docs/decisions/NNNN-*.md` |

## Conditions

Any conditional acceptance ("signed pending fix of X by date Y").
Empty section if signoff is unconditional.

| Condition | Owner | Deadline | Tracking link |
| --- | --- | --- | --- |
