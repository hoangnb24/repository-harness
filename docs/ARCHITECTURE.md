# Architecture

The upstream Harness product is implemented as a Rust workspace with a CLI and
SQLite durable layer. Its primary source is `crates/harness-cli/`, organized
into domain, application, infrastructure, and interface modules. Schema
migrations live in `scripts/schema/`, while installers and validation scripts
form the distribution boundary.

The reusable template does not select an application stack for a consumer
project. The discovery guidance below is for that consumer application after a
user-provided spec and stack decision exist; it does not describe the upstream
Harness CLI as unimplemented.

The optional compatibility control plane has three state forms: a tracked
read-only baseline at `.harness/core-state/`, tracked typed JSONL deltas at
`.harness/changesets/`, and one ignored writable `harness.db` per checkout or
worktree. When that surface is explicitly used, bootstrap verifies baseline
identity, replays only post-baseline deltas, and activates the local database
atomically. Installed consumers keep their databases local and do not inherit
the upstream baseline. The default repository workflow requires none of this
state.

## Discovery Before Shape

Before proposing implementation shape, identify:

- Product surfaces: browser, mobile, desktop, CLI, API, worker, or service.
- Runtime stack: language, framework, database, queues, providers, and hosting.
- Core domains: the product concepts that deserve stable names and contracts.
- Boundary inputs: user input, API requests, webhooks, jobs, files, credentials,
  provider payloads, and environment configuration.
- Validation ladder: the smallest checks that can prove the selected stack.

Record stack choices in `docs/decisions/` when they meaningfully constrain
future work.

## Default Layering

```text
domain
  <- application
      <- infrastructure
          <- interface
              <- app surfaces
```

## Consumer Candidate Structure

```text
app/
  domain/
    entities/
    value-objects/
    repositories/
    services/

  application/
    commands/
    queries/
    handlers/

  infrastructure/
    database/
    logging/
    notifications/

  interface/
    controllers/
    dto/
    presenters/
    routes/
    middlewares/

surfaces/
  browser/
  mobile/
  desktop/
  cli/
```

This is a thinking template, not a scaffold. Create real folders only when an
accepted change enters implementation and the selected stack needs them.

## Dependency Rule

Inner layers must not depend on outer layers.

| Layer | May depend on | Must not depend on |
| --- | --- | --- |
| domain | nothing project-external except tiny pure utilities | framework, database, UI, provider, process/env |
| application | domain | framework, UI, provider, database concrete clients |
| infrastructure | domain, application | interface controllers or UI |
| interface | all backend layers | UI state or platform shell assumptions |
| app surfaces | API contracts and app-facing clients | domain internals directly |

## Parse-First Boundary Rule

Unknown data must be parsed at boundaries before it enters inner code.

Boundaries include:

- HTTP request bodies, params, and query strings.
- Session payloads and identity claims.
- Environment variables.
- Database rows returned from external clients.
- Platform shell payloads.
- Deep links, tokens, and signed URLs.
- Provider webhooks, events, and async payloads.

Target flow:

```text
unknown input
  -> parser
  -> typed DTO or command
  -> application use case
  -> domain object/value object
```

Inner layers should work with meaningful product types such as `UserId`,
`AccountId`, `WorkspaceId`, `Role`, `DateRange`, or domain-specific IDs,
rather than repeatedly validating raw strings.

## Command/Query Boundary

If the product has both reads and writes, keep command/query separation clear at
the code level even when the storage layer is simple:

- Commands mutate state and own audit side effects.
- Queries read state and format for consumers.
- Shared domain rules live in domain/application, not controllers.

## Observability Contract

The future server should emit one canonical JSON log line per request with:

- timestamp
- level
- request_id
- user_id when known
- action
- duration_ms
- status_code
- message

Audit logs are product records. Application logs are operational records. Do not
use one as a substitute for the other.
