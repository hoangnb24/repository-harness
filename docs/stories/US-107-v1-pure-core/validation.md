# US-107 V1 Pure Core Validation

Status: **Implemented and fully validated; review re-acceptance pending**

## Proof Strategy

Acceptance requires four independent equalities/boundaries:

1. Frozen grammar = live `harness --help` = independently extracted Rust source
   definition, including exact order/options/exits/mutations.
2. Raw downloaded release material + separately injected pinned trust/root,
   canonical ledger digest, and freshness state -> authenticated bundle lifecycle + strict
   index/ledger/source verification -> private `VerifiedRelease`; no adjacent
   key can select its own anchor.
3. Declared manifest/files -> read-only deterministic audit; executable/tool
   definitions remain inert bytes.
4. Any Phase 2 write/recovery request -> exit 4/64/3 as contracted -> identical
   filesystem snapshot.

The existing Phase 1 verifier must retain all nine trust, schema, V0 freeze,
path, WAL capture, archive, availability, and policy groups while evolving only
the core-live/bridge-absent lifecycle.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Strict duplicate/floating JSON and optional-null rejection; JCS stability; small-order/zero-scalar rejection; version-pinned Unicode full folding for paths; GitHub-style Unicode heading lowercase; pinned root/ancestor/final swap and same-size rewrite negatives; CommonMark link/heading forms; golden human/envelope projection; fallible stdout exit mapping. |
| Integration | Signed Phase 1 core/revocation/rotation/rollback fixtures; noncanonical detached envelopes; missing/self-issued/stale/incomplete-threshold/wrong-root/fixture-production negatives; mandatory offline and ledger-digest pins; bridge/high-water/unindexed/forbidden-ledger negatives; bidirectional schema/runtime differential; same-document fragment negatives; corrupt-state mutator refusals; deterministic ready/unresolved/invalid results. |
| E2E | Native `scripts/bin/harness` grammar/dispatch/version; JSON Schema validation of live envelopes; audit executable/tool canary and unchanged tree; control-injection rendering; mutation/refusal tree snapshots. |
| Platform | Cargo `harness` identity binds Unix and `.exe`; Unix safe-handle behavior is tested. Non-Unix repository inspection deliberately fails closed until Phase 7; promoted five-platform artifact/behavior parity is not claimed. |
| Dependency | Direct core dependencies exclude `rusqlite`/V0; source contains no process-command constructor; ports expose no write/process method. |
| Release lifecycle | Core workflow source/repository identity and proof-before-promotion guard; external evidence absent; bridge file/entrypoints absent. |

## Focused Negative Proof

- Add or reorder a core command in memory: grammar comparison fails.
- Add an option or exit: whole-definition comparison fails.
- Invoke `migrate`, bridge verbs, V0 lifecycle verbs, `help`, or unknown text:
  exit 64 and no success output.
- Supply bridge-signed material, stale sequence, unindexed source bytes, or a
  signed asset whose ledger row is changed to `forbidden-v0-operational`:
  release verification fails before planning.
- Rewrite an otherwise usable adjacent ledger reason, change its independent
  digest pin, or pretty-print a valid detached signature envelope: canonical
  trust verification fails before asset authorization.
- Supply an unsigned/missing bundle envelope, self-issued replacement roots,
  a stale pre-revocation bundle, only one side of a root-rotation threshold, a
  wrong root-bundle sequence rollback, unauthorized rollback, or fixture trust
  under production policy: authentication fails before release keys count.
- Replay equal root sequence/equal digest: it is idempotent. Replay lower or
  equal-sequence/different-digest root state: it fails. Authenticate the higher
  revocation/rotation fixtures: only then do revoked keys stop counting.
- Add `tasks` to the manifest or change a managed byte: audit exits 3.
- Add schema-invalid IDs/consts/digests/optional nulls/nested fields, an extra
  Harness close, malformed unresolved token, or control-character path:
  runtime rejects it and human output cannot inject a new line.
- Use sequence `9007199254740991`: schema and runtime accept it. Increment it
  once: both reject it as outside the interoperable JCS integer range.
- Link to percent-encoded Unicode and duplicate same-document anchors: valid
  fragments pass and a missing local fragment exits 3.
- Use `urn:`, another valid URI scheme, or a network-path URL: audit leaves the
  external target unjudged. Percent-encode `#` inside a relative filename: it
  remains part of the path rather than becoming a fragment separator. A
  one-letter Windows drive reference remains path-like and fails closed.
