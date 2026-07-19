# Test Matrix

This file preserves the proof vocabulary and brownfield import shape used by
Harness consumers. The authoritative operational matrix is stored in SQLite
and queried with:

```bash
scripts/bin/harness-cli query matrix --active --summary
```

The upstream Harness repository has implemented behavior and executable proof.
An installed consumer starts without consumer-product rows and adds them only
when real work is accepted. Do not mark a row implemented until tests or other
validation evidence exist.

## Status Values

| Status | Meaning |
| --- | --- |
| planned | Accepted as intended behavior, not implemented |
| in_progress | Actively being built |
| implemented | Implemented and proof exists |
| changed | Contract changed after earlier implementation |
| retired | No longer part of the product contract |

## Matrix

No static product rows are shipped in this legacy view. Use `story add` and
`story update` for operational records. Brownfield repositories may add rows
here before importing their existing state.

## Evidence Rules

- Unit proof covers pure domain and application rules.
- Integration proof covers backend enforcement, data integrity, provider
  behavior, jobs, or service contracts.
- E2E proof covers user-visible browser flows.
- Platform proof covers only shell, deployment, mobile, desktop, or runtime
  behavior that cannot be proven in lower layers.
- A story can be implemented without every proof column if the story packet
  explains why.

## V1 Phase Gates

The separate V1 core does not use the legacy SQLite matrix above. Its accepted
Phase 1-5 gates are mechanical or authenticated evidence gates:

```bash
scripts/verify-v1-phase1-contracts.sh
scripts/verify-v1-phase2-core.sh
scripts/verify-v1-phase3-recovery.sh
scripts/verify-v1-phase4-bridge.sh
scripts/verify-v1-phase5-evidence.sh --dogfood-only
```

US-108 records 43 focused Phase 3 test functions, all 18 install, 15 update,
and 13 committed-update rollback checkpoints, 89 total `harness-core` tests,
181 workspace Rust tests, and 11 Phase 3 proof groups. The accepted Phase 3
evidence also proves retained hard-link witnesses for every
`before_sha256=None` create that recovery may later classify or remove, pinned
repository-root `st_dev`/`st_ino` journal binding that rejects copied cross-root recovery
evidence, canonical preview digests that match the emitted
`details.operations` array, read-only probe validation of staged/backup
evidence before `prepared` or `applying` recovery is surfaced, and monotonic
recovery validation that refuses payload downgrade or equal-sequence digest
drift before mutation. `rolling-back` remains explicit-only and is not a probe
status. Independent security (`gpt-5.4`, high reasoning) and behavior
(`gpt-5.6-sol`, medium reasoning) reviewers accepted exact candidate `1f957ce`,
integrated as `8e67593` with identical Git tree `9cd22cdb24d2`. Those Phase 3
results alone do not establish the later Phase 4, Phase 5, or Phase 7 gates.

US-109 supplies a separate accepted `harness-v0-migrate` implementation with 13 focused
tests and 10 Phase 4 proof groups. The evidence covers every schema 1..=13,
WAL-only recovery, unknown metadata, active-writer refusal, encrypted and
explicit-risk plaintext archives, unique staging and atomic no-replace
publication, abandoned/foreign custody preservation, exact live/archive export,
Phase 3 receipt recovery, pinned custody-directory swap rejection across
preview/recovery/audit, immutable fixture digests, and the structural core
boundary. The bridge never mutates V1 and has exactly four commands. An
independent reviewer accepted exact candidate `880cb9b`, fast-forwarded with
identical Git tree `0f81d3f0f4c8`. Phase 5 was then evaluated separately.
Five-platform promotion and Windows safe capture/atomic publication remain
Phase 7 evidence; Phase 4 proves only coherent compilation/help and controlled
unsupported exit 5 on Windows.

US-110 supplies accepted authenticated Phase 5 baseline evidence: an in-place
map pinned to accepted Phase 4, fixed P0-P7 schemas, exact ordinary-task argv,
offline SSH Ed25519 verification against caller-pinned out-of-repository owner
material, distinct repository-scoped owner IDs/repositories/bundle identities,
conditional same-stable-owner key sharing, enabled versioned acceptance tools,
bundle-resolved commits, complete packet custody/digests, strict UTC ordering,
and adversarial oracle verification:

