# US-105 Repository Harness V1 Implementation Validation

Status: **Implementation in progress / Phases 1-5 accepted at the authenticated baseline gate / Phases 6-8 not started**

Phase 6 remains not started: its candidate improvements must be evaluated
against the two authenticated pre-candidate baselines recorded by US-110.

Decision 0014 supersedes this packet's former bridge conversion/journal matrix.
The Phase 4 acceptance oracle is archive-only: exact capture/export,
append-only publication, no bridge V1 mutation, and core Phase 3 receipt
recovery. US-109 is authoritative for the detailed proof.

## Proof Strategy

US-105 is complete only when each phase has evidence for the exact artifact it
hands to the next phase, the fixed release-only pilot protocol has passed, and
Phase 8 has lawfully completed after the approved compatibility obligations.
Evidence is layered so a later success cannot conceal an earlier boundary
failure:

1. Contract proof freezes schemas, grammars, identities, ownership, payload,
   recovery, compatibility, and retirement conditions.
2. Unit proof covers pure role/asset, manifest, path, digest, mode, journal, and
   state-transition rules.
3. Integration proof covers real filesystem operations, authenticated payload
   selection, atomic commits, immutable V0 reads, recovery, and process
   boundaries.
4. Platform proof binds the same contracts to each promoted Bash, PowerShell,
   and direct-binary artifact.
5. Release-only pilot proof tests behavior using fixed P0-P7 cards and fully
   accounts for human attention.
6. Retirement proof shows actual window closure and policy satisfaction before
   V0 leaves the default product.

Cause and effect: if a kill-point test finds a success receipt before the
atomic commit, conversion safety has failed. A later successful `resume`, pilot
run, or Windows artifact cannot repair that proof; Phase 4 returns to work and
all dependent evidence is rerun for the corrected candidate.

Phase 2 core implementation proof and independent review pass; Phase 3 and
Phase 4 implementation, validation, and independent review pass. US-110 adds
accepted authenticated Phase 5 baseline evidence at exact `b2dd775`; no
production-promoted mutation/recovery adapter, five-platform artifact set,
candidate improvement, or Phase 6-8 acceptance exists.
Decision
0012 is authorization evidence: Gate G0 is approved/open, the window is
`2027-01-01T00:00:00Z` through `2027-12-31T23:59:59Z`, inclusive, local
archives are retained indefinitely, bridge release assets are retained through
`2028-06-30T23:59:59Z`, inclusive, and Phase 8 is eligible no earlier than
`2028-01-01T00:00:00Z` after all closure conditions pass. Decision 0013 and
US-106 implement and prove Phase 1; US-107 implements and proves Phase 2;
US-108 implements, validates, and independently accepts Phase 3; US-109 does
the same for Phase 4. US-110 accepts Phase 5 at the authenticated baseline gate;
Phases 6-8 remain not-started dependencies. Primary fast-forward integration and
trust-enabled full premerge passed on exact `b2dd775`; acceptance documentation
was integrated at `3a65768`.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Role activation/ownership/origin/required combinations; update policies; safe paths; manifest forbidden fields; schema/range compatibility; repository-mode transitions; payload disposition; journal state transitions; audit/status exits. |
| Integration | Authenticated-index install; fresh/brownfield/update filesystems; backups and atomic rename; target-owned preservation; bridge read-only database/export and append-only archive; exact receipt recovery; digest conflicts; process-spawn denial. |
| E2E | Repository-local CLI flows for all six core and four bridge commands; dogfood; release-only P0-P7 cards; archive-only V0-to-V1 cutover and post-window V0 removal. No browser E2E is implied. |
| Platform | Bash/direct binary on macOS arm64/x64 and Linux x64/arm64; PowerShell/direct `.exe` on Windows x64; checksums/authentication, paths with spaces/Unicode, line endings, atomic/recovery semantics, and equivalent manifests/exits. |
| Performance | No speed claim is required for acceptance. Record command duration/resource regressions during release proof, but never trade integrity, deterministic results, or recovery for a threshold invented after implementation. |
| Logs/Audit | Deterministic machine/human output contains identity, mode, role/path issue, and next action; no telemetry/task/run/trace state; audit starts no target tool; bridge reports archive/export identities only; pilot interventions are release evidence only. |

### Contract Boundary Proof

