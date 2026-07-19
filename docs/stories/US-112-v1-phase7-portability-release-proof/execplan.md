# US-112 V1 Phase 7 Portability And Release Proof Exec Plan

Status: **In progress: fixture contract and build-receipt infrastructure
implemented; remote execution, acceptance, and promotion pending**

## Goal

Implement the deterministic portability and pre-promotion proof stack while
keeping tags, publishing, production signing, Phase 7 acceptance, and Phase 8
closed.

## Scope

In scope:

- Decision 0016 and the Phase 7 story packet.
- Exact fixture and platform matrices.
- Five-platform build/authentication/identity proof.
- Bash, PowerShell, and direct-binary parity.
- Promotion refusal when deferred Phase 6 or Phase 7 evidence is incomplete.

Out of scope:

- Live P0-P7 execution and owner signatures.
- Release tags, publishing, promotion, or production keys.
- V0 removal or compatibility-window changes.

## Risk Classification

Risk flags:

- Public contracts.
- Cross-platform behavior.
- Existing release and installer behavior.
- Weak proof until the complete platform matrix executes.
- Multi-domain release, bridge, core, installer, and workflow boundaries.

Hard gates:

- Validation requirements may not be weakened.
- No target mutation before artifact authentication and platform support
  checks.
- No promotion until deferred Phase 6 and complete Phase 7 proof both pass.

## Planning Mode

This high-risk story and its resume capsule own the cross-platform release
work. Ordinary repository tasks do not require this plan.

## Work Phases

1. Freeze the Phase 6 framework revision and Decision 0016 boundary.
2. Inventory existing fixtures, workflows, artifact names, and platform gaps.
3. Define closed Phase 7 evidence schemas and exact candidate identity.
4. Implement the fixture matrix and local platform-independent negatives.
5. Implement five-platform build, installer, and direct-binary proof.
6. Verify identity/equivalence and promotion refusal; obtain independent
   review before any separate release action.

The first bounded slice implements steps 3-4 only as a non-production fixture
contract. It adds exact candidate identity, ten byte-bound repository-shape
fixtures, five pending artifact/checksum placeholders, and fail-closed
promotion negatives. It does not execute or satisfy step 5, and it does not
assert any Phase 7 proof flag.

The next bounded slice implements only the build/checksum/help-grammar portion
of step 5. A closed build receipt binds the exact source commit and tree,
`Cargo.lock`, command-implementation binding, workflow revision and bytes,
native platform tuple, artifact, checksum, and raw help output. The capture
refuses a dirty tree, mutable/non-HEAD candidate, cross-target tuple, unsafe or
preexisting output, and non-exact six-command help. The collector reads either
one receipt or exactly five downloaded workflow directories and never executes
the artifacts.

Cause and effect: a successful native `cargo build` changes only
`results.build` to the schema-fixed `passed`, and exact `--help` bytes change
only `results.help_grammar_only` to `passed`. Because the slice does not run an
installer or the behavioral command matrix and supplies no authenticated
attestation, installer and full direct-binary proof remain `pending`,
provenance remains `checksum-only-unattested`, and platform acceptance and all
release authorities remain blocked.

## Resume Capsule

- Objective: implement Phase 7 portability and release proof without promotion.
- Completed: Decision 0016 accepted; intake #9 recorded; US-112 packet opened;
  fixture-only schema/inventory/verifier; separate closed build-receipt schema;
  native capture wrapper; read-only single/five collector; exact five-runner
  workflow wiring; focused adversaries; and static workflow authority checks.
- Current evidence: local focused tests pass. The workflow has not been
  dispatched, no remote receipt has been downloaded, and no platform is
  accepted. A post-commit local macOS arm64 capture is diagnostic only.
- Remaining: remote five-runner execution, authenticated provenance, full
  direct-binary and installer execution, cross-platform equivalence, deferred
  Phase 6 live evidence, review, acceptance, and any separately authorized
  release action.
- Exact next action: `review this receipt-infrastructure commit, then separately authorize an immutable candidate workflow run if five-runner diagnostic capture is desired`
- Validation ladder: documentation and JSON checks; focused fixture/proof
  tests; installer/direct-binary tests; five-platform workflow; full premerge;
  stop at the first failed boundary.
- Decisions and assumptions: framework acceptance opens engineering only;
  deferred live experiments remain mandatory before acceptance/promotion.
- Blockers and owners: external pilot custody/signatures remain with repository
  owners; production release authority remains with release maintainers.
- Working state: this continuation started from
  `5fdec632f940523ed17bbbc54f1c05e40115a1f8`; neither the fixture proof nor a
  build receipt authorizes a tag, release, publish, signing, attestation,
  promotion, platform acceptance, or live-pilot mutation.

## Stop Conditions

Pause for human confirmation if:

- a supported-platform claim would require unavailable execution evidence;
- a production key, tag, publish, or remote mutation becomes necessary;
- a fixture would weaken an earlier security/recovery contract;
- the deferred Phase 6 obligation would need removal rather than deferral.
