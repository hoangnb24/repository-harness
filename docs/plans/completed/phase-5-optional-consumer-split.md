# Phase 5 Optional Consumer Split

Date: 2026-07-21

## Status

Completed

## Outcome

Finish reduction Phase 5 by making Symphony the explicit owner of orchestration
policy and Symphony-specific operational evaluation while keeping only generic,
versioned integrity primitives in the optional Harness compatibility CLI.
Ordinary Harness installations contain neither orchestration nor evaluation
machinery, and repository validation proves that boundary.

## Context

- `docs/WORKFLOW.md` defines the repository-centered default.
- Decision `0009` makes `hoangnb24/symphony` the canonical orchestration
  product while retaining generic Harness protocol capabilities.
- Decision `0020` makes the ten-file core the default installation profile.
- Decision `0022` freezes legacy lifecycle writes while retaining protocol-v1
  compatibility during its published runway.
- `docs/contracts/harness-orchestration-v1.md` is the current consumer-neutral
  integrity boundary.
- The standalone Symphony repository already owns its scheduler, worktrees,
  run state, Harness adapter, changeset coordination, PR flow, UI, and product
  evaluation.

## Scope

In scope:

- Record the lasting ownership boundary for reduction Phase 5.
- Make Symphony the named owner of scheduling, run orchestration, conflict
  recovery policy, changeset coordination, PR/review sync, and its operational
  evaluation.
- Keep work-graph reads, atomic compare-and-set enforcement, transactional
  changeset application, and compatibility discovery in the optional Harness
  CLI while protocol v1 remains supported.
- Reclassify the current repository workflow checks so they are not presented
  as agent/trace evaluations.
- Add mechanical proof that the default install contains no orchestration,
  trace-scoring, benchmark, or evaluation payload.
- Keep historical Symphony and control-plane material reachable only through
  explicit compatibility/history paths.

Out of scope:

- Change or remove protocol-v1 behavior used by released Symphony.
- Rewrite or delete historical SQLite records, schemas, changesets, or E11
  migration evidence.
- Change Symphony source in this repository; it is already canonical in
  `hoangnb24/symphony`.
- Remove compatibility implementation before a versioned consumer migration.

## Approach

1. Publish a decision separating generic integrity primitives from orchestration
   and evaluation policy.
2. Update current product and compatibility discovery to point orchestration
   work to the standalone Symphony repository.
3. Move repository-workflow regression scripts from `tests/evals/` to a name
   matching their actual core-boundary role.
4. Add an install-boundary test proving the default payload contains no
   orchestration or evaluation surface, while explicit CLI installation retains
   the compatible protocol contract.
5. Run focused installer, documentation, boundary, protocol, and full pre-merge
   validation.

## Risks And Recovery

- **Protocol breakage:** do not remove or reshape protocol-v1 primitives.
  Recovery is a normal Git revert; no schema or state migration is performed.
- **Historical erasure:** retain E11 and compatibility records as provenance.
- **False split claim:** validate both the manifest and a fresh installed tree,
  not documentation alone.
- **Cross-repository drift:** point to the canonical Symphony repository and
  retain released cross-repository compatibility smoke tests.

## Progress

- [x] Confirm Phase 4 is merged and create the dedicated Phase 5 branch.
- [x] Inspect current Harness and Symphony ownership boundaries.
- [x] Publish the Phase 5 decision and update discovery.
- [x] Reclassify core workflow tests and add installation-boundary proof.
- [x] Run focused and repository-wide validation.
- [x] Record the result and move this plan to `docs/plans/completed/`.

## Decisions

- 2026-07-21: Treat work-graph reads, atomic CAS, and transactional changeset
  application as generic compatibility primitives. Symphony owns when and how
  to use them; moving atomicity out of Harness would weaken the published data
  integrity contract.
- 2026-07-21: Treat `tests/evals/test-repository-workflow.sh` and
  `test-task-authority.sh` as core workflow regression tests, not an optional
  observability-evaluation extension.

## Validation

- Focused proof: Phase 5 boundary, documentation contract, both workflow
  regressions, manifest-link proof, and Bash installer-mode suite passed.
- Integration or end-to-end proof: a fresh core install contained neither
  optional consumer; protocol-v1 native-artifact smoke and fresh-consumer
  changeset tracking passed.
- Repository-required checks: `scripts/validate-premerge.sh` passed against a
  fresh materialization of tracked core state, including 99 Rust tests, Clippy
  with warnings denied, reconstruction/recovery, installers, protocol,
  workflow, release, and post-merge recovery gates.
- Local-state caveat: the ignored upstream `harness.db` still differs from
  tracked replay in the `intake` table, as recorded by Phase 4. It was not
  mutated; authoritative tracked-state validation passed.

## Result

Complete. Symphony remains the independent owner of orchestration policy and
runtime evidence. Harness core installs neither orchestration nor evaluation
machinery. Generic atomic protocol primitives remain available only through
explicit compatibility selection, the old maturity/proposal-engine Phase 5 is
preserved as compatibility history, and mechanical validation enforces the
new boundary.