```bash
scripts/verify-v1-phase5-evidence.sh --dogfood-only  # partial gate only
scripts/verify-v1-phase5-evidence.sh --require-pilot-baselines \
  --trusted-owner-registry /absolute/external/trusted-owners.json \
  --trusted-owner-registry-sha256 f55a117eb20df727ee21cb922345d62bce3f3afc4458ba5a8b057dc430c9bb6d
```

On exact `b2dd775`, the full caller-pinned live invocation passed six proof groups
and rejected 42/42 adversarial cases. The corrected current gate rejects four
additional GitHub path/hostname alias attacks plus duplicate-key and atomic
pathname-substitution trust-registry attacks, for 48/48. It authenticated two complete packets for
distinct canonical repositories, repository-scoped owner IDs, bundles, and
external Ed25519 keys under one stable GitHub identity. Both signatures and
bundle revisions verified. The external registry remains outside the candidate
repository at SHA-256
`f55a117eb20df727ee21cb922345d62bce3f3afc4458ba5a8b057dc430c9bb6d`;
the tracked trusted-owner registry remains empty.

Benchmark P1 is inapplicable and benchmark P6 failed; e-inna P0/P1/P3/P6
failed. These are baseline measurements rather than candidate improvement
tests, so they do not block Phase 5. Decision 0016 accepts the implemented
Phase 6 framework for sequencing and opens Phase 7 engineering; live candidate
P0-P7 evidence remains deferred and mandatory before Phase 7 acceptance or
promotion. Primary fast-forward integration and trust-enabled full
premerge passed on exact `b2dd775`; acceptance documentation was integrated at
`3a65768`.

US-111 framework validation covers only documentation/JSON structure, portable
template neutrality, cold-versus-warm custody authority, changeset replay, and
Phase 5/US-110 byte preservation. It must never be reported as a candidate
card, comparison, or pilot improvement. Decision 0016 records the separate
owner framework acceptance and Phase 7 engineering opening; it does not supply
Phase 7 acceptance, promotion, or Phase 8 progress.

US-112's first bounded Phase 7 slice adds a Draft 2020-12 closed candidate and
fixture evidence contract plus byte-bound fresh, brownfield, nested-instruction,
docs-only, monorepo, spaces/Unicode, LF, CRLF, custom-update, and bridge cases.
The focused gate rejects duplicate JSON keys, incomplete or colliding platform
inventories, digest/candidate drift, and unsafe acceptance/release claims:

```bash
scripts/verify-v1-phase7-release-proof.sh
tests/release/test-v1-phase7-release-proof.sh
scripts/verify-v1-phase7-release-proof.sh --require-promotable  # expected exit 2
```

This is fixture-only evidence: all five platform results and authentication
states are pending, no real platform has passed, deferred Phase 6 live evidence
is pending, every US-112 proof flag remains unasserted, Phase 7 acceptance/tag/
publish/signing/promotion remain blocked, and Phase 8 remains closed.

US-112's next bounded slice adds separate non-production build receipts without
changing that fixture-only schema. A native capture requires a clean exact
HEAD candidate and exact platform/target/runner tuple, builds the release V1
`harness`, and writes its checksum without execution. A read-only build job
sets bytecode suppression before repository-local imports, with a workflow-wide
environment defense, so its clean-status gate cannot be invalidated by
`scripts/__pycache__` created by capture itself. It then uploads those bytes;
an isolated OIDC job uses the exact-pinned v3.2.0 action
plus exact-pinned v8.0.1 download and v7.0.1 upload actions to attest them
without candidate execution, and a separate read-only native
job downloads both inputs. Only successful signed-bundle verification may
capture six-command JSON help and finalize a receipt bound to
the source tree, `Cargo.lock`, command binding, workflow bytes, artifact,
bundle, and verification-record digests. A read-only collector repeats that
verification for one or the exact five downloaded receipt directories:

```bash
tests/release/test-v1-build-receipts.sh
tests/release/test-v1-build-receipt-workflow.sh
tests/release/test-v1-artifact-provenance.sh
tests/release/test-v1-attestation-workflow.sh
tests/release/test-release-workflow-contract.sh
```

