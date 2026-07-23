# 0020 Installation Profiles And Knowledge Boundaries

Date: 2026-07-21

## Status

Accepted and active. Decision 0026 amends the default core to include the
explicit-only onboarding skill pair without adding an installation profile.

## Context

Decision `0019` made the repository-centered workflow authoritative but left the
installer physically distributing the earlier SQLite lifecycle, its historical
documents, upstream Harness product material, schemas, bootstrap scripts, and a
platform CLI binary to every consumer.

That payload creates conflicting signals. For example, a consumer receives a
generic repository workflow saying that no Harness CLI operation is required,
while the same installation adds database ignore rules, fourteen migrations,
CLI lifecycle manuals, and an executable. The root README and architecture also
describe this upstream Rust repository, not the consumer application.

The CLI and SQLite state still have real compatibility users. Removing them or
silently stripping existing installations would break external orchestration
and strand historical data. The boundary therefore needs packaging, not a code
deletion.

## Decision

Harness has exactly two installation profiles:

1. **Core** is the default. It installs only the compact repository map,
   repository-centered workflow, generic product/planning/decision structure,
   and the templates required to extend that structure.
2. **Core plus CLI** is selected explicitly with `--with-cli` in Bash or
   `-WithCli` in PowerShell. It adds the complete compatibility surface:
   lifecycle and protocol documentation, bootstrap scripts, every schema
   migration, database and binary ignore rules, release metadata, and one
   checksum-verified platform binary.

The CLI bundle is atomic at its observable boundary. Static compatibility files
and schemas are staged before they replace target files, and a failed binary
download or checksum leaves both the prior bundle and prior binary untouched.
An explicit CLI upgrade implies CLI selection and retains the immutable release
reference, backup, checksum, and atomic executable replacement contract.

An ordinary core install or refresh never downloads a CLI, creates
database-specific ignore rules, removes an existing executable, or deletes an
existing database. Existing compatibility files are left in place unless the
user separately selects a destructive, backed-up conflict mode.

Repository artifacts have one primary audience classification:

- **core**: generic consumer truth installed by default;
- **compatibility**: installed only with explicit CLI selection;
- **upstream-only**: product, implementation, release, and maintenance truth
  for this source repository; or
- **historical**: retained for provenance and forensic review.

Default documentation links only through core material. Compatibility and
historical indexes remain deliberately reachable in this source repository and
from stable upstream links, but they do not compete with the installed current
workflow.

Application-legibility work from the former Phase 2 follow-up in decision
`0019` is deferred until a real application supplies observable behavior. This
decision makes no claim that reducing the payload improves agent outcomes.

## Alternatives Considered

1. **Keep the full payload and merely document the CLI as optional.** Rejected
   because the physical install would continue presenting database machinery
   and upstream product documents as default consumer truth.
2. **Install only the CLI binary as the optional component.** Rejected because
   the executable depends on schemas, bootstrap behavior, protocol semantics,
   ignore rules, and compatible documentation.
3. **Delete the CLI and SQLite implementation.** Rejected because compatibility
   and historical state remain supported and no usage evidence justifies an
   irreversible removal.
4. **Offer arbitrary feature flags for individual documents and scripts.**
   Rejected because combinatorial profiles would replace one ceremony surface
   with another.
5. **Install upstream README and architecture as examples.** Rejected because
   their names and placement make them appear authoritative for the consumer.

## Consequences

Positive:

- A fresh default install has one clear authority path and no control-plane
  runtime.
- Consumers opt into one complete compatibility contract instead of assembling
  transitive CLI dependencies themselves.
- Upstream implementation and historical evidence remain available without
  becoming consumer product truth.
- Existing binaries and databases survive ordinary core refreshes.

Tradeoffs:

- External automation that assumed every fresh install contained the CLI must
  add the explicit compatibility flag.
- Installers must keep Bash and PowerShell profile behavior equivalent.
- The source documentation needs separate current, compatibility, and
  historical discovery paths.
- Compatibility remains maintained even though it is no longer the default.

## Follow-Up

- Decision 0021 resolves the application-legibility follow-up using the first
  real `e-inna-brain` evidence checkpoint. That checkpoint proves compact-core
  discovery and decision-boundary behavior while keeping the full runtime and
  interface loop explicitly unproven and active.
- Consider removing compatibility implementation only under a later decision
  with direct usage evidence and a recoverable migration.
