# US-113 Proportional V1 Release Gate

Status: **In progress**

## Current Behavior

V1 promotion is blocked on P0-P7 across two pilots, exact-five platform proof,
and a sentinel-triggered diagnostic evidence loop.

## Target Behavior

Decision 0018 makes promotion depend on normal premerge, smoke proof for only
the platforms claimed as supported, ordinary pull-request approval, and
CI-produced binaries, checksums, and attestations that the owner can download
and test before publishing.

Example: Linux x64 may be supported after its build and four smoke checks pass.
Windows remains explicitly unsupported until its adapter and native proof pass;
it does not block the Linux release.

## Scope

- Align the Phase 6/7 plan and story contracts with Decision 0018.
- Retire the sentinel push trigger in favor of optional manual diagnostics.
- Add a focused documentation contract for the smaller gate.

## Non-Goals

- Deleting historical Phase 5 or Phase 6 evidence.
- Claiming a supported platform before its native mutation smoke passes.
- Publishing or promoting a release in this story.
