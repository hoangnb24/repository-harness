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
Phase 1-5 gates are mechanical or authenticated evidence gates:

```bash
scripts/verify-v1-phase1-contracts.sh
scripts/verify-v1-phase2-core.sh
scripts/verify-v1-phase3-recovery.sh
scripts/verify-v1-phase4-bridge.sh
scripts/verify-v1-phase5-evidence.sh --dogfood-only
```

US-108 records 43 focused Phase 3 test functions, all 18 install, 15 update,
and 13 committed-update rollback checkpoints, 89 total `harness-core` tests,
181 workspace Rust tests, and 11 Phase 3 proof groups. The accepted Phase 3
evidence also proves retained hard-link witnesses for every
`before_sha256=None` create that recovery may later classify or remove, pinned
repository-root `st_dev`/`st_ino` journal binding that rejects copied cross-root recovery
evidence, canonical preview digests that match the emitted
`details.operations` array, read-only probe validation of staged/backup
evidence before `prepared` or `applying` recovery is surfaced, and monotonic
recovery validation that refuses payload downgrade or equal-sequence digest
drift before mutation. `rolling-back` remains explicit-only and is not a probe
status. Independent security (`gpt-5.4`, high reasoning) and behavior
(`gpt-5.6-sol`, medium reasoning) reviewers accepted exact candidate `1f957ce`,
integrated as `8e67593` with identical Git tree `9cd22cdb24d2`. Those Phase 3
results alone do not establish the later Phase 4, Phase 5, or Phase 7 gates.

US-109 supplies a separate accepted `harness-v0-migrate` implementation with 13 focused
tests and 10 Phase 4 proof groups. The evidence covers every schema 1..=13,
WAL-only recovery, unknown metadata, active-writer refusal, encrypted and
explicit-risk plaintext archives, unique staging and atomic no-replace
publication, abandoned/foreign custody preservation, exact live/archive export,
Phase 3 receipt recovery, pinned custody-directory swap rejection across
preview/recovery/audit, immutable fixture digests, and the structural core
boundary. The bridge never mutates V1 and has exactly four commands. An
independent reviewer accepted exact candidate `880cb9b`, fast-forwarded with
identical Git tree `0f81d3f0f4c8`. Phase 5 was then evaluated separately.
Five-platform promotion and Windows safe capture/atomic publication remain
Phase 7 evidence; Phase 4 proves only coherent compilation/help and controlled
unsupported exit 5 on Windows.

US-110 supplies accepted authenticated Phase 5 baseline evidence: an in-place
map pinned to accepted Phase 4, fixed P0-P7 schemas, exact ordinary-task argv,
offline SSH Ed25519 verification against caller-pinned out-of-repository owner
material, distinct repository-scoped owner IDs/repositories/bundle identities,
conditional same-stable-owner key sharing, enabled versioned acceptance tools,
bundle-resolved commits, complete packet custody/digests, strict UTC ordering,
and adversarial oracle verification:

```bash
scripts/verify-v1-phase5-evidence.sh
```

On exact `b2dd775`, the caller-pinned live invocation passed six proof groups
and rejected 42/42 adversarial cases. It authenticated two complete packets for
distinct canonical repositories, repository-scoped owner IDs, bundles, and
external Ed25519 keys under one stable GitHub identity. Both signatures and
bundle revisions verified. The external registry remains outside the candidate
repository at SHA-256
`f55a117eb20df727ee21cb922345d62bce3f3afc4458ba5a8b057dc430c9bb6d`;
the tracked trusted-owner registry remains empty.

Benchmark P1 is inapplicable and benchmark P6 failed; e-inna P0/P1/P3/P6
failed. These are baseline measurements rather than Phase 6 acceptance tests,
so they do not block Phase 5. Phase 6 has not started and will compare a future
candidate against them. Exact `b2dd775` has independent approval with no
remaining findings, but full premerge for the final documentation commit is
not claimed.

Authorized full premerge uses only the paired
`HARNESS_PHASE5_TRUSTED_OWNER_REGISTRY` and
`HARNESS_PHASE5_TRUSTED_OWNER_REGISTRY_SHA256` variables; the focused forwarding
contract runs the copied premerge under `/bin/bash`, requires six ordered case
markers, and rejects partial, unknown, positional, and dogfood-only bypass
inputs. The no-pair path uses a literal zero-argument verifier call, avoiding
empty-array expansion under macOS Bash 3.2 with `set -u`.

Mandatory premerge also snapshots `git status --short --untracked-files=all`
before verification and requires the exact same status afterward. The two
Phase 1/2 generated bridge executable names, `scripts/bin/harness-v0-migrate`
and `scripts/bin/harness-v0-migrate.exe`, are ignored explicitly; the source
crate and unrelated `scripts/bin` paths remain visible.
