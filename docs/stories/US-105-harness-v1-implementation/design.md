# US-105 Repository Harness V1 Implementation Design

Status: **Implementation in progress / Phases 1-3 accepted / Phases 4-8 not started**

## Domain Model

### Compatibility authorization

Decision 0012 supplies the compatibility values that were a predecessor to
product implementation. Gate G0 is approved/open. Decision 0013 and US-106
freeze and prove Phase 1. US-107 implements, validates, and independently
accepts the hardened pure Phase 2 core at exact candidate `1b1add5`, integrated
as `e77e028` with the identical Git tree. US-108 implements, validates, and
independently accepts Phase 3 at exact candidate `1f957ce`, integrated as
`8e67593` with identical Git tree `9cd22cdb24d2`. Phases 4-8 remain not started.

| Approved value | Current policy | Cause and effect |
| --- | --- | --- |
| Compatibility window | `2027-01-01T00:00:00Z` through `2027-12-31T23:59:59Z`, inclusive | Phase 1 can encode exact support and release contracts. Support covers security, data-loss, archive/recovery, and supported-input compatibility defects or mitigations, not new V0 features. |
| Local conversion archives | Retained indefinitely as write-once, checksum-verified recovery evidence under repository-owner custody | No install, update, audit, bridge command, uninstall, or Phase 8 action may automatically delete, overwrite, truncate, or relocate an archive. Explicit manual deletion must warn that V0 recovery is lost. |
| Bridge release assets | Retained through `2028-06-30T23:59:59Z`, inclusive | Release maintainers periodically verify every supported-platform binary, checksum, authenticated index or attestation, supported-input matrix, release notes, source tag, and reproducible build instructions. |
| Phase 8 eligibility | No earlier than `2028-01-01T00:00:00Z` and only after every Decision 0012 closure condition passes | The timestamp does not itself authorize removal; an unresolved recovery/security/data-integrity condition or missing retained asset delays removal. |

The window assumes the V1 core and bridge are generally available on every
declared platform by `2027-01-01T00:00:00Z`. If they are not, the window must
not silently shrink. A new explicit decision must shift the start, end,
bridge-asset retention, and Phase 8 eligibility, reaffirm indefinite local
archive retention, and preserve at least 365 supported days.

A conversion journal created before `2027-12-31T23:59:59Z` closes the window
remains eligible for supported resume or rollback. A known unresolved in-window
recovery case delays actual Phase 8 removal. Phase 8 also requires no unresolved
supported-range security, data-loss, or archive-integrity defect, verified
bridge-asset retention, and separate removal authorization and validation.

### Roles and assets

A `Role` describes why a target path participates in the V1 seed kit. Each role
has four independent fields:

| Field | Allowed values | Rule |
| --- | --- | --- |
| `activation` | `active`, `unresolved`, `disabled` | Unresolved is structurally installed but contains named completion markers; disabled is outside the selected contract. |
| `ownership` | `managed-file`, `managed-block`, `target-owned` | Only the declared managed surface may be mutated by V1. |
| `origin` | `created`, `v0-adopted`, `brownfield-mapped` | Origin records how the selected path entered the manifest; it does not grant mutation ownership. |
| `required` | `true`, `false` | A required active role must be complete for readiness; an optional role may be disabled. |

A `ManagedAsset` binds a role to an asset identifier, target path, template
identifier and release, base/current digest where applicable, optional marker
identity, and update policy. Update policy is exactly `replace-if-base`,
`three-way-review`, or `never-auto-patch`. Every target-owned adopted or mapped
asset uses `never-auto-patch`.

Cause-and-effect example:

1. `docs/adr/` is explicitly mapped as the target's decisions role.
2. Its origin becomes `brownfield-mapped`, but its ownership remains
   `target-owned`.
3. `harness update` sees a newer decision template.
4. Because the target path is `never-auto-patch`, update reports the available
   template but writes nothing to existing ADRs.
5. Audit checks the recorded mapping and required links, not the prose quality
   or directory name.

Valid readiness transitions are deterministic:

- `unresolved -> active` only after every named completion marker is removed or
  satisfied and structural audit passes;
- `active -> unresolved` when a required managed completion marker is
  introduced by an explicit update;
- an optional role may move to or from `disabled` only through an explicit
  install/update selection;
- an invalid digest, unsafe path, broken required link, missing managed marker,
  or contradictory manifest never becomes `unresolved`; it is `invalid`.

### Binary and release identities

