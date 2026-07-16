# US-105 Repository Harness V1 Implementation

Status: **Implementation authorized / Phase 1 ready**

This is the durable implementation initiative packet for the eight phases in
`docs/REFACTOR_PLAN.md`. It records intended work and required proof. It does
not claim that V1 code, tests, releases, pilots, or phase acceptance exists.
Decision 0012 supplies authorization policy, not implementation evidence.

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

The accepted V1 direction exists only in planning artifacts:

- `docs/REFACTOR_PLAN.md` defines the eight implementation phases.
- Decision 0011 accepts a separate, time-bounded `harness-v0-migrate` bridge.
- Decision 0012 accepts the exact compatibility, retention, support, and
  retirement policy and opens Gate G0.
- US-104 reconciles the execution contracts but explicitly implements no V1
  product behavior.

The approved compatibility window is `2027-01-01T00:00:00Z` through
`2027-12-31T23:59:59Z`, inclusive. Local conversion archives are retained
indefinitely, bridge release assets are retained through
`2028-06-30T23:59:59Z`, inclusive, and Phase 8 is eligible no earlier than
`2028-01-01T00:00:00Z` after every closure condition passes. Cause and effect:
those values resolve Gate G0, so Phase 1 is ready to begin; no implementation
has begun, and Phases 2-8 remain unstarted and dependent on preceding phase
acceptance.

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
- `docs/stories/US-104-refactor-plan-execution-contracts/**`
- `docs/stories/US-105-harness-v1-implementation/**`

This packet maps those contracts into implementation and proof. Decision 0012
and the synchronized refactor plan authorize only the Phase 1 starting state;
they do not supply product or phase-acceptance evidence.

## Non-Goals

- Changing Decision 0012's dates, retention, support, or retirement policy
  without a new explicit human decision.
- Claiming Phase 1 has begun or passed merely because Gate G0 is approved.
- Implementing or changing source, tests, installers, scripts, workflows,
  Cargo metadata, lockfiles, schemas, manifests, payloads, or release assets.
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
