# Execution Plan: Harness Self-Update Hardening

Date: 2026-07-22

## Status

Completed

## Outcome

Harness has one application-owned update workflow. It rejects downgrades and
release-identity mismatches, freezes every managed input across conflict
resolution, retains a remotely re-verifiable candidate, updates only the
repository-local executable, and gives installers the same resumable behavior.

## Context

- `docs/decisions/0025-latest-release-self-update-and-human-directed-conflicts.md`
- `docs/ARCHITECTURE.md`
- `crates/harness/src/application/service.rs`
- `crates/harness/src/infrastructure/release_handoff.rs`
- `scripts/install-harness.sh` and `scripts/install-harness.ps1`
- Independent review of the initial feature branch found split orchestration,
  incomplete drift detection, downgrade paths, weak staged-candidate identity,
  wrong-executable replacement, and non-resumable installer conflicts.

## Scope

In scope:

- Application-level self-update orchestration with infrastructure ports.
- Exact release-tag, candidate-version, installed-version, and executable-target
  checks.
- Full update-plan input freezing and continuation drift rejection.
- Remote re-verification of retained candidates.
- Resumable installer conflict behavior.
- Recovery for core/binary version skew and focused cross-surface tests.

Out of scope:

- Background updates, multiple release channels, or a new signing authority.

## Approach

1. Move update policy out of the release adapter and `main.rs` into an
   application service; leave download, process, and replacement mechanics in
   infrastructure.
2. Bind candidates to the exact pointer version, prevent application-level
   downgrades, and require the running executable to be the selected
   repository's installed binary before mutation.
3. Store frozen bytes for the complete managed path union, verify them before
   continuation, and reject any newly introduced conflict.
4. Make installers run the staged candidate before binary replacement, retain
   it on conflict, and automatically continue a pending session on rerun.
5. Add regression tests, update product/decision truth, run focused proof, then
   run the repository validation ladder.

## Risks And Recovery

- A refactor could weaken the existing file transaction. Keep the current
  `InstallationStatePort::apply` transaction unchanged and test its boundaries.
- A conflict during the one-time bootstrap may be driven by an executable that
  predates `--continue`. The installer retains the candidate and automatically
  invokes continuation when rerun after the resolution is edited.
- If executable replacement fails after core activation, keep the verified
  candidate durable so the next update or installer run can finish the binary
  phase without downgrading core state.
- Recovery before release is branch-local: revert this feature branch. Consumer
  state schemas are not released or migrated in place.

## Progress

- [x] Record review findings and the hardening sequence.
- [x] Refactor self-update orchestration and trust/version checks.
- [x] Freeze and validate the complete conflict-session plan.
- [x] Unify installer conflict and continuation behavior.
- [x] Add proof and run validation.

## Decisions

- 2026-07-22: Application owns update policy; infrastructure exposes candidate,
  process, filesystem, and executable-replacement capabilities.
- 2026-07-22: A local checksum stored beside a candidate is not a trust anchor;
  continuation re-fetches the checksum for the session's exact immutable
  release identity.
- 2026-07-22: Any managed-file drift after conflict staging invalidates the
  session plan. Harness will not silently recalculate an unreviewed plan.

## Validation

- Focused proof: `cargo test -p harness --locked`, strict Clippy, and macOS,
  Linux, and Windows-target Rust checks pass.
- Integration or end-to-end proof: process-level tests prove exact release
  identity, remotely rechecked retained candidates, wrong-executable refusal,
  version-skew recovery, real repository-local Unix replacement,
  complete-input drift rejection, and downgrade refusal.
  The Bash installer test proves conflict retention and installer-driven
  continuation before binary replacement.
- Repository-required checks: `scripts/validate-premerge.sh` passes from a clean
  temporary checkout bootstrapped from tracked compatibility state. Focused
  installer, manifest, documentation, coherence, and release contracts also
  pass in the source checkout.

## Result

Complete. Self-update policy now lives in `SelfUpdateApplication`; the interface
routes commands and `main.rs` only composes dependencies. Exact release and
binary versions must agree, neither candidate nor hidden candidate mode can
downgrade installed provenance, and mutation requires the selected repository's
local executable. Conflict continuation freezes every managed input, remotely
re-verifies the retained candidate, and verifies the snapshot again under the
application lock before activation.

Installers execute candidates before replacement. A conflict leaves the old
binary unchanged and retains the candidate; rerunning after resolution
continues the exact pending version. A durable candidate also lets a later
update repair rare core/executable version skew before any further core update.