| Identity | Repository-local binary | Grammar | State boundary |
| --- | --- | --- | --- |
| V0 operational CLI | `scripts/bin/harness-cli` or `.exe` | Existing V0 lifecycle verbs, including database `migrate` and operational `audit` | May operate on V0 SQLite and changesets; never interprets a V1 manifest. |
| V1 core | `scripts/bin/harness` or `.exe` | `install`, `update`, `audit`, `scaffold`, `status`, `version` | Never opens V0 SQLite/changesets; has no `migrate` verb. |
| V0 bridge | `scripts/bin/harness-v0-migrate` or `.exe` | `inspect`, `export`, `preview`, `apply`, `resume`, `rollback`, `version` | Immutable read of published V0 inputs plus bounded journal-owned filesystem conversion. |

Aliases and grammar-translation wrappers across these identities are invalid.
Each artifact reports its own semantic version. The V1 CLI declares supported
manifest-schema and template-release ranges; each template release declares
its required CLI range; the bridge declares its exact V0 schema and changeset
grammar range.

### Release, conversion, and evaluation records

- `PayloadIndex`: authenticated release inventory and destination rules.
- `DispositionEntry`: one classification for every candidate release path.
- `V0Export`: neutral `repository-harness-v0-export/v1` representation that
  preserves source identity, schema version, category, digest, and disposition
  without importing V0 task state into V1.
- `ConversionArchive`: checksummed, untracked preservation of recognized V0
  inputs, export, provenance, and its own manifest.
- `OperationJournal`: transient untracked filesystem-operation log with
  before/after digests; never a task lifecycle log.
- `CutoverReceipt`: V1-manifest record of a completed conversion, written only
  at the atomic commit point and naming export/archive digests.
- `PilotCard`: immutable release-only scenario definition P0-P7 with repository
  revision, candidate identities, environment, prompt, fixtures, acceptance
  tests, evaluator, intervention log, and evidence locations.

## Application Flow

### Initiative gate and phase flow

1. Use accepted Decision 0012 as the Gate G0 evidence for the exact dates,
   retention, support, and removal-precondition policy.
2. Begin Phase 1 only through a separately executed implementation change and
   make the approved values inputs to contracts and release metadata. This
   authorization documentation does not itself begin Phase 1.
3. Complete Phases 1 through 7 linearly; each phase consumes the preceding
   phase's reviewed proof rather than assuming a later pilot or release will
   repair an earlier contract gap.
4. Keep Phase 8 dormant while the compatibility window is open, even if Phase
   7 release proof has passed.
5. Begin Phase 8 no earlier than `2028-01-01T00:00:00Z`, and only after
   wall-clock evidence and every Decision 0012 support, recovery, security,
   archive-integrity, asset-retention, and separate authorization/validation
   condition pass.

### V1 install and update

1. Resolve the authenticated payload index and verify release identity and all
   source digests.
2. Inspect the repository mode and selected role mappings without treating a
   pathname as proof of ownership.
3. Produce an exact preview: paths created, managed blocks changed, target-owned
   paths left untouched, backups, role states, and expected manifest result.
4. Reject unsafe paths, unsupported manifest/template versions, mixed-invalid
   V0/V1 state, digest mismatches, and ambiguous ownership before mutation.
5. Apply only authorized managed-file or managed-block operations, preserving
   backups and post-image digests needed for safe recovery.
6. Run deterministic structural checks.
7. Atomically commit the validated manifest. A crash before this point leaves
   no new manifest that claims success; rerun/recovery revalidates current
   digests before acting.

Example: a fresh install creates a selected managed template containing an
exact completion marker. The write and manifest commit succeed because the
structure is valid, then `status` reports `installed/unresolved` and `audit`
returns 2. V1 does not fill the marker by guessing a test command.

### V1 audit, status, scaffold, and version

- `audit` parses the manifest and authenticated index, validates safe paths,
  digests, markers, role state, required links, and forbidden fields, then
  returns 0 ready, 2 unresolved, or 3 invalid. It starts no target process.
- `status` reports installation/readiness, repository mode, V0/V1/bridge
  identities, compatibility decision, and exact invalid/unresolved reasons. It
  returns 0 for valid or unresolved state and 3 for invalid state.
- `scaffold` explicitly creates a selected neutral target-owned work artifact
  from a published template contract; it never creates operational task state
  or infers a stack.
- `version` and `--version` report identical V1 identity and compatibility
  ranges without reading or changing target state.

### V0 bridge conversion

1. `inspect` recognizes V0 only from the conservative database/schema,
   companion-changeset, or known-installer signature; unknown `.harness`
   metadata is classified unknown/unowned and preserved.
