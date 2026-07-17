# US-105 Repository Harness V1 Implementation Exec Plan

Status: **Implementation in progress / Phases 1-2 accepted / Phase 3 implemented and locally validated, acceptance pending**

## Goal

Deliver the accepted Repository Harness V1 refactor through all eight phases
without collapsing the permanent V1 seed-kit boundary into V0 operational
behavior, losing target/V0 state, weakening release proof, or removing V0
before its approved obligations end.

Decision 0012 supplies the exact compatibility-window, retention, support, and
retirement policy. Gate G0 is approved/open. Decision 0013 and US-106 implement
and prove Phase 1; US-107 implements and proves Phase 2; US-108 implements and
locally validates Phase 3. Phase 3 acceptance is pending. Phases 4-8 remain not
started and depend on accepted evidence from their
predecessors.

## Scope

In scope for the implementation initiative, in dependency order:

- Phase 1 contracts and authenticated release inventory.
- Phase 2 permanent pure V1 core and its six-command grammar.
- Phase 3 safe V1 install/update transitions and recovery.
- Phase 4 separately versioned, immutable-input V0 bridge.
- Phase 5 dogfood, pilot enrollment, and fixed baselines.
- Phase 6 capability evaluation with cards P0-P7.
- Phase 7 portability, cross-platform artifacts, and release proof.
- Phase 8 V0 removal from the default product after actual window closure.
- Unit, integration, recovery, platform, release, and pilot evidence attached
  to the phase that creates the behavior.

In scope for the current authorization-documentation change only:

- `docs/decisions/0012-v0-compatibility-window-and-retention.md`
- `docs/REFACTOR_PLAN.md`
- `docs/stories/US-105-harness-v1-implementation/overview.md`
- `docs/stories/US-105-harness-v1-implementation/design.md`
- `docs/stories/US-105-harness-v1-implementation/execplan.md`
- `docs/stories/US-105-harness-v1-implementation/validation.md`

Out of scope for the current packet-writing change:

- Every product, test, script, workflow, Cargo, lockfile, release, database,
  `.harness`, unrelated plan/decision/story, and Herdr mutation outside those
  files.
- Harness CLI/database/changeset operations, pushing, publishing, tagging,
  releasing, opening a PR, or executing pilots.

Out of scope for V1 core:

- V0 database/changeset semantics and a permanent `migrate` command.
- Mandatory Harness calls during ordinary target work.
- Task/run/prompt/result/trace/telemetry state, a daemon, or scheduler.
- Semantic prose scoring, target-tool execution by audit, target stack
  selection, and language-specific installation branches.
- Automatic downgrade to V0 or conversion of unknown/foreign metadata.

## Risk Classification

Risk flags:

- **Data model and loss:** V0 SQLite/changesets, V1 manifest transitions,
  conversion archive, rollback, and final V0 removal.
- **Audit/security:** authenticated payload identity, digest enforcement,
  no-target-execution, safe paths, and unknown ownership.
- **Public contracts:** three binary identities, six V1 commands, seven bridge
  commands, exit behavior, manifests, release assets, and support window.
- **Cross-platform:** Bash, PowerShell, five binary labels, line endings,
  Unicode/spaces, and atomic filesystem behavior.
- **Existing behavior:** V0 is implemented and distributed today.
- **Weak proof:** Phase 1 contract fixtures and acceptance evidence now exist;
  Phase 2 core runtime evidence exists; atomic mutation/recovery, promoted
  release artifacts, pilots, and Phase 4-8 evidence do not; US-108 contains
  the Phase 3 candidate evidence.
- **Multi-domain:** CLI, filesystem, installers, release integrity, migration,
  recovery, docs/templates, evaluation, and retirement.

Hard gates:

- **G0 — compatibility authorization:** a human-approved exact window start
  date, exact window end date, and archive-retention policy must be durable
  before implementation begins. Current state: approved/open by Decision 0012.
  The window is `2027-01-01T00:00:00Z` through
  `2027-12-31T23:59:59Z`, inclusive; local archives are retained indefinitely;
  and bridge release assets are retained through
  `2028-06-30T23:59:59Z`, inclusive.