| Requirement | Negative case | Required proof | Planned evidence |
| --- | --- | --- | --- |
| Role fields are independent and normative. | Treat `v0-adopted` as permission to rewrite a target-owned file. | Table-driven transition/update-policy tests reject the write and leave bytes unchanged. | Phase 2-3 role/asset unit and filesystem results. |
| Manifest is provenance, not operations. | Add `task`, `run`, `prompt`, `result`, `trace`, telemetry, scheduler, database, or semantic-changeset fields. | Schema rejects each field and audit returns invalid. | Phase 1 schema fixtures and Phase 2 negative tests. |
| Payload index is authoritative. | Add an unindexed file or forbidden `harness.db*`, changeset, schema, V0 binary, or lifecycle path. | Build/release verification fails before artifact promotion. | Phase 1 ledger and Phase 7 exact-artifact report. |
| Audit is structural and read-only. | Manifest asks audit to run a target test or a malicious fixture exposes a process hook. | No process starts; audit reports only structural state. | Phase 2 process-denial integration proof on all release platforms. |
| Archive publishes once. | Crash before no-replace archive rename. | No accepted archive exists; fresh unique retry preserves abandoned/foreign bytes; V0 inputs hash identically. | Phase 4 append-only archive proof. |
| Unknown state is preserved. | `.harness/foreign-tool.json` exists beside recognized V0 state. | Inspect/archive report unknown/unowned and leave its digest unchanged. | Phase 4 unknown-metadata fixture. |
| Phase 8 is time/policy gated. | Engineering is ready but it is before `2028-01-01T00:00:00Z`, a supported recovery/security/data-loss/archive-integrity case remains open, retained assets are unverified, or separate removal authorization/validation is missing. | Retirement change is blocked, V0 default artifacts remain, and local archives are never automatically removed. | Decision 0012, G8 evidence, and the Phase 8 precondition report. |

## Requirement-To-Proof Matrix

### Six V1 Core Commands

| Requirement | Positive cases | Negative / boundary cases | Required acceptance proof | Status |
| --- | --- | --- | --- | --- |
| `install` | Fresh selected roles; V0-path adoption where permitted; explicit brownfield mapping; valid unresolved install. | Unsafe destination; ambiguous ownership; mixed-invalid state; bad payload digest; crash before manifest commit. | Exact preview; byte/digest before-after report; atomic-manifest kill point; no database/changesets; target-owned bytes unchanged; resulting mode/readiness. | **Phase 3 accepted:** signed install, exact confirmation, fresh brownfield mapping, manifest-last commit, all 18 install kill points, deterministic rerun/resume/rollback, and no false success pass. |
| `update` | Replace-if-base; supported manifest transition; explicit three-way review; idempotent rerun. | Edited base; target-owned asset; unsupported downgrade; interrupted write; payload/template/CLI range mismatch. | Policy matrix, conflict output, backups, unchanged target bytes, no false success, rerun equivalence. | **Phase 3 accepted:** managed-file conflict, managed-block interior replacement, target-owned preservation, archive-receipt retention, backups, atomic exchange, status probe, and recovery pass. |
| `audit` | Ready exit 0; unresolved exit 2; deterministic repeated result. | Bad schema/path/digest/marker/link/forbidden field exit 3; malicious target-tool hook; V0-only repository. | Golden machine/human output, filesystem/process monitor showing no writes/spawns, no V0 database open, stable exits. | **Phase 2 accepted:** pinned Unix snapshot tests, deterministic structural exits, unchanged canary tree/sentinel, and no process/DB port. This is not universal event proof; safe non-Unix inspection and portable event evidence remain Phase 7. |
| `scaffold` | Explicit selected neutral template at safe target path; repeated preview. | Stack inference; overwrite existing target content; lifecycle/task record creation; unsafe path. | Payload/template identity, exact preview/diff, collision rejection, manifest/provenance result, no operational fields. | **Phase 3 accepted:** exact authenticated creation, target-owned/never-auto-patch manifest state, and repeated exact idempotent no-op pass. |
| `status` | Fresh-v1 or brownfield-v1, with or without an authenticated archive receipt; valid and unresolved exit 0. | Live V0 without explicit archive receipt, foreign custody, or corrupt manifest exit 3; attempt to repair state. | Mode/identity/readiness golden outputs, read-only filesystem/database/process proof, exact invalid reason. | **Phases 2 and 4 accepted:** structural states remain deterministic/read-only; non-Unix safe handles remain Phase 7. |
| `version` and `--version` | Same V1 version and accepted manifest/template ranges on every platform. | Alias to V0, mismatched output, unrecognized/downgrade range. | Byte-equivalent normalized output, binary identity/digest, grammar snapshot with only six commands. | **Phase 2 accepted:** native alias output and exact six-command grammar match. Five-platform promoted artifacts remain Phase 7. |

