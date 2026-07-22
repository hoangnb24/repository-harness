# Test Suite Map

Use this map to answer four questions before changing or deleting a test:

1. What behavior does it protect?
2. Who observes the failure?
3. Which validation entry point invokes it?
4. What product or compatibility boundary must disappear before the test can
   be removed?

The normal Linux entry point is `scripts/validate-premerge.sh`. It runs Rust
workspace tests first and then the shell contracts listed below. Windows
installer behavior runs separately in `.github/workflows/premerge.yml`.

## Current Core

| Location | Protects | Failure visible to | Invocation | Removal boundary |
| --- | --- | --- | --- | --- |
| `crates/harness/tests/` | Core installation, latest-release handoff, provenance, agent-resolvable three-way updates, recovery, and clean architecture | Every default Harness installation | `cargo test --workspace --locked` | Remove only with the Rust `harness` maintenance product |
| `tests/workflow/` | Repository-centered read-only, bounded, durable-plan, and authority behavior | Agents and maintainers using the default workflow | Directly from `scripts/validate-premerge.sh` | Replace only with stronger real-agent outcome evaluation |
| `tests/docs/test-doc-contracts.sh` | Current authority, documentation indexes, installation boundaries, and validation entry points remain coherent | Contributors and installed-core maintainers | Directly from `scripts/validate-premerge.sh` | Remove only after equivalent link and authority checks exist elsewhere |
| `tests/boundary/test-phase5-optional-consumer-split.sh` | A fresh core does not install Symphony, SQLite lifecycle, traces, scoring, or evaluation machinery | Default core users | Directly from `scripts/validate-premerge.sh` | Remove when the core/optional-consumer boundary no longer exists |
| `tests/maintenance/test-harness-release-classification.sh` | Core-affecting changes trigger the correct `harness` release | Core release maintainers | Directly from `scripts/validate-premerge.sh` | Remove with automated core releases |
| `tests/release/test-harness-release-*` and `test-post-merge-release-recovery.sh` | Core asset inventory, source identity, workflow shape, and failed-release recovery | Users downloading native `harness` binaries | Directly from `scripts/validate-premerge.sh` | Remove with native core publication |

## Optional Compatibility CLI

These tests are intentionally not evidence for the default repository workflow.
They protect the published SQLite and protocol-v1 compatibility surface.

| Location | Protects | Failure visible to | Invocation | Removal boundary |
| --- | --- | --- | --- | --- |
| `crates/harness-cli/` tests | CLI domain rules, SQLite persistence, replay, protocol operations, and legacy lifecycle behavior | Explicit `harness-cli` and protocol-v1 consumers | `cargo test --workspace --locked` | Versioned protocol/CLI retirement with consumer migration |
| `tests/bootstrap/` | Fresh and existing checkouts can reconstruct the ignored local database from tracked state | Source maintainers and explicit CLI users | Directly from `scripts/validate-premerge.sh` | Removal of tracked SQLite reconstruction |
| `tests/changesets/` | Source mutations produce deterministic semantic changesets | Protocol and rebuild consumers | Directly from `scripts/validate-premerge.sh` | Removal of semantic changesets from the compatibility contract |
| `tests/ci/` | CI rejects core-state drift that cannot be rebuilt | Compatibility maintainers | Directly from `scripts/validate-premerge.sh` | Removal of tracked core state |
| `tests/coherence/` | Schema versions, release pins, changesets, and reconstructed database state agree | Compatibility release maintainers | Directly from `scripts/validate-premerge.sh` | Removal of the SQLite release train |
| `tests/core/` | Historical "core state" command, durable-state, and schema-replay contracts of `harness-cli` | Protocol-v1 consumers | Schema-replay contract is direct; assertion helpers are called by boundary tests | Rename or remove when protocol-v1 no longer uses this terminology |
| `tests/boundary/test-phase4-control-plane-freeze.sh` | Accidental source-default lifecycle writes are rejected while explicit and machine compatibility writes still work | Source maintainers and protocol consumers | Directly from `scripts/validate-premerge.sh` | Completion of the compatibility-write migration |
| `tests/installer/` compatibility cases | Optional CLI payload, upgrade, checksum, rollback, and Windows parity | Explicit CLI-profile installers | Linux direct plus Windows workflow | Retirement of the optional CLI installer profile |
| `tests/protocol/` | Current and frozen native binaries retain the protocol-v1 JSON contract | Symphony and other protocol-v1 consumers | Native smoke direct; frozen-artifact scripts through release/upgrade tests | Versioned protocol-v1 retirement |
| `tests/snapshot/` | Tracked database snapshots compact without losing replay equivalence | Compatibility maintainers | Directly from `scripts/validate-premerge.sh` | Removal of tracked snapshots |
| `tests/worktrees/` | Conflicting tracked state from multiple worktrees has a documented recovery path | Compatibility maintainers using Git worktrees | Directly from `scripts/validate-premerge.sh` | Removal of tracked state from ordinary branches |
| `tests/maintenance/test-harness-cli-release-classification.sh` | Compatibility-affecting changes trigger a CLI release | CLI release maintainers | Directly from `scripts/validate-premerge.sh` | Retirement of CLI publication |
| `tests/release/test-harness-cli-candidate.sh` and legacy release guards | Candidate CLI artifacts preserve frozen upgrade and release contracts | CLI release maintainers and consumers | Reusable release workflows and upgrade tests | Retirement of CLI publication and its upgrade window |

## Historical Migration Proof

One-time E11 repository-separation and cutover executables were removed after
their caller audit found no current pre-merge, release-workflow, installed
payload, or protocol requirement. Their completed plans, frozen evidence, and
Git history retain the historical result without making the old verifiers look
like current product tests.

Removed groups include `tests/cutover/`, `tests/history/`, E11-specific boundary
allowlists, and `scripts/e11-*` / `scripts/verify-e11-*`. Reintroducing one
requires a current observable invariant and a normal validation entry point;
historical provenance alone is insufficient.

## Shared Support

- `tests/fixtures/` contains inputs consumed by compatibility rebuild tests; it
  is not an independently executable suite.
- `tests/*/assert-*.sh` scripts are helpers. A zero direct-reference count does
  not prove they are unused because wrappers may resolve them relative to their
  own directory.
- `tests/release/download-v0.1.14-artifact.sh` downloads the frozen initial CLI
  artifact used to prove upgrade compatibility.

When adding a test, place it under the product boundary it protects and update
this map. Avoid phase-number names for new tests; name the observable invariant
instead.
