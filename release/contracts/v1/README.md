# Phase 1 Machine-Readable Contracts

These files are normative inputs, not a V1 release payload. The focused
verifier checks closed schemas, grammar boundaries, current-path coverage,
frozen V0 bytes/parser surfaces, threshold signatures, freshness rules, path
safety, archive integrity, and the positive/negative fixtures.

`bootstrap-identity.json`, `command-grammars.json`,
`command-implementation-binding.json`, and `release-artifacts.json` have closed
schemas plus exact validators. The command binding is now
`core-live-bridge-absent`: Phase 2 mechanically compares the platform-native
`scripts/bin/harness` machine help and Rust source definitions with the frozen
grammar, while both Phase 4 bridge entrypoints remain absent.

The core bootstrap workflow source is present but unpromoted in Phase 2; the
bridge workflow remains reserved absent. The closed lifecycle still blocks
production core bootstrap because external repository-protection and pinned
artifact-attestation evidence are not present. The current V0 release artifact
inventory remains separate and is compared with the live V0 workflow matrix
and build-script target/binary mapping, so an extra platform or renamed V0
binary cannot be hidden by editing only this directory.

`path-dispositions.json` is the authoritative Phase 1 ledger. An eventual core
artifact may select only authenticated `managed-v1` and `optional-v1` entries,
and its independent trust input must pin this ledger's canonical digest;
adjacent release bytes cannot self-authorize a replacement. This directory
does not itself authorize publishing or installation.
