# Design

## Domain Model

This story does not change runtime domain models. It classifies release-facing
surfaces:

- `static preflight`: browser-only DBML/CSV mapping and visualization served
  from `web/`;
- `local runner`: `127.0.0.1` Python/DuckDB job runner that calls the existing
  pipeline and serves generated artifacts;
- `release gate`: the Harness/story/decision/test evidence used to accept the
  local RC.

## Application Flow

No application flow changes. CLI, connector, web-runner, dashboard, package,
benchmark, and artifact audit commands continue to use existing code paths.

## Interface Contract

No command, route, artifact name, JSON schema, or report artifact contract
changes. Documentation clarifies that:

- `https://smart-eda.vercel.app` is static preflight only;
- `make web-runner` / `vsf-profiler web` starts the full local runner on
  `127.0.0.1`;
- `make demo-full` is the canonical local RC demo path.

## Data Model

No database or artifact schema changes.

## UI / Platform Impact

`vercel.json` remains static-only. `.vercelignore` continues excluding backend
source, tests, docs, generated data, outputs, and local state from the static
deployment payload.

## Observability

Harness story, decision, test matrix, and trace/audit evidence record the
release-freeze proof. Generated local files such as `.DS_Store`, caches,
private env files, data, and outputs are outside release scope.

## Alternatives Considered

1. Add hosted backend behavior. Rejected because US-053 is release cleanup and
   the product contract remains local-first.
2. Leave Vercel wording implicit. Rejected because release reviewers need a
   clear static-vs-local boundary.
3. Delete all untracked files. Rejected because source/docs/tests can be
   release-worthy and generated/user-created files must be classified before
   removal.
