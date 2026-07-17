# Validation

## Proof Strategy

US-109 is accepted only when executable evidence proves four independent
claims: source V0 bytes never change; conversion success cannot be reported
before archive and manifest-last commit; resume/rollback are deterministic and
journal-bounded; and the permanent V1 core remains isolated from bridge/V0
code. Documentation or fixture presence alone is not proof.

Each positive conversion test records exact bytes and metadata for
`harness.db`, WAL, SHM, recognized changesets, provenance, and unknown
`.harness` files before invoking the bridge. It compares them after inspect,
export, preview, successful apply, every injected failure, resume, and
rollback. Each negative fixture must fail closed while preserving the same
tree.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Exact seven-command grammar; schema 1..=13 bounds; closed changeset header/operation/version parser; duplicate JSON rejection; deterministic source/category/payload/export/preview digests; journal transition validation; plaintext two-flag requirement. |
| Integration | Descriptor/no-follow capture; DB+WAL recovery and standalone online backup; SHM forensic-only; unknown metadata preservation; write-once encrypted/default and plaintext/ack archives; idempotent apply; manifest/receipt-last; structural V1 audit; mixed-invalid detection. |
| Recovery | Journal-bound resume repeats incomplete steps only; rollback restores/removes matching journal-owned images; target edit causes zero rollback mutation and `recovery-required`; V0 inputs and archives never change. |
| Kill point | Stop after detection, export, archive, each filesystem operation, temporary manifest write, temporary receipt evidence, and atomic manifest commit; prove no false success and deterministic next action. |
| Contract/isolation | Core help/source remain exactly six commands and reject bridge verbs/migrate; `harness-core` has no bridge/rusqlite/V0 dependencies; core payload scan rejects bridge-only legacy bytes; live bridge help/source equals frozen grammar. |
| Fixtures | Immutable schemas 1..=13, grammar v1/v2, WAL-only commit, unknown metadata, symlink/ancestor/final replacement, in-place tamper, unsupported schema, malformed/unknown changeset, archive/export/journal tamper, and target-edit conflict. |
| Platform | macOS/Linux descriptor behavior is exercised where available. Windows and complete five-platform artifact equivalence remain Phase 7 release proof; Phase 4 must fail closed where its safe capture adapter is unavailable. |
| Release | Bridge workflow/metadata are source-only and live-unpromoted; no publish, tag, production key, protection claim, or attestation is created. Earlier lifecycle verifiers evolve without weakening core isolation or production gates. |

## Concrete Oracles

### WAL-only recovery

1. Create a schema-13 V0 database in WAL mode.
2. Commit a row while preventing checkpoint into the main file.
3. Confirm the raw main-file view alone lacks the row.
4. Run bridge capture and online backup over staged DB+WAL.
5. Assert the standalone snapshot and neutral export contain the row.
6. Assert source DB, WAL, and SHM bytes/digests are unchanged.

### No false success

1. Inject a stop after archive verification but before target operations.
2. Assert the archive and journal exist and authenticate.
3. Assert `.harness/manifest.json` does not claim converted success.
4. Resume and assert only remaining operations execute.
5. Assert the manifest appears only at the atomic commit point and embeds the
   receipt matching export, snapshot, archive, mode, recipient, and path.

### Safe rollback

1. Stop after a journal-owned target file is written.
2. Roll back without outside edits and assert the exact pre-image returns.
3. Repeat, edit the target after the stop, and request rollback.
4. Assert exit 4, `recovery-required`, zero rollback writes, preserved human
   edit, preserved archive, and unchanged V0 inputs.

### Mixed-version boundary

1. Place recognized V0 artifacts beside a V1 manifest with no completed
   receipt.
2. Run `harness status --json` and assert `mixed-invalid`, exit 3, and no byte
   changes.
3. Scan core sources/dependencies and assert no SQLite open, V0 schema parser,
   changeset parser, or bridge dispatch exists.

## Fixtures

- One immutable database for every exact schema version 1 through 13.
- Valid version-1 header with operation versions 1/default and 2.
- Rejections for unsupported schema 0/14, malformed/duplicate JSON, unknown
  operation, unsupported operation version, and incompatible database shape.
- WAL-only committed row with raw DB/WAL/SHM digests.
- Recognized provenance plus arbitrary `.harness/foreign-tool.bin` bytes.
- Tampered source, archive, export, journal, receipt, and target post-image
  cases.
- Deterministic test age/X25519 recipient/identity material isolated from any
  production bundle.

Fixture generation must be reproducible and the generated inventory immutable.
Tests consume copies so no accepted fixture is modified in place.

