# Overview

## Current Behavior

The accepted V1 refactor plan established a template-first direction, but still
described a permanent V1 conversion command and did not fully separate
installation success from target readiness, V0 database semantics from V1
audit, or pilot evidence from ordinary work.

## Target Behavior

The planning artifacts define an execution-complete V1 contract without
implementing it: deterministic role/asset state, distinct V0/V1 identities,
the accepted time-bounded V0 bridge, recoverable conversion, dependency-ordered
phases, authenticated payload boundaries, and release-only pilot evaluation.

This change creates no V1 operational state or product telemetry. Separately,
the current repository's V0 workflow evidence is recorded externally by
orchestration in the isolated .harness/refactor-plan.db planning database:
intake #3 and story US-104 already exist there, and the orchestrator records
Decision 0011 and the final trace. That evidence does not make the V1 product
operational.

## Affected Users

- V1 implementers and release maintainers.
- Existing V0 repository maintainers using the future bridge.
- Pilot evaluators and target-repository maintainers.

## Affected Product Docs

This high-risk packet owns exactly three surfaces:

- docs/REFACTOR_PLAN.md
- docs/decisions/0011-time-bounded-v0-conversion.md
- docs/stories/US-104-refactor-plan-execution-contracts/**

## Non-Goals

- Implementing V1 code, binaries, installers, payloads, manifests, tests, or
  releases.
- Editing US-103, V0 code, scripts, databases, changesets, or other
  documentation.
- Creating V1 operational state, product telemetry, or a V1 implementation.
- The writing agent running Harness bootstrap, CLI, database, changeset,
  release, publish, or migration operations. Required current-V0 workflow
  evidence is recorded externally by orchestration.
