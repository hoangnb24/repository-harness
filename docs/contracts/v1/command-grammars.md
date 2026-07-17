# V1 Core And Bridge Command Grammar

Contract: `repository-harness-command-grammar/v1`

The machine-readable design authority is
`release/contracts/v1/command-grammars.json`. Phase 1 intentionally contains
neither runtime, so it cannot claim live CLI derivation. The closed
`command-implementation-binding.json` names the grammar and schema by exact
path/digest, declares `contract-only-entrypoints-absent`, and reserves these
future entrypoints:

- Phase 2 core: `scripts/bin/harness` and `scripts/bin/harness.exe`.
- Phase 4 bridge: `scripts/bin/harness-v0-migrate` and
  `scripts/bin/harness-v0-migrate.exe`.

The Phase 1 verifier proves all four are absent. If one appears while the
binding remains contract-only, verification fails instead of pretending the
grammar still represents the implementation. Phase 2 and Phase 4 acceptance
must replace the corresponding absence declaration with live CLI-help and
source-command extraction parity, including exact options, exits, and mutation
boundaries. The grammar schema and implementation-binding schema are closed;
an unknown field, reordered command, changed digest, mismatched entrypoint, or
seventh core command is a contract failure.

## Permanent V1 core

The executable identity is `harness` (`harness.exe` on Windows). The only
top-level commands are `install`, `update`, `audit`, `scaffold`, `status`, and
`version`; `--version` is an exact alias for `version`. `migrate`, every V0
lifecycle verb, and every bridge verb are unknown-command errors.

| Command | Boundary | Preview and recovery |
| --- | --- | --- |
| `install` | May create declared managed assets/recovery data and atomically commit the manifest. | `--preview`; `--resume <operation-id>` or `--rollback <operation-id>`. |
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

The bridge identity is `harness-v0-migrate` (`.exe` on Windows). Its only
top-level commands are `inspect`, `export`, `preview`, `apply`, `resume`,
`rollback`, and `version`.

`inspect`, `preview`, and `version` are read-only. `export` may write only a new
neutral export and archive staging output after exact source capture; it never
writes V0 sources or selected target paths. `apply` performs the bounded
journal-owned conversion. `resume` and `rollback` are explicit top-level bridge
commands because they are part of the temporary bridge state machine, not the
permanent core grammar.

All bridge commands are deterministic and non-interactive unless `apply`
requests confirmation. Non-interactive apply requires
`--non-interactive --accept-preview-sha256 <digest>`. Archive recovery choices
are options: default encrypted `--age-recipient`, or
`--archive-plaintext --acknowledge-plaintext-recovery-risk`. These options do
not add commands or permit source writes.

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
