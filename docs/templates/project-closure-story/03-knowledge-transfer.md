# Knowledge Transfer — <project-name>

## Walkthrough Sessions

| Date | Topic | Outgoing | Incoming | Recording / notes link |
| --- | --- | --- | --- | --- |
| YYYY-MM-DD | Architecture tour | <name> | <name> | <link or "see notes/<file>"> |
| YYYY-MM-DD | Deploy + rollback live demo | <name> | <name> | <link> |
| YYYY-MM-DD | Incident playbook walkthrough | <name> | <name> | <link> |
| YYYY-MM-DD | Test suite + CI walkthrough | <name> | <name> | <link> |

Add or remove rows as the project's surface dictates. Each session
must produce either a recording link or a written notes file.

## Runbooks To Read

- `docs/playbooks/*` — list specific entries that this project uses
  routinely (e.g. `production-readiness-checklist.md` if it exists,
  `hypercare-plan.md`, etc.).
- Internal runbooks (paths under `docs/runbooks/` if the project has
  them).
- External: vendor-side runbooks linked from
  `01-handover-docs.md` § External Integrations.

## Recurring Operational Tasks

| Task | Cadence | Owner after handover | Reference |
| --- | --- | --- | --- |
| Dependency review | monthly | <name> | <link to checklist or playbook> |
| Backup verification | weekly | <name> | <link> |
| On-call rotation update | as roster changes | <name> | <link> |
| Certificate / domain renewal | annual / per cert | <name> | `02-credentials-handover.md#SSL` |
| Security patch review | weekly | <name> | <link> |

## Story Hand-Off Notes

For each in-flight `US-NNN.REQ-MMM`, summarise context the new
owner cannot reconstruct from code:

- `US-NNN.REQ-MMM` — <one-paragraph context, decision history, current
  blocker>.

## Open Questions From Incoming Owner

Bullet list. Each question is paired with a date asked and date
resolved. No question may remain unresolved at signoff.

- <YYYY-MM-DD asked> — <question> — <YYYY-MM-DD resolved by ...>
