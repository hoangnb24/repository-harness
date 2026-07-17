# US-106 V1 Phase 1 Design

Status: **Implemented / accepted**

## Domain Model

The Phase 1 domain is a chain of immutable declarations:

```text
bootstrap identity/pin
  -> root-threshold trust bundle
  -> release-role threshold
  -> signed payload index + role sequence
  -> disposition ledger join
  -> closed manifest/receipt and deterministic audit contract
```

Core and bridge have separate instances of every trust entity. A `KeyId` binds
raw Ed25519 public bytes. A `HighWaterMark` binds trust domain, role, sequence,
and canonical digest. A `RollbackAuthorization` is a root-threshold exception
for one exact lower sequence/digest under one exact active trusted root-bundle
sequence; it does not reduce the mark. Passing the root signature equation is
insufficient when the authorization names any other bundle sequence.

A `DispositionEntry` binds one current surface/path to exactly one of six
states. An eventual core artifact is the intersection of authenticated index
entries and `managed-v1`/`optional-v1` ledger entries. This makes signature and
path authorization independent checks.

A V0 `CaptureObservation` records file identity, byte length, and SHA-256 for
pre-copy, copied, and post-copy bytes. A `LogicalSnapshot` is an SQLite online
backup made only after staged DB+WAL recovery. Staged SHM is forensic evidence,
not logical input.

## Application Flow

### Contract verification

1. Parse every JSON document while rejecting duplicate member names.
2. Validate closed schemas and recursive forbidden manifest fields.
3. Compare the path ledger with the live installer manifest, schema discovery,
   generated binary destinations, and five-platform release path matrix.
4. Compare frozen V0 SQL bytes/hashes with current sources and replay migrations
   1–13 in an isolated temporary database.
5. Extract current parser operation arms and compare the exact changeset matrix;
   compare command/capability/version snapshots without executing Harness CLI.
6. Use the Phase 1-only Rust crypto helper (`ed25519-dalek::verify_strict` plus
   canonical, non-small-order, torsion-free point and scalar checks) for every
   fixture signature, then exercise threshold, crossover, high-water,
   rollback, revocation, and rotation decisions.
7. Materialize path negatives in a temporary directory and verify ADS,
   collision, symlink, ancestor-swap, final-swap, and mutation rejection.
8. Copy read-only DB/WAL/SHM fixtures through one pinned root descriptor, prove
   pre/copy/post identity-size-hash equality, recover only staged DB+WAL, and
   prove the standalone backup contains the WAL-only committed row.
9. Verify exact bootstrap/command/release arrays, archive tamper, monthly
   availability coverage/complete-set binding, and Decision 0012/0013 values.

No step constructs a V1 product artifact or writes a conversion result.

### Trust cause and effect

If two bridge release keys sign a core index, the Ed25519 equations are valid
but neither key belongs to `core-release`; zero authorized signatures count and
verification fails. If two core release keys sign sequence 41 after the client
stored 42, threshold passes but freshness fails. Only a separate 2-of-3 core
root authorization for the exact sequence/digest and the active trusted core
root-bundle sequence permits that one rollback. For example, with root bundle
3 active, an otherwise correct authorization signed by two valid roots but
naming bundle 2 passes envelope verification and then fails semantic
authorization.

## Interface Contract

The permanent core grammar is exactly:

```text
harness install|update|audit|scaffold|status|version
```

The bridge grammar is exactly:

```text
harness-v0-migrate inspect|export|preview|apply|resume|rollback|version
```

The full option and exit matrices are design authority in
`release/contracts/v1/command-grammars.json`; they are not extracted from a V1
or bridge runtime in Phase 1 because neither runtime exists.
`command-implementation-binding.json` closes that boundary: it pins the grammar
and schema digests, names `scripts/bin/harness[.exe]` as Phase 2 entrypoints and
`scripts/bin/harness-v0-migrate[.exe]` as Phase 4 entrypoints, and requires all
four to be absent. If an entrypoint appears early, Phase 1 fails. Phase 2/4 can
be accepted only after replacing the relevant absence state with parity among
the frozen grammar, live CLI help, and live source extraction, including
options, exits, and mutation boundaries.

The bootstrap identity follows the same lifecycle. Phase 1 reserves absent
core and bridge workflow paths for Phases 2 and 4. Production acceptance stays
blocked until the later phase supplies the workflow file, bound repository
protection evidence, exact pinned artifact-attestation evidence, and live
workflow-identity proof. The existing V0 release workflow remains separate and
is live-derived by release inventory verification.

Phase 1 exposes only the focused verification script:

```text
scripts/verify-v1-phase1-contracts.sh
```

It prints nine ordered proof groups and a final count. A failed invariant exits
1 with the exact contract error. It takes no mutation options and does not read
or create root Harness workflow state.

Before those groups, the wrapper runs `generate.py --check`, builds only the
non-publishable `v1-contract-crypto` test helper, and passes its exact path to
the Python checker. That helper is verification infrastructure, not the Phase
2 `harness` runtime or an installable release artifact.

## Data Model

There is no new product database. Machine contracts are versioned JSON; frozen
V0 schemas retain exact SQL bytes; fixtures contain JSON, opaque archive bytes,
and one SQLite DB/WAL/SHM triplet.

The V1 manifest schema is closed and forbids operational task/run/prompt/result/
trace/database/changeset fields recursively. A completed conversion receipt is
embedded only in `.harness/manifest.json` and references the untracked archive;
Phase 1 creates only a schema/example, not a receipt in this repository.

The archive contract defaults to age/X25519 encryption. Fixture archive bytes
are explicitly labeled unsafe test-only opaque ciphertext and contain no real
repository recovery data.

## UI / Platform Impact

There is no runtime CLI implementation or installer UI change. The contracts
normalize path safety across macOS, Linux, and Windows: NFC plus case-fold
collisions fail everywhere; reparse/symlink semantics fail closed; `.exe`
identity is explicit. The existing V0 Bash/PowerShell installers remain
unchanged.

## Observability

The focused verifier emits local test progress only. It creates temporary
schema-replay, path, capture, and standalone-backup files and removes them when
done. It records no Harness trace, telemetry, task, result, database, or
changeset. Release availability receipts are future signed release records,
not product telemetry.

## Alternatives Considered

1. Add prose only. Rejected because path, schema, parser, and signature drift
   would not fail CI.
2. Build the Phase 2 Rust product verifier now. Rejected because the product
   binary is a later phase boundary. Phase 1 includes only a non-publishable
   strict-Ed25519 fixture helper so contract proof does not depend on unsafe
   hand-written verification arithmetic.
3. Use one trust fixture for core and bridge. Rejected because it would not
   prove key crossover rejection or separate counters/workflows.
4. Generate a main-database-only fixture. Rejected because it cannot prove the
   accepted WAL-only recovery rule.
5. Modify current V0 help or parser to simplify snapshots. Rejected because
   Phase 1 freezes V0 rather than changing behavior.
