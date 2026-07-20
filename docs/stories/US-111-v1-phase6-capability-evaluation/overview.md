# US-111 V1 Phase 6 Capability Evaluation

> Current release-gate note (Decision 0017): this detailed P0-P7 framework is
> optional for V1 promotion. The historical framework and baselines remain
> intact; one fixed-condition dogfood comparison is now required instead.

Status: **Framework accepted by owner for sequencing; live candidate efficacy
deferred; Phase 7 engineering opened without acceptance/promotion; Phase 8 not
started**

## Current Behavior

Phase 5 is accepted at its authenticated pre-candidate baseline gate. The two
enrolled repository scopes have fixed P0-P7 cards, immutable starting
revisions, locked environments, authenticated custody, and honest baseline
outcomes. Those records do not contain Phase 6 candidate subjects.

US-111 began with a docs-only authority and template slice. The combined stack
now also contains evaluator, warm-capture, and evidence-verifier scripts; closed
schemas, a baseline lock, and an evidence index; Rust test-only release
expectations; and the V0 installer-manifest entry for the agent map. The updated
portable templates provide bounded routes, exact resume actions, validation
ladders, and target-owned contracts without changing production runtime or CLI
semantics.

## Target Behavior

The initial docs-only slice established authority and neutral portable
templates. The implemented framework and regression integration now provide:

1. Decision 0015 defines clean `cold-clone` custody and isolated
   `warm-v0-copy` custody, pre-candidate capture, live-state immutability,
   sensitive-byte exclusions, identity separation, and external signing.
2. Portable templates route agents to target-owned planning, architecture,
   validation, feedback, and maintenance sources without choosing a stack or
   requiring ordinary Harness operations.
3. Resume capsules name one exact next action and an ordered validation ladder.
4. Invariant, feedback, repeated-correction, and gardening contracts name a
   target owner and repository-native durable home.
5. Evaluator, capture, and verifier scripts plus closed schemas enforce custody,
   identity, comparison, and release-boundary rules without admitting live
   evidence by directory prefix.
6. Rust test-only release expectations and the V0 installer manifest keep the
   framework aligned with the earlier release stack without changing runtime,
   CLI, or installer command semantics.
7. Decision 0016 accepts this framework for sequencing; the fixed live cards
   remain mandatory efficacy evidence before Phase 7 acceptance or promotion.

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
- Release maintainers get an honest framework-accepted/deferred-efficacy
  signal, not Phase 7 acceptance or promotion authority.

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
- Changing production runtime or CLI semantics, installer command semantics, or
  production workflows.
- Requiring a language, framework, package manager, repository layout, or
  Harness-only plan during ordinary work.
- Claiming live Phase 6 efficacy, Phase 7 acceptance, promoting/publishing/
  tagging a release, or advancing Phase 8. Decision 0016 separately opens only
  Phase 7 engineering.
