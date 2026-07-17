# US-105 Repository Harness V1 Implementation Validation

Status: **Implementation in progress / Phases 1-2 accepted / Phase 3 implemented and locally validated, acceptance pending**

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

Phase 2 core implementation proof and independent review pass; Phase 3
implementation/local validation pass with acceptance pending; Phase 4-8
product proof remains prospective. No production-promoted mutation/recovery
adapter, five-platform artifact set, pilot result, bridge, or later phase
acceptance exists. Decision
0012 is authorization evidence: Gate G0 is approved/open, the window is
`2027-01-01T00:00:00Z` through `2027-12-31T23:59:59Z`, inclusive, local
archives are retained indefinitely, bridge release assets are retained through
`2028-06-30T23:59:59Z`, inclusive, and Phase 8 is eligible no earlier than
`2028-01-01T00:00:00Z` after all closure conditions pass. Decision 0013 and
US-106 implement and prove Phase 1; US-107 implements and proves Phase 2;
US-108 implements and locally validates Phase 3. Phases 4-8 remain not-started
dependencies. Only the Phase
1 and Phase 2 matrix rows are passed.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Role activation/ownership/origin/required combinations; update policies; safe paths; manifest forbidden fields; schema/range compatibility; repository-mode transitions; payload disposition; journal state transitions; audit/status exits. |
| Integration | Authenticated-index install; fresh/brownfield/update filesystems; backups and atomic rename; target-owned preservation; mixed-invalid blocking; bridge read-only database/export/archive/apply/resume/rollback; digest conflicts; process-spawn denial. |
| E2E | Repository-local CLI flows for all six core and seven bridge commands; dogfood; release-only P0-P7 cards; complete V0-to-V1 cutover and post-window V0 removal. No browser E2E is implied. |
| Platform | Bash/direct binary on macOS arm64/x64 and Linux x64/arm64; PowerShell/direct `.exe` on Windows x64; checksums/authentication, paths with spaces/Unicode, line endings, atomic/recovery semantics, and equivalent manifests/exits. |
| Performance | No speed claim is required for acceptance. Record command duration/resource regressions during release proof, but never trade integrity, deterministic results, or recovery for a threshold invented after implementation. |
| Logs/Audit | Deterministic machine/human output contains identity, mode, role/path issue, and next action; no telemetry/task/run/trace state; audit starts no target tool; bridge journal contains only conversion operations; pilot interventions are release evidence only. |

### Contract Boundary Proof

| Requirement | Negative case | Required proof | Planned evidence |
| --- | --- | --- | --- |
| Role fields are independent and normative. | Treat `v0-adopted` as permission to rewrite a target-owned file. | Table-driven transition/update-policy tests reject the write and leave bytes unchanged. | Phase 2-3 role/asset unit and filesystem results. |
| Manifest is provenance, not operations. | Add `task`, `run`, `prompt`, `result`, `trace`, telemetry, scheduler, database, or semantic-changeset fields. | Schema rejects each field and audit returns invalid. | Phase 1 schema fixtures and Phase 2 negative tests. |
| Payload index is authoritative. | Add an unindexed file or forbidden `harness.db*`, changeset, schema, V0 binary, or lifecycle path. | Build/release verification fails before artifact promotion. | Phase 1 ledger and Phase 7 exact-artifact report. |
| Audit is structural and read-only. | Manifest asks audit to run a target test or a malicious fixture exposes a process hook. | No process starts; audit reports only structural state. | Phase 2 process-denial integration proof on all release platforms. |
| Conversion commits once. | Crash before manifest/receipt atomic rename. | No success receipt exists; V0 inputs hash identically; resume/rollback is safe. | Phase 4 parameterized kill-point report. |
| Unknown state is preserved. | `.harness/foreign-tool.json` exists beside recognized V0 state. | Inspect/preview report unknown/unowned; apply/resume/rollback leave its digest unchanged. | Phase 4 unknown-metadata fixture. |
| Phase 8 is time/policy gated. | Engineering is ready but it is before `2028-01-01T00:00:00Z`, a supported recovery/security/data-loss/archive-integrity case remains open, retained assets are unverified, or separate removal authorization/validation is missing. | Retirement change is blocked, V0 default artifacts remain, and local archives are never automatically removed. | Decision 0012, G8 evidence, and the Phase 8 precondition report. |

## Requirement-To-Proof Matrix

### Six V1 Core Commands

