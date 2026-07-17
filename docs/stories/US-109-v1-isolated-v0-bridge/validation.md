# US-109 Validation Contract

Status: **in_progress pending independent acceptance**

## Required proof matrix

| Layer | Concrete proof |
| --- | --- |
| Grammar | Live help, Rust source marker, and JSON contract equal exactly `inspect`, `export`, `archive`, `version`; removed verbs exit 64. |
| Capture | Schemas 1–13 inspect on temporary copies; source identity/size/digest remains unchanged; link and mutation races fail closed. |
| Export | WAL-only committed row appears in neutral export; live and archived export bytes/digests are identical; output is create-new. |
| Archive | Encrypted default and explicit two-flag plaintext work; manifests/members verify; tamper fails; two attempts publish unique IDs no-replace. |
| Crash/retry | An abandoned staging path is not accepted, adopted, deleted, or overwritten; retry safely publishes a fresh unique archive. |
| Ownership | Foreign `.harness/legacy`, `.harness/recovery`, and unauthenticated `.harness-v0-archive` remain unchanged and unowned. |
| Core boundary | Core grammar stays six commands and source/dependencies contain no SQLite or bridge implementation. |
| Receipt recovery | First install preview binds the archive and pinned custody identity; an ordinary-directory swap between pin/read or preview/recovery is rejected with no manifest; restoring the exact ancestor permits safe resume. |
| Platform | macOS/Linux exercise descriptor behavior. Windows compiles, exposes four-command help, and repository capture exits controlled-unsupported 5 until Phase 7. |
| Fixtures | Inventory size/SHA checks pass before and after; tracked fixture bytes have no diff. |

## Cause-and-effect examples

1. Write a row only to V0 WAL, freeze the writer, and export. If export omitted
   WAL, the row would disappear; the test asserts it is present.
2. Publish archive A, leave a foreign `.staging-*`, then publish archive B. If
   retry reused paths, A or the foreign marker would change; all three remain
   intact and A/B IDs differ.
3. Interrupt core install after receipt staging. If the bridge owned recovery,
   no safe continuation would exist; instead normal `install --resume` commits
   the exact receipt manifest-last.
4. Put foreign files under `.harness/legacy` and `.harness/recovery`. Archive
   reports them unknown/unowned and their bytes remain unchanged.
5. Run `inspect` on Windows. The crate parses the command but opens no repository
   capture handle and exits 5, proving the Phase 7 boundary is controlled.
6. Pin custody A, rename it away, and replace it with an exact-copy B. If reads
   were independently reopened, B could supply the key/archive. The production
   filesystem port instead rejects B's device/inode; recovery likewise rejects
   B until the exact previewed A is restored.

## Commands

```text
cargo test --locked --offline --package harness-v0-migrate
cargo test --locked --offline --package harness-core --test phase3_recovery fresh_install_recovery_commits_exact_v0_archive_receipt_without_reading_sqlite -- --exact
scripts/verify-v1-phase1-contracts.sh
scripts/verify-v1-phase2-core.sh
scripts/verify-v1-phase3-recovery.sh
scripts/verify-v1-phase4-bridge.sh
cargo test --workspace --locked --offline
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --locked --offline -- -D warnings
scripts/validate-premerge.sh
git diff --check
```

Passing these commands proves the local candidate only. Independent review of
the committed hashes is still required before Phase 4 acceptance. Phase 5,
Phase 7, production promotion, signing, and publishing stay closed.
