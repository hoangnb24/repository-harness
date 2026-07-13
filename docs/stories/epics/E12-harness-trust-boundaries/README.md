# E12 Harness Trust Boundaries

## Status

in progress

## Intake

- Current local intake: `#17` (numeric ids are local to the active Harness DB).
- Type: `harness_improvement`.
- Lane: `high-risk`.
- Story: `US-101 Harness Trust Boundary Hardening`.
- Governing decisions:
  `docs/decisions/0005-prebuilt-rust-harness-cli.md` and
  `docs/decisions/0008-self-improving-harness-lifecycle.md`.

## Goal

Make the Harness claims that affect agent authority mechanically true: only
fresh proof can implement a story, query paths cannot mutate state, the local
CLI and database disclose revision drift before their output is trusted,
context is retrieved by task shape, and repository checks run before merge.

## Starting Evidence

- `story update --status implemented` can produce an implemented story with no
  verification command or proof, after which `audit` reports entropy `0/100`.
- `query sql` accepts mutating statements through a command classified as a
  read and emits no semantic operation record.
- A source checkout can pair current docs and Rust source with an older ignored
  `scripts/bin/harness-cli` and database schema.
- The mandatory bootstrap reads the full operating manual and historical matrix
  before the work lane is known.
- Release validation runs after merge/tagging, and the durable audit does not
  check documentation, command, version, or shim parity.

## Ordered Workstreams

1. Close story-completion bypasses.
2. Make SQL query execution physically read-only.
3. Add bootstrap coherence checks and focused matrix views.
4. Make context and authority rules task-shaped and keep generated shims equal.
5. Add pre-merge contract/document checks and representative task evaluations.

Each workstream is validated and committed independently. Later workstreams may
depend on earlier invariants but must not weaken them.

## Exit Signal

The full verification wrapper passes; negative fixtures prove every former
bypass fails; a fresh or stale source checkout receives an actionable coherence
result; read-only tasks require no Harness mutation; and pull requests run the
same core contract checks before merge that releases rely on afterward.

## Non-Goals

- Reintroduce Symphony product source or runtime into this repository.
- Replace SQLite, Clap, the semantic changeset protocol, or the external
  orchestration contract.
- Claim production application observability from Harness task traces.
- Automatically accept, merge, or deploy changes.
