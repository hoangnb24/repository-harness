# US-111 V1 Phase 6 Capability Evaluation

Status: **In progress: authority and portable framework implemented; live
candidate cards and Phase 6 acceptance pending; Phases 7-8 not started**

## Current Behavior

Phase 5 is accepted at its authenticated pre-candidate baseline gate. The two
enrolled repository scopes have fixed P0-P7 cards, immutable starting
revisions, locked environments, authenticated custody, and honest baseline
outcomes. Those records do not contain Phase 6 candidate subjects.

The existing portable story and validation templates still contain V0 Harness
lifecycle instructions and do not give a target a bounded agent map, an exact
resume action, a validation ladder, or target-owned contracts for invariants,
feedback, repeated corrections, and gardening.

## Target Behavior

This slice starts Phase 6 by establishing the authority and neutral capability
framework:

1. Decision 0015 defines clean `cold-clone` custody and isolated
   `warm-v0-copy` custody, pre-candidate capture, live-state immutability,
   sensitive-byte exclusions, identity separation, and external signing.
2. Portable templates route agents to target-owned planning, architecture,
   validation, feedback, and maintenance sources without choosing a stack or
   requiring ordinary Harness operations.
3. Resume capsules name one exact next action and an ordered validation ladder.
4. Invariant, feedback, repeated-correction, and gardening contracts name a
   target owner and repository-native durable home.
5. Phase 6 stays in progress until the already fixed live cards are instantiated
   and evaluated under signed comparable conditions.

Cause and effect: an interrupted task no longer leaves the next agent with
"continue implementation." The capsule instead names, for example, "run the
target's focused check for the changed boundary; if it passes, inspect the
broader check," along with the exact path and stop-on-failure ladder. A later
agent can act without reconstructing the prior conversation.

## Affected Users

- Target repository owners select paths, commands, ownership, and exceptions.
- Agents get bounded discovery and resumable work state from ordinary
  repository files.
- Evaluation custodians get an explicit clean-versus-warm custody choice and
  closed evidence identity rules.
- Release maintainers get an honest in-progress Phase 6 signal, not acceptance
  or promotion authority.

## Affected Product Docs

- `docs/decisions/0015-phase6-cold-warm-evaluation-custody.md`
- `docs/templates/agent-map.md`
- `docs/templates/story.md`
- `docs/templates/validation-report.md`
- `docs/templates/high-risk-story/{execplan,validation}.md`
- `docs/REFACTOR_PLAN.md`
- `docs/stories/US-105-harness-v1-implementation/**`
- `docs/TEST_MATRIX.md`

## Non-Goals

- Running, editing, or inventing live P0-P7 candidate evidence.
- Accessing or changing a pilot repository, private snapshot, archive, raw
  database, external trust registry, or key.
- Adding evaluator scripts, schemas, Rust code, installer behavior, or
  production workflows.
- Requiring a language, framework, package manager, repository layout, or
  Harness-only plan during ordinary work.
- Claiming Phase 6 acceptance, opening Phase 7, promoting/publishing/tagging a
  release, or advancing Phase 8.
