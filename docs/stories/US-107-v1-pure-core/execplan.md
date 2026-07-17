# US-107 V1 Pure Core Exec Plan

Status: **Implemented, fully validated, and accepted**

## Goal

Implement and prove the separate six-command V1 core from accepted Phase 1
contracts without changing V0 or crossing into Phase 3 mutation recovery,
Phase 4 conversion, or production release work.

## Scope

In scope:

- `harness-core` domain/application/interface/infrastructure and separate
  filesystem, manifest, release-material, and pinned-trust ports.
- Exact live `harness`/Windows binary identity and closed command extraction.
- Strict authenticated bundle lifecycle plus payload/index/ledger verification
  for separately injected release and trust inputs.
- Deterministic manifest audit, status, version, planning, and preview.
- Safe mutation/recovery refusal until Phase 3.
- Core-live/bridge-absent command binding and bootstrap workflow lifecycle.
- Present-but-unpromoted core workflow source.
- Focused Rust and mechanical positive/negative proof plus premerge integration.

Out of scope:

- All Phase 3-8 behavior named in the overview non-goals.
- V0 source/schema/installer changes.
- Harness planning DB, intake, matrix query, database migration, trace, or
  `.harness` changeset operations; external orchestration owns US-107.

## Risk Classification

- **Public grammar:** exact command/option/exit/mutation parity.
- **Security:** strict trust threshold, source allowlist, safe paths, links, and
  target-process denial.
- **Existing behavior:** V0 must remain frozen and pass its full suite.
- **Mutation/data loss:** Phase 2 must refuse writes whose recovery proof does
  not exist.
- **Release lifecycle:** workflow source may be present, but production
  acceptance must remain blocked on external evidence.

## Work Phases

1. Verify the branch is the clean exact base and read all accepted Phase 1/V1
   contracts without invoking Harness state operations.
2. Add the isolated Rust core package and explicit filesystem, manifest,
   release-material, and independent pinned-trust ports.
3. Implement strict JSON/JCS, trust-bundle old/new root thresholds,
   revocation/rollback freshness, Ed25519 release threshold,
   payload/ledger/source-set, safe path, pinned snapshot, manifest,
   CommonMark link/anchor, output, and preview rules.
4. Implement the closed CLI parser and one source command definition consumed
   by dispatch and independently extracted by proof.
5. Keep the live CLI's release adapter unpromoted and make every write/recovery
   request return a deterministic no-op/refusal.
6. Evolve binding/bootstrap schemas and contracts to core live, bridge absent;
   add the guarded unpromoted workflow.
7. Add Rust positive/negative tests and the focused Phase 2 verifier; evolve
   Phase 1 proof without weakening its trust/V0 checks.
8. Run formatting, workspace check/test/clippy, both focused verifiers, full
   premerge, diff/scope checks, then record acceptance truthfully.
9. Use the smart-commits inspection discipline to keep all inspected Phase 2
   files in one logical change. Per the review-resume instruction, do not stage,
   commit, or push; leave the validated working tree for the orchestrator to
   amend.

## Stop Conditions

Stop if a change would:

- add a seventh command, `migrate`, V0 grammar, SQLite, or a process executor;
- allow unindexed/bridge/V0-operational source bytes into a core plan;
- make audit or status write, execute, or infer undeclared state;
- execute install/update/scaffold without Phase 3 recovery guarantees;
- claim production workflow protection, attestation, signing, or publishing;
- create/modify planning DB state, `.harness` changesets, or
  `repomix-output.xml`; or
- require changing frozen V0 behavior to make Phase 2 pass.
