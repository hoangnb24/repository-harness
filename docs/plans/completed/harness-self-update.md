# Execution Plan: Harness Self-Update And Conflict Resolution

Date: 2026-07-22

## Status

Completed

## Outcome

An installed `harness` can discover and verify the published immutable
`harness-v*` GitHub release, hand the update to that candidate, and either
apply its embedded core atomically or leave an agent-resolvable conflict
session that can be continued or aborted after human direction.

## Context

- `README.md` currently presents `harness update` as the future-upgrade command.
- `docs/product/installation-profiles.md` defines the all-or-nothing core update
  contract.
- `crates/harness/` already owns embedded distributions, three-way merge,
  transactional workspace activation, backups, and provenance.
- The current executable cannot discover a later release, and overlapping
  merges report a conflict without retaining the three merge inputs.

## Scope

In scope:

- Published core GitHub-release discovery and checksum-verified candidate
  download.
- Candidate handoff without executing a remote shell installer.
- Direct update from the installed base to the candidate's embedded payload.
- Durable, ignored conflict packets containing base, local, incoming, and
  agent-editable resolved files.
- `harness update --continue` and `harness update --abort`.
- Drift detection and atomic application after every conflict is resolved.
- Focused application, filesystem, CLI, and release-handoff proof.

Out of scope:

- Background updates, multiple channels, telemetry, delta patches, custom
  signing infrastructure, general upgrade graphs, and automated semantic
  conflict decisions.

## Approach

1. Extend the merge result and installation-state ports so a conflicting merge
   retains conflict-marker content and a resumable resolution session.
2. Make update planning stage conflicts, make continuation consume resolved
   content only after drift checks, and make abort remove only staged state.
3. Add a release-source boundary that resolves the latest candidate, verifies
   its checksum, and invokes the candidate for preview, apply, continue, or
   abort while keeping the installed executable unchanged until success.
4. Update command output and product documentation, then run focused and full
   repository validation.

## Risks And Recovery

- A failed or conflicted update must leave managed files, provenance, and the
  installed executable unchanged. The existing transaction journal protects
  activation; the new session stores only ignored staging state.
- A workspace file changed after conflict detection must reject continuation
  and preserve the session for inspection or abort.
- A candidate checksum or version mismatch must fail before candidate
  execution.
- Recovery: run `harness update --abort` to remove staged resolution state. If
  implementation validation fails before release, revert this feature branch;
  existing installed cores remain compatible because no released schema is
  changed in place.

## Progress

- [x] Create the feature branch and record the accepted behavior.
- [x] Implement resumable conflict staging, continuation, and abort.
- [x] Implement latest-release candidate discovery, verification, and handoff.
- [x] Add command output, documentation, and focused tests.
- [x] Run repository validation and record the result.

## Decisions

- 2026-07-22: Trust immutable GitHub release assets plus their published
  SHA-256 sidecars for the initial implementation; custom channels and signing
  remain deferred.
- 2026-07-22: Harness owns detection, staging, drift checks, and atomic apply;
  an agent edits the staged resolution only after obtaining human direction.
- 2026-07-22: Conflict detection writes no managed workspace file and does not
  replace the installed executable.

## Validation

- Focused proof: `cargo test -p harness --locked` and
  `cargo clippy -p harness --all-targets --locked -- -D warnings` pass.
- Integration or end-to-end proof: the real CLI downloads a fixture release,
  verifies its checksum/version, stages a conflict without changing live
  authority, retains the exact candidate, and applies an agent-edited
  resolution through `--continue`.
- Repository-required checks: one source-worktree run reached the pre-existing
  ignored `harness.db` parity mismatch; a clean temporary checkout bootstrapped
  from tracked state and passed `scripts/validate-premerge.sh` after the final
  review refinements.

## Result

Complete. `harness update` now resolves the published core release, verifies
and hands off to that candidate, and replaces the executable after successful
core activation. Overlapping edits retain the verified candidate and four-way
resolution packet without changing live managed files. An agent can explain
the semantic conflict, obtain human direction, edit the staged RESOLVED copy,
preview with `--continue --dry-run`, and apply with `--continue`; unresolved
markers, input tampering, and live drift fail closed, while `--abort` removes
only staged state.

Focused Rust, architecture, CLI handoff, installer, documentation, and release
tests pass. The full pre-merge repository contract passes from a clean checkout
materialized from tracked compatibility state. The source worktree's ignored
historical `harness.db` remains untouched and still differs from tracked
materialization in `intake`; that pre-existing local-state condition is not a
product-change failure.

Post-review hardening is recorded in `harness-self-update-hardening.md`; it
supersedes this plan's initial orchestration, drift, candidate-retention, and
installer-replacement details.
