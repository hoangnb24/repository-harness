# Repository Harness V1 Normative Contracts

Contract version: `1`

Status: Normative for Phase 1; runtime implementation is deferred.

These documents and the machine-readable material in
`release/contracts/v1/` freeze the inputs to Phases 2–8. If prose and JSON
conflict, the stricter fail-closed rule applies and the conflict must be fixed
by a reviewed contract change before implementation proceeds.

- `manifest-and-state.md` defines the manifest, roles, assets, modes,
  compatibility ranges, receipt placement, unresolved markers, forbidden
  fields, and deterministic output.
- `command-grammars.md` defines the permanent six-command V1 grammar and the
  separate seven-command bridge grammar, including exits, preview,
  non-interactive confirmation, recovery options, and the Phase 1
  contract-only/absent implementation binding that later phases must replace
  with live CLI and source parity.
- `payload-trust.md` defines indexes, detached signatures, threshold bundles,
  canonicalization, freshness, bootstrap identity, destination rules, and the
  path-disposition ledger.
- `scaffold-and-audit.md` defines deterministic safe-path, link, marker,
  digest, and zero-process-execution rules.
- `compatibility-conversion-and-retirement.md` binds Decision 0012 and Decision
  0013 to archive custody, exact V0 capture, availability evidence, and Phase 8.
- `v0-compatibility.md` freezes schemas 1–13, the changeset parser matrix, V0
  feature surface, and category dispositions without extending V0 behavior.

Example dependency: Phase 2 can parse `manifest-v1.schema.json`, but it cannot
invent a seventh core command. Phase 4 can read the frozen V0 schema copies,
but those bridge-only files cannot enter the core index. A later release cannot
claim acceptance if either boundary check fails.