### V0 Bridge Commands

| Requirement | Positive cases | Negative / boundary cases | Required acceptance proof | Status |
| --- | --- | --- | --- | --- |
| `inspect` | Recognized V0 schema 1..=13 and published changeset grammar; known provenance; companion layout. | Schema outside range; unreadable DB; arbitrary `.harness`; foreign metadata. | Read-only-open instrumentation, categorized inventory, before/after source hashes, unsupported/preserved output. | **Phase 4 accepted.** |
| `export` | Neutral `repository-harness-v0-export/v1` for every supported category. | Unknown category, corrupt row, grammar outside range, partial output. | Schema validation, stable category/source/payload digests, no V0 task fields in V1 manifest, safe retry. | **Phase 4 accepted.** |
| `archive` | Frozen supported input; encrypted default or explicit plaintext; unique final ID. | Source drift; tamper; foreign custody; abandoned staging; publication collision. | DB/WAL/SHM exact hashes, member/aggregate digests, no-replace retry, no V1 target mutation. | **Phase 4 accepted.** |
| `version` | Bridge version, platform, schema 1..=13, exact changeset grammar range, compatibility statement. | Pretends to be V1 core/V0 CLI; range differs from release metadata; unsupported platform. | Binary/index identity match, cross-platform golden output, separate artifact/payload scan. | **Phase 4 accepted;** promoted five-platform identity remains Phase 7. |

### Supported Platforms

The rows below are intended V1 release-proof targets. They do not claim that a
V1 or bridge artifact currently exists.

| Platform label | Installation / executable surfaces | Required acceptance proof | Status |
| --- | --- | --- | --- |
| `macos-arm64` | Bash installer; direct `harness`; bridge during approved window. | Authenticated artifact/index; install/update/audit parity; recovery/atomic rename; spaces/Unicode and LF paths; correct identities. | Not started; depends on Phase 7. |
| `macos-x64` | Bash installer; direct `harness`; bridge during approved window. | Same contract and normalized manifest/exit outcomes as macOS arm64 plus architecture identity. | Not started; depends on Phase 7. |
| `linux-x64` | Bash installer; direct `harness`; bridge during approved window. | Authenticated artifact, core/bridge separation, filesystem recovery, fixture matrix, normalized parity. | Not started; depends on Phase 7. |
| `linux-arm64` | Bash installer; direct `harness`; bridge during approved window. | Same contract and normalized outcomes as Linux x64 plus architecture identity. | Not started; depends on Phase 7. |
| `windows-x64` | PowerShell installer; direct `harness.exe`; bridge `.exe` during approved window. | Authenticated `.exe` artifacts; CRLF/LF, Unicode/spaces, Windows path/safe-rename/recovery, normalized manifest/exit parity. | Not started; depends on Phase 7. |

Every supported artifact must prove candidate identity before promotion. A
missing artifact means that platform is unsupported; another platform's test
does not substitute for it.

### Recovery And Kill Points

| Kill / conflict case | Expected state | Required proof | Status |
| --- | --- | --- | --- |
| Before archive publication | No accepted archive; V0 unchanged; unique staging may remain. | Retry uses a fresh stage/ID and preserves the abandoned path. | Implemented locally; independent acceptance pending. |
| After archive publication | One immutable accepted archive; V0 unchanged. | Re-inspect/export verifies exact manifest/member digests; a new archive cannot overwrite it. | Implemented locally; independent acceptance pending. |
| During core receipt install | Phase 3 recovery evidence exists; bridge owns no recovery. | Exact `install --resume` commits the same receipt manifest-last or rollback follows ordinary core rules. | Implemented locally; independent acceptance pending. |
| Archive/export tamper | Invalid; no V1 mutation. | Bridge/core refuse the mismatched digest and preserve every source/archive byte. | Implemented locally; independent acceptance pending. |

### Pilot Cards P0-P7

Each baseline/candidate pair fixes repository revision (or a documented
comparable revision), candidate identities, prompt, fixtures, tests, model,
reasoning, tools, permissions, evaluator, and environment. Every intervention
records actor, timestamp, taxonomy, minutes, and outcome effect.

