# US-108 V1 Install, Update, And Recovery Exec Plan

Status: **Implemented and locally validated; orchestrator acceptance pending**

## Goal

Close the six residual Phase 3 gates from US-107 by implementing authenticated,
preview-bound, crash-safe V1 mutation and command-owned recovery without
crossing the Phase 4 bridge or Phase 7 release boundaries.

## Scope

In scope:

- An explicit Phase 3 mutation port injected after Phase 2 authentication.
- Fresh install, supported monotonic update, and neutral scaffold writes.
- Managed-file and managed-block updates, target-owned preservation, and all
  three update policies.
- Exact preview/confirmation, backups, staged after-images, journal ownership,
  fsync ordering, atomic writes, and manifest-last commit.
- Deterministic resume/rollback, kill points, idempotency, and conflict proof.
- US-108 docs, a focused mechanical verifier, premerge integration, and exact
  evidence updates to US-105 and the refactor plan.

Out of scope:

- V0 parsing, SQLite, changesets, conversion, archive creation, bridge
  commands/binaries/workflows, or a permanent migrate command.
- Production trust/payload promotion, signing, publishing, tagging, or release
  workflow activation.
- Target process execution, language detection, platform generator behavior,
  pilots, or Phase 5-8 work.
- `.harness/changesets`, DB files, `repomix-output.xml`, or unrelated user
  state.

## Risk Classification

Risk flags:

- **Audit/security:** only threshold-authenticated indexed bytes may reach the
  mutation port.
- **Data loss:** replacement, rollback, and crash recovery affect repository
  files.
- **Public contracts:** exits, previews, six-command grammar, and manifest
  transitions are user-visible.
- **Existing behavior:** accepted Phase 1 and Phase 2 proof must stay green.
- **Cross-platform:** Unix is implemented now while non-Unix must remain an
  honest Phase 7 fail-closed boundary.
- **Weak proof:** Phase 2 intentionally contains no mutation evidence.

Hard gates:

- Phase 2 `VerifiedRelease` must be the sole source of candidate bytes.
- A manifest can become authoritative only at the last atomic rename.
- A digest or ownership ambiguity must stop before overwrite.
- Phase 4 and Phase 7 lifecycle states must remain closed.

## Work Phases

1. Preserve `HarnessCore::new` as the Phase 2 no-write construction path and
   add a separate mutation-injected constructor.
2. Add pure plan/manifest/update-policy logic and exact preview operations.
3. Add the descriptor-anchored Unix writer, backups, staged images, journal
   integrity, durable flushes, and manifest-last commit.
4. Add resume/rollback with release, command, operation, path, and digest
   ownership checks.
5. Add unit and signed-release integration tests for fresh install, update,
   scaffold, managed blocks, target-owned preservation, conflicts,
   confirmation, monotonic transitions, idempotency, failure exits, kill
   points, resume, and rollback.
6. Add `scripts/verify-v1-phase3-recovery.sh` plus a mechanical source/runtime
   verifier and wire it into premerge after Phase 1/2 proof.
7. Run locked offline fmt/check/test/clippy, all three focused verifiers,
   `git diff --check`, and full premerge.
8. Update status and exact evidence counts only from the final passing tree.

All implementation steps are complete in the unstaged review worktree. Phase 4
and Phase 7 remain unopened: the live binary still uses unavailable production
release/trust ports, and platforms without the proven atomic exchange boundary
fail closed.

## Stop Conditions

Stop and preserve evidence if:

- candidate bytes can reach a write without successful Phase 2 verification;
- any recovery path is not command-owned or cannot prove before/post digests;
- rollback would overwrite a changed target post-image;
- a failure can return success or leave a new manifest claiming completion;
- implementation requires a seventh command, V0 reader, SQLite, process
  executor, language branch, production key, promoted workflow, or non-Unix
  portability claim;
- accepted Phase 1/2 proof must be weakened; or
- validation would modify tracked `.harness` changesets, DB files,
  `repomix-output.xml`, or unrelated state.