- **G8 — retirement eligibility:** Phase 8 requires Phase 7 acceptance, proof
  that the approved end date has actually passed, and proof that every approved
  support, recovery, security, archive-integrity, and asset-retention condition
  is satisfied. It is eligible no earlier than `2028-01-01T00:00:00Z` and
  requires separate removal authorization and validation. Engineering
  readiness or a forecast is not elapsed-time proof.
- Any change to a locked product decision requires a new explicit human
  decision before affected work resumes.

## Work Phases

The dependency chain is intentionally linear:

```text
G0 approved/open by Decision 0012
  -> Phase 1 accepted by Decision 0013 and US-106
  -> Phase 2 accepted by US-107 at exact candidate 1b1add5
  -> Phase 3 implemented and locally validated by US-108, acceptance pending
  -> Phase 4
  -> Phase 5
  -> Phase 6
  -> Phase 7
  -> wait for actual window closure + support/retention proof (G8)
  -> Phase 8
```

No phase may borrow acceptance from a later phase. For example, a successful
pilot cannot excuse an unauthenticated payload, and a passing platform build
cannot excuse a bridge rollback that overwrites a target edit.

Current phase state: Phases 1 and 2 are implemented and accepted. Independent
security and behavior review accepted exact Phase 2 candidate `1b1add5`, which
was integrated as `e77e028` with the identical Git tree. Phase 3 is implemented
and locally validated by US-108, with acceptance pending. Phases 4-8 remain not
started and dependent on the preceding
phase's accepted evidence plus their own gates.

Anticipated paths below identify review surfaces, not permission to modify
them in this planning change. New filenames remain subject to the Phase 1
contract inventory, but binary identities and boundaries are already locked.

### Phase 1: Contracts And Release Inventory

**Dependency:** Satisfied by accepted Decision 0012. **Status: implemented and
accepted by Decision 0013 and US-106.** The phase consumes the approved dates
and retention policy; it does not choose defaults for them.

**Implementation:**

1. Freeze role/asset, repository-mode, command/exit, manifest, payload-index,
   machine-readable output, and compatibility contracts.
2. Freeze the first bridge artifact identity, supported V0 schema 1..=13 and
   exact documented changeset grammar range, Decision 0012 compatibility and
   support statement, complete retained-asset set, and availability checks.
3. Inventory every current source/install/release path and every V0 data
   category into one disposition ledger.
4. Build immutable V0 fixtures from supported schemas/grammars without
   altering their source state.
5. Freeze new V0 operational feature development.

**Anticipated files/subsystems:** `docs/contracts/`, V1/bridge schema and fixture
definitions under `tests/fixtures/`, current payload input
`scripts/harness-install-files.txt`, release/build metadata, `tests/core/`,
`tests/installer/`, `tests/release/`, and `.github/workflows/`. Historical
decision documents remain history rather than being rewritten.

**Acceptance evidence:** schema validation fixtures; grammar/exit snapshots;
one-to-one path disposition report; V0 category/range inventory; payload-index
authentication verification; negative CI fixtures proving unindexed and
forbidden V0 paths cannot enter core; durable reference to the approved G0
decision values; strict small-order/zero-scalar rejection; descriptor-anchored
capture drift proof; and exact bootstrap, release, and monthly complete-set
receipt validation. Result: passed by
`scripts/verify-v1-phase1-contracts.sh` (nine proof groups) and the full
`scripts/validate-premerge.sh`; see US-106 validation evidence.

**Logical commit boundary:** contracts, fixtures, inventory, and failing/pass
contract enforcement land together; no Phase 2 V1 application behavior or
Phase 4 conversion writes enter this boundary.

### Phase 2: Pure V1 Core

**Dependency:** Phase 1 contracts and inventory are reviewed and passing.
**Status: implemented, fully validated, and accepted by US-107.**

**Implementation:**

1. Create the distinct repository-local V1 binary identity.
2. Implement only `install`, `update`, `audit`, `scaffold`, `status`, and
   `version` through domain/application, filesystem/release/trust/manifest
   infrastructure, and CLI interface ports.
3. Enforce manifest forbidden fields, safe paths, deterministic structural
   audit, read/write command boundaries, and absence of V0 database access.
4. Make `version` and `--version` equivalent and reject every unrecognized
   top-level command, including `migrate`.

