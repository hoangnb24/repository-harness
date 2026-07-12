# US-072 Validation Provider Registry And Audit Cleanup

## Status

implemented

## Lane

normal

## Product Contract

Harness should distinguish real validation gaps from unmodeled local proof
commands. When a repository depends on local test, build, browser, platform,
or registered review checks, those
capabilities should be visible through the tool registry or through an explicit
verification contract. Audit and proposal output should then focus on current
actionable drift, not retired stories or stale missing-provider wording.

## Relevant Product Docs

- `docs/TOOL_REGISTRY.md`
- `docs/HARNESS_AUDIT.md`
- `docs/IMPROVEMENT_PROTOCOL.md`
- `docs/HARNESS_COMPONENTS.md`

## Acceptance Criteria

- Repo-local validation capabilities used by orchestrated work are modeled clearly
  enough that `query tools --capability <name> --status present` or the story
  verification contract explains the available proof path.
- The `coverage` and `browser-e2e` capability gaps are resolved by registering
  real providers, documenting why they are intentionally inactive, or replacing
  the stale capability expectation with the correct current proof source.
- Retired stories with leftover verification commands no longer inflate audit
  drift unless the project intentionally wants retired proof commands audited.
- Implemented stories with known passing evidence, especially `US-066` and
  `US-067`, have durable verification state aligned with their story evidence.
- `harness-cli propose` no longer emits stale suggestions that contradict the
  current tool registry state, such as treating design-validation as absent
  when an appropriate review provider is registered and present.
- The cleanup keeps source-of-truth boundaries intact: durable records,
  markdown story packets, and committed changesets remain explainable after a
  fresh rebuild.

## Design Notes

- Commands: `tool register`, `tool check`, `query tools`, `audit`, `propose`,
  `story verify`, and `story verify-all`.
- Queries: inspect current providers by capability and audit drift categories
  before changing policy.
- API: no application API change in this story.
- Tables: likely uses existing `tool`, `story`, `trace`, and `backlog` tables;
  add schema only if audit semantics cannot be represented cleanly.
- Domain rules: retired stories are historical records; audit should not treat
  them the same as active or implemented stories unless a retained verification
  command is intentionally meaningful.
- UI surfaces: none.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-072 --unit 1 --integration 1 --e2e 0 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | Rust tests cover any changed audit, proposal, tool registry, or story verification semantics. |
| Integration | CLI smoke shows the intended provider state for design-validation, browser-e2e, coverage, and local build/test capabilities. |
| E2E | `scripts/bin/harness-cli propose` and `scripts/bin/harness-cli audit` no longer report stale validation-provider or retired-story drift. |
| Platform | `scripts/validate-changeset-rebuild.sh` proves durable story state survives replay. |
| Release | `cargo fmt --check`, `cargo test --workspace`, `cargo clippy --workspace -- -D warnings`, and `git diff --check` pass if Rust code changes. |

## Harness Delta

This story turns repeated validation-provider friction into a bounded Harness
improvement. The goal is not to add more ceremony; it is to make the existing
proof path visible so agents can ask Harness what is equipped instead of
rediscovering local validation commands from prior traces.

## Evidence

- Intake: `#175`
- Implemented cleanup:
  - `audit` ignores retired stories with leftover `verify_command` values, so
    `US-061` and `US-063` no longer inflate active verification drift.
  - `propose` suppresses the historical local-validation-provider friction once
    the current registry has present providers for `coverage`,
    `build-verification`, `browser-e2e`, `platform-smoke`, and
    `design-validation`.
  - Registered present providers:
    - `cargo-workspace-tests` for `coverage`.
    - A project build provider for `build-verification`.
    - A browser test provider for `browser-e2e`.
    - A platform smoke provider for `platform-smoke`.
    - A project review provider for `design-validation`.
  - Refreshed durable story verification for `US-066` and `US-067`; both now
    have `last_verified_result=pass`.
- Validation passed:
  - `cargo test -p harness-cli -- --nocapture`
  - `cargo build -p harness-cli`
  - `scripts/bin/harness-cli story verify US-067`
  - `scripts/bin/harness-cli story verify US-066`
  - `scripts/bin/harness-cli audit` reports `Entropy score: 0/100`.
  - `scripts/bin/harness-cli propose` no longer emits
    `Tool registry lacks entries for local validation capabilities`.
  - `scripts/bin/harness-cli story verify US-072`
  - `scripts/validate-changeset-rebuild.sh`
  - Fresh temp DB rebuild from `.harness/changesets` reports audit entropy
    `0/100`, generates no proposals, and passes `story verify US-072`.
