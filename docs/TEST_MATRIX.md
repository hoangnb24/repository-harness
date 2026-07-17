# Test Matrix

This file preserves the proof vocabulary and brownfield import shape used by
Harness consumers. The authoritative operational matrix is stored in SQLite
and queried with:

```bash
scripts/bin/harness-cli query matrix --active --summary
```

The upstream Harness repository has implemented behavior and executable proof.
An installed consumer starts without consumer-product rows and adds them only
when real work is accepted. Do not mark a row implemented until tests or other
validation evidence exist.

## Status Values

| Status | Meaning |
| --- | --- |
| planned | Accepted as intended behavior, not implemented |
| in_progress | Actively being built |
| implemented | Implemented and proof exists |
| changed | Contract changed after earlier implementation |
| retired | No longer part of the product contract |

## Matrix

No static product rows are shipped in this legacy view. Use `story add` and
`story update` for operational records. Brownfield repositories may add rows
here before importing their existing state.

## Evidence Rules

- Unit proof covers pure domain and application rules.
- Integration proof covers backend enforcement, data integrity, provider
  behavior, jobs, or service contracts.
- E2E proof covers user-visible browser flows.
- Platform proof covers only shell, deployment, mobile, desktop, or runtime
  behavior that cannot be proven in lower layers.
- A story can be implemented without every proof column if the story packet
  explains why.

## V1 Phase Gates

The separate V1 core does not use the legacy SQLite matrix above. Its accepted
Phase 1/2 gates and the locally validated Phase 3 candidate are mechanical:

```bash
scripts/verify-v1-phase1-contracts.sh
scripts/verify-v1-phase2-core.sh
scripts/verify-v1-phase3-recovery.sh
```

US-108 records 43 focused Phase 3 test functions, all 18 install, 15 update,
and 13 committed-update rollback checkpoints, 89 total `harness-core` tests,
181 workspace Rust tests, and 11 Phase 3 proof groups. The Phase 3 candidate
also proves retained hard-link witnesses for every `before_sha256=None` create
that recovery may later classify or remove, pinned repository-root
`st_dev`/`st_ino` journal binding that rejects copied cross-root recovery
evidence, canonical preview digests that match the emitted
`details.operations` array, read-only probe validation of staged/backup
evidence before `prepared` or `applying` recovery is surfaced, and monotonic
recovery validation that refuses payload downgrade or equal-sequence digest
drift before mutation. `rolling-back` remains explicit-only and is not a probe
status. Phase 4 bridge and Phase 7 production/platform rows remain absent and
must not be inferred from those results. Phase 3 acceptance remains pending
until fresh exact-hash reviewers approve the candidate.