**Anticipated files/subsystems:** workspace metadata (`Cargo.toml` and eventual
lockfile changes), a distinct V1 Rust binary/crate surface under `crates/`,
repository-local `scripts/bin/harness[.exe]` packaging, manifest/release/
filesystem ports, `tests/core/`, and command snapshot/contract fixtures. The
existing `crates/harness-cli/` remains the V0 identity during the window.

**Acceptance evidence:** six-command help/grammar snapshot; unit tests for role
and readiness transitions; manifest schema negative tests; integration tests
showing audit/status/version are read-only; process-spawn denial proof for
audit; dependency/build inspection proving no SQLite/V0 reader in core; fresh
inspection proof that no database or changesets appear. Result: passed by 46
Phase 2 Rust tests, `scripts/verify-v1-phase2-core.sh` (eleven proof groups),
the evolved nine-group Phase 1 verifier, workspace check/test/clippy, and full
premerge; see US-107 validation evidence.

**Logical commit boundary:** the pure six-command V1 core and its mechanical
boundary tests form one reviewable stack after Phase 1; installer recovery,
bridge reader, pilot evidence, and release promotion stay out.

### Phase 3: Install/Update Recovery

**Dependency:** Phase 2 core command and mutation boundaries pass.

**Status:** implemented and locally validated by US-108; orchestrator
acceptance pending.

**Implementation:**

1. Implement fresh selection, V0-path adoption without conversion, and explicit
   brownfield role mapping where repository mode permits it.
2. Add exact previews, backups, atomic manifest writes, idempotency, supported
   manifest transitions, and safe rerun/recovery.
3. Enforce `replace-if-base`, `three-way-review`, and `never-auto-patch` at the
   managed surface boundary.
4. Reject target edits, unsafe paths, unsupported downgrade, and mixed-invalid
   state without claiming success.

**Anticipated files/subsystems:** V1 application/filesystem/manifest code under
`crates/`, Bash and PowerShell V1 installer/update surfaces in `scripts/`,
authenticated payload material, `tests/installer/`, `tests/fixtures/`, and
recovery/idempotency integration tests.

**Acceptance evidence:** fresh and brownfield fixtures; managed-file,
managed-block, and target-owned matrices; repeated-install/update idempotency;
crash-before-commit fixtures; three-way conflicts; unsupported downgrade;
target-edit preservation; unresolved versus invalid exit proofs; no false
success manifest after any failure.

**Logical commit boundary:** install/update mutation and recovery behavior plus
its fixtures land after the pure core boundary; no V0 reader or bridge command
is linked into the V1 artifact.

**Current evidence:** 43 focused Phase 3 Rust tests (eighteen recovery unit and
twenty-five signed integration), every one of 18 install, 15 update, and 13
committed-update rollback checkpoints, 89 total `harness-core` tests, 181
workspace Rust tests, and 11/11 Phase 3 mechanical proof groups. Phase 1/2 gates
remain unchanged; Phase 4 and Phase 7 remain closed pending acceptance.

### Phase 4: Isolated V0 Bridge

**Dependency:** Phase 3 provides a stable V1 manifest commit/recovery target;
Phase 1 has frozen the bridge compatibility and archive contracts.

**Implementation:**

1. Build a separate bridge binary and release index with an immutable,
   read-only V0 reader.
2. Implement `inspect`, `export`, `preview`, `apply`, `resume`, `rollback`, and
   `version` around the export/archive/journal state machine.
3. Add conservative V0 detection, unknown/unowned preservation,
   mixed-version detection, atomic receipt commit, and conflict-safe recovery.
4. Execute the complete parameterized kill-point suite.

**Anticipated files/subsystems:** a separate bridge/reader crate or binary under
`crates/`, bridge-only release/build metadata and repository-local binary path,
immutable copies of supported V0 fixtures under `tests/fixtures/`, conversion
and cutover tests under `tests/cutover/`, and bridge artifact checks in
`tests/release/` and `.github/workflows/`. The reader may understand V0; the V1
core crate and payload may not depend on it.

**Acceptance evidence:** schema 1..=13 and exact-grammar fixture results;
database/changeset before-and-after hashes proving immutability; export and
archive digest verification; unknown metadata preservation; every kill point;
idempotent apply/resume; target-edit rollback conflict; mixed-invalid
detection; core artifact scan proving bridge/V0 reader absence.