- Leave an exact declared unresolved token: repeated audit exits 2 with
  byte-identical JSON.
- Name an executable and proof command in a declared tool document: audit reads
  the link but never creates the executable's sentinel.
- Synchronize root/ancestor/final replacement or a same-size in-place rewrite:
  pinned-handle proof refuses success rather than mixing snapshots. Read-only
  snapshot change and host I/O failure use the documented exit 74, not
  validated-invalid exit 3 or an undocumented exit 4.
- Invoke all three mutators, preview, resume/rollback, malformed confirmation,
  and `migrate`: the complete filesystem mode/digest snapshot is unchanged.
- Make stdout writes fail: help/read/mutator rendering returns exit 74 and
  version rendering preserves its frozen exit 70 through a fallible writer
  rather than panicking with an out-of-contract process exit.
- Request workflow promotion: the only promotion job depends on proof and exits
  1; the workflow has no content/id-token write permission or publish action.

## Commands

Focused proof already run during implementation:

```bash
scripts/verify-v1-phase1-contracts.sh
scripts/verify-v1-phase2-core.sh
cargo test -p harness-core --locked
cargo clippy -p harness-core --all-targets --locked -- -D warnings
```

Final acceptance additionally requires:

```bash
bash -n scripts/verify-v1-phase1-contracts.sh
bash -n scripts/verify-v1-phase2-core.sh
PYTHONPYCACHEPREFIX=<temporary> python3 -m py_compile \
  scripts/verify_v1_phase1_contracts.py \
  scripts/verify_v1_phase2_core.py \
  tests/fixtures/v1-phase1/generate.py
python3 tests/fixtures/v1-phase1/generate.py --check
cargo fmt --all -- --check
cargo check --workspace --locked
cargo test --workspace --locked
cargo clippy --workspace --all-targets --locked -- -D warnings
git diff --check
scripts/validate-premerge.sh
git status --short -- .harness repomix-output.xml crates/harness-cli \
  scripts/schema scripts/install-harness.sh scripts/install-harness.ps1 \
  scripts/harness-install-files.txt '.github/workflows/*bridge*' \
  'scripts/bin/harness-v0-migrate*'
```

## Validation Evidence

Validation evidence passes on the same working tree:

- Phase 1: 9/9 evolved proof groups.
- Deterministic Phase 1 fixtures: 72/72 files reproduce.
- Phase 2 Rust: 46 tests (24 unit and 22 integration), 0 failed.
- Phase 2 mechanical verifier: 11/11 proof groups.
- Focused core clippy: passed with warnings denied.
- Workspace check/test/clippy: passed; 138 Rust tests passed and warnings were
  denied.
- Full `scripts/validate-premerge.sh`: passed, including the evolved Phase 1
  verifier, the Phase 2 verifier, V0 CLI/install/release regressions, live-doc
  checks, and workflow proof.

These are implementation-validation results, not authority to self-approve a
review. Commit `9b84ba8` was rejected, so Phase 2 review re-acceptance remains
pending until the orchestrator amends and the reviewer accepts this hardened
tree.

## Residual Phase 3 Gates

Phase 2 intentionally leaves these gates closed:

1. A promoted authenticated payload/bootstrap source must be supplied; test
   fixture keys never become production trust.
2. File backups, journal ownership, exact before/post images, and recovery
   metadata must be defined without adding a command.
3. Install/update/scaffold execution must use descriptor-anchored writes,
   durable flush ordering, atomic manifest commit, and crash kill-point proof.
4. `--accept-preview-sha256` must be rechecked immediately before commit.
5. Resume must execute only incomplete command-owned operations; rollback must
   stop before overwriting a target edit.
6. Idempotency, replace-if-base, managed-block three-way review,
   never-auto-patch, unsupported transition/downgrade, and no-false-success
   matrices must pass.

Until all six close, a plan does not authorize a write and exit 4 is the safe
result.

## Residual Phase 4 And Phase 7 Gates

- Phase 4 still owns the absent `harness-v0-migrate[.exe]` reader/converter,
  V0 schema 1..=13 capture, export/archive/journal state machine, conversion
  receipt, and bridge workflow. No bridge source or grammar was added here.
- Phase 7 still owns safe equivalent root/ancestor/final handle semantics on
  non-Unix platforms, proportional event/syscall monitoring where portable,
  exact five-platform artifact identity, installer equivalence, attestation,
  and promoted workflow/repository-protection evidence. Phase 2's workflow
  remains source-present-unpromoted and production bootstrap remains blocked.
