# Exec Plan

## Goal

Deliver the Phase 4 `harness-v0-migrate` bridge as an isolated, separately
versioned repository-local artifact. Supported V0 repositories gain a
source-immutable, archive-first, resumable conversion path while the V1 core
keeps exactly six commands and no SQLite/V0 dependency.

## Scope

In scope:

- Complete US-109 packet and honest Phase 4 status/evidence updates.
- Separate bridge crate, seven-command parser, repository-local binary, and
  bridge-only release workflow/metadata in an unpromoted lifecycle state.
- Frozen schema 1 through 13 and changeset recognition.
- Descriptor-anchored raw DB/WAL/SHM, changeset, and provenance capture.
- Staged DB+WAL recovery and SQLite online-backup snapshot.
- Neutral deterministic export, encrypted-default/write-once archive, and
  plaintext two-flag override.
- Deterministic preview, journaled apply, manifest-last commit, resume,
  rollback, mixed-version status classification, kill points, fixtures,
  verifier, isolation scans, and regression proof.

Out of scope:

- V0 source migration or lifecycle changes.
- Permanent-core bridge code, SQLite dependency, target execution, or
  additional command.
- Automatic archive removal, V1-to-V0 downgrade, production keys, release
  signing/publishing, PR operations, deploys, pilots, or Phase 7 five-platform
  promotion.

## Risk Classification

Risk flags:

- Data model and data loss: V0 SQLite/WAL recovery and conversion commit.
- Audit/security: no-follow capture, encryption, archive custody, tamper
  refusal, and journal ownership.
- Public contracts: separate binary identity and exact seven-command grammar.
- Cross-platform: Unix descriptor proof now; declared five-platform promotion
  remains gated to Phase 7.
- Existing behavior: V0 schemas, changesets, and binary remain frozen.
- Weak proof and multi-domain: capture, crypto, filesystem recovery, core
  status, packaging, and docs require independent layers of proof.

Hard gates:

- Data migration/loss and audit/security make this a high-risk story.
- Decisions 0011, 0012, and 0013 are locked. A discovered need to change their
  security, custody, support-window, or dependency rules stops implementation
  for explicit human decision.

## Work Phases

1. **Packet and contracts.** Create all four US-109 documents. Bind the live
   bridge crate, source grammar, repository-local entrypoint, and unpromoted
   workflow to the existing frozen contracts without altering core grammar.
2. **Reader, capture, inspect, and export.** Implement strict arguments,
   descriptor-anchored no-follow capture, schema/changeset recognition,
   staged WAL recovery, online backup, neutral export, and immutable fixtures.
3. **Archive, preview, and apply.** Implement encrypted-default or explicitly
   acknowledged plaintext archive creation, deterministic operations and
   preview digest, journal transitions, idempotent writes, V1 audit, and
   manifest/receipt-last commit.
4. **Resume, rollback, and kill points.** Bind recovery to conversion/root/input
   evidence, replay incomplete work only, refuse target edits, and enumerate
   each required stop boundary.
5. **Status, packaging, and verifier.** Add a structural mode observation that
   does not parse V0 in core; evolve Phase 1-3 lifecycle assertions from
   bridge-absent to bridge-live-unpromoted; add release-source and payload
   isolation scans.
6. **Full verification and evidence.** Run focused tests, Phase 1-4 verifiers,
   workspace tests, formatting, clippy, premerge, and diff checks. Update
   US-105/US-109 evidence without marking US-109 complete in the shared DB.
7. **Reviewable commits.** Preserve the task changeset and commit logical
   milestones: packet/contracts; reader/inspect/export; archive/preview/apply;
   recovery/kill points; packaging/verifier/docs. Do not push.

## Detailed Safety Sequence

1. Inspect identifies recognized and unknown inputs without mutation.
2. Preview captures and validates source bytes but leaves no durable output.
3. Apply repeats the validation so a stale preview cannot authorize changed
   inputs.
4. Export and standalone snapshot are created before archive sealing.
5. Archive creation uses create-new/no-replace and verifies every member.
6. Only after archive verification does the journal enter `prepared` and then
   `applying`.
7. Each target operation checks its recorded before-image immediately before
   mutation and records its exact post-image afterward.
8. Candidate V1 structure is audited before commit.
9. Temporary manifest/receipt bytes are verified, then the complete manifest
   containing the receipt is atomically committed last.
10. Resume or rollback uses only the matching journal and refuses on any
    evidence mismatch.

## Stop Conditions

Pause for human confirmation if:

- age/X25519 interoperability cannot be implemented without changing the
  accepted confidentiality contract;
- the frozen schema/changeset contracts are insufficient to distinguish
  supported V0 from foreign data;
- source immutability cannot be proven with the required same-handle and
  parent-descriptor checks on the implementation platform;
- a desired conversion requires V0 task state in the V1 manifest;
- archive retention, rollback conflict behavior, compatibility dates, trust
  domains, or core dependency direction would need to change; or
- a verifier can pass only by weakening authentication, path, custody,
  recovery, release, or validation gates.

Ordinary implementation defects, missing tests, or unavailable Phase 7
platform runners are not policy decisions. They are fixed locally or reported
as exact deferred boundaries.

