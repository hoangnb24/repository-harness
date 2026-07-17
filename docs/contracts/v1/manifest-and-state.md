# V1 Manifest, Repository State, And Output Contract

Contract: `repository-harness-manifest/v1`

## Placement and compatibility

The only committed V1 manifest is `.harness/manifest.json`. A first install may
embed a top-level `v0_archive_receipt`; this records evidence linkage, not
converted operational state. It is accepted only from an explicit
`--v0-archive-manifest` path under authenticated `.harness-v0-archive` custody.
The receipt binds the exact archive manifest, neutral export, standalone backup,
payload, source capture, confidentiality mode, archive ID, and bridge release.
It is write-once: later install/update cannot replace it.

The closed V1 receipt contract supports bridge release `1.0.0` exactly. Both
the archive manifest and embedded receipt use that literal; any other string,
including a later semantic version, fails before mutation until a reviewed
contract and core release explicitly add support.

The manifest declares:

- its schema version and repository mode;
- V1 CLI minimum and maximum semantic versions;
- template-release minimum and maximum semantic versions;
- the exact payload-index role, sequence, and digest; and
- one entry for every selected role.

Unsupported schema or range decisions fail before mutation. Install/update own
future manifest transitions; status/audit never rewrite a manifest to make it
compatible.

## Roles and assets

Every role records four independent state axes:

| Axis | Values | Direct effect |
| --- | --- | --- |
| `activation` | `active`, `unresolved`, `disabled` | Unresolved is structurally valid but not ready. Disabled is legal only for `required=false`. |
| `ownership` | `managed-file`, `managed-block`, `target-owned` | Mutation is limited to the declared managed surface. |
| `origin` | `created`, `v0-adopted`, `brownfield-mapped` | Origin records provenance; it never grants ownership. |
| `required` | boolean | A required role cannot be disabled. |

Each role also records its stable role and asset IDs, repository-relative path,
template ID/release when applicable, exact-byte base/current SHA-256 values,
managed marker identity when applicable, update policy, and unresolved marker
list. Update policy is exactly `replace-if-base`, `three-way-review`, or
`never-auto-patch`. Target-owned assets always use `never-auto-patch`.

Example:

1. `docs/adr/` is selected as the decisions role.
2. The manifest records `brownfield-mapped` plus `target-owned`.
3. A new template release exists.
4. Because ownership is target-owned and policy is `never-auto-patch`, update
   may report the template but writes no ADR bytes.
5. Audit validates the mapping and links; it does not rename the directory or
   score ADR prose.

## Unresolved and invalid states

An unresolved marker is the exact ASCII token
`REPOSITORY-HARNESS-UNRESOLVED(<role-id>:<marker-id>)`. The manifest lists each
expected token and path. A required role is `unresolved` exactly while one or
more listed tokens remain in its managed surface. Missing markers, extra
undeclared marker IDs, marker/path disagreement, unsafe paths, digest mismatch,
or missing managed-block delimiters are invalid—not unresolved.

Concrete effect: a fresh template with a named test-command placeholder may be
installed and reported unresolved. If a user deletes only the opening block
delimiter, the asset is invalid because V1 can no longer identify its managed
surface safely.

## Repository modes

| Mode | Required evidence | Mutating V1 behavior |
| --- | --- | --- |
| `fresh-v1` | Valid manifest initialized from repository files. It may contain an authenticated V0 archive receipt. | Allowed within the six-command core contract; archived V0 rows are never active state. |
| `brownfield-v1` | Valid explicit target mappings initialized from existing repository files. It may contain an authenticated V0 archive receipt. | Allowed; target-owned bytes remain immutable. |

Recognized live `harness.db` without an explicit first-install archive receipt
blocks mutation: the user must freeze and archive it first. A foreign or
unauthenticated `.harness-v0-archive`, `.harness/legacy`, or `.harness/recovery`
pathname grants no ownership and remains untouched. There is no
`conversion-in-progress` or `converted-v1-with-archive` mode.

Example: V0 contains task row 42. The bridge export retains row 42 as historical
evidence. Core install reads repository files, not row 42, so fresh V1 has no
active task 42. The manifest receipt proves exactly which archive/export was
preserved before cutover.

A pathname alone never proves a mode. For example, `.harness/` plus an unknown
file is not V0 evidence; it is preserved as unknown/unowned.

## Forbidden manifest fields

At any depth, manifest member names are rejected when their normalized name is
one of: `task`, `tasks`, `run`, `runs`, `prompt`, `prompts`, `result`, `results`,
`user`, `users`, `trace`, `traces`, `raw_command_output`, `telemetry`, `score`,
`scores`, `scheduler`, `schedule`, `queue`, `intake`, `story`, `backlog`,
`decision`, `database`, `sqlite`, or `changeset`. Unknown fields also fail
because every schema object is closed.

Cause and effect: adding `"tasks": []` does not become harmless extension
metadata. Schema validation fails, audit exits invalid, and no mutating command
may commit that manifest.

## Deterministic output envelope

Machine output is one UTF-8 JSON line matching
`repository-harness-output/v1`. It contains command identity, outcome, exit
code, mutation classification, repository mode, release identity, sorted
notices, and command-specific `details`. It never includes current time,
duration, random IDs, absolute host paths, environment values, or raw command
output. Paths use normalized repository-relative `/` spelling and arrays use
the order specified by each command contract.

`details.operations[*]` is closed rather than an arbitrary extension object.
Each operation contains exactly its stable operation ID, enumerated kind,
safe relative path, allowed disposition, and nullable before/after SHA-256.
An added nested field such as `shell_command` invalidates the whole envelope.

Human output is derived from the same envelope. Diagnostics go to stderr.
Given identical repository bytes, manifest, index, arguments, and compatibility
inputs, stdout, stderr, exit code, preview digest, and mutation plan are byte
identical.