| Requirement | Positive cases | Negative / boundary cases | Required acceptance proof | Status |
| --- | --- | --- | --- | --- |
| `install` | Fresh selected roles; V0-path adoption where permitted; explicit brownfield mapping; valid unresolved install. | Unsafe destination; ambiguous ownership; mixed-invalid state; bad payload digest; crash before manifest commit. | Exact preview; byte/digest before-after report; atomic-manifest kill point; no database/changesets; target-owned bytes unchanged; resulting mode/readiness. | **Phase 3 locally validated:** signed install, exact confirmation, fresh brownfield mapping, manifest-last commit, all 18 install kill points, deterministic rerun/resume/rollback, and no false success pass; acceptance pending. |
| `update` | Replace-if-base; supported manifest transition; explicit three-way review; idempotent rerun. | Edited base; target-owned asset; unsupported downgrade; interrupted write; payload/template/CLI range mismatch. | Policy matrix, conflict output, backups, unchanged target bytes, no false success, rerun equivalence. | **Phase 3 locally validated:** managed-file conflict, managed-block interior replacement, target-owned preservation, converted-mode receipt retention, backups, atomic exchange, status probe, and recovery pass; acceptance pending. |
| `audit` | Ready exit 0; unresolved exit 2; deterministic repeated result. | Bad schema/path/digest/marker/link/forbidden field exit 3; malicious target-tool hook; V0-only repository. | Golden machine/human output, filesystem/process monitor showing no writes/spawns, no V0 database open, stable exits. | **Phase 2 accepted:** pinned Unix snapshot tests, deterministic structural exits, unchanged canary tree/sentinel, and no process/DB port. This is not universal event proof; safe non-Unix inspection and portable event evidence remain Phase 7. |
| `scaffold` | Explicit selected neutral template at safe target path; repeated preview. | Stack inference; overwrite existing target content; lifecycle/task record creation; unsafe path. | Payload/template identity, exact preview/diff, collision rejection, manifest/provenance result, no operational fields. | **Phase 3 locally validated:** exact authenticated creation, target-owned/never-auto-patch manifest state, and repeated exact idempotent no-op pass; acceptance pending. |
| `status` | Fresh-v1, brownfield-v1, v0-legacy, conversion-in-progress, converted-with-archive; valid and unresolved exit 0. | Mixed-invalid or corrupt manifest exit 3; attempt to repair state. | Mode/identity/readiness golden outputs, read-only filesystem/database/process proof, exact invalid reason. | **Phase 2 accepted:** absent/ready/unresolved/invalid V1 structural states are deterministic and read-only on the safe Unix adapter. V0/bridge modes remain Phase 4; non-Unix safe handles remain Phase 7. |
| `version` and `--version` | Same V1 version and accepted manifest/template ranges on every platform. | Alias to V0, mismatched output, unrecognized/downgrade range. | Byte-equivalent normalized output, binary identity/digest, grammar snapshot with only six commands. | **Phase 2 accepted:** native alias output and exact six-command grammar match. Five-platform promoted artifacts remain Phase 7. |

### V0 Bridge Commands

| Requirement | Positive cases | Negative / boundary cases | Required acceptance proof | Status |
| --- | --- | --- | --- | --- |
| `inspect` | Recognized V0 schema 1..=13 and published changeset grammar; known provenance; companion layout. | Schema outside range; unreadable DB; arbitrary `.harness`; foreign metadata. | Read-only-open instrumentation, categorized inventory, before/after source hashes, unsupported/preserved output. | Not started; depends on Phase 4. |
| `export` | Neutral `repository-harness-v0-export/v1` for every supported category. | Unknown category, corrupt row, grammar outside range, partial output. | Schema validation, stable category/source/payload digests, no V0 task fields in V1 manifest, safe retry. | Not started; depends on Phase 4. |
| `preview` | Exact archive/export identity, planned operations, preserved paths, role/readiness outcome. | Input changes after inspect/export; ambiguous ownership; unsafe destination; unsupported V1 range. | Zero target mutation, expected/actual digest conflict, complete operation ledger, deterministic repeated preview. | Not started; depends on Phase 4. |
| `apply` | Archived supported input; all selected idempotent operations; deterministic V1 audit; atomic receipt. | Kill at every point; target conflict; input digest drift; audit invalid; receipt rename failure. | Full kill-point matrix, V0 immutability, no pre-commit success, completed receipt binds bridge/export/archive digests. | Not started; depends on Phase 4. |
| `resume` | Continue only incomplete operations from a validated journal; repeated resume after completion is harmless. | Journal tamper; changed source/post-image; unsupported bridge; unknown operation. | Operation execution counts, journal/digest verification, reject-and-preserve conflict, unchanged completed operations. | Not started; depends on Phase 4. |
| `rollback` | Restore/remove only journal-owned matching writes before commit. | Human edit after apply; path now foreign; rollback after unsupported state; request to delete archive/V0 DB. | Pre/post byte hashes, conflict preservation, archive/source survival, recovery-required result when ownership/digest fails. | Not started; depends on Phase 4. |
| `version` | Bridge version, platform, schema 1..=13, exact changeset grammar range, compatibility statement. | Pretends to be V1 core/V0 CLI; range differs from release metadata; unsupported platform. | Binary/index identity match, cross-platform golden output, separate artifact/payload scan. | Not started; depends on Phases 1, 4, and 7. |

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

