# Design

## Domain Model

This planning-only change has three document-level entities:

- The V1 execution contract in the refactor plan.
- The accepted time-bounded V0 conversion decision.
- This high-risk packet, which records scope, proof, and rollback.

The plan's normative role model separates activation
active/unresolved/disabled, ownership managed-file/managed-block/target-owned,
origin created/v0-adopted/brownfield-mapped, and required boolean. It also
defines managed metadata and prohibits automatic patching of target-owned
adopted or mapped files.

The accepted migration decision is that V0 database conversion is a separately
versioned repository-local harness-v0-migrate bridge. It has a bounded
compatibility window and never becomes a permanent V1 core command.

## Application Flow

1. A future high-risk implementation reads the reconciled plan and Decision
   0011 before changing product behavior.
2. It builds contracts, pure V1 core, install/update recovery, isolated bridge,
   dogfood/baselines, capability evaluation, release proof, and V0 removal in
   that order.
3. Ordinary target work remains outside that sequence and uses native tools.

## Interface Contract

The planning contract reserves V1 core grammar for install, update, audit,
scaffold, status, and version. It distinguishes V0 harness-cli database audit
and migrate behavior from V1 structural audit. The bridge has its own
inspect/export/preview/apply/resume/rollback grammar and identity.

## Data Model

The writing change creates or changes no V1 database, manifest, schema,
operational state, or product telemetry. The planned V1 manifest contract is
documented only and forbids task/run/prompt/result state.

The current repository's isolated .harness/refactor-plan.db is V0 workflow
evidence, not V1 product state. Orchestration has recorded intake #3 and story
US-104 there and will record Decision 0011 and the final trace. The writing
agent does not invoke Harness commands or modify that database.

## UI / Platform Impact

No executable UI or platform behavior changes. The plan preserves future Bash,
PowerShell, and direct-binary proof requirements without changing them.

## Observability

No V1 trace, operational telemetry, or product telemetry is created. The
externally recorded V0 intake, story, decision, and final trace are current
repository workflow evidence only. The release-only pilot protocol specifies
future product evidence and total human-attention accounting; it is not
activated for ordinary tasks by this story.

## Alternatives Considered

1. Append a bridge exception while retaining permanent V1 migrate wording.
   Rejected because implementation would have contradictory command contracts.
2. Convert V0 state through V1 install/update. Rejected because database
   conversion needs an isolated reader, archive, journal, and support window.