| Card | Requirement | Acceptance proof | Mandatory failure examples | Status |
| --- | --- | --- | --- | --- |
| P0 | Install or brownfield adoption. | Valid manifest/path report; target-owned before/after hashes; correct unresolved/ready status; install intervention total. | Overwrite, guessed completion, wrong readiness, missing identity. | Baseline: benchmark passed; e-inna failed. Phase 6 candidate evaluation not started. |
| P1 | V0 conversion when eligible. | Export/archive/receipt digests; selected kill-point recovery; no V0 mutation or document move. Written inapplicability if no V0. | Data mutation/loss, hidden move, missing archive, unlogged recovery help. | Baseline: benchmark inapplicable; e-inna failed. Phase 6 candidate evaluation not started. |
| P2 | Ordinary small task. | Target-native acceptance passes with zero core Harness commands and no plan created merely for Harness. | Mandatory Harness call, artificial durable plan, functional regression. | Baseline: benchmark passed; e-inna passed. Phase 6 candidate evaluation not started. |
| P3 | Interrupted complex task. | Fresh agent resumes from target durable plan and passes target acceptance without human reconstruction. | Human reconstructs state, missing decision/progress, changed environment without rerun. | Baseline: benchmark passed; e-inna failed. Phase 6 candidate evaluation not started. |
| P4 | Native invariant repair. | Seeded representative violation fails a named check; agent uses output to repair; same check passes. | Check absent/non-runnable, correction relayed without logging, unrelated rewrite. | Baseline: benchmark passed; e-inna passed. Phase 6 candidate evaluation not started. |
| P5 | Direct feedback repair. | From clean worktree, agent uses applicable target tests/compiler, CI/build, review, rendered docs/links, runtime/UI/observability, deployment, or recovery feedback and passes target proof. | Evaluator supplies hidden evidence, target feedback not used, candidate regression. | Baseline: benchmark passed; e-inna passed. Phase 6 candidate evaluation not started. |
| P6 | Capability inheritance. | Repeated correction becomes a durable target capability; held-out agent discovers and uses it without original discussion. | Capability exists only in chat, evaluator points it out, held-out task is not comparable. | Baseline: benchmark failed; e-inna failed. Phase 6 candidate evaluation not started. |
| P7 | Gardening convergence. | First run makes bounded relevant repair; second identical-condition run finds no repeat drift or unrelated rewrite. | Repeated churn, scope expansion, undocumented evaluator cleanup. | Baseline: benchmark passed; e-inna passed. Phase 6 candidate evaluation not started. |

Release comparison additionally requires at least two eligible pilots for
distinct canonical repositories and authenticated repository-bundle digests,
no functional regression, all applicable cards, and one concrete fully
accounted human-attention or context/validation-discovery improvement. A card
may be inapplicable only with a written evaluator finding.

### V0 Removal

| Requirement | Precondition / negative case | Required acceptance proof | Status |
| --- | --- | --- | --- |
| Actual window closure | Forecasted date, local clock assumption, or early engineering completion is insufficient. | Decision 0012's exact end date plus authoritative timestamp/evidence that it has passed. | Not started; depends on G8 and Phase 8. |
| Support/distribution exit | Any approved support case, conversion obligation, or distribution-ending condition remains open. | Policy checklist signed by responsible owner with referenced issue/support/distribution evidence. | Not started; depends on Phase 8. |
| Archive retention/disposition | Deletion or loss would violate Decision 0012. | Inventory/digest proof that local archives remain unchanged indefinitely and required bridge assets remain available through `2028-06-30T23:59:59Z`. | Not started; depends on Phase 8. |
| Default payload contains no V0 | Any V0 CLI, schema, DB, changeset, lifecycle doc, or bridge-only path enters the V1 core artifact. | Authenticated-index/ledger scan and extracted-artifact negative tests on all platforms. | Not started; depends on Phase 8. |
| Fresh V1 has no V0 state | Install creates/opens SQLite, changesets, or V0 binary. | Clean-repository install diff and process/file-open monitor; no forbidden path. | Not started; depends on Phase 8. |
| Permanent grammar remains six commands | `migrate`, V0 lifecycle verb, alias, or bridge verb appears in core help/dispatch. | Command snapshot for `install`, `update`, `audit`, `scaffold`, `status`, `version` only; unknown commands rejected. | Not started; depends on Phase 8. |
| History remains auditable | Removal rewrites accepted decisions or destroys required historical/recovery evidence. | Post-removal ownership/disposition review; decisions and required policy evidence still readable. | Not started; depends on Phase 8. |
| Bridge is not core | Retained reader/archive material is linked, indexed, or installed by default core. | Dependency/object scan plus payload separation proof; any retained artifact follows approved policy only. | Not started; depends on Phase 8. |

