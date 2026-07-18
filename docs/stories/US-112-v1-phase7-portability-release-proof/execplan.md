# US-112 V1 Phase 7 Portability And Release Proof Exec Plan

Status: **In progress: gate opened by Decision 0016; implementation pending**

## Goal

Implement the deterministic portability and pre-promotion proof stack while
keeping tags, publishing, production signing, Phase 7 acceptance, and Phase 8
closed.

## Scope

In scope:

- Decision 0016 and the Phase 7 story packet.
- Exact fixture and platform matrices.
- Five-platform build/authentication/identity proof.
- Bash, PowerShell, and direct-binary parity.
- Promotion refusal when deferred Phase 6 or Phase 7 evidence is incomplete.

Out of scope:

- Live P0-P7 execution and owner signatures.
- Release tags, publishing, promotion, or production keys.
- V0 removal or compatibility-window changes.

## Risk Classification

Risk flags:

- Public contracts.
- Cross-platform behavior.
- Existing release and installer behavior.
- Weak proof until the complete platform matrix executes.
- Multi-domain release, bridge, core, installer, and workflow boundaries.

Hard gates:

- Validation requirements may not be weakened.
- No target mutation before artifact authentication and platform support
  checks.
- No promotion until deferred Phase 6 and complete Phase 7 proof both pass.

## Planning Mode

This high-risk story and its resume capsule own the cross-platform release
work. Ordinary repository tasks do not require this plan.

## Work Phases

1. Freeze the Phase 6 framework revision and Decision 0016 boundary.
2. Inventory existing fixtures, workflows, artifact names, and platform gaps.
3. Define closed Phase 7 evidence schemas and exact candidate identity.
4. Implement the fixture matrix and local platform-independent negatives.
5. Implement five-platform build, installer, and direct-binary proof.
6. Verify identity/equivalence and promotion refusal; obtain independent
   review before any separate release action.

## Resume Capsule

- Objective: implement Phase 7 portability and release proof without promotion.
- Completed: Decision 0016 accepted; intake #9 recorded; US-112 packet opened.
- Remaining: inventory, schemas, fixtures, runners, workflows, five-platform
  execution, identity lock, and independent review.
- Exact next action: `inspect .github/workflows and tests/release for the current five-platform artifact matrix and immutable promotion guards`
- Validation ladder: documentation and JSON checks; focused fixture/proof
  tests; installer/direct-binary tests; five-platform workflow; full premerge;
  stop at the first failed boundary.
- Decisions and assumptions: framework acceptance opens engineering only;
  deferred live experiments remain mandatory before acceptance/promotion.
- Blockers and owners: external pilot custody/signatures remain with repository
  owners; production release authority remains with release maintainers.
- Working state: branch `refactor/harness-v1` at the Decision 0016 opening
  changeset; no tag, publish, or live pilot mutation.

## Stop Conditions

Pause for human confirmation if:

- a supported-platform claim would require unavailable execution evidence;
- a production key, tag, publish, or remote mutation becomes necessary;
- a fixture would weaken an earlier security/recovery contract;
- the deferred Phase 6 obligation would need removal rather than deferral.
