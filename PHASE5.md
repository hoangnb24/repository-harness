# Reduction Phase 5 — Optional Consumer Split

Complete on 2026-07-21.

## Outcome

Symphony is the canonical owner of orchestration policy and Symphony-specific
runtime evaluation. Harness core remains repository-centered and installs no
orchestration or evaluation machinery. Generic atomic protocol primitives stay
in the explicitly selected compatibility CLI for the published protocol-v1
window.

## Ownership Matrix

| Capability | Owner | Default Harness install |
| --- | --- | --- |
| Repository map, plans, decisions, mechanical checks | Harness core | Included |
| Work-graph consistency, atomic CAS, changeset apply/replay | Harness compatibility CLI | Excluded |
| Selection, polling, worktrees, runs, retry policy, PR/sync, UI | [Symphony](https://github.com/hoangnb24/symphony) | Excluded |
| Application logs, metrics, fixtures, interface and E2E proof | Consumer application | Excluded |
| Legacy trace scoring, audit, proposal, benchmark material | Compatibility/history | Excluded |

## Cause And Effect

```text
Symphony reads revisioned work through protocol v1
  -> Symphony chooses a runnable item
  -> Harness atomically accepts or rejects the guarded mutation
  -> Symphony decides whether to retry, skip, or stop
```

Harness owns the atomic guarantee. Symphony owns the orchestration decision.
This prevents stale writes without making the generic repository template own
a scheduler.

## Evidence Matrix

| Requirement | Evidence |
| --- | --- |
| Symphony owns product orchestration | Decision `0009`, E11 cutover evidence, and the independently released `hoangnb24/symphony` repository |
| Generic primitives remain compatible | `docs/contracts/harness-orchestration-v1.md` and native-artifact protocol smoke |
| Core contains neither optional consumer | `tests/boundary/test-phase5-optional-consumer-split.sh` installs and inspects a fresh core |
| Core regression tests are not mislabeled evaluations | `tests/workflow/test-repository-workflow.sh` and `tests/workflow/test-task-authority.sh` |
| Legacy evaluation machinery cannot regain default authority | `docs/WORKFLOW.md`, compatibility headers, and exact installer manifests |

## Completion Boundary

Phase 5 does not delete protocol v1, SQLite history, or legacy commands. Phase 4
proved those surfaces still have compatibility consumers. Deletion belongs to
a later phase after a versioned migration and recovery window.

The superseded maturity/proposal-engine roadmap is preserved at
`docs/compatibility/phase-5-evolution-infrastructure-legacy.md`.
