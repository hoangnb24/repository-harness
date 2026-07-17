# US-107 V1 Pure Core Design

Status: **Implemented and fully validated; review re-acceptance pending**

## Domain Model

The core domain contains only manifest roles, authenticated payload assets,
safe paths, repository readiness, deterministic operations, and the closed
output envelope. It has no task, run, prompt, result, trace, telemetry, score,
scheduler, queue, database, SQLite, or semantic-changeset entity.

Four explicit ports isolate host concerns:

| Port | Input/output | Phase 2 authority |
| --- | --- | --- |
| `FileSystemPort` | Read/test one declared path and validate the command-scoped root snapshot before success. | No write/process method exists; a read-only identity change or host I/O failure is exit 74, while a mutator preview conflict is exit 4. |
| `ManifestPort` | Strictly parse `.harness/manifest.json` through the filesystem port. | Duplicate members, unknown fields, and recursively forbidden operational fields fail closed. |
| `ReleasePort` | Supply downloaded raw index/signatures, trust-bundle/signatures, adjacent path-ledger bytes, and exact indexed source bytes. | It cannot supply bootstrap roots, trust policy, root state, release freshness, or the authoritative ledger digest. |
| `TrustPort` | Supply independently pinned bootstrap/current-root state, canonical path-ledger digest, test/production policy, and mandatory first-install or existing high-water state. | Adjacent bundle keys or rewritten ledger rows never become authority; production rejects fixture roots, bundles, and keys. |

`HarnessCore` receives all four ports by dependency injection. Unit tests use
memory ports. The repository CLI uses an OS read adapter, the JSON manifest
adapter, and separate unavailable-release/unavailable-trust adapters because
Phase 2 has no promoted payload or production root state. Phase 3 can replace
only the adapter/execution boundary; it does not need to add a seventh command
or introduce V0 state.

## Application Flow

### Audit

1. Open `.harness/manifest.json` through a declared no-follow read.
2. Reject duplicate JSON members, unknown schema fields, and forbidden
   operational names before deserializing the domain object.
3. Validate CLI/template ranges, core role/sequence/digest identity, repository
   mode, receipt consistency, role independence, ownership/update policy,
   unique role/marker/path identities, and platform collision keys.
4. For each enabled role, read only its declared path. On Unix the adapter pins
   one root descriptor for the entire command, uses `openat` plus `NOFOLLOW`,
   retains ancestor/final handles, reads the final handle twice, compares
   pre/copy/post identity/size/mtime/ctime and exact bytes/hashes, and reopens
   each namespace component through its still-pinned parent.
5. Parse deterministic CommonMark structure with exact-pinned `pulldown-cmark`
   for inline links/titles, escaped
   parentheses, reference links, images, code-span/fence exclusions, ATX and
   Setext headings, same-document and cross-file fragments, valid external URI
   schemes, percent-encoded path characters versus fragment separators, and
   duplicate anchors. One-letter colon prefixes remain repository-path
   candidates so Windows drive references fail closed instead of bypassing path
   validation as URI schemes. Heading
   IDs use NFC plus GitHub-style Unicode lowercase; filesystem collision keys
   retain their separate full-case-fold rule. Compare exact bytes, managed marker
   pairs (including every extra/mismatched close), and exact unresolved tokens.
6. Sort notices/violations and emit one envelope. No command string is parsed
   from target bytes and no target process API exists in the port/application.
7. Before exit 0/2, reopen the repository root namespace and require its
   identity to match the command-pinned root. Non-Unix inspection returns the
   deterministic fail-closed I/O result until Phase 7 supplies equivalent safe
   handle semantics.

Concrete canary:

1. The test repository declares an executable `audit-canary.sh` whose body
   writes `audit-spawned-canary` if executed.
2. A declared tool-definition document names that executable as its target
   tool and links to it.
3. Audit reads both declared files and validates the link/digests.
4. Two audits return identical ready JSON, the repository tree is byte/mode
   identical, and `audit-spawned-canary` does not exist.

This is proportional proof for the declared canary and repository tree,
combined with the no-process/no-write port architecture and executed race
tests. It is not described as a portable event-level or universal syscall
trace; that broader five-platform evidence remains Phase 7.

### Authenticated preview

1. `ReleasePort` supplies only downloaded release bytes. `TrustPort`
   independently supplies pinned roots/current bundle sequence+digest, the
   canonical Phase 1 ledger digest, production/test policy, and release
   freshness.
