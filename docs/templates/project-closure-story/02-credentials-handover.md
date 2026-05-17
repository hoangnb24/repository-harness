# Credentials Handover — <project-name>

> **No raw secrets in this file.** Every entry is a REFERENCE to a
> secret store. The incoming owner verifies access via the store; this
> file never holds passwords, tokens, or keys.

## Secret Stores Used

| Store | Purpose | Access mechanism |
| --- | --- | --- |
| <vault name / 1Password vault / cloud KMS / sealed-secrets repo> | <prod / staging / dev / CI> | <SSO group / shared invite / IAM role> |

## Required Credential Categories

| Category | Reference (NOT the value) | Verified by incoming | Verified date |
| --- | --- | --- | --- |
| Database — prod | <vault path or item name> | [ ] | YYYY-MM-DD |
| Database — staging | <vault path> | [ ] | YYYY-MM-DD |
| Cloud provider root account | <vault path> | [ ] | YYYY-MM-DD |
| Domain registrar | <vault path> | [ ] | YYYY-MM-DD |
| SSL / TLS cert renewal | <vault path or service> | [ ] | YYYY-MM-DD |
| Email / transactional sender | <vault path> | [ ] | YYYY-MM-DD |
| Payment provider | <vault path> | [ ] | YYYY-MM-DD |
| Monitoring / alerts | <vault path> | [ ] | YYYY-MM-DD |
| CI/CD runner secrets | <vault path> | [ ] | YYYY-MM-DD |
| Third-party API keys (per integration) | <vault path> | [ ] | YYYY-MM-DD |

Add rows as needed. Remove rows that genuinely do not apply (e.g. no
payment provider used).

## Access Verification Protocol

For each row, the INCOMING owner attempts access end-to-end (not just
"can I see the entry" — actually use it). Block signoff on any
failed verification.

## Rotation Schedule

Credentials needing rotation in next 90 days from handover end-date:

| Credential | Next rotation due | Owner after handover |
| --- | --- | --- |
| <name> | YYYY-MM-DD | <incoming owner> |

## Revocation Of Outgoing Access

After incoming owner verifies all rows, the OUTGOING owner's access is
revoked. Record revocation date below for audit.

- Outgoing access revoked: YYYY-MM-DD by <name>.
