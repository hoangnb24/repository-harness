# Design

## Domain Model

Describe entities, value objects, and business rules.

## Application Flow

Describe commands, queries, and handlers.

## Interface Contract

Describe routes, messages, commands, request DTOs, response DTOs, and errors.

## Data Model

Describe tables, indexes, migrations, and retention concerns.

## UI / Platform Impact

Describe browser, mobile, desktop, CLI, deployment, or platform-shell impact.

## Observability

Describe logs, audit records, metrics, or traces.

## Performance Budget

State the budget BEFORE writing code; measure after. Drift triggers a decision doc or a story to fix.

| Metric | Budget | Measurement method |
| --- | --- | --- |
| P95 latency (server) | `<ms>` | `<APM / log aggregation / synthetic probe>` |
| P99 latency (server) | `<ms>` | same |
| Largest Contentful Paint (UI) | `<ms — e.g. < 2500>` | `<RUM tool, Lighthouse CI>` |
| Interaction to Next Paint (UI) | `<ms — e.g. < 200>` | same |
| Cumulative Layout Shift (UI) | `<score — e.g. < 0.1>` | same |
| Payload size (response) | `<bytes — e.g. < 250 KB>` | `<gzip-encoded, measured at edge>` |
| Query count per request | `<n>` | `<query log / N+1 detector>` |
| Cost per invocation (AI / external) | `<USD>` | per `docs/playbooks/ai-feature-integration.md` § Cost & Latency Budget |

Leave a row empty only if it genuinely does not apply. Replace `<placeholder>` with concrete numbers — "fast" is not a budget.

## Alternatives Considered

1. Option.