2. The canonical trust-bundle digest is verified under
   `repository-harness-core-trust-bundle-v1`. Equal sequence/equal digest is
   idempotent; lower or equal/different is rejected. Higher revocation bundles
   require exact previous digest and old-root 2-of-3; rotations require both
   old-root and new-root 2-of-3 before new revocations take effect.
3. Strict JSON/JCS and Ed25519 verification then require canonical raw bytes
   for every detached signature envelope and the exact core
   domain/role, canonical non-small-order points, nonzero canonical scalar,
   distinct authorized keys, and a 2-of-3 release threshold. Offline first
   install requires an exact digest or minimum sequence. A lower release needs
   the exact root-signed rollback domain/role/sequence/digest and active root-
   bundle sequence; successful rollback never lowers stored high-water.
4. The verifier rejects bridge material, stale sequence/digest, a rewritten
   adjacent ledger that differs from the independent canonical digest, unindexed
   supplied bytes, missing indexed bytes, forbidden/bridge/source-only ledger
   rows, schema-invalid optional nulls/IDs, digest/length disagreement, unsafe
   destinations, and full-Unicode folded source/destination collisions.
5. Only a `VerifiedRelease` reaches planning. Plans sort stable operations and
   hash their canonical JSON.
6. Install/update/scaffold first audit any existing manifest and update binds
   the candidate payload transition. Corrupt/mixed state produces no plan;
   structurally valid unresolved state remains explicit in the envelope.
7. `--preview` returns that plan. Non-preview execution returns exit 4, so a
   correct plan cannot bypass the missing Phase 3 journal/atomic-commit proof.

## Interface Contract

The interface parser is driven by the frozen source command definition. It
accepts only the six top-level commands and their frozen options. Parse errors
return 64 before repository adapters are constructed. `--non-interactive` and
`--accept-preview-sha256` must appear together; `--resume` and `--rollback` are
mutually exclusive and cannot be combined with preview/confirmation options.

The source file contains a delimited JSON command definition. Verification
extracts the literal without compiling it and separately reads the live
binary's `--help`. Comparing both entire objects with
`release/contracts/v1/command-grammars.json` covers command order, binary
identity, option order, exit arrays, forbidden commands, and mutation strings.

## Data Model

The committed manifest schema and output schema remain the Phase 1 contracts.
Phase 2 creates no repository manifest. An absent repository uses a deterministic
unbound release placeholder in output; it does not claim a signed payload.
Audit of an absent manifest is invalid exit 3, while status reports absence at
exit 0.

Preview operations use only the already-closed operation fields. The preview
SHA-256 is over canonical JSON for that operation array and is exposed as a
sorted notice, not an extensible arbitrary output object.

## UI / Platform Impact

The Cargo binary is named `harness`, giving `harness` on Unix and `harness.exe`
on Windows. Focused local proof installs the native build at the exact
repository-local identity. The unpromoted workflow binds the same name across
the existing five platform labels. Cross-platform promotion/artifact proof is
still Phase 7.

## Observability

Outputs contain only deterministic command, outcome, exit, mutation,
repository mode, release identity, notices, readiness, violations, and closed
operations. They contain no time, duration, random identifier, absolute path,
environment value, raw command output, or telemetry.

Human output is an exact golden-tested projection of the same envelope: it
uses explicit contract enum strings, preserves case-sensitive IDs/paths, emits
release/readiness/operation fields, and escapes control characters before any
line is rendered. Manifest runtime validation mirrors the closed JSON schema,
including const values, IDs, digests, optional-null rejection, and nested
closed fields. Help and envelope output use fallible stdout writes; an output
device failure returns host-I/O exit 74 for help/read/mutator output and the
version command's existing contracted internal exit 70 instead of panicking.

## Alternatives Considered

1. Add a V1 subcommand to `harness-cli`. Rejected because V0 and V1 identities
   and database semantics must remain separate.
2. Let audit execute declared proof commands. Rejected because target bytes are
   untrusted execution input and semantic target proof is outside structural
   audit.
3. Implement writes without recovery. Rejected because a preview that looks
   correct does not prove crash-safe backup, journal ownership, atomic manifest
   commit, resume, or target-edit-preserving rollback.
4. Accept a payload directory glob. Rejected because only the authenticated
   index joined with the Phase 1 ledger can authorize core assets.