**Logical commit boundary:** bridge reader, commands, recovery, fixtures, and
separate packaging form an isolated review stack. The last commit in that stack
must demonstrate no bridge object/path entered the V1 core index.

### Phase 5: Dogfood, Pilot Enrollment, And Baselines

**Dependency:** Phases 1-4 pass deterministic acceptance. Pilot owners have
separately authorized repository access and evaluation; Decision 0012 remains
the controlling compatibility policy.

**Implementation:**

1. Dogfood V1 against Repository Harness's current useful paths without a
   cosmetic move or mandatory ordinary-task command.
2. Enroll at least two unrelated target repositories with immutable starting
   revisions, eligibility findings, owners, evidence custody, and environment
   locks.
3. Freeze signed cards P0-P7 and run applicable baseline cards before candidate
   capability evaluation.
4. Record written evaluator findings for any inapplicable card; do not silently
   omit it.

**Anticipated files/subsystems:** Repository Harness role mappings/templates,
`tests/evals/`, external pilot repositories only under separate owner
authorization, and future evidence beneath
`docs/stories/US-105-harness-v1-implementation/evidence/phase-5/`. Pilot
revisions and raw evidence must not be fabricated in this packet.

**Acceptance evidence:** no-path-move diff; ordinary-task transcript with zero
Harness commands; two or more eligibility records; immutable revision and
environment records; signed card hashes; baseline results or explicit
inapplicability findings; complete baseline intervention/time accounting.

**Logical commit boundary:** repository-owned dogfood mappings and evaluation
protocol/evidence references are reviewable separately from candidate outcomes.
External pilot changes, if any, remain in their repositories and are never
silently folded into this repository's commit.

### Phase 6: Capability Evaluation

**Dependency:** Phase 5 enrollment, cards, environment locks, and baseline
evidence are complete. A missing baseline cannot be reconstructed after seeing
candidate results.

**Implementation:**

1. Instantiate selected planning, invariant, feedback,
   capability-inheritance, and gardening contracts in each authorized pilot.
2. Run the same fixed cards with candidate identities while holding model,
   reasoning, tools, permissions, evaluator, and comparable revision constant.
3. Record every intervention and total human attention.
4. Fail the candidate on any protocol negative condition; do not explain away
   a failed acceptance test.

**Anticipated files/subsystems:** target-native docs/checks/feedback in
authorized pilots, `tests/evals/`, evaluation tooling that does not enter the
V1 installed payload, and future evidence beneath
`docs/stories/US-105-harness-v1-implementation/evidence/phase-6/`.

**Acceptance evidence:** card-by-card candidate results P0-P7; acceptance-test
outputs; baseline/candidate identity comparison; intervention logs with actor,
timestamp, reason, minutes, and outcome effect; negative-condition report;
held-out discovery proof for P6; two-run bounded convergence proof for P7.

**Logical commit boundary:** candidate capability/evaluation evidence is
separate from baseline enrollment and from Phase 7 release mechanics. Any
candidate product correction triggered by a failed card returns to its owning
earlier phase and reruns dependent evidence rather than being hidden in an
evidence-only commit.

### Phase 7: Portability And Release Proof

**Dependency:** Phase 6 cards pass with valid comparable evidence, and all
earlier deterministic product proofs remain green for the exact candidate.

**Implementation:**

1. Exercise fresh, brownfield, nested-instruction, docs-only, monorepo-shaped,
   spaces/Unicode, line-ending, custom-update, and bridge fixtures.
2. Build and authenticate exact candidate artifacts for macOS arm64/x64, Linux
   x64/arm64, and Windows x64.
3. Prove Bash, PowerShell, and direct-binary behavior is equivalent at the
   manifest/audit boundary and no language manifest is interpreted.
4. Bind candidate CLI, template, payload-index, and bridge identities to the
   already-run pilot evidence before promotion.

**Anticipated files/subsystems:** `scripts/build-*` and installer surfaces,
release identity/checksum/authentication metadata, `.github/workflows/`,
`tests/installer/`, `tests/protocol/`, `tests/release/`, portability fixtures,
and future evidence beneath
`docs/stories/US-105-harness-v1-implementation/evidence/phase-7/`.

**Acceptance evidence:** five-platform artifact matrix; installer/direct-binary
smokes; authenticated index/digest proof; platform-equivalent manifest and exit
outcomes; fixture matrix; candidate identity lock; complete pilot comparison;
all release criteria and negative conditions checked before any tag promotion.

