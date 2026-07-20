# US-111 V1 Phase 6 Capability Evaluation Design

> Decision 0018 retains this design for optional deeper evaluation; it is not
> the mandatory V1 release gate.

Status: **Framework accepted by owner for sequencing / live candidate efficacy
pending / no Phase 7 acceptance or promotion**

## Domain Model

`CustodyLane` is exactly `cold-clone` or `warm-v0-copy`. The former admits only
an authenticated repository bundle and selected candidate subject. The latter
admits a pre-candidate private copy of required V0 runtime members under
Decision 0015; it never admits a live database path.

`WarmConditionMaster` binds the validated raw DB/WAL/SHM capture manifest and
the standalone logical snapshot produced from a disposable recovery copy. The
raw trio and standalone snapshot are sealed immutable after validation.
Recovery-mutated staged files are construction intermediates and cannot become
the master or a run input.

`RunDerivative` is a fresh baseline or candidate copy created directly from the
same sealed standalone master. Baseline and candidate derivatives have distinct
custody IDs, cannot derive from one another, and must have the expected equal
pre-subject content digest. Master and derivative identities are reverified
immediately before each run.

`ConditionIdentity` binds the fixed card, repository starting state, custody
manifest, sealed raw-trio and standalone-master digests when warm, derivation
procedure and expected derivative digest, fixtures, environment, tools,
permissions, checks, and external trust scope. It intentionally omits candidate
bytes and results.

`SubjectIdentity` binds the exact baseline or candidate tree/capability bytes
evaluated under one condition plus its run-derivative custody ID/digest and
immediate pre-run verification receipt. A comparable pair therefore has equal
condition identity and unequal subject identity.

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
2. Make existing V0 Harness instructions explicitly conditional on a target
   actually using that durable layer, and add neutral target-owned proof and
   capability routes for ordinary targets.
3. Add the agent map to the V0 installer manifest and record its explicitly
   selected `optional-v1` disposition; do not claim authenticated V1 core
   payload inclusion.
4. At the original framework checkpoint, mark US-105 and the phase summaries as
   Phase 6 in progress with framework complete and live cards pending. Decision
   0016 later accepts that framework for sequencing without changing the live
   evidence state.
5. Validate structural completeness, JSON, neutrality, changed-file scope, and
   Phase 5/US-110 preservation.

Future authorized live-card flow:

1. External custody selects the card's declared lane and authenticates the
   condition before candidate disclosure.
2. For a warm lane, recovery uses a disposable staged pair to create the
   standalone master; the validated raw trio and standalone master are sealed
   immutable, and the staging pair is never promoted to master custody.
3. The custodian creates separate fresh baseline and candidate derivatives from
   the same sealed master, then reverifies master and derivative identity
   immediately before each run.
4. The baseline or candidate subject is introduced into only its own derivative.
5. The agent follows target-owned map routes and the fixed card; interventions
   are recorded under the Phase 5 taxonomy.
6. Target-owned acceptance and negative checks run under the validation ladder.
7. External signing binds condition, sealed-master and derivative digests,
   subject, evidence, times, and custody.
8. Comparison rejects master/derivative drift, condition drift, subject
   mismatch, hidden correction,
   functional regression, or failed negative conditions.

## Interface Contract

The initial docs-only slice added Markdown and one JSON ledger entry. The
implemented framework now adds evaluator, warm-capture, and evidence-verifier
scripts; closed schemas, a baseline lock, and an evidence index. The
combined-stack regression integration also updates Rust test-only release
expectations and places `docs/templates/agent-map.md` in the existing V0
installer manifest, so fresh V0 installs carry the neutral template. It creates
no new production CLI command grammar, runtime service, database field,
installer command semantics, or live candidate evidence. Authenticated V1 core
payload inclusion remains a later gate.

Portable templates use angle-bracket completion markers. A target activates a
template only after replacing required markers with its own paths, commands,
owners, and availability decisions. Structural V1 audit may detect unresolved
markers; it does not execute target commands or judge prose semantics.

## Data And Custody Model

Tracked evidence may include manifests, digests, redacted findings, public-key
fingerprints, signed envelopes, and external custody references. Raw databases,
WAL/SHM, archives, decrypted members, private keys, recipient identities,
credentials, and external trust registries remain untracked and external.

Warm custody seals the raw trio and standalone logical master after validation.
Separate fresh derivatives are created from that same master for baseline and
candidate runs. Evidence binds raw-trio/master digests to the condition and
binds derivative identity/digest plus the immediate pre-run verification
receipt to the subject. Recovery-mutated staged DB/WAL files cannot serve as a
condition master or derivative source.

No live database mutation occurs. The isolated V0 planning database used to
record this repository task is not a pilot input and is never copied into a
portable template or candidate condition.

## Portability

The templates name no pilot, language, package manager, model, evaluator, or
default architecture. Existing V0 Harness guidance remains for compatible
targets but is explicitly conditional and never mandatory for an ordinary
target. Other targets use their own proof and capability routes, and explicitly
record unavailable feedback surfaces instead of fabricating one.

For example, one target may route validation to a single documentation link
check, while another routes to several target-owned checks. Both use the same
ordered fields; neither template assumes how those checks are implemented.

## Observability

The initial docs slice is observable through reviewable diffs, JSON parsing,
template neutrality searches, preservation hashes, and replayable changesets.
The implemented framework adds schema validation, executable custody and
release-boundary negatives, synthetic warm-capture tests, and regression gates.
It does not generate live card results, intervention totals, signatures, or
release evidence.

## Alternatives Considered

1. Put capability routes only in `AGENTS.md`. Rejected because a reusable map
   needs a neutral scaffold and brownfield targets may map the role elsewhere.
2. Keep V0 CLI and Harness-delta guidance unconditional. Rejected because V1
   ordinary work has no mandatory Harness operation or task database. The
   existing fields remain backward-compatible but apply only when the target
   actually uses that V0 durable layer or selects a Harness delta.
3. Make repeated corrections evaluator-owned. Rejected because the capability
   must be discoverable and maintainable by the target after evaluation ends.
4. Treat a filled template as Phase 6 proof. Rejected because template presence
   does not demonstrate behavior on any fixed live card.