The workflow tests require the explicit setup-python `python-path` on every
platform and reject `python3`/shebang fallbacks, OIDC permission outside the
attestation job, candidate execution inside that job, broken artifact handoff,
mutable or substituted privileged-job action refs, and runner variables
reaching candidate subprocesses. The allowlist adversary includes GitHub
command-file channels, Actions runtime/OIDC values, tokens, `PYTHONPATH`, and
`PYTHONHOME`. The provenance
test also exercises the installed `gh` parser so a fake runner cannot hide
mutually exclusive verification flags.

The build-receipt regression runs capture and finalizer in a temporary clean
Git repository with bytecode environment variables unset and repository-local
cache placement forced; it requires no `__pycache__`, no `.pyc`, and unchanged
Git status after both entrypoints.

CI attempt 2, run `29682593310` at candidate
`47d3ae1a341e87cd1d76811aa7f21b4fba707fec`, passed the macOS arm64/x64 and
Linux x64/arm64 build rows. Windows failed during compilation before artifact
upload because platform-neutral journal ownership validation called a
`#[cfg(unix)]` formatter through `OsMutationPort`. The correction keeps the
formatter private but platform-neutral, while all descriptor-backed mutation
methods remain Unix-only. Phase 3's static contract rejects that exact cfg
leak by structurally associating every outer attribute with the pure formatter
and inspecting the actual `cfg(not(unix))` `apply`/`recover` blocks for an
unconditional pre-journal error. Attribute association walks the comment-masked
source while slicing original offsets and starts at the complete function item,
including `pub(...)`, `const`, `async`, `unsafe`, and `extern` qualifiers. Thus
visibility, same-line/separate-line comments, nested blocks, adjacent line
comments, or intervening attributes cannot hide a cfg. Required `apply` and
`recover` method items must also have no `cfg` or `cfg_attr` outer attribute;
the matcher normalizes Rust's optional raw-identifier prefix, so `r#cfg` and
`r#cfg_attr` are equivalent and cannot bypass the check. Each complete method
body must contain exactly the Unix dispatch and non-Unix refusal blocks, with
only comments or whitespace outside them. The non-Unix block is then limited
to inert argument consumption followed by the unconditional pre-journal error.
Seeded self-tests reject ordinary/raw and comment-spaced attributes,
alternative Windows-excluding cfg expressions, conditionally absent methods,
unconditional or Windows-conditional filesystem work outside the refusal, and
non-Unix success returns that retain inert refusal text.
Local `cargo check --locked --package
harness-core --all-targets --target x86_64-pc-windows-msvc` supplies
Windows-target compile coverage. Attestation,
verification/execution, and collection were skipped in the failed run, so no
platform is accepted:
`build=passed`, `provenance=github-sigstore-attested`, and
`help_grammar_only=passed` prove compilation, authenticated diagnostic build
origin, and machine-help identity. Installer/full direct-binary results in the
build receipt, deferred Phase 6 P0-P7 evidence, platform equivalence,
acceptance, production signing, and every release action remain pending or
blocked.

CI attempt 3, run `29685632567` at published candidate
`dd5648daa0db822f29a90fc47fcfbfce43db4a88`, completed GitHub/Sigstore
provenance verification and the six-command execution proof on all five
platforms. Windows job `88189458225` then failed only in the native
controlled-unsupported installer test: Windows PowerShell 5.1 promoted the
installer's expected stderr and exit 1 to a terminating `NativeCommandError`
because the parent test used `ErrorActionPreference=Stop` with `2>&1`.
The corrected test retains `Stop` for its own failures but launches the child
through `System.Diagnostics.Process`, captures stdout and stderr independently,
and asserts exact empty stdout, the exact refusal line plus platform newline,
exit 1, absent destination state, and unchanged artifact/checksum hashes.
The execution-proof verifier pins the complete reviewed CRLF PowerShell test
bytes at SHA-256
`059da9845613392a761a4016576d140c9be6c9957c430bcb6b192048696ad5a6`.
Adversaries reject required strings moved into block/trailing comments, active
redirect=false with a comment-preserved true marker, loose matching with the
exact comparison in a comment, native `*>&1`, and forced exit 1. The failed
Windows assertion and skipped final collection mean no platform is accepted;
Windows publication, five-platform equivalence, Phase 7 acceptance, and
release authority remain pending or blocked.

