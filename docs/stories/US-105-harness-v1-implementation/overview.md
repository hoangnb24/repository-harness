# US-105 Repository Harness V1 Implementation

Status: **Planned / gated**

This is the durable implementation initiative packet for the eight phases in
`docs/REFACTOR_PLAN.md`. It records intended work and required proof. It does
not claim that V1 code, tests, releases, pilots, compatibility dates, or
retention policy exist.

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
- US-104 reconciles the execution contracts but explicitly implements no V1
  product behavior.

No exact compatibility-window start date, exact end date, or archive-retention
policy has been approved. Cause and effect: without those values, an
implementer cannot know how long the bridge must be distributed or how long
recovery evidence must remain available; therefore no product implementation
in Phases 1-7 may begin. This packet is planning work and does not cross that
gate.

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
   after the approved window has actually closed and every approved
   support-exit and archive-retention condition is satisfied.

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
- `docs/stories/US-104-refactor-plan-execution-contracts/**`
- `docs/stories/US-105-harness-v1-implementation/**`

This packet maps those contracts into implementation and proof. Creating this
packet changes only the four US-105 files; it does not revise the accepted plan
or decision.

## Non-Goals

- Approving, estimating, or inventing compatibility-window dates.
- Choosing an archive-retention duration or support-exit policy without human
  approval.
- Claiming Phase 1 has begun merely because this planning packet exists.
- Implementing or changing source, tests, installers, scripts, workflows,
  Cargo metadata, lockfiles, schemas, manifests, payloads, or release assets.
- Running Harness bootstrap, CLI, database, migration, or changeset commands in
  this worktree.
- Modifying `.harness`, other stories, the refactor plan, decisions, or
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
