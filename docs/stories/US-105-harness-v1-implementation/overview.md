# US-105 Repository Harness V1 Implementation

Status: **Implementation in progress / Phase 1 accepted / Phase 2 validated, re-acceptance pending / Phase 3 blocked**

This is the durable implementation initiative packet for the eight phases in
`docs/REFACTOR_PLAN.md`. Phase 1 contract, fixture, inventory, and enforcement
proof is accepted by US-106. The separate pure V1 core and its hardened Phase 2
boundary pass the full US-107 validation, but review re-acceptance is pending
after commit `9b84ba8` was rejected. Atomic installer mutation, bridge conversion
writes, production release, pilots, and Phase 3-8 acceptance do not exist.
Decision 0012 supplies authorization policy; Decision 0013 and US-106 supply
accepted Phase 1. US-107 supplies validated Phase 2 implementation evidence,
not authority to self-approve the rejected review.

## Current Behavior

The repository currently implements Harness V0:

- `scripts/bin/harness-cli[.exe]` exposes the V0 operational grammar.
- `crates/harness-cli/` owns the Rust CLI and SQLite-backed lifecycle behavior.
- `scripts/schema/001-init.sql` through `013-changeset-content-sha.sql` define
  the current durable schema history.
- Bash and PowerShell installers distribute the V0 documents, schemas, and
  prebuilt CLI for the current five platform labels.
- V0 ordinary work uses a local SQLite database and may emit semantic
  changesets.

The accepted V1 direction now has the Phase 1 contract layer and the Phase 2
pure core runtime:

- `docs/REFACTOR_PLAN.md` defines the eight implementation phases.
- Decision 0011 accepts a separate, time-bounded `harness-v0-migrate` bridge.
- Decision 0012 accepts the exact compatibility, retention, support, and
  retirement policy and opens Gate G0.
- Decision 0013 accepts the threshold trust, bootstrap, archive
  confidentiality, exact V0 capture, and availability contract.
- `docs/contracts/v1/`, `release/contracts/v1/`, and deterministic fixtures
  freeze the schemas, grammars, ledgers, V0 inputs, and negative boundaries.
- `scripts/verify-v1-phase1-contracts.sh` mechanically enforces Phase 1 and is
  part of premerge.
- `crates/harness-core/` builds the separate `scripts/bin/harness[.exe]`
  identity with exactly the six frozen commands. Phase 2 audit/status/version
  inspect declared V1 state; authenticated preview plans are deterministic;
  mutation requests refuse because Phase 3 recovery is absent.
- `scripts/verify-v1-phase2-core.sh` proves live help/source/contract parity,
  payload and path rejection, deterministic output, no-exec audit, no-op
  mutation boundaries, core-live/bridge-absent binding, and the unpromoted
  release workflow guard.
- US-104 reconciles the execution contracts but explicitly implements no V1
  product behavior.

The approved compatibility window is `2027-01-01T00:00:00Z` through
`2027-12-31T23:59:59Z`, inclusive. Local conversion archives are retained
indefinitely, bridge release assets are retained through
`2028-06-30T23:59:59Z`, inclusive, and Phase 8 is eligible no earlier than
`2028-01-01T00:00:00Z` after every closure condition passes. Cause and effect:
those values resolve Gate G0. Phase 1 froze the contract boundary and Phase 2
implemented and validated the pure core against it. Phase 3 remains blocked
until Phase 2 review re-acceptance. Phases 3-8 remain unimplemented and
dependent on preceding phase acceptance.

For example, the presence of `.harness/` cannot currently authorize a V1
conversion. It may contain V0 changesets, another tool's metadata, or unrelated
files. The future bridge must first prove a recognized V0 signature, preserve
unknown state, and create an export and archive before it changes any selected
target path.

## Target Behavior

After the gated initiative completes, Repository Harness has two deliberately
separate product paths during the approved compatibility window and one
permanent path afterward:

1. The permanent V1 binary is `scripts/bin/harness[.exe]`, with exactly six
   top-level commands: `install`, `update`, `audit`, `scaffold`, `status`, and
   `version`.
2. V1 installs or maps visible repository-native knowledge assets and records
   only provenance, role state, ownership, digests, and recovery metadata. It
   creates no task, run, prompt, result, trace, telemetry, scheduler, SQLite,
   or semantic-changeset state.
