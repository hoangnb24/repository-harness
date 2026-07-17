# Phase 1 Machine-Readable Contracts

These files are normative inputs, not a V1 release payload. The focused
verifier checks closed schemas, grammar boundaries, current-path coverage,
frozen V0 bytes/parser surfaces, threshold signatures, freshness rules, path
safety, archive integrity, and the positive/negative fixtures.

`bootstrap-identity.json`, `command-grammars.json`,
`command-implementation-binding.json`, and `release-artifacts.json` have closed
schemas plus exact validators. The command implementation binding says Phase 1
is contract-only, names the exact future Phase 2/4 entrypoints, and requires
those entrypoints to be absent. A later phase must replace that state with live
CLI-help and source extraction parity before acceptance.

The bootstrap workflow paths are likewise reserved and absent: core for Phase
2 and bridge for Phase 4. Their closed lifecycle declarations block production
bootstrap acceptance until the file, repository-protection evidence, pinned
artifact attestation, and live workflow validation all exist. By contrast, the
current V0 release artifact inventory is compared with the live V0 workflow
matrix and build-script target/binary mapping now, so an extra platform or
renamed V0 binary cannot be hidden by editing only this directory.

`path-dispositions.json` is the authoritative Phase 1 ledger. An eventual core
artifact may select only authenticated `managed-v1` and `optional-v1` entries;
this directory does not itself authorize publishing or installation.
