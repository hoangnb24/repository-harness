# V1 Core And Bridge Command Grammar

Contract: `repository-harness-command-grammar/v1`

The machine-readable design authority is
`release/contracts/v1/command-grammars.json`. Phase 1 accepted both runtimes as
absent. Phase 2 evolved the closed `command-implementation-binding.json` to
`core-live-bridge-absent`; Phase 4 evolves it to
`core-live-bridge-live-unpromoted` while retaining the exact grammar and schema
digests.
It binds these identities:

- Phase 2 core: live platform-native `scripts/bin/harness`; Cargo binary name
  `harness`, which produces the Windows identity `scripts/bin/harness.exe`.
- Phase 4 bridge: live source and platform-native build identities
  `scripts/bin/harness-v0-migrate` and `scripts/bin/harness-v0-migrate.exe`,
  with production promotion still blocked.

The evolved Phase 1 verifier builds both identities, installs their native
executables at the exact repository-local paths, parses both machine-help
documents, extracts both Rust command definitions, and compares them with the
frozen grammars. Negative proof fails on an extra/reordered command or any
option, exit, or mutation-boundary drift. The schemas remain closed; an unknown field,
changed digest, mismatched identity, or seventh core command is a contract
failure.

## Phase 2 mutation boundary

The Phase 2 core provides real parsing, strict release verification through an
injected release port, manifest inspection, deterministic audit/status/version,
and deterministic install/update/scaffold planning. It does not execute a
write. `--preview` can succeed when an authenticated release is injected; a
non-preview mutation returns conflict exit 4. The repository-local CLI has no
promoted Phase 2 payload, so its mutation commands return the explicit
`authenticated-release-unavailable` or Phase 3 recovery refusal without
creating `.harness` state.

Cause and effect: `harness install --resume op-1` parses as the frozen install
grammar, but atomic journal ownership does not exist yet. It therefore returns
exit 4 and leaves every byte unchanged. Phase 3 may implement that option's
atomic backup/journal execution without changing the six-command grammar.

## Permanent V1 core

The executable identity is `harness` (`harness.exe` on Windows). The only
top-level commands are `install`, `update`, `audit`, `scaffold`, `status`, and
`version`; `--version` is an exact alias for `version`. `migrate`, every V0
lifecycle verb, and every bridge verb are unknown-command errors.

| Command | Boundary | Preview and recovery |
| --- | --- | --- |
| `install` | May create declared managed assets/recovery data and atomically commit the manifest. On first install only, `--v0-archive-manifest <path>` binds a verified archive receipt into that same transaction. | `--preview`; `--resume <operation-id>` or `--rollback <operation-id>`. |
| `update` | May update declared managed surfaces/recovery data and atomically commit the manifest. | Same options as install. |
| `audit` | Strictly read-only; starts zero processes. | No recovery option. |
| `scaffold` | May create one explicitly selected neutral artifact; never operational task state. | `--preview`; `--resume` or `--rollback` for its own interrupted operation. |
| `status` | Strictly read-only. | Reports recovery-required state but cannot resolve it. |
| `version` | Strictly read-only and repository-independent. | None. |

Install, update, and scaffold support `--non-interactive` only with
`--accept-preview-sha256 <digest>`. The digest binds the canonical deterministic
preview. If current bytes produce a different preview, the command exits with
conflict and performs no mutation. Interactive confirmation is never inferred
from a TTY in non-interactive mode.

Recovery is an option on the command that owns the mutation, not a new
top-level command. `harness update --resume op-...` revalidates every before and
post image and performs only incomplete update operations. `--rollback` restores
only matching command-owned bytes and stops before overwriting a target edit.

## Separate V0 bridge

Decision 0014 replaces the proposed conversion grammar. The bridge identity is
`harness-v0-migrate` (`.exe` on Windows), and its only top-level commands are
exactly `inspect`, `export`, `archive`, and `version`. `preview`, `apply`,
`resume`, and `rollback` are usage errors; the bridge has no conversion journal
or target mutation to preview or recover.

- `inspect` reads either frozen live V0 input or an archive manifest. With an
  age identity it also verifies encrypted inner members.
- `export --output <new-path>` writes one new neutral, read-only SQLite export
  from live frozen input or `--archive-manifest`; an encrypted archive also
  needs `--age-identity-file`.
- `archive` writes one new archive under `.harness-v0-archive`. Encrypted mode
  requires `--age-recipient`; plaintext requires both
  `--archive-plaintext` and `--acknowledge-plaintext-recovery-risk`.
- `version` is repository-independent and read-only.

Cause and effect: `archive` captures exact DB+WAL+SHM and recognized evidence,
publishes a unique checksummed archive with no-replace semantics, and stops.
It cannot create `.harness/manifest.json`, `.harness/recovery`, or
`harness-v1.db`. The user then runs normal `harness install
--v0-archive-manifest <path>`; Phase 3 recovery commits fresh V1 files and the
archive receipt together, manifest last.

## Exit contract

| Code | Meaning |
| --- | --- |
| `0` | Successful ready/read-only result or completed mutation. |
| `2` | Structurally valid but unresolved V1 readiness. |
| `3` | Invalid manifest, trust, path, schema, grammar, archive, or repository state. |
| `4` | Conflict or recovery-required state; evidence preserved. |
| `5` | Bridge input is recognized but outside the frozen supported range. |
| `64` | Closed-grammar/argument usage error. |
| `70` | Internal invariant failure with no claimed success. |
| `74` | I/O failure with no claimed success; recovery metadata may be present only for a started mutator. |

Core never emits 5. Install/update return 2 only after atomically committing a
structurally valid unresolved manifest. Status returns 0 for ready or
unresolved state and reports readiness in the envelope; audit returns 2 for
unresolved. A parse error is always 64 and cannot touch repository state.
