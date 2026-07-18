# US-111 V1 Phase 6 Capability Evaluation Design

Status: **Framework implemented / live candidate evaluation pending / no Phase
6 acceptance**

## Domain Model

`CustodyLane` is exactly `cold-clone` or `warm-v0-copy`. The former admits only
an authenticated repository bundle and selected candidate subject. The latter
admits a pre-candidate private copy of required V0 runtime members under
Decision 0015; it never admits a live database path.

`ConditionIdentity` binds the fixed card, repository starting state, custody
manifest, fixtures, environment, tools, permissions, checks, and external
trust scope. It intentionally omits candidate bytes and results.

`SubjectIdentity` binds the exact baseline or candidate tree/capability bytes
evaluated under one condition. A comparable pair therefore has equal condition
identity and unequal subject identity.

`AgentMap` contains bounded routes for planning, architecture, validation,
feedback, and maintenance. Each route has a first target-owned source, a
continue condition, and a stop condition; it does not recursively preload the
repository.

`ResumeCapsule` contains objective, verified completed work, remaining work,
one exact next action, ordered validation ladder, decisions/assumptions,
blockers/owners, and working-state identity.

`InvariantContract` contains a target-owned rule, owner, runnable check,
bounded remediation, and exception path. `FeedbackContract` contains the
surface owner, direct target route, success signal, and explicit unavailable
behavior. `RepeatedCorrectionContract` promotes recurrence into a target-owned
instruction, example, check, test, script, review rule, or equivalent durable
capability. `GardeningContract` contains bounded scope, owner, trigger/cadence,
runner, allowed-change policy, validation, and second-run convergence.

## Application Flow

Framework flow in this slice:

1. Freeze Decision 0015 before any Phase 6 candidate evidence is created.
2. Replace operational V0 instructions in portable templates with neutral
   target-owned prompts.
3. Add the agent map and record its explicitly selected `optional-v1`
   disposition; do not claim authenticated payload inclusion.
4. Mark US-105 and phase summaries as Phase 6 in progress with framework
   complete and live cards pending.
5. Validate structural completeness, JSON, neutrality, changed-file scope, and
   Phase 5/US-110 preservation.

Future authorized live-card flow:

1. External custody selects the card's declared lane and authenticates the
   condition before candidate disclosure.
2. The candidate subject is introduced into only that private root.
3. The agent follows target-owned map routes and the fixed card; interventions
   are recorded under the Phase 5 taxonomy.
4. Target-owned acceptance and negative checks run under the validation ladder.
5. External signing binds condition, subject, evidence, times, and custody.
6. Comparison rejects condition drift, subject mismatch, hidden correction,
   functional regression, or failed negative conditions.

## Interface Contract

This slice adds Markdown and one JSON ledger entry only. It creates no new CLI,
command grammar, runtime service, schema, database field, installer behavior,
or evaluation script.

Portable templates use angle-bracket completion markers. A target activates a
template only after replacing required markers with its own paths, commands,
owners, and availability decisions. Structural V1 audit may detect unresolved
markers; it does not execute target commands or judge prose semantics.

## Data And Custody Model

Tracked evidence may include manifests, digests, redacted findings, public-key
fingerprints, signed envelopes, and external custody references. Raw databases,
WAL/SHM, archives, decrypted members, private keys, recipient identities,
credentials, and external trust registries remain untracked and external.

No live database mutation occurs. The isolated V0 planning database used to
record this repository task is not a pilot input and is never copied into a
portable template or candidate condition.

## Portability

The templates name no pilot, language, package manager, model, evaluator,
default architecture, or mandatory Harness command. They permit any
target-native check or feedback surface and explicitly record unavailable
surfaces instead of fabricating one.

For example, one target may route validation to a single documentation link
check, while another routes to several target-owned checks. Both use the same
ordered fields; neither template assumes how those checks are implemented.

## Observability

This docs slice is observable through reviewable diffs, JSON parsing, template
neutrality searches, preservation hashes, and replayable changesets. It does
not generate live card results, intervention totals, signatures, or release
evidence.

## Alternatives Considered

1. Put capability routes only in `AGENTS.md`. Rejected because a reusable map
   needs a neutral scaffold and brownfield targets may map the role elsewhere.
2. Keep the V0 CLI commands in portable stories. Rejected because V1 ordinary
   work has no mandatory Harness operation or task database.
3. Make repeated corrections evaluator-owned. Rejected because the capability
   must be discoverable and maintainable by the target after evaluation ends.
4. Treat a filled template as Phase 6 proof. Rejected because template presence
   does not demonstrate behavior on any fixed live card.