## Commands

```text
cargo test --locked --offline --package harness-v0-migrate
scripts/verify-v1-phase1-contracts.sh
scripts/verify-v1-phase2-core.sh
scripts/verify-v1-phase3-recovery.sh
scripts/verify-v1-phase4-bridge.sh
cargo test --workspace --locked --offline
cargo fmt --check
cargo clippy --workspace --all-targets --locked --offline -- -D warnings
scripts/validate-premerge.sh
git diff --check
```

## Acceptance Evidence

The preserved candidate passes the ready focused checks on macOS arm64:

- `cargo test --locked --offline --package harness-v0-migrate`: exit 0, 4 unit,
  11 positive/kill-point integration, and 11 rejection integration tests.
- `cargo test --locked --offline --package harness-core`: exit 0, 41 unit, 1
  binary, 24 Phase 2, and 25 Phase 3 tests.
- `scripts/verify-v1-phase1-contracts.sh`: exit 0, 9/9 proof groups.
- `scripts/verify-v1-phase2-core.sh`: exit 0, 11/11 proof groups.
- `scripts/verify-v1-phase3-recovery.sh`: exit 0, 11/11 proof groups.
- `scripts/verify-v1-phase4-bridge.sh`: exit 0, 10/10 executable proof
  groups; committed fixture inventory matched before and after the complete
  run.
- `cargo test --workspace --locked --offline`: exit 0 across the legacy CLI,
  core Phase 2/3, bridge, and contract-crypto suites.
- `cargo fmt --check`: exit 0.
- `cargo clippy --workspace --all-targets --locked --offline -- -D warnings`:
  exit 0.
- `scripts/validate-premerge.sh`: exit 0 after supplying the installed
  Homebrew ripgrep path required by the local shell environment.
- `git diff --check 9ad31ce..HEAD` and `git diff --check`: exit 0.

The fixture verifier checks every inventory member's exact byte count and
SHA-256, including schema 1..=13 DB/WAL/SHM and the WAL-only fixture. The full
workspace test/fmt/clippy/premerge chain is green; independent review remains
pending. US-109 remains `in_progress`; Phase 5 stays closed. Windows safe
capture/atomic commit and promoted five-platform artifact equivalence remain
Phase 7 production proof and are not claimed here. Harness bootstrap remains
unavailable in this worktree because authoritative core state is absent; no
empty `harness.db` was initialized.

## Rejection Closure Oracles

1. Symlinked WAL/SHM and changeset ancestors now produce an error and zero
   archive, recovery, export, or manifest output; true absence alone is
   optional.
2. Empty, self-rehashed, wrong-member, wrong-export, and concurrently
   prepositioned archives cannot pass without the matching authenticated
   journal witnesses; publication is descriptor-relative and no-replace.
3. Unknown-field, edited, copied-root, and authentication-mismatched journals
   authorize no target mutation; states are closed and monotonic.
4. Archive, source, export, snapshot, receipt, journal, adopted-target, root,
   and live-target drift are checked before rollback's first target write;
   `rolling-back` supports crash-consistent reverse completion.
5. Extra or altered tables, columns, indexes, views, and triggers fail schema
   capture, and every operation-specific v2 timestamp requirement in the
   frozen matrix is enforced.
6. Invalid UTF-8 TEXT uses `textbyteshex`; embedded NUL text, integer extrema,
   multiple exact IEEE-754 bit patterns, and blobs round-trip exactly.
7. Editing `AGENTS.md`, `README.md`, or `docs/ARCHITECTURE.md` after preview or
   before resume changes the complete plan witness and fails before target
   mutation.
8. Output, archive, journal, staged receipt, temporary manifest, and final
   manifest writes traverse from one pinned root with no-follow descriptors;
   output and journal-temp symlink attacks do not escape or overwrite.
9. A permissive Unix umask still yields custody directories at 0700 and files
   at 0600.
10. Core status, with no bridge or SQLite dependency, reports ready only when
    the receipt authenticates to the exact journal, archive payload/manifest,
    export, and standalone snapshot witnesses; tamper becomes mixed-invalid.
11. Phase 4 proof runs behavioral commands and tests on temporary fixture
    copies and compares the committed fixture inventory before and after.
12. The Windows workflow runs compile, grammar, and explicit repository-command
    fail-closed checks only; Unix success integration and production promotion
    stay deferred to Phase 7.
13. `--version` is rejected, every contracted command token is enumerated, and
    filesystem/output I/O failures map to exit 74 while other frozen error
    classes retain their contracted exits.
