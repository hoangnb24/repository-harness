# V1 Manifest, Repository State, And Output Contract

Contract: `repository-harness-manifest/v1`

## Placement and compatibility

The only committed V1 manifest is `.harness/manifest.json`. A completed V0
conversion receipt is embedded at the manifest's top-level
`conversion_receipt` field. It is never inferred from an archive directory and
is never placed in a target-owned document. The receipt names the untracked
archive path, export digest, standalone backup digest, archive/ciphertext
digest, confidentiality mode, recipient fingerprints, and bridge release.

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
| `fresh-v1` | Valid manifest; no recognized active V0 state. | Allowed within command contract. |
| `brownfield-v1` | Valid explicit target mappings; no V0 conversion claim. | Allowed; target-owned bytes remain immutable. |
| `v0-legacy` | Recognized V0 state and no V1 manifest. | Core mutation refused; bridge may inspect. |
| `conversion-in-progress` | Valid untracked bridge journal; no completed receipt. | Core mutation refused; bridge resume/rollback only. |
| `converted-v1-with-archive` | Valid manifest plus embedded completed receipt and matching archive/export identities. | Allowed; archive never mutated. |
| `mixed-invalid` | Contradictory V0/V1 state, false/missing receipt, or ambiguous ownership. | All mutation refused; status/audit explain exact causes. |

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