2. The immutable reader opens recognized schema versions 1 through 13
   read-only, verifies the bridge's published changeset grammar range, and
   never runs a V0 migration.
3. `export` writes and checksums the neutral export.
4. Before target mutation, the bridge writes and verifies the conversion
   archive under
   `.harness/legacy/v0-conversion/<conversion-id>/`.
5. `preview` lists every proposed managed operation, conflict, preserved path,
   archive/export digest, and resulting role state.
6. `apply` creates the transient journal, rechecks compatibility and input
   digests, performs idempotent operations, and validates V1 structure.
7. The commit point atomically renames a fully validated V1 manifest plus
   receipt. Only then is conversion `completed`.
8. `resume` repeats only incomplete journal operations after validating all
   recorded digests. `rollback` restores only journal-owned paths whose current
   post-image still matches; neither operation deletes the archive or writes
   the V0 database.

Conflict example: after an interrupted apply, a maintainer edits a newly
created managed block. The current digest no longer matches the journal's
post-image. Rollback refuses to overwrite it, preserves the V0 inputs and
archive, marks recovery required, and asks for a human choice.

## Interface Contract

### Permanent V1 command contract

| Command | Mutability | Required result |
| --- | --- | --- |
| `harness install` | Write, after preview/confirmation or its documented deterministic non-interactive contract | Fresh/adopted/mapped roles, backups as needed, and atomic manifest; no claimed success on failure. |
| `harness update` | Write, under per-asset update policy | Supported manifest/template transition, explicit three-way review, or reject-and-preserve conflict. |
| `harness audit` | Read-only | Deterministic structural result: exit 0 ready, 2 unresolved, 3 invalid; no target execution or V0 reads. |
| `harness scaffold` | Write, explicit selected artifact only | Neutral scaffold at a safe path; no stack inference or lifecycle record. |
| `harness status` | Read-only | Repository mode, installation/readiness, identities, compatibility, and exact issues; exit 0 reportable or 3 invalid. |
| `harness version` / `harness --version` | Read-only | Same V1 CLI version and supported schema/template ranges. |

Any other top-level V1 command, especially `migrate`, is a contract failure.
Only `install`, `update`, and `scaffold` may mutate files.

### Bridge command contract

| Command | Mutability | Required result |
| --- | --- | --- |
| `inspect` | Read-only | Recognized/preserved/unsupported inventory and compatibility result. |
| `export` | Creates export only | Versioned neutral export with source/category/payload digests. |
| `preview` | Read-only apart from already requested export/archive preparation | Exact operation plan, conflicts, result state, and digests; no target mutation. |
| `apply` | Journal-bounded writes | Idempotent conversion and atomic receipt, or preserved recovery-required state. |
| `resume` | Journal-bounded writes | Only incomplete operations after digest validation; conflict stops. |
| `rollback` | Journal-bounded restoration | Only matching journal-owned changes restored; archive and V0 inputs preserved. |
| `version` | Read-only | Bridge version, supported V0 schema/grammar range, platform identity, and compatibility statement. |

The bridge's first accepted schema range is 1 through 13 inclusive. The exact
changeset grammar range and bridge artifact version must be frozen and proven
in Phase 1; this packet does not invent them.

### Repository modes and errors

The modes are `fresh-v1`, `brownfield-v1`, `v0-legacy`,
`conversion-in-progress`, `converted-v1-with-archive`, and `mixed-invalid`.
V0 artifacts plus a V1 manifest without a completed receipt are
`mixed-invalid`; V1 mutation is blocked until bridge resume or rollback
resolves the state.

Errors are reject-and-preserve. They name the failed contract, affected path or
identity, expected/actual digest when safe to disclose, and next allowed
action. They never repair ambiguous ownership automatically.

## Data Model

### V1 manifest contract

The committed manifest is versioned and sufficient to reconstruct structural
role state without a database. It contains:

- manifest schema and V1 CLI/template compatibility identities;
- repository mode and installation/readiness state;
- one role record with activation, ownership, origin, and required fields;
- one asset record with stable asset/template identifiers, path, release,
  digests, marker identity if applicable, and update policy;
- authenticated payload-index identity/digest;
- only tool-local recovery references needed for incomplete V1 mutations;
- completed bridge receipt, if converted, with bridge/export/archive digests.

Schema validation rejects task, run, prompt, result, user, trace,
raw-command-output, telemetry, score, scheduler, database, and semantic
changeset fields. A schema rejection is invalid state, not unresolved content.

