# 0023 Vercel Static Preflight and Local Runner Release Boundary

Date: 2026-06-16

## Status

Accepted

## Context

VSF Data Profiler now has a static browser workspace, a local `127.0.0.1` web
runner, database connector modes, package/PDF export, and release-candidate
demo commands. The release docs need a clear deployment boundary so reviewers
do not mistake the Vercel static site for a hosted Python/DuckDB backend.

## Decision

Treat Vercel as a static preflight deployment only:

- serve the browser-side DBML/CSV mapping and visualization UI from `web/`;
- keep `vercel.json` configured for static output without install/build steps;
- exclude Python source, tests, docs, data, outputs, scripts, and local state
  through `.vercelignore`;
- run full browser-driven profiling jobs only through `vsf-profiler web` or
  `make web-runner` on `127.0.0.1`;
- keep upload mode, local path mode, database connectors, LLM narratives,
  package/PDF export, and dashboard backend jobs local-only.

## Alternatives Considered

1. Host the Python/DuckDB runner on Vercel. Rejected because the product
   contract is local-first, uses local file paths/connectors, and has no
   hosted backend/auth/runtime design.
2. Remove Vercel references entirely. Rejected because the static preflight UI
   is useful for quick DBML/CSV mapping checks and already has a static deploy
   configuration.
3. Merge static preflight and local runner wording. Rejected because it hides
   the most important release boundary for reviewers.

## Consequences

Positive:

- The release candidate has a crisp deployment story.
- Full profiling remains inspectable through the local CLI/web runner.
- Static deployment cannot imply raw CSV upload, connector access, or hosted
  job execution.

Tradeoffs:

- The hosted URL is intentionally limited and cannot produce full run
  artifacts.
- Users must start a local process for upload/path jobs and dashboards.

## Verification

```text
rg -q 'static preflight' README.md docs/product/vsf-data-profiler.md docs/releases/v0.2-rc.md
rg -q '127.0.0.1' README.md docs/product/vsf-data-profiler.md docs/releases/v0.2-rc.md
node --check web/app.js
scripts/bin/harness-cli decision verify 0023
```