**Logical commit boundary:** release packaging/workflows and exact-candidate
proof form the final pre-promotion stack. Promotion/tag/publish is a later
explicit release action, never an automatic side effect of merging an
implementation commit.

### Phase 8: V0 Removal After The Window

**Dependency:** Phase 7 accepted; the approved window end has actually passed;
the time is no earlier than `2028-01-01T00:00:00Z`; and G8 has evidence for
every approved support, recovery, security, archive-integrity, and
asset-retention condition plus separate removal authorization and validation.
This phase may not run on a planned date or an exception invented by the
implementer.

**Implementation:**

1. Re-inventory the default payload and source ownership immediately before
   removal.
2. Remove V0 operational CLI/code, SQLite/schema/changeset payload, lifecycle
   docs, installer branches, and default release paths identified by the
   approved disposition ledger.
3. End bridge distribution/support only as Decision 0012 permits. Retain every
   supported-platform binary, checksum, authenticated index or attestation,
   supported-input matrix, release notes, source tag, and reproducible build
   instructions through `2028-06-30T23:59:59Z`, inclusive, with periodic
   availability verification.
4. Leave every local conversion archive at its existing path and bytes. It is
   retained indefinitely; Phase 8 may not automatically delete, overwrite,
   truncate, or relocate it.
5. Preserve accepted decisions and necessary historical evidence; removal of
   default behavior does not rewrite history.
6. Re-run fresh V1, upgrade/recovery, six-command grammar, payload-negative,
   and platform proof.

**Anticipated files/subsystems:** V0 `crates/harness-cli/`, `scripts/schema/`,
V0 installer/bootstrap/release paths, V0 payload entries and tests, Cargo
workspace metadata, documentation that claims current V0 operation, workflows,
and historical/bridge assets classified by the approved retention ledger.
Exact deletions come from the Phase 1 ledger plus a Phase 8 re-inventory.

**Acceptance evidence:** timestamped G8 approval/evidence; closure of every
known in-window recovery case and supported-range security, data-loss, and
archive-integrity defect; post-removal disposition report; fresh V1 install
with no SQLite/database/changesets/V0 binary; top-level grammar exactly the six
commands; local-archive non-mutation proof; bridge-retention/availability proof;
five-platform core artifacts; repository search and authenticated-index
negatives for forbidden V0 payload.

**Logical commit boundary:** V0 default-product removal and coupled regression
updates form a dedicated, reversible review stack after G8. It cannot be mixed
with Phase 7 candidate promotion or used to retroactively shorten the window.

## Stop Conditions

Pause and preserve the current state if:

- Implementation cannot encode Decision 0012's exact dates, retention scope,
  support scope, or Phase 8 preconditions without weakening or inventing a
  value.
- A proposed phase starts before its predecessor acceptance evidence is
  reviewed.
- A change would add a permanent V1 command, alias V0/V1 identities, put the V0
  reader in core, or make ordinary work call Harness.
- Manifest or payload design introduces operational database/task/telemetry
  state, or audit would execute a target process.
- A path's ownership is ambiguous, a digest differs, an input version is
  unsupported, or unknown metadata would be claimed, moved, or deleted.
- Resume/rollback cannot prove an operation is journal-owned and its current
  digest matches the expected safe image.
- A failed operation would leave a success manifest/receipt or require
  weakening a kill-point, target-edit, or immutability test.
- A supported platform cannot produce the authenticated exact-candidate
  artifact or equivalent contract result.
- A pilot lacks owner authorization, immutable revision, environment lock,
  comparable baseline, complete intervention log, or applicable acceptance
  proof.
- A pilot negative condition occurs; return to the owning phase and rerun
  invalidated downstream proof.
- Product behavior, data ownership, archive custody, compatibility support, or
  release criteria become ambiguous or depart from Decisions 0011 and 0012 or
  the accepted plan.
- Phase 8 is requested before `2028-01-01T00:00:00Z`, before actual window
  closure, while any approved support/recovery/security/retention condition is
  unmet, or without separate removal authorization and validation.
- Scope expansion would modify consumer repositories, publish artifacts, or
  remove historical evidence without separate explicit authorization.
