# 0023 Optional Consumer Ownership

Date: 2026-07-21

## Status

Accepted and active. Decision 0026 classifies the explicit-only onboarding
skill pair as core workflow guidance rather than a generic evaluation
consumer.

## Context

The repository-centered core no longer requires the Rust CLI or SQLite
lifecycle. The optional compatibility profile still exposes a versioned
machine protocol used by the independently released Symphony product. That
protocol includes consistent work-graph reads, atomic compare-and-set story
updates, isolated database snapshots, semantic operation logging, and
transactional changeset application.

Reduction Phase 5 originally described moving Symphony-facing work graphs,
compare-and-set updates, semantic changesets, traces, and evaluations into
optional extensions. Repository separation completed the physical product
move: `hoangnb24/symphony` now owns the runner, worktrees, selection, run state,
Harness adapter, PR/review flow, synchronization, UI, and product-specific
operational evidence. Harness still needs to distinguish that orchestration
policy from the generic integrity primitives supplied through protocol v1.

Moving atomic compare-and-set or changeset application into Symphony would
make the consumer responsible for Harness storage invariants. For example, a
read followed by an unguarded write could accept stale work after another
process changes its status. Keeping the atomic operation in Harness lets
Symphony choose its retry policy without weakening data integrity.

The source tree also has two scripts under `tests/evals/` that exercise the
default repository workflow and task authority. They are core regression tests,
not trace experiments or post-hoc agent evaluations. Their current location
obscures the extension boundary.

## Decision

Reduction Phase 5 separates optional consumers by ownership:

1. `repository-harness` core owns the repository map, Git-native knowledge and
   plans, decision boundaries, and mechanical repository checks installed by
   default.
2. The optional Harness compatibility CLI owns generic storage-integrity and
   compatibility primitives while protocol v1 remains supported: discovery,
   consistent work-graph reads, isolated database snapshots, atomic CAS,
   semantic operation logging, transactional changeset application, replay,
   and recovery.
3. `hoangnb24/symphony` owns orchestration policy: work selection, polling,
   worktrees, run lifecycle, timeouts, retry/conflict handling, changeset
   coordination, PR/review synchronization, UI, and Symphony runtime evidence.
4. Consumer applications own application-specific runtime commands, logs,
   metrics, reproduction fixtures, browser/CLI interaction, and end-to-end
   proof. Harness does not ship generic observability adapters.
5. Trace-scoring, context-scoring, benchmark, audit, and proposal material in
   this repository remains legacy compatibility/history. It is not installed
   by core and does not become an ordinary-work evaluation requirement.
6. Repository workflow and task-authority scripts are classified as core
   workflow regression tests, not optional evaluations.
7. A fresh core installation must contain no orchestration contract, Symphony
   runtime, CLI/database lifecycle, trace/scoring, benchmark, or evaluation
   payload. Mechanical installation proof enforces this boundary.
8. Protocol-v1 primitives are not removed or changed during Phase 5. Their
   removal requires a later versioned migration with consumer proof and a
   recovery window, as required by decision `0022`.

The resulting dependency direction is:

```text
ordinary repository
  -> Harness core files only

explicit orchestration user
  -> Symphony orchestration policy
  -> optional Harness protocol primitives
  -> target repository state

application evaluation
  -> real application, CI, PR, logs, metrics, and interface evidence
  -/-> mandatory Harness traces or scores
```

## Alternatives Considered

1. **Move all protocol behavior into Symphony.** Rejected because it would
   duplicate Harness storage rules, weaken atomicity, and break the released
   protocol contract.
2. **Keep Symphony policy documented as part of Harness.** Rejected because it
   restores two product owners and makes the generic template responsible for
   one orchestrator's lifecycle.
3. **Add orchestration and evaluation profiles to the Harness installer.**
   Rejected because the products already have independent repositories and
   releases; extra installer profiles would recreate ownership coupling.
4. **Move core workflow regression tests out as evaluations.** Rejected because
   they mechanically prove the default product contract and belong in normal
   pre-merge validation.

## Consequences

Positive:

- A default Harness install remains small and contains no orchestration or
  evaluation control plane.
- Symphony can evolve scheduling, retries, run artifacts, UI, and PR behavior
  on its own release cycle.
- Harness retains atomic guarantees needed by every compatible consumer.
- Evaluation uses evidence produced by real work rather than mandatory
  self-reported traces.

Tradeoffs:

- The optional CLI remains sizable during the protocol compatibility runway.
- Cross-repository compatibility tests remain necessary.
- Historical trace and benchmark documents remain visible through explicit
  compatibility/provenance discovery until later removal criteria are met.

## Follow-Up

- Maintain released Symphony-to-Harness protocol smoke coverage.
- Revisit protocol deletion only after a versioned consumer migration.
- Add evaluation tooling to the owning application or Symphony repository only
  when a concrete experiment requires it; do not add it to the core payload.