3. Ordinary target work uses the target's own docs, scripts, tests, CI, review,
   runtime feedback, deployment, and recovery. It requires no Harness command.
4. The separately versioned `scripts/bin/harness-v0-migrate[.exe]` bridge reads
   only its published V0 range, produces a neutral export and checksummed
   archive, and uses an untracked operation journal for `apply`, `resume`, and
   safe `rollback`.
5. V1 commits conversion success only after the archive/export, selected file
   operations, and deterministic V1 audit succeed. Before that atomic commit,
   no manifest may claim success.
6. Release promotion depends on deterministic product proof and fixed
   release-only pilot cards P0-P7. Template presence alone is insufficient.
7. V0 operational code and payload leave the default product only in Phase 8,
   no earlier than `2028-01-01T00:00:00Z`, after the approved window has
   actually closed and every support, recovery, security, archive-integrity,
   asset-retention, and separate authorization/validation condition is
   satisfied. Phase 8 never automatically deletes or relocates a local archive.

Concrete role example: if a V0 repository already has a useful `AGENTS.md`, V1
may record the `agent_map` role as `active`, `managed-block`, `v0-adopted`, and
`required=true`. An update may review or replace only the marker-delimited V1
block. It may not rewrite the target-owned text around that block. If required
completion markers remain, installation still succeeds but readiness is
`unresolved`; audit returns exit 2 rather than guessing content or claiming the
repository ready.

## Affected Users

- Repository Harness implementers, who need phase ordering, binary boundaries,
  contracts, stop conditions, and reviewable commit boundaries.
- Release and support maintainers, who must publish authenticated artifacts,
  the approved compatibility statement, platform proof, and retirement proof.
- Existing V0 repository maintainers, whose databases, changesets, documents,
  and unknown metadata must remain recoverable and unmodified by the reader.
- Brownfield and fresh V1 adopters, whose target-owned files and chosen paths
  must be preserved.
- Pilot repository owners and evaluators, who must authorize release-only
  evaluation and receive fixed cards, environment locks, and fully accounted
  intervention records.
- Agents doing ordinary target work, who must not acquire a mandatory Harness
  command or V1 operational database workflow.

## Affected Product Docs

The accepted behavior is defined by:

- `docs/REFACTOR_PLAN.md`
- `docs/decisions/0011-time-bounded-v0-conversion.md`
- `docs/decisions/0012-v0-compatibility-window-and-retention.md`
- `docs/decisions/0013-v1-security-and-v0-capture-contract.md`
- `docs/contracts/v1/**`
- `release/contracts/v1/**`
- `docs/stories/US-104-refactor-plan-execution-contracts/**`
- `docs/stories/US-105-harness-v1-implementation/**`
- `docs/stories/US-106-v1-phase1-contracts-and-release-inventory/**`
- `docs/stories/US-107-v1-pure-core/**`

This packet maps those contracts into implementation and proof. Decision 0012
authorizes the schedule/retention boundary; Decision 0013 plus US-106 provide
Phase 1 acceptance, and US-107 provides Phase 2 implementation/validation with
review re-acceptance pending. They do not provide Phase 3 mutation/recovery or
later phase proof.

## Non-Goals

- Changing Decision 0012's dates, retention, support, or retirement policy
  without a new explicit human decision.
- Claiming a later phase has begun or passed from Phase 1 contract proof.
- Implementing V1 runtime/installer behavior, bridge conversion writes,
  production signing/publishing, pilots, or Phase 2-8 behavior in Phase 1.
- Running Harness bootstrap, CLI, database, migration, or changeset commands in
  this worktree.
- Modifying `.harness`, unrelated stories or decisions, or
  `repomix-output.xml`.
- Creating a permanent V1 `migrate` command, an alias between V0 and V1
  binaries, or automatic V1-to-V0 downgrade.
- Moving or renaming useful target documents for cosmetic consistency.
- Inferring ownership from a pathname or automatically patching target-owned
  adopted or brownfield-mapped content.
- Making V1 audit execute target tests, compilers, CI, deployment checks,
  runtime processes, or semantic prose evaluation.
- Adding hosted telemetry, issue/PR automation, automatic work
  classification, a daemon, scheduler, universal score, or language-specific
  target architecture to V1 core.
- Running release-only pilots during ordinary work or changing any pilot
  repository without its owner's separate authorization.
- Publishing, pushing, tagging, releasing, opening a PR, or changing Herdr
  resources as part of this packet.