## Fixtures

Planned deterministic fixtures include:

- Every valid and relevant invalid role-state combination, including required
  unresolved, disabled optional, target-owned adopted, and managed-block marker
  cases.
- Valid manifests plus one fixture per forbidden field, unsafe path, missing
  marker/link, wrong digest, unsupported CLI/template/schema range, and
  repository mode.
- Payload indexes with valid authentication, bad authentication, changed
  digest, invalid destination, duplicate/missing ledger entry, unindexed file,
  and each forbidden V0 path class.
- Fresh, brownfield, nested-instruction, docs-only, monorepo-shaped,
  spaces/Unicode, LF/CRLF, target-edit, three-way conflict, idempotent rerun,
  and unsupported downgrade repositories.
- Immutable V0 schema versions 1 through 13, plus below/above/unknown versions;
  the exact supported changeset grammar versions frozen in Phase 1; corrupt,
  partial, WAL/companion, known-provenance, and foreign `.harness` cases.
- Unique archive staging/publication, abandoned and foreign custody, tampered
  members, exact live/archive exports, core receipt interruption/resume, and
  immutable V0 source bytes.
- Exact release artifacts and authenticated indexes for all five platform
  labels; normalization compares semantics while preserving expected
  platform-specific executable suffixes and line endings.
- Signed P0-P7 card definitions, immutable target revisions, locked
  environments, seeded failures, baseline/candidate evidence, evaluator
  findings, and intervention logs for at least two authorized pilots with
  distinct canonical repositories, repository-scoped owner IDs, and bundle
  digests. The stable owner identity may be the same.
- Pre-window and post-window retirement fixtures driven by approved policy
  values; no test substitutes invented dates or retention defaults.

Fixture sources containing V0 state are copied and hashed before a test. Tests
operate on isolated copies and compare the original hashes afterward. Pilot
fixtures and evidence require repository-owner authorization and must not be
fabricated from this planning packet.

## Commands

Product/test commands are listed only when their scripts and binaries exist.
The accepted Phase 5 gate uses the caller-pinned external registry and complete
packets; the partial dogfood check is not live acceptance:

```bash
set -e
story=docs/stories/US-105-harness-v1-implementation

for file in overview.md design.md execplan.md validation.md
do
  test -s "$story/$file"
rg -q '^Status: \*\*Implementation in progress / Phases 1-5 accepted .* / Phases 6-8 not started .*\*\*$' "$story/$file"
done

for heading in \
  'Current Behavior' 'Target Behavior' 'Affected Users' \
  'Affected Product Docs' 'Non-Goals'
do
  rg -q "^## $heading$" "$story/overview.md"
done

for heading in \
  'Domain Model' 'Application Flow' 'Interface Contract' 'Data Model' \
  'UI / Platform Impact' 'Observability' 'Alternatives Considered'
do
  rg -q "^## $heading$" "$story/design.md"
done

for heading in 'Goal' 'Scope' 'Risk Classification' 'Work Phases' 'Stop Conditions'
do
  rg -q "^## $heading$" "$story/execplan.md"
done

for phase in 1 2 3 4 5 6 7 8
do
  rg -q "^### Phase $phase:" "$story/execplan.md"
done

for heading in \
  'Proof Strategy' 'Test Plan' 'Fixtures' 'Commands' 'Acceptance Evidence'
do
  rg -q "^## $heading$" "$story/validation.md"
done

for heading in \
  'Six V1 Core Commands' 'V0 Bridge Commands' 'Supported Platforms' \
  'Recovery And Kill Points' 'Pilot Cards P0-P7' 'V0 Removal'
do
  rg -q "^### $heading$" "$story/validation.md"
done

rg -q 'Gate G0 is approved/open' "$story/design.md"
rg -q 'Current state: approved/open by Decision 0012' "$story/execplan.md"
rg -q 'Phase 1 contract' "$story/validation.md"
rg -q 'Phases 6-8' "$story/validation.md"

scripts/verify-v1-phase1-contracts.sh
scripts/verify-v1-phase2-core.sh
scripts/verify-v1-phase3-recovery.sh
scripts/verify-v1-phase4-bridge.sh
scripts/verify-v1-phase5-evidence.sh --require-pilot-baselines \
  --trusted-owner-registry /absolute/external/trusted-owners.json \
  --trusted-owner-registry-sha256 f55a117eb20df727ee21cb922345d62bce3f3afc4458ba5a8b057dc430c9bb6d
git diff --check
git status --short
```