| Kill / conflict case | Expected state after interruption | Required resume proof | Required rollback proof | Status |
| --- | --- | --- | --- | --- |
| After V0 detection | V0 inputs unchanged; no export/archive/journal/success manifest required. | Reinspect from immutable inputs and reach same inventory. | No-op; never touches V0. | Not started; depends on Phase 4. |
| After export write | Verified or safely replaceable export; no target mutation or success manifest. | Validate/recreate export deterministically, then continue once. | Remove only journal-owned incomplete export if policy permits; V0 unchanged. | Not started; depends on Phase 4. |
| After archive write/verification | Checksummed archive present; no target mutation or success manifest. | Verify archive/export digests and continue without rewriting V0. | Preserve archive; no target/V0 mutation. | Not started; depends on Phase 4. |
| After each planned filesystem operation | Journal names completed operation and before/after digest; no success receipt before commit. | Parameterized test repeats only remaining operations; completed post-images unchanged. | Restore/remove only matching journal-owned operations in reverse-safe order; stop on changed post-image. | Not started; depends on Phase 4. |
| After temporary manifest/receipt write | Temporary files uncommitted; old manifest state remains authoritative. | Revalidate all operations/audit and atomically commit once. | Remove only matching temporaries and roll back matching journal-owned writes; preserve archive/V0. | Not started; depends on Phase 4. |
| Immediately after atomic commit | One coherent manifest/receipt references verified export/archive; state is committed/completable. | Detect committed identity, finish bookkeeping idempotently, never replay target writes. | No automatic pre-commit rollback claim; follow documented post-commit recovery while preserving V0/archive. | Not started; depends on Phase 4. |
| Input changes between preview and apply | No mutation; digest conflict and recovery/represent action required. | Reinspect/re-export only after explicit new preview. | No-op; preserve all evidence. | Not started; depends on Phase 4. |
| Target edit after a recorded file operation | Recovery-required; human bytes preserved. | Stop because post-image digest differs; require human decision. | Stop and reject overwrite; preserve journal/archive/V0. | Not started; depends on Phase 4. |
| Journal/archive/export tamper | Invalid/recovery-required; no further mutation. | Refuse until trusted evidence is restored or a human chooses a new conversion. | Never use untrusted digests to overwrite paths. | Not started; depends on Phase 4. |

### Pilot Cards P0-P7

Each baseline/candidate pair fixes repository revision (or a documented
comparable revision), candidate identities, prompt, fixtures, tests, model,
reasoning, tools, permissions, evaluator, and environment. Every intervention
records actor, timestamp, taxonomy, minutes, and outcome effect.

