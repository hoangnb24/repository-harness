# V1 Phase 6 Capability-Evaluation Framework

This directory contains the source-only Phase 6 evaluation protocol. It is not
part of the V1 installed payload and does not claim Phase 6 acceptance.

`baseline-lock.json` binds the accepted Phase 5 framework and authenticated
packets at exact Repository Harness commit `5d6e6bc`. `schemas/` contains
closed records for cold-clone and warm-V0-copy lanes, comparable conditions,
evaluation subjects, intervention totals, results, comparisons, packet
custody, and external authentication.

Complete packets reject duplicate JSON keys before any digest, schema, or
signature decision. Candidate subjects bind the lane's exact base commit/tree
and a manifest-digested Git bundle; verification imports that bundle into a
new bare repository, resolves the declared candidate commit/tree, proves the
base is its ancestor, and requires every declared capability path to be a
committed blob. Comparison outcomes are copied mechanically from the
authenticated Phase 5 or signed warm baseline and signed candidate result;
failed-to-passed improvement cards are derived from those outcomes.

Every P1 finding, negative-condition clearance, and improvement claim carries
packet-manifest artifact and SHA-256 references. Every condition prompt has a
separate owner signature asserting its exact digest before candidate execution,
and the held-out P3/P6 record must name that same prompt, so a harmless dummy
prompt cannot hide path or descriptive capability hints.

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
destination and emits a closed, allowlist-redacted public manifest. Capture
pins the source root, exact optional WAL/SHM namespace, recognized-member
inventory, and directory change tokens before copying; it rescans after handle
acquisition and at completion and rejects creation, removal, replacement, or
even transient create/remove activity.

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
