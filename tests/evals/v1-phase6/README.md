# V1 Phase 6 Capability-Evaluation Framework

This directory contains the source-only Phase 6 evaluation protocol. It is not
part of the V1 installed payload and does not claim Phase 6 acceptance.

`baseline-lock.json` binds the accepted Phase 5 framework and authenticated
packets at exact Repository Harness commit `5d6e6bc`. `schemas/` contains
closed records for cold-clone and warm-V0-copy lanes, comparable conditions,
evaluation subjects, intervention totals, results, comparisons, packet
custody, and external authentication.

The committed evidence index is deliberately
`candidate-results-pending`. Framework verification succeeds in that state;
`--require-candidate-results` returns the documented pending outcome until
owner-authorized warm capture, fresh-agent execution, candidate evidence, and
external signatures exist.

## Lane boundary

- `cold-clone` uses only an authenticated Phase 5 repository bundle and runs
  P0-P7.
- `warm-v0-copy` uses an externally held, owner-authorized copy of ignored V0
  runtime files and runs only P0/P1.

Raw databases, WAL/SHM files, standalone backups, V0 archive payloads, private
keys, absolute owner paths, and unredacted V0 rows are prohibited from this
tree. The capture utility writes raw material only beneath an external private
destination and emits a closed, allowlist-redacted public manifest.

## Commands

```bash
scripts/verify-v1-phase6-evidence.sh --framework-only
scripts/verify-v1-phase6-evidence.sh
scripts/verify-v1-phase6-evidence.sh --require-candidate-results
tests/evals/test-v1-phase6-evidence.sh
```

Complete candidate verification will additionally require a caller-pinned
external trusted-owner registry and its independently obtained SHA-256. The
tracked repository never supplies its own trust root.
