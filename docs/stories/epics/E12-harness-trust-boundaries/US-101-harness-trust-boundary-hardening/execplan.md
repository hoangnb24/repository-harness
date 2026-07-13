# Exec Plan

## Goal

Turn the audit's highest-risk findings into enforced, regression-tested Harness
invariants and deliver them as a reviewable sequence of logical commits.

## Scope

In scope:

- Story lifecycle mutation and completion semantics.
- SQL query effect isolation.
- Source-checkout CLI/database coherence and matrix retrieval shape.
- Agent context, request-class authority, and generated shim parity.
- Pull-request contract/document checks and representative task evaluations.
- Documentation and maturity claims directly coupled to those behaviors.

Out of scope:

- Symphony implementation or release automation.
- New application UI, browser, metrics, or tracing products.
- Unrelated refactors of the large Rust modules.
- Automatic merge, deployment, or external cleanup.

## Risk Classification

Risk flags:

- Public contracts.
- Existing behavior.
- Weak proof around instruction/runtime parity.
- Cross-platform installer behavior.
- Durable task-state integrity.

Hard gates:

- Validation requirements must not be weakened.
- Protocol-v1 consumers must retain compatible JSON envelopes and capabilities.
- Historical reconstruction must not be confused with interactive mutation.

## Work Phases

1. Synchronize `main`, rebuild the release CLI, and migrate local state.
2. Create the hardening branch and durable story packet.
3. Close generic completion bypasses and commit focused proof.
4. Enforce read-only SQLite queries and commit focused proof.
5. Add coherence checks and focused matrix retrieval; commit focused proof.
6. Simplify context/authority rules and unify instruction shims; commit proof.
7. Add pre-merge contract/doc/eval enforcement; commit proof.
8. Run the full release-grade validation wrapper, push, and open a pull request.

## Stop Conditions

Pause for human confirmation if:

- A required fix needs a breaking protocol-v1 response or capability change.
- Historical state would need deletion or rewriting.
- Validation requirements would need to be weakened.
- The fix would reintroduce Symphony source/runtime ownership.
- A destructive external action beyond the requested branch, push, and PR is
  required.
