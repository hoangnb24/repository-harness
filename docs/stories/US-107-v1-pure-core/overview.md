# US-107 V1 Pure Core

Status: **Implemented, fully validated, and accepted**

## Current Behavior

At exact base `60042891a0b6e0ecd6b1ff66c3e019cf01fea680`, Phase 1
had accepted the V1 contracts but deliberately required all future core and
bridge entrypoints/workflows to be absent. Repository operation still belonged
to the unchanged V0 `harness-cli`, SQLite schemas, and V0 installers.

Phase 2 now adds a separate `harness-core` Rust package whose binary name is
`harness`. Focused verification builds that package and places the native
binary at `scripts/bin/harness`; the same Cargo binary name produces
`scripts/bin/harness.exe` on Windows. It does not alias, wrap, or modify
`harness-cli`.

## Target Behavior

The permanent V1 surface has exactly six top-level commands, in this order:

```text
install update audit scaffold status version
```

The implementation provides the Phase 2 portion of each contract:

| Command | Phase 2 behavior | Cause and effect |
| --- | --- | --- |
| `install` | Parses all frozen options, authenticates an injected payload through independent release/trust ports, audits any existing manifest, and creates a deterministic file plan. | `--preview` can return the plan only from valid state; a write request returns exit 4 because Phase 3 has not supplied atomic recovery. |
| `update` | Requires and semantically audits a valid existing manifest, binds its release identity to an allowed authenticated transition, and preserves structurally valid unresolved state. | Corruption, a stale/equal-different payload, a missing manifest, or a target-byte conflict is reported without changing bytes. |
| `audit` | Reads the manifest and only its declared safe paths through one pinned command root, then validates compatibility, roles, digests, markers, CommonMark links/anchors, and unresolved tokens. | A declared executable/tool definition remains inert bytes in the canary fixture. Ready is 0, unresolved is 2, validated invalid is 3, and host I/O failure is 74. |
| `scaffold` | Selects one authenticated template and requires its exact signed destination. | A different or existing destination is rejected; no generator or target tool runs. |
| `status` | Reports absent, ready, unresolved, or invalid V1 structural state. | It never repairs a manifest or infers V0 ownership from `.harness/`. |
| `version` / `--version` | Emits the same V1 identity without reading repository state. | An injected filesystem that panics on reads is not called. |

`harness --help` is deterministic machine JSON. The Phase 1 and Phase 2
verifiers compare its full command/options/exits/mutation array with both the
frozen grammar and the independently extracted Rust source definition. An
extra or reordered command fails.

Downloaded release material cannot choose its own trust anchor. `ReleasePort`
supplies the index, detached envelopes, trust bundle, ledger, and indexed
bytes; the separate `TrustPort` supplies pinned bootstrap/current roots, active
root-bundle sequence/digest, the authoritative canonical path-ledger digest,
release high-water or mandatory offline-first-install pin, and the
production-versus-test policy. Cause and effect: a
self-issued bundle may sign its own index, but it cannot satisfy the pinned
old-root threshold, so planning never receives a `VerifiedRelease`.

On Unix, one repository-root descriptor is retained for the whole command and
every component is opened relative to it. Each declared file is read twice
through the pinned final handle with pre/copy/post identity, size, change-time,
and exact-byte/hash comparison; root namespace identity is revalidated before
success. On platforms without this safe handle implementation, repository
inspection fails closed with exit 74 until Phase 7; `version` remains
repository-independent.

## Affected Users

- V1 core implementers, who now have a pure, dependency-injected runtime
  boundary for Phase 3.
- Repository owners, who can run deterministic structural audit/status without
  giving Harness permission to execute target-controlled tools.
- Release maintainers, who have a present-but-unpromoted workflow source and a
  mechanically closed promotion guard.
- V0 users, whose current CLI, schemas, commands, database behavior, and
  installer remain unchanged.

## Affected Product Docs

- `docs/REFACTOR_PLAN.md`
- `docs/contracts/v1/**`
- `release/contracts/v1/**`
- `docs/stories/US-105-harness-v1-implementation/**`
- this US-107 packet

## Non-Goals

- Phase 3 atomic writes, backup/journal creation, recovery, resume, rollback,
  idempotent install/update, or manifest transition execution.
- Phase 4 V0 recognition, SQLite reads, conversion, export, archive, or bridge
  entrypoints/workflow.
- A promoted payload, production keys, signing, publishing, tagging, releases,
  attestations, repository-protection changes, or pilot execution.
- Any V0 parser, command, schema, installer, or behavior change.
- Harness planning database, intake/story/query operations, `.harness`
  changesets, `repomix-output.xml`, push, or external mutation.
