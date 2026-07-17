# US-106 V1 Phase 1 Contracts And Release Inventory

Status: **Implemented / accepted**

## Current Behavior

Repository Harness currently ships V0. Its Bash and PowerShell installers read
`scripts/harness-install-files.txt`, discover all `scripts/schema/*.sql`, and
download a platform-specific `harness-cli` plus adjacent checksum. The Rust V0
parser exposes 50 public command paths, reads schema versions 1–13, and accepts
changeset header v1 plus a closed operation set at operation versions 1–2.

The V1 refactor plan previously described the intended manifest, six-command
core, separate seven-command bridge, release index, and conversion archive, but
those rules were not versioned machine contracts. As a result, Phase 2 could
not mechanically answer questions such as:

- whether `scripts/schema/013-changeset-content-sha.sql` may enter core;
- whether one release signature is enough;
- how sequence 41 behaves after sequence 42 was accepted;
- whether a committed WAL-only row survives capture; or
- whether `docs/README.md` and `docs/readme.md` are portable together.

Decision 0012 opens G0. Decision 0013 records the approved security, bootstrap,
archive-confidentiality, exact capture, and availability contract. The external
orchestrator owns the isolated planning-database record for this story; this
worktree runs no Harness CLI, root database, migration, or changeset operation.

## Target Behavior

Phase 1 is accepted only when repository files make every boundary concrete:

1. Closed JSON schemas define manifest/roles, payload indexes, trust bundles,
   detached signatures, rollback authorization, deterministic output, archive
   manifests, and availability receipts.
2. The V1 core grammar contains exactly six commands. The separate bridge
   grammar contains exactly seven. Preview, deterministic non-interactive
   confirmation, exits, mutation ownership, and recovery choices are explicit.
3. Core and bridge use disjoint Ed25519 2-of-3 root/release bundles, domain
   tags, counters, tags, workflows, high-water marks, and fixtures.
4. Every current install/release path and V0 data category has exactly one
   disposition. Core construction rejects unindexed and V0-operational paths.
5. The exact SQL bytes for schemas 1–13, current 50-command surface, protocol
   capabilities, and complete changeset operation/version matrix are frozen.
6. A focused verifier proves positive and negative schema, grammar, path,
   trust, freshness, archive, symlink/swap, source-read-only, and WAL-only cases.

Concrete example: the verifier reads the real current installer manifest and
requires the ledger's `installer-manifest` rows to be exactly equal. Adding one
new V0 payload line without a reviewed disposition makes premerge fail. A
correct Ed25519 signature cannot override a forbidden disposition.

## Affected Users

- V1 core implementers, who receive closed Phase 2 inputs rather than choosing
  security or grammar rules in code.
- Bridge implementers and V0 repository owners, who receive exact reader and
  capture boundaries without Phase 1 performing conversion.
- Release maintainers, who own separate signing domains and weekly/monthly
  availability evidence.
- Target repository owners, whose useful paths and encrypted recovery evidence
  remain under their ownership.
- Reviewers, who can run one focused verifier and see exactly which contract
  group failed.

## Affected Product Docs

- `docs/REFACTOR_PLAN.md`
- `docs/decisions/0013-v1-security-and-v0-capture-contract.md`
- `docs/contracts/v1/**`
- `release/contracts/v1/**`
- `docs/stories/US-105-harness-v1-implementation/**`
- this US-106 packet

## Non-Goals

- Implementing `harness[.exe]`, its six runtime commands, or its installer.
- Implementing `harness-v0-migrate[.exe]`, a V0 reader, conversion writes,
  journals, export, apply, resume, or rollback.
- Changing or expanding any V0 public behavior, installer behavior, schema,
  command, capability, or changeset grammar.
- Creating production keys, signing, release workflows, artifacts, tags,
  attestations, releases, pilots, or Phase 8 removal.
- Treating fixture keys as production material or GitHub/Sigstore provenance as
  the V1 payload trust root.
- Running Harness bootstrap, CLI, database, migration, or changeset operations
  in this worktree; external orchestration owns the US-106 workflow record.
- Modifying `.harness`, Herdr resources, unrelated work, or
  `repomix-output.xml`.