US-112's local execution slice adds checksum/platform preflight to the real V1
binary, a V1-only Bash installer and PowerShell controlled-unsupported installer
surface, external signed-test-payload
and independent trust adapters, and a closed execution receipt. The focused
test runs install, update, audit, scaffold, status, and version across fresh,
brownfield, nested-instruction, docs-only, monorepo, spaces/Unicode, LF, CRLF,
custom-update, and bridge fixtures. It also seeds inert Cargo and package
manifests and proves they are not interpreted:

```bash
cargo test -p harness-core --test phase7_direct_binary
tests/release/test-v1-phase7-execution-proof.sh
tests/release/test-v1-build-receipt-workflow.sh
```

Cause and effect: matching a checksum alone permits nothing to execute. The
signed bundle must first bind the exact repository/workflow/ref/SHA and
artifact name/digest; only then may platform validation and command parsing
occur. Valid external test trust permits signed payload planning, and exact
preview acceptance permits mutation. Failure at any earlier step produces no
later step or owner-file change. Verified diagnostic provenance sets no
platform proof flag and cannot replace remote five-runner evidence, deferred
Phase 6 P0-P7 evidence, acceptance, production signing, or promotion.

The reviewed corrections add Unix destination-escape adversaries for a linked
target root, `scripts`, and `scripts/bin`; independently resolved candidate and
workflow identity; cross-binding from every execution proof to an independently
verified build receipt's platform/target/runner/artifact-name/artifact-SHA-256/
bundle-SHA-256/verification-record-SHA-256 tuple; and
normalized-payload digest recomputation. PowerShell authenticates and validates
the native Windows artifact, then refuses before destination creation, copy, or
move. Windows receipts must say
`controlled-unsupported-before-mutation`, so their presence completes only an
inventory and leaves five-platform equivalence pending. The diagnostic has no
promotion or release job; when all diagnostics pass it finishes green, while
closed receipt authority fields and this story keep release authority blocked.

Authorized full premerge uses only the paired
`HARNESS_PHASE5_TRUSTED_OWNER_REGISTRY` and
`HARNESS_PHASE5_TRUSTED_OWNER_REGISTRY_SHA256` variables; the focused forwarding
contract runs the copied premerge under `/bin/bash`, requires six ordered case
markers, and rejects partial, unknown, positional, and dogfood-only bypass
inputs. The no-pair path uses a literal zero-argument verifier call, avoiding
empty-array expansion under macOS Bash 3.2 with `set -u`.

GitHub Pre-Merge provisions the original external public owner registry from
the repository variable `PHASE5_TRUSTED_OWNER_REGISTRY_BASE64` before checkout.
It decodes only to a unique `runner.temp` file, verifies the pinned SHA-256
`f55a117eb20df727ee21cb922345d62bce3f3afc4458ba5a8b057dc430c9bb6d`,
then scopes the verified path and that exact digest to the existing paired
premerge variables. Missing variables, changed bytes/digest, tracked or
candidate-derived registries, secret substitution, and inexact forwarding fail
closed. The workflow oracle removes only the exact reviewed provisioning and
premerge environment blocks. It then masks quoted string contents in every
remaining GitHub expression and rejects any `vars`, `secrets`, or `steps`
context identifier, including dot, bracket, computed `format()`, split-key, and
whitespace forms; literal trust markers also remain prohibited outside those
blocks. Nineteen workflow adversaries cover global scopes, Windows steps,
computed access, and post-checkout candidate overwrites. This is CI trust-input
provisioning only: it is not a private key,
production signing input, acceptance record, or release authority. The manual
Harness CLI release workflow remains unchanged.

Mandatory premerge also snapshots `git status --short --untracked-files=all`
before verification and requires the exact same status afterward. The two
Phase 1/2 generated bridge executable names, `scripts/bin/harness-v0-migrate`
and `scripts/bin/harness-v0-migrate.exe`, are ignored explicitly; the source
crate and unrelated `scripts/bin` paths remain visible.
