# 0011 Time-Bounded V0 Conversion

Date: 2026-07-16

## Status

Accepted

Superseded in part by Decision 0014. The automatic conversion, target mutation,
bridge journal, resume/rollback, and bridge-written V1 receipt described below
remain historical rationale; the separate time-bounded reader/archive boundary
remains in force.

## Context

Decision 0004 made SQLite, schema migrations, and operational records the V0
durable layer. Decision 0005 made the repository-local prebuilt harness-cli
binary its stable operational entrypoint. Those decisions remain accurate
history for V0, but the accepted V1 direction removes that operational control
plane from the default product.

A permanent V1 migrate command would preserve the V0 database boundary inside
the new core and make two incompatible command grammars appear interchangeable.
Conversely, deleting conversion immediately could strand repositories with V0
documents, SQLite state, and changesets. The product needs a bounded,
recoverable transition without making V0 semantics a permanent V1 dependency.

## Decision

V0 database conversion is a separately versioned, repository-local
harness-v0-migrate artifact with a declared, time-bounded compatibility window.
It is not a permanent V1 core command.

The permanent V1 core grammar is install, update, audit, scaffold, status, and
version. Install and update own future V1 manifest schema transitions. V1 audit
is a deterministic structural audit and never opens V0 SQLite state or executes
target tools.

The bridge:

- reads recognized V0 inputs through an immutable, read-only reader;
- supports only the explicitly published V0 schema and changeset grammar range;
- emits a neutral versioned export and checksummed archive before any mutation;
- uses a transient untracked filesystem-operation journal with resume and safe
  rollback;
- preserves ambiguous, foreign, or unknown state rather than guessing
  ownership; and
- records a completed cutover receipt in the V1 manifest only after the
  archive/export and V1 contract checks succeed.

The release plan must publish the bridge version, exact supported V0 input
range, compatibility-window start and end dates, archive retention policy, and
the conditions for ending distribution. A bridge release that expands the
supported range is a new versioned artifact with its own proof; it does not
silently change V1 core support.

## Alternatives Considered

1. Keep a V1 conversion command permanently. Rejected because it couples the
   V1 core to V0 database semantics and weakens the clean grammar boundary.
2. Delete all V0 conversion support with V1. Rejected because existing
   repositories need a safe, auditable route that preserves source evidence.
3. Let V1 install infer and rewrite arbitrary .harness metadata. Rejected
   because a directory name does not establish ownership and guessing can
   destroy another tool's state.
4. Keep both operational workflows indefinitely. Rejected because ordinary
   work would retain the exact mandatory control-plane ambiguity V1 removes.

## Consequences

Positive:

- V1 remains a small template-maintenance product with no permanent SQLite
  conversion command.
- Existing V0 users receive an explicit export, archive, recovery path, and
  compatibility statement.
- Binary identity, grammar, and audit semantics are unambiguous during
  cutover.

Tradeoffs:

- A separate bridge has release, platform, fixture, archive, and retirement
  cost during the compatibility window.
- V1 cannot promise automatic downgrade from its manifest/content back into a
  V0 operational database.
- The product must retain enough V0 reader knowledge to support the published
  range, while preventing that reader from entering the V1 payload.

## Amendments To Earlier Decisions

This decision amends, without deleting or rewriting history:

- Decision 0004: SQLite remains the accepted V0 durable layer, including its
  historical schema-migration semantics. It is no longer part of the default
  V1 core; the bridge is the bounded reader/export path for that history.
- Decision 0005: the prebuilt repository-local binary remains the V0
  distribution decision for harness-cli. V1 uses a distinct binary identity
  and grammar, while harness-v0-migrate is separately versioned for the
  compatibility window. Decision 0005 does not make a V0 migrate command a
  permanent V1 command.

## Follow-Up

- Record the exact compatibility-window dates before implementation begins.
- Define and prove the first bridge's supported V0 schema/grammar range,
  archive retention, kill points, and platform artifacts.
- Remove V0 operational payload and code from the default product only after
  the window closes and its documented recovery obligations are met.
