# US-065 Agent Setup Status Surface

## Status

implemented

## Lane

normal (stronger validation: adds a public API contract and cross-platform UI)

## Product Contract

Users can see, at a glance, which coding agents are set up and ready, and what
to do about the ones that are not. Symphony exposes agent readiness through a
new backend endpoint and renders it as an "Agents" strip in the Web UI, using
the readiness engine built in US-064.

`GET /api/agents` returns readiness for every known adapter
(`claudecode`, `codex`, `custom`): whether its binary is present, a heuristic
(no-network) auth check, an overall status (`ready` / `needs-setup` /
`not-installed` / `unknown`), which adapter is active, and an actionable `next`
hint when a prerequisite is unmet.

The UI shows one card per adapter with a color-coded status badge, the active
marker, the binary/auth detail, and the next-step hint. The strip degrades
gracefully: if the endpoint is unavailable it shows "Agent status unavailable"
rather than breaking the board.

## Relevant Product Docs

- `docs/SYMPHONY_SCOPE.md` (sections 4.5, 8, 12.3)
- `docs/SYMPHONY_QUICKSTART.md` (Agent Prerequisites)
- `docs/stories/US-064-first-class-symphony-claudecode-adapter.md`
- `docs/stories/epics/E08-symphony-web-ui-controller/US-048-local-web-backend-api.md`

## Acceptance Criteria

- `GET /api/agents` returns 200 with an `agents` array covering `claudecode`,
  `codex`, and `custom`, each carrying `active`, `binary_present`,
  `binary_detail`, `auth_ready`, `auth_detail`, `overall`, and `next`.
- The route is matched before the static-file GET fallback, and non-GET methods
  return 405 like the other `/api/*` routes.
- The UI renders an Agents strip with one badge per adapter, color-mapped by
  `overall`, marking the active adapter and surfacing the `next` hint.
- The strip degrades gracefully when the endpoint fails.
- Readiness values are treated as informational: an unconfirmed prerequisite is
  a warning, never a hard error.

## Design Notes

- Endpoint: `crates/harness-symphony/src/web.rs` (`agents_response`,
  `AgentsResponse`), serializing `all_agent_readiness` from US-064.
- The `#[allow(dead_code)]` guard on `all_agent_readiness` was removed once the
  endpoint became a real caller.
- UI: `crates/harness-symphony/web-ui/src/main.tsx` (`AgentsStrip`,
  `AgentCard`, `loadAgents`); a `warning` tone was added to
  `components/ui/badge.tsx` for `needs-setup`.
- Auth checks are heuristic and environment-dependent by design, which is why
  the endpoint never reports them as hard failures.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-065 --unit 1 --integration 1 --e2e 1 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | `web.rs` handler test: `GET /api/agents` returns the three adapters. |
| Integration | Live server curl returns the readiness JSON; non-GET returns 405. |
| E2E | Playwright: strip renders a badge per adapter; degrades on endpoint failure. |
| Platform | UI builds (tsc + vite) and renders in the browser shell. |
| Release | Workspace tests, fmt, clippy; `npm run build`. |

## Evidence

- `cargo test -p harness-symphony` — 86 passed (the 2 failures are the
  pre-existing git-2.28 `pr::tests`); `cargo clippy --workspace -- -D warnings`
  and `cargo fmt --check` clean.
- Live curl of `GET /api/agents` returned readiness for all three adapters;
  `POST /api/agents` returned 405.
- `npm run build` — clean (tsc + vite, no type errors).
- `npm run e2e -- tests/agents.spec.ts` — 2 passed (render + graceful
  degradation).

## Harness Delta

This story turns US-064's readiness engine into a user-facing surface so agent
setup state is visible in the Web UI, not just in `doctor`.