### Payload contract

The authenticated payload index, not a glob or source-tree convention, is the
release authority. Each entry records release identity and authentication,
logical asset, source SHA-256, destination rule, role, template identity, and
path disposition. Every candidate release path appears exactly once in the
disposition ledger as:

- managed V1 payload;
- optional V1 payload;
- source-only/not installed;
- target-owned destination only;
- bridge-only legacy payload; or
- forbidden V0 operational payload.

Build cause and effect: CI verifies the authenticated index, selects only its
managed/optional entries, validates each digest/destination, and fails if an
unindexed path or forbidden V0 path enters the V1 core artifact. Forbidden
examples include `harness.db*`, `.harness/changesets/**`, `scripts/schema/**`,
the V0 operational binary, and V0 lifecycle documentation. A separately
authenticated bridge index may include its immutable reader and fixtures but
cannot be merged into the V1 core index.

### Bridge payload, archive, and recovery contract

The archive contains recognized V0 database files, recognized changesets,
known V0 provenance, the neutral export, and an archive manifest with digests.
Unknown/unowned metadata stays in place and is recorded as preserved. The
journal contains conversion identifier, state, operation identifiers, owned
paths/markers, and before/after digests; it contains no V0 lifecycle records.

The state machine is:

```text
discovered -> inspected -> exported -> archived -> prepared -> applying
    -> committed -> completed
                         ^
failure -----------------+ (resume or rollback from a recorded safe point)
```

The atomic manifest-and-receipt rename is the sole commit point. Kill-point
tests interrupt after detection, export, archive, each planned file operation,
temporary-manifest write, and atomic commit. Before commit they must prove V0
inputs unchanged and no success receipt; afterward they must prove a coherent
completed receipt or an explicit recoverable failure.

Local conversion archives are write-once, checksum-verified recovery evidence
retained indefinitely under repository-owner custody. Automated product
actions may not delete, overwrite, truncate, or relocate them. Manual deletion
is outside the bridge workflow and must warn that V0 recovery is lost.

## UI / Platform Impact

The product surface is a repository-local CLI plus Bash/PowerShell installer
and release artifacts. The Phase 7 proof target is the existing five platform
labels:

- `macos-arm64`
- `macos-x64`
- `linux-x64`
- `linux-arm64`
- `windows-x64`

macOS and Linux prove Bash installation and the direct `harness` and, during
the window, bridge binary. Windows proves PowerShell installation and `.exe`
identities. Each platform must authenticate the same payload index, produce
equivalent manifests/audit outcomes, reject the same forbidden paths, and
preserve line-ending/path semantics. Spaces and Unicode paths, nested
instructions, docs-only repositories, and monorepo-shaped repositories are
fixture dimensions, not separate product grammars.

A platform without a promoted and verified artifact is unsupported; an error
must name the unsupported platform before target mutation.

## Observability

V1 core emits deterministic human-readable and machine-readable command
results sufficient to identify release, mode, role state, path, digest
conflicts, and next action. Exact envelope/version fields are frozen in Phase
1. Core commands do not send telemetry or create task/run/trace records.

The bridge journal and receipt are recovery/provenance records, not product
analytics. They remain local and untracked except for explicit evidence copies
authorized by a pilot owner.

Pilot evidence is release-only. Each intervention records actor, timestamp,
taxonomy reason, minutes, and outcome effect; reports total human attention by
card and pilot. No target is required to continue collecting evaluation data
after the release decision.

## Alternatives Considered

1. Begin Phase 1 and fill dates later. Rejected because artifact availability,
   support cost, recovery promises, and Phase 8 eligibility would be undefined.
2. Put conversion into `harness install` or add permanent `harness migrate`.
   Rejected because V0 database semantics would enter the permanent V1 core.
3. Infer ownership from familiar paths. Rejected because `.harness/`,
   `AGENTS.md`, or `docs/` can be target-owned or foreign; guessing can destroy
   evidence or target content.
4. Treat a failed apply as permission to overwrite on retry. Rejected because a
   human edit after interruption must win over journal automation.
5. Let audit run target tests to decide readiness. Rejected because structural
   seed-kit validation and target semantic validation are different trust and
   execution boundaries.
6. Promote after templates and installers pass fixtures only. Rejected because
   release behavior must also pass the fixed pilot protocol without hidden
   human labor.
7. Remove V0 at Phase 7 release. Rejected because Phase 8 is gated by actual
   window closure and approved support/retention conditions, not engineering
   readiness alone.
