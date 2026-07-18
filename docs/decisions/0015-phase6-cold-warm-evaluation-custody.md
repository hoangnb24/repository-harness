# 0015 Phase 6 Cold And Warm Evaluation Custody

Date: 2026-07-18

## Status

Accepted for the Phase 6 framework. Live candidate cards and Phase 6
acceptance remain pending.

## Context

Phase 5 froze authenticated pre-candidate baselines. Phase 6 must compare
candidate capabilities without letting candidate bytes rewrite the starting
condition, mutate a live V0 repository, self-authorize evidence, or place
sensitive recovery material in Git.

Two custody lanes are required because the cards do not start from the same
kind of repository:

- Most capability cards can start from a new clone at an immutable revision.
- A V0 conversion card needs the pre-candidate V0 runtime state, including a
  possible WAL-only commit, but must never operate on the owner's live copy.

The evidence model also needs two distinct identities. If one identifier tries
to mean both "the conditions stayed comparable" and "this exact candidate was
evaluated," either a changed condition can be hidden behind a new candidate ID
or candidate bytes can be mistaken for baseline custody.

## Decision

### Two closed custody lanes

Every live Phase 6 card declares exactly one lane before candidate disclosure.

`cold-clone` is the default lane:

1. An external custodian resolves the authenticated repository bundle and
   immutable starting revision recorded by Phase 5.
2. The custodian creates a fresh clone or worktree from that bundle in a new
   private evaluation root.
3. No ignored runtime state, local database, archive, credential, key, or
   previous candidate work is copied into the root.
4. The custodian records the clean starting tree identity before candidate
   capability bytes are introduced.

`warm-v0-copy` is permitted only for a card whose applicability requires V0
runtime evidence:

1. Before candidate disclosure, the repository owner quiesces V0 writers and
   authorizes isolated capture.
2. The custodian uses Decision 0013/0014 capture semantics to copy the Git
   working state and required raw DB, WAL, SHM, recognized changesets, and
   provenance through pinned no-follow handles with equal pre/copy/post
   identity, size, and SHA-256.
3. Raw runtime bytes move only into a new private, access-controlled evaluation
   root. SQLite may open only the private staged DB+WAL; SHM stays forensic.
4. The live source remains byte-for-byte unchanged. A source identity change,
   active writer, missing required member, or mixed-time capture invalidates
   the condition before candidate execution.

The lanes never merge. A cold clone cannot quietly inherit ignored V0 state,
and a warm copy cannot be described as a clean clone.

### Live-state and repository prohibitions

Phase 6 tooling, agents, and card commands must not mutate or open the owner's
live V0 database for writing. They must not use a live archive as scratch
space, alter Phase 5 packets, or modify the caller-pinned trust registry.

Raw `harness.db*` files, raw V0 archives, decrypted archive members, private
keys, recipient identities, credential files, and external trust registries
must not be committed. Git evidence may contain closed manifests, lowercase
digests, redacted findings, command descriptions, signed envelopes, public-key
fingerprints, and references to externally retained evidence. A digest proves
identity; it is not permission to publish the underlying sensitive bytes.

### Pre-candidate capture

The condition manifest, target bundle/revision, fixtures, environment lock,
custody lane, and—when warm—raw-member inventory/digests are captured and
externally authenticated before candidate bytes or results are disclosed to
the run custodian. Candidate authors cannot backfill or replace that capture.

If a condition must change after disclosure, the run is not repaired in place.
The custodian creates a new condition identity, reruns the comparable baseline
where required, and evaluates the candidate again. The invalidated run remains
auditable and cannot contribute to acceptance.

### Condition identity and subject identity

`condition_identity` names what must remain equal for a comparable
baseline/candidate pair. It binds at least:

- card/catalog revision and applicability;
- canonical repository and immutable starting revision or comparable-revision
  finding;
- custody lane and pre-candidate capture manifest digest;
- fixtures, locked acceptance checks, environment, tools, permissions, and
  intervention taxonomy;
- external custodian/trust scope and publication-before-disclosure record.

`condition_identity` excludes the baseline/candidate result and the capability
bytes intentionally under test.

`subject_identity` names the exact thing evaluated under those conditions. It
binds the subject kind (`pre-candidate-baseline` or `phase6-candidate`), exact
repository tree or capability-bundle digest, template/release identity when
applicable, and subject publication identity. Baseline and candidate therefore
have different subject identities while sharing one condition identity.

