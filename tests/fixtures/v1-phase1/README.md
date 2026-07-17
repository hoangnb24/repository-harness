# Phase 1 Frozen Historical Fixtures

All key material here is test-only. `generate.py` derives deterministic private
seeds from labels containing `UNSAFE TEST ONLY`; those seeds are deliberately
unsuitable for production and never appear in a release trust bundle. Generated
bundles contain public keys only and mark them as fixtures.

The fixture set covers:

- valid core and bridge 2-of-3 indexes with disjoint keys/counters/tags;
- identity/order-2 public keys, zero-scalar signatures, a forged small-order
  2-of-3 envelope, unknown keys, role/domain crossover, bad thresholds,
  re-encoding, freeze, rollback, validly signed wrong active-root-bundle
  sequence, revocation, and root rotation;
- exact/mismatched bootstrap order/domains/roles/tag/sequence namespaces,
  reserved-workflow lifecycle/path, malformed schemas, closed command/release
  arrays, contract-only implementation binding, and nested output fields;
- valid/invalid manifests, forbidden fields, Windows ADS spellings, command
  grammar, release binary drift, and paths;
- an actual SQLite main/WAL/SHM set whose committed row is present only through
  WAL recovery, copied through a pinned root descriptor with ancestor/final
  swap and DB/WAL mutation/replacement negatives;
- exact weekly availability boundaries, decreasing/wrong-month timestamps,
  and incomplete category/platform receipt sets; and
- archive ciphertext bytes plus a one-byte tampered negative.

The focused verifier materializes symlinks and path swaps in a temporary
directory from `path-cases.json`; it never mutates these committed fixtures.
Decision 0014 removed inputs that the historical generator consumed, so
`generate.py` is retained only as provenance and is not a supported fixture
authority. Both direct regeneration and `generate.py --check` exit with a
controlled historical-only message. Use
`scripts/verify-v1-phase1-contracts.sh` for the cryptographic accepted-baseline
check. It binds the 94 immutable evidence artifacts to `9ad31ce` while allowing
this README and the historical generator wrapper to state their current
authority honestly; the directory still contains exactly 96 tracked files.
