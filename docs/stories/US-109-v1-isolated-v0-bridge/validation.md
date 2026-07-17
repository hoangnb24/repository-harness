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

Pending implementation. Record exact commands, exit codes, focused test names,
fixture inventory digest, verifier proof count, and platform boundaries here.
US-109 remains `in_progress` in the shared database until independent Phase 4
acceptance. Phase 5 stays closed, and Phase 7 production/five-platform
promotion remains closed.