A result is admissible only when its condition identity matches the fixed card
and its subject identity resolves to the exact bytes that produced the
evidence. Reusing one subject identity for different bytes, or claiming two
different condition identities as a comparable pair without a written rerun,
fails closed.

### External trust and signing

Phase 5's external trust boundary continues:

- The invoking authority supplies a digest-pinned trust registry from outside
  the candidate repository.
- The tracked repository cannot self-authorize a pilot, custodian, signer,
  subject, or result.
- Offline signatures bind condition identity, subject identity, custody lane,
  evidence manifest digest, canonical repository, starting revision,
  completion time, and publication identity.
- Signing private keys and archive decryption identities remain external.
- Test keys may be generated only in disposable fixtures and cannot authorize
  live evidence or appear in a production trust bundle.

The candidate fails when trust is missing, self-declared, digest-mismatched,
cross-scoped, signed after an inadmissible rewrite, or unable to resolve the
named subject bytes.

### Phase boundaries

This decision starts only the repository-owned Phase 6 framework. It does not
accept any live card, pilot comparison, human-attention improvement, release
candidate, or production workflow.

Phase 6 can close only after every required live P0-P7 candidate card has
admissible signed evidence, negative conditions fail closed, no functional
regression exists, and the comparison contract passes. Phase 7 remains closed
until that acceptance. Phase 8 remains closed until Phase 7 acceptance and all
Decision 0012 time, support, recovery, security, archive-integrity,
asset-retention, and separate authorization/validation conditions pass.

## Concrete Cause And Effect

### Cold clone

1. A candidate author has an untracked helper in a previous working directory.
2. The custodian creates a fresh clone from the authenticated starting bundle.
3. The helper is absent because ignored and untracked state is not copied.
4. Only the signed candidate subject is introduced, so the result is attributable
   to that subject under the recorded condition.

### Warm V0 copy

1. A committed row exists only in the live V0 WAL.
2. The owner quiesces writers; the custodian captures DB+WAL+SHM before
   candidate disclosure and records equal pre/copy/post identities and hashes.
3. Recovery opens only the private DB+WAL copy, so the committed row is visible
   without writing the live database.
4. The candidate operates on the private copy; Git receives only the signed
   manifest and digests, never the raw database or archive.

### Identity split

1. Baseline and candidate use the same starting revision, fixtures, tools,
   permissions, and custody manifest.
2. They share one `condition_identity`.
3. Their different repository/capability bytes produce different
   `subject_identity` values.
4. If permissions change for the candidate, the condition identity changes and
   the pair is rejected until both sides are rerun under the new condition.

### External signing

1. A candidate commits a public key and signs its own result.
2. The invoking authority's external registry does not authorize that key for
   the repository scope.
3. Signature verification fails even if the cryptography is valid.
4. The result cannot count toward Phase 6 and cannot open Phase 7.

## Alternatives Considered

1. Run every card from a cold clone. Rejected because a V0 applicability card
   would lose ignored DB/WAL state and could falsely become inapplicable.
2. Run warm cards in the live repository. Rejected because evaluation or
   SQLite recovery could mutate owner state and contaminate later runs.
3. Store raw DB/archive bytes in Git for reproducibility. Rejected because
   recovery evidence can contain sensitive operational history and credentials;
   externally retained custody plus authenticated digests is sufficient.
4. Use one run identity for conditions and candidate. Rejected because it
   cannot express equal conditions with different subjects or force a rerun
   when conditions change.
5. Let the candidate repository carry its trust registry or signer. Rejected
   because candidate-controlled bytes cannot independently authorize
   themselves.

## Consequences

Positive:

- Cold cards start clean, while eligible V0 cards retain exact pre-candidate
  runtime truth without live mutation.
- Comparable conditions and evaluated subject bytes are independently
  auditable.
- Sensitive runtime and signing material stay outside Git.
- A documentation/framework commit cannot be mistaken for Phase 6, 7, or 8
  acceptance.

Tradeoffs:

- Warm capture requires owner coordination, writer quiescence, private storage,
  and external evidence retention.
- A condition change requires rerunning the comparable pair instead of editing
  a result in place.
- Live Phase 6 evidence requires an external custodian/trust/signing ceremony.

## Follow-Up

- Instantiate the neutral target-owned templates only in authorized evaluation
  copies.
- Produce live candidate subjects and externally signed P0-P7 evidence under
  US-111.
- Keep Phase 7 release proof and Phase 8 removal in their separately gated
  phases.