## Acceptance Evidence

Current product evidence: **Phases 1-5 accepted at the authenticated baseline
gate; Phases 6-8 not started**.
Decision 0012 is G0
authorization evidence; Decision 0013 is the accepted security/data-integrity
decision; US-106 supplies versioned contracts, frozen V0 inputs, complete
dispositions, deterministic fixtures, and mechanical enforcement. US-107 adds
the live pure core, strict authenticated planning boundary, deterministic
structural audit, and mutation-refusal evidence. US-108 adds the Phase 3
mutation/recovery evidence below; it is not Phase 4 or later evidence.

The accepted Phase 1 evidence specifically rejects small-order/zero-scalar
Ed25519 forgeries, Windows ADS paths, ancestor/final capture swaps, DB/WAL
mutation or replacement, bootstrap/command/release drift, incomplete monthly
asset sets, and non-reproducible generated fixtures.

| Phase | Required evidence location/record | Current result |
| --- | --- | --- |
| 1 | Contracts, schemas, disposition ledger, fixtures, G0 reference, CI negatives. | **Passed.** Nine focused proof groups and full premerge passed; Decision 0013 and US-106 are durable evidence. |
| 2 | Core unit/integration, grammar, dependency, mutation, and no-target-execution reports. | **Accepted.** Forty-six Rust tests (24 unit, 22 integration), eleven mechanical proof groups, 72 deterministic fixtures, 138 workspace Rust tests, evolved nine-group Phase 1 proof, workspace check/test/clippy, and full premerge passed. Independent security and behavior review accepted exact candidate `1b1add5`, integrated as `e77e028` with the identical Git tree. The canary/tree/architecture proof is not claimed as universal syscall evidence; US-107 records the boundary. |
| 3 | Install/update filesystem, idempotency, conflict, and recovery reports. | **Accepted.** Forty-three focused tests (eighteen recovery unit, twenty-five signed integration), all 18 install, 15 update, and 13 committed-update rollback checkpoints, 89 total `harness-core` tests, 181 workspace Rust tests, and 11/11 mechanical proof groups pass. Exact emitted-preview/private-write binding, commit/resume payload reauthentication, root-bound recovery ownership, damaged-evidence probe refusal, crash-resumable reverse rollback, manifest-last durability, safe conflict/race handling, read-only status, idempotency, and monotonic mode/receipt preservation are covered. Independent security and behavior review accepted exact candidate `1f957ce`, integrated as `8e67593` with identical Git tree `9cd22cdb24d2`. |
| 4 | Bridge range, immutability, export/archive, journal, kill-point, and separation reports. | **Accepted.** Thirteen focused tests and ten mechanical proof groups pass; independent review accepted exact candidate `880cb9b` with identical Git tree `0f81d3f0f4c8`. |
| 5 | Dogfood, enrollment, signed card, environment, and baseline records. | **Accepted at the authenticated live baseline gate on exact `b2dd775`.** Six proof groups passed and 44/44 adversarial cases were rejected. Two packets under one stable GitHub identity use distinct repository-scoped owner IDs, canonical repositories, bundles, and external Ed25519 keys; signatures and bundle revisions verified. Benchmark P1 is inapplicable and P6 failed; e-inna P0/P1/P3/P6 failed. These are honest pre-candidate measurements, not Phase 6 acceptance. |
| 6 | Candidate P0-P7 results, intervention totals, negative-condition and comparison reports. | Not started; depends on Phase 5 acceptance. |
| 7 | Fixture matrix, five-platform exact artifacts, authentication, identity, and release proof. | Not started; depends on Phase 6 acceptance. |
| 8 | G8 closure/policy evidence, removal ledger, fresh-install/core-grammar/platform regressions. | Not started; depends on Phase 7, G8, and separate removal authorization/validation. |

Planning-packet verification may prove only that these four documents are
present, structurally complete, whitespace-clean, and scoped. Record the exact
shell/Git results and documentation commit hash in the task completion report;
do not reinterpret that evidence as implementation, test, release, pilot, or
date proof.
