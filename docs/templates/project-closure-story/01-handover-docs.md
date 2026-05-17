# Handover Docs Index — <project-name>

## Read In This Order

1. `README.md` — project overview, run commands, quick start.
2. `docs/HARNESS.md` (if harnessed) — operating model.
3. `docs/product/*` — current product contract.
4. `docs/decisions/*` — why important choices were made.
5. `docs/stories/epics/*` — recent + open story packets.
6. `docs/TEST_MATRIX.md` — proof status (which behaviour is provably
   covered, which is not).

## Key Decisions Still In Force

| Decision | Why it matters today |
| --- | --- |
| `docs/decisions/NNNN-stack-selection.md` | Locks runtime stack; deviating requires superseding decision. |
| `docs/decisions/NNNN-data-model.md` | <one-line consequence the incoming owner needs to know> |

Cite each decision still constraining current work. Skip decisions
that have already been superseded.

## Open Stories at Handover

| Story | Status | Tokens in flight | New owner |
| --- | --- | --- | --- |
| `docs/stories/epics/EXX-name/US-NNN-slug.md` | in progress / blocked / awaiting review | `US-NNN.REQ-001`, `US-NNN.SC-003` | <name> |

Block signoff on any unassigned in-flight token.

## Maintenance Surfaces

- Dependencies last updated: YYYY-MM-DD. Next review due: YYYY-MM-DD.
- Known tech debt entries: list links to backlog rows.
- Recurring playbooks consulted by this project:
  `docs/playbooks/<name>.md` × N uses.

## External Integrations

| Integration | Purpose | Credential reference | Contact |
| --- | --- | --- | --- |
| <provider> | <what it does for the app> | `02-credentials-handover.md#<row>` | <vendor account manager> |

Credential VALUES live in the secret store, not here — this row
points to the reference row in `02-credentials-handover.md`.
