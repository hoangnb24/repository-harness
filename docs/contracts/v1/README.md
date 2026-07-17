# Repository Harness V1 Normative Contracts

Contract version: `1`

Status: Normative; Phase 1 accepted, the core runtime is live, and the Phase 4
bridge source is live-unpromoted.

These documents and the machine-readable material in
`release/contracts/v1/` freeze the inputs to Phases 2–8. If prose and JSON
conflict, the stricter fail-closed rule applies and the conflict must be fixed
by a reviewed contract change before implementation proceeds.

- `manifest-and-state.md` defines the manifest, roles, assets, modes,
  compatibility ranges, receipt placement, unresolved markers, forbidden
  fields, and deterministic output.
- `command-grammars.md` defines the permanent six-command V1 grammar and the
  separate seven-command bridge grammar, including exits, preview,
  non-interactive confirmation, recovery options, and the implementation
  binding. Phase 2 replaces the core's former absence state with live CLI and
  source parity; Phase 4 adds separate bridge CLI/source parity without adding
  bridge commands or dependencies to the core.
- `payload-trust.md` defines indexes, detached signatures, threshold bundles,
  canonicalization, freshness, bootstrap identity, destination rules, and the
  path-disposition ledger.
- `scaffold-and-audit.md` defines deterministic safe-path, link, marker,
  digest, and zero-process-execution rules.
- `compatibility-conversion-and-retirement.md` binds Decision 0012 and Decision
  0013 to archive custody, exact V0 capture, availability evidence, and Phase 8.
- `v0-compatibility.md` freezes schemas 1–13, the changeset parser matrix, V0
  feature surface, and category dispositions without extending V0 behavior.

Example dependency: the Phase 2 core parses `manifest-v1.schema.json`, but it
cannot invent a seventh core command. Phase 4 can read the frozen V0 schema copies,
but those bridge-only files cannot enter the core index. A later release cannot
claim acceptance if either boundary check fails.