| Card | Requirement | Acceptance proof | Mandatory failure examples | Status |
| --- | --- | --- | --- | --- |
| P0 | Install or brownfield adoption. | Valid manifest/path report; target-owned before/after hashes; correct unresolved/ready status; install intervention total. | Overwrite, guessed completion, wrong readiness, missing identity. | Not started; depends on Phases 5-6. |
| P1 | V0 conversion when eligible. | Export/archive/receipt digests; selected kill-point recovery; no V0 mutation or document move. Written inapplicability if no V0. | Data mutation/loss, hidden move, missing archive, unlogged recovery help. | Not started; depends on Phases 5-6. |
| P2 | Ordinary small task. | Target-native acceptance passes with zero core Harness commands and no plan created merely for Harness. | Mandatory Harness call, artificial durable plan, functional regression. | Not started; depends on Phases 5-6. |
| P3 | Interrupted complex task. | Fresh agent resumes from target durable plan and passes target acceptance without human reconstruction. | Human reconstructs state, missing decision/progress, changed environment without rerun. | Not started; depends on Phases 5-6. |
| P4 | Native invariant repair. | Seeded representative violation fails a named check; agent uses output to repair; same check passes. | Check absent/non-runnable, correction relayed without logging, unrelated rewrite. | Not started; depends on Phases 5-6. |
| P5 | Direct feedback repair. | From clean worktree, agent uses applicable target tests/compiler, CI/build, review, rendered docs/links, runtime/UI/observability, deployment, or recovery feedback and passes target proof. | Evaluator supplies hidden evidence, target feedback not used, candidate regression. | Not started; depends on Phases 5-6. |
| P6 | Capability inheritance. | Repeated correction becomes a durable target capability; held-out agent discovers and uses it without original discussion. | Capability exists only in chat, evaluator points it out, held-out task is not comparable. | Not started; depends on Phases 5-6. |
| P7 | Gardening convergence. | First run makes bounded relevant repair; second identical-condition run finds no repeat drift or unrelated rewrite. | Repeated churn, scope expansion, undocumented evaluator cleanup. | Not started; depends on Phases 5-6. |

Release comparison additionally requires at least two unrelated eligible pilots,
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
- Parameterized bridge journals for every state and kill point, tampered
  digests, incomplete operations, human post-image edits, committed receipts,
  and recovery-required conflicts.
- Exact release artifacts and authenticated indexes for all five platform
  labels; normalization compares semantics while preserving expected
  platform-specific executable suffixes and line endings.
- Signed P0-P7 card definitions, immutable target revisions, locked
  environments, seeded failures, baseline/candidate evidence, evaluator
  findings, and intervention logs for at least two unrelated authorized pilots.
- Pre-window and post-window retirement fixtures driven by approved policy
  values; no test substitutes invented dates or retention defaults.

Fixture sources containing V0 state are copied and hashed before a test. Tests
operate on isolated copies and compare the original hashes afterward. Pilot
fixtures and evidence require repository-owner authorization and must not be
fabricated from this planning packet.

## Commands

Future product/test command paths will be added only when their scripts and
binaries exist. This packet must not present imaginary commands as runnable
proof. The current planning change is verified with read-only shell checks and
Git only:

```bash
set -e
story=docs/stories/US-105-harness-v1-implementation

for file in overview.md design.md execplan.md validation.md
do
  test -s "$story/$file"
rg -q '^Status: \*\*Implementation in progress / Phases 1-2 accepted / Phase 3 implemented and locally validated, acceptance pending\*\*$' "$story/$file"
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
rg -q 'Phases 4-8 remain' "$story/validation.md"

scripts/verify-v1-phase1-contracts.sh
scripts/verify-v1-phase2-core.sh
scripts/verify-v1-phase3-recovery.sh
git diff --check
git status --short
```

## Acceptance Evidence

Current product evidence: **Phases 1-2 accepted; Phase 3 implemented and
locally validated, with orchestrator acceptance pending**. Decision 0012 is G0
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
| 3 | Install/update filesystem, idempotency, conflict, and recovery reports. | **Implemented and locally validated; acceptance pending.** Twenty-six focused tests (ten recovery unit, sixteen signed integration), all 18 install and 15 update kill points, 72 total `harness-core` tests, 164 workspace Rust tests, and 11/11 mechanical proof groups pass. Exact preview/private-write binding, commit/resume payload reauthentication, authenticated recovery ownership, manifest-last durability, safe conflict/race handling, read-only status, idempotency, and monotonic mode/receipt preservation are covered. |
| 4 | Bridge range, immutability, export/archive, journal, kill-point, and separation reports. | Not started; depends on Phase 3 acceptance. |
| 5 | Dogfood, enrollment, signed card, environment, and baseline records. | Not started; depends on Phase 4 acceptance. |
| 6 | Candidate P0-P7 results, intervention totals, negative-condition and comparison reports. | Not started; depends on Phase 5 acceptance. |
| 7 | Fixture matrix, five-platform exact artifacts, authentication, identity, and release proof. | Not started; depends on Phase 6 acceptance. |
| 8 | G8 closure/policy evidence, removal ledger, fresh-install/core-grammar/platform regressions. | Not started; depends on Phase 7, G8, and separate removal authorization/validation. |

Planning-packet verification may prove only that these four documents are
present, structurally complete, whitespace-clean, and scoped. Record the exact
shell/Git results and documentation commit hash in the task completion report;
do not reinterpret that evidence as implementation, test, release, pilot, or
date proof.
