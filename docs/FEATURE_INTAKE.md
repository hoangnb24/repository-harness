# Feature Intake

This intake gate applies to change, build, and fix requests before code or
durable Harness state changes. A new project spec also enters through this gate
before it becomes product docs, stories, or implementation work.

Answer, explain, review, diagnose, plan, and status requests stay read-only.
They do not bootstrap or initialize Harness, record intake, update a story or
backlog item, or record a trace. If the user later asks to implement a proposed
change, that new change request enters this gate.

The human does not need to classify risk. The harness does.

## Intake Flow

```text
User prompt
    |
    v
Classify input type
    |
    v
Restate as work item
    |
    v
Find affected product docs and stories
    |
    v
Run risk checklist
    |
    v
Choose lane: tiny, normal, or high-risk
```

## Input Types

Use the input type to decide where the work should land before choosing the risk
lane.

| Type | Use when | Typical artifact |
| --- | --- | --- |
| New spec | Turning a user-provided project spec into harness-ready docs | Product docs, candidate epics, decisions |
| Spec slice | Implementing selected behavior from an accepted spec | Story packet |
| Change request | Changing, fixing, or refining accepted behavior | Story packet or direct patch |
| New initiative | Adding a larger product area that needs multiple stories | Initiative notes plus story packets |
| Maintenance request | Changing technical, operational, or dependency behavior | Story packet, validation report, or decision |
| Harness improvement | Improving how humans and agents collaborate | Direct docs update or `scripts/bin/harness-cli backlog add` |

Do not create or extend a monolithic spec by default after intake. Use product
docs, stories, decisions, and initiative notes as the living surface.

## Lanes

### Tiny

Use for low-risk docs, copy, names, or narrow edits.

Also use for initial project setup when the work is limited to installing
declared dependencies, wiring a server entrypoint, adding a health/smoke
endpoint, or opening a local development database connection without creating
domain schema, CRUD behavior, auth, authorization, provider integration, or
data migration. A health endpoint in a new benchmark or scaffolded project is
smoke proof, not a public contract escalation by itself.

Requirements:

- Record the intake row before implementation; tiny work skips story packet
  overhead, not durable task classification.
- Patch directly.
- Keep affected docs current.
- Run available quick checks.
- Update the harness only if friction was found.

### Normal

Use for story-sized behavior with bounded blast radius.

Requirements:

- Create or update one story file from `docs/templates/story.md`.
- Link relevant product docs.
- Add or update validation expectations.
- Implement the smallest vertical slice when implementation exists.
- Record or update proof status with `scripts/bin/harness-cli story add` and
  `scripts/bin/harness-cli story update`.

### High-Risk

Use when the work can affect security, data, scope, contracts, or multiple
roles/platforms.

Requirements:

- Create a story folder using `docs/templates/high-risk-story/`.
- Fill in `execplan.md`, `overview.md`, `design.md`, and `validation.md`.
- Ask for human confirmation before implementation if direction is ambiguous.
- Record a durable decision when behavior, architecture, authorization, data
  ownership, API shape, or validation requirements change meaningfully. Use a
  `docs/decisions/NNNN-*.md` file from `docs/templates/decision.md`, then add
  or refresh the durable row with `scripts/bin/harness-cli decision add`.
  Decision text in a trace is not a durable decision record.

## Risk Checklist

Mark one flag for each item that applies:

| Risk flag | Applies when the work touches |
| --- | --- |
| Auth | login, logout, sessions, JWT, password, refresh token |
| Authorization | roles, permissions, tenant or company scope |
| Data model | schema, migrations, uniqueness, deletion, retention |
| Audit/security | audit logs, privacy, sensitive data, access logs |
| External systems | email, payments, cloud services, provider SDKs, queues, webhooks |
| Public contracts | API shape, response envelope, client-visible behavior |
| Cross-platform | desktop/mobile/browser split, native shell behavior, deep links |
| Existing behavior | already implemented or test-covered behavior changes |
| Weak proof | unclear or missing tests around the affected area |
| Multi-domain | more than one product domain changes at once |

## Classification

```text
0-1 flags:
  tiny or normal, based on code impact

2-3 flags:
  normal with stronger validation

4+ flags:
  high-risk

Any hard gate:
  high-risk unless the human explicitly narrows scope
```

Hard gates:

- Auth.
- Authorization.
- Data loss or migration.
- Audit/security.
- External provider behavior.
- Removing or weakening validation requirements.

## Output

At the end of intake, the agent should be able to say:

```text
Lane: normal
Reason: touches authorization, API contract, and audit behavior.
Docs: permissions, account-settings, audit-log.
Story: docs/stories/epics/E02-access-control/US-014-manager-updates-role.md.
Validation: unit, integration, E2E.
```
