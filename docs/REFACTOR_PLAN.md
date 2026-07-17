# Repository Harness V1 Refactor Plan

Date: 2026-07-16

Status: Direction and Phases 1-2 accepted; Phase 3 implemented and locally validated, acceptance pending; Phases 4-8 not started

Planning stories: US-103 and US-104; implementation initiative: US-105;
Phase 2 implementation: US-107; Phase 3 implementation candidate: US-108

## Executive Outcome

Repository Harness V1 is an installable, template-first seed kit for
agent-legible repositories. It supplies a short repository map, structured
knowledge templates, an authenticated release payload, and small explicit
maintenance utilities. It is not a mandatory operational control plane.

After installation, agents use the target repository's own documentation,
scripts, tests, compiler, CI, review process, runtime/UI inspection,
observability, deployment checks, and recovery procedures. The ordinary path is:

~~~text
receive task -> read AGENTS.md -> follow target-owned links -> inspect and change
the repository -> run target-native proof -> update target knowledge when needed
-> use the repository's normal review workflow
~~~

No V1 command is mandatory in that path. Installation proves that a seed kit was
placed safely; it does not prove that the target is ready for agent work.

V1 replaces V0 only after deterministic product checks and release-only
behavior evidence show that the installed repository supports proportional
planning, executable native invariants, direct feedback, durable capability
improvement, and bounded recurring maintenance.

## Anchor Evidence Classification

The governing anchor is OpenAI's
[Harness engineering: leveraging Codex in an agent-first world](https://openai.com/index/harness-engineering/).
This plan deliberately distinguishes what that article directly supports from
the decisions and hypotheses made for this product.

| Classification | Statement | Mechanism -> expected behavior -> proof |
| --- | --- | --- |
| Direct observation from the article | Agents benefit from a concise entrypoint, repository-specific context, native feedback loops, executable checks, and humans steering scarce attention. | Short map plus target-native links -> an agent finds the next authoritative source -> a representative agent task finds it without a human relay. |
| Direct observation from the article | Repeated agent failures should become durable repository capability instead of repeated human explanation. | Add a document, test, script, lint, CI check, skill, or feedback surface -> a later agent can use it -> a held-out task demonstrates the benefit. |
| Deliberate V1 product decision | V1 is template-first, repository-native, path-stable, and optional during ordinary work. | Visible normal repository artifacts and no task lifecycle database -> no required Harness call for normal work -> ordinary-work scenario card passes with zero Harness commands. |
| Deliberate V1 product decision | V1 audit is a deterministic structural boundary, and the payload index is authoritative. | Authenticated index, manifest, hashes, markers, paths, and links -> repeatable audit without semantic guessing -> unit and fixture proof plus release-index verification. |
| Release hypothesis | A seed kit improves human attention, discoverability, repairability, and maintenance proportionally. | Instantiated target capability -> comparable baseline/candidate task -> release-only pilot evidence with fixed conditions and total human-attention accounting. |
| Case-specific practice, not generalized | This repository currently uses docs/, a Rust binary, Bash/PowerShell installers, and prior SQLite/changeset state. | Preserve useful paths and create a V0 bridge -> this repository migrates without cosmetic moves -> dogfood and bridge fixtures prove it. Other targets choose their own architecture and tools. |

The article is not authority for a required folder layout, language, model,
provider, scheduler, risk lane, workflow database, or universal quality score.
Those would need a separate V1 decision and evidence.

## Locked Product Decisions

The following accepted decisions are normative for V1:

- The portable core is template-first and repository-native.
- Installed knowledge uses visible normal repository paths; .harness/ contains
  only V1 provenance and tool-local recovery metadata, never shared task state.
- Existing useful paths and relative links are adopted in place. Cosmetic
  renames are prohibited.
- No Harness command is mandatory before, during, or after ordinary work.
- Audit is deterministic and structural; it never runs target tools or judges
  prose semantics.
- Release promotion requires behavior proof, not template-presence proof.
- Permanent V1 core commands are install, update, audit, scaffold, status, and
  version. Conversion from V0 is a separately versioned, time-bounded bridge,
  not a permanent V1 command.
- Decision 0012 fixes the compatibility window, local-archive custody,
  bridge-release retention, and Phase 8 eligibility and closure conditions.
- Repository Harness validates its own source layering. V1 templates ask a
  target to describe and enforce its own architecture; they do not prescribe
  domain/application/infrastructure/interface layering to targets.

Changing a locked decision requires a new explicit human decision.

### Approved Compatibility And Retention Policy

Decision 0012 opens Gate G0 with these exact values:

- The compatibility window is `2027-01-01T00:00:00Z` through
  `2027-12-31T23:59:59Z`, inclusive. Support covers security, data-loss,
  archive/recovery, and supported-input compatibility defects or mitigations,
  not new V0 features.
- Local conversion archives are write-once, checksum-verified recovery evidence
  under repository-owner custody and are retained indefinitely. No install,
  update, audit, bridge command, uninstall, or Phase 8 action may automatically
  delete, overwrite, truncate, or relocate them. Manual deletion must be
  explicit and warn that V0 recovery is lost.
- Every supported-platform bridge binary, checksum, authenticated index or
  attestation, supported-input matrix, release notes, source tag, and
  reproducible build instructions is retained through
  `2028-06-30T23:59:59Z`, inclusive. Release maintainers own periodic
  availability verification.
- Phase 8 is eligible no earlier than `2028-01-01T00:00:00Z` and only after
  Phase 7 acceptance; all support and recovery obligations close; no known
  unresolved in-window recovery case remains; no unresolved supported-range
  security, data-loss, or archive-integrity defect remains; bridge-asset
  retention is verified; and separate removal authorization and validation
  exist.

The approved window assumes V1 core and bridge general availability on every
declared platform by `2027-01-01T00:00:00Z`. If that does not occur, the window
must not silently shrink. A new explicit decision must shift the start, end,
bridge-asset retention, and Phase 8 eligibility together, reaffirm indefinite
local-archive retention, and preserve at least 365 supported days.

A conversion journal created before `2027-12-31T23:59:59Z` closes the window
remains eligible for supported resume or rollback. Cause and effect: the end of
the calendar window stops new ordinary window obligations, but it does not
abandon an already-started recovery case; any known unresolved case delays
actual Phase 8 removal.

## Product Boundary And Stable Repository Shape

V1 installs or maps only selected roles. The familiar default candidates remain
path-compatible:

~~~text
AGENTS.md
docs/README.md
docs/ARCHITECTURE.md
docs/product/
docs/decisions/
docs/stories/
docs/templates/
docs/contracts/       optional
docs/reviews/         optional
.harness/manifest.json
~~~

A fresh install creates only selected roles. A V0 repository adopts these
paths in place. A brownfield repository can map a role to an existing path such
as docs/adr/ or CONTRIBUTING.md. It must not create a second directory merely
because the default candidate has a different name.

Path stability has concrete effects:

1. Existing valid documents are neither moved nor renamed by V1.
2. Relative links and Git history remain valid unless the target separately
   approves a move for its own reason.
3. A new path is created only when a selected role has no suitable home, and
   preview names that path.
4. A target-owned adopted or brownfield-mapped file is never automatically
   patched by install, update, recovery, or audit.

### Product Does And Does Not

V1 does install/adopt a repository map, neutral templates, provenance, explicit
scaffolding, deterministic audit, and explicit updates. It can report a
repository's declared state. It does not select a stack, infer semantic
ownership, run target tests, run a daemon or scheduler, create task/run/prompt/
result records, store telemetry, classify work risk, or replace Git, CI,
issues, reviews, logs, metrics, traces, deployment, or normal recovery.

Templates ask targets for runnable answers:

- planning triggers for no plan, lightweight planning, and resumable plans;
- exact invariant checks, remediation, and exception paths;
- relevant test/compiler, CI/build, review-comment, rendered-doc/link,
  runtime/UI/observability, deployment, and reset/recovery feedback routes;
- maintenance scope, owner, trigger or cadence, runner, bounded-change policy,
  validation, and convergence expectation.

An unavailable feedback surface is explicitly marked unavailable. V1 does not
invent tools for it.

## Role And Asset State Model

Each role has four independent normative fields:

| Field | Values | Meaning |
| --- | --- | --- |
| activation | active, unresolved, disabled | Active is instantiated and auditable; unresolved is intentionally installed but still contains exact completion markers; disabled is outside the target's selected contract. |
| ownership | managed-file, managed-block, target-owned | A managed-file is wholly maintained by V1; a managed-block is only a marker-delimited V1 block in a target file; target-owned content belongs to the target. |
| origin | created, v0-adopted, brownfield-mapped | Created was made by V1; v0-adopted maps a recognized compatible V0 path; brownfield-mapped is an explicit target mapping. |
| required | true, false | A required active role must be structurally complete for a ready audit; optional roles may be disabled. |

Each managed asset also records asset identifier, template identifier, template
release, base digest, current digest when appropriate, marker identity for a
managed block, and update-policy. Update-policy is one of replace-if-base,
three-way-review, or never-auto-patch. Target-owned adopted and mapped files
always use never-auto-patch, even when their role is active.

Illustrative manifest entry:

~~~json
{
  "role": "agent_map",
  "activation": "unresolved",
  "ownership": "managed-block",
  "origin": "v0-adopted",
  "required": true,
  "asset": "agent-map-root",
  "template": "agent-map",
  "template_release": "v1.0.0",
  "base_sha256": "...",
  "marker": "repository-harness:v1:agent-map",
  "update_policy": "three-way-review",
  "path": "AGENTS.md"
}
~~~

The manifest has no task, run, prompt, result, user, trace, raw-command-output,
telemetry, score, or scheduler fields. Schema tests reject those field names.

### Installation, Readiness, And Audit Outcomes

Tool installation and repository readiness are separate:

| State | install/update | status | audit |
| --- | --- | --- | --- |
| Structurally valid, unresolved | Succeeds and writes provenance. It never fills placeholders by guessing. | Reports installation=installed and readiness=unresolved, naming each marker. | Reports structural=valid, readiness=unresolved, and returns the documented unresolved outcome. |
| Structurally valid, ready | Succeeds. | Reports readiness=ready. | Returns clean after deterministic checks. |
| Invalid | Aborts before committing a new manifest or transition; preserves existing files. | Reports invalid with the exact failed contract. | Returns invalid; examples are bad schema, unsafe path, bad digest, missing managed marker, or broken required link. |
| Disabled optional role | Does not create or validate the role. | Reports disabled. | Is not a failure unless a manifest contradicts required=true. |

The canonical exit contract is: audit exit 0 for ready, exit 2 for unresolved,
and exit 3 for invalid. Status is read-only and returns 0 when it can report a
valid or unresolved manifest and 3 for invalid state. These codes are product
contracts, not claims about content quality.

## CLI Identity And Compatibility

V0 and V1 use distinct binary identities and grammars so a command cannot
silently change database semantics.

| Surface | Repository-local path | Grammar | Semantics | Compatibility fence |
| --- | --- | --- | --- | --- |
| V0 operational CLI | scripts/bin/harness-cli or harness-cli.exe | harness-cli v0.x init, migrate, audit, intake, story, query, and other V0 lifecycle verbs | migrate changes SQLite schema; audit inspects V0 database/changeset operational state | Frozen during compatibility window; it never interprets a V1 manifest. |
| V1 core CLI | scripts/bin/harness or harness.exe | harness install, update, audit, scaffold, status, version; --version is equivalent to version | install/update/scaffold are explicit file mutations; audit/status/version are read-only structural operations | It never opens or mutates V0 SQLite/changesets. No migrate verb exists. |
| V0 conversion bridge | scripts/bin/harness-v0-migrate or harness-v0-migrate.exe | inspect, export, preview, apply, resume, rollback, version | Reads V0 state, produces a neutral export/archive, and performs one bounded conversion | Separate release and support window; not installed as the V1 core command. |

No alias maps harness to harness-cli, or harness-cli to a V1 grammar. The
installer may place V1 beside V0 during the compatibility window, but must
print both identities and require an explicit bridge apply before cutover.
Shell wrappers may invoke the binary of the same identity only; they may not
translate one grammar into the other.

V1 CLI and template releases use semantic versions. A V1 CLI declares the
minimum and maximum manifest schema and template-release ranges it accepts.
Install/update own forward manifest schema transitions and refuse an
unsupported downgrade. A template release declares its required V1 CLI range.
Status reports the three identities and compatibility decision without changing
state.

Repository modes are fresh-v1, brownfield-v1, v0-legacy,
conversion-in-progress, converted-v1-with-archive, and mixed-invalid. A
converted repository has a V1 manifest plus a completed bridge receipt naming
the export and archive digests. V0 artifacts plus a manifest without that
receipt are mixed-invalid; ordinary V1 mutation is blocked until bridge resume
or rollback resolves it.

## Authoritative Payload And V1 Core Boundaries

Each V1 release has a signed or otherwise authenticated payload index. The
index, not a glob or source-directory convention, is authoritative for every
installed file. It includes release identity, signing/authentication evidence,
logical asset, source digest, destination path rule, role, template identity,
and path disposition.

The path disposition ledger labels every candidate path as one of:

- managed V1 payload;
- optional V1 payload;
- source-only/not installed;
- target-owned destination only;
- bridge-only legacy payload; or
- forbidden V0 operational payload.

CI builds the payload exclusively from the authenticated index, verifies every
digest and destination rule, and rejects forbidden V0 paths such as harness.db,
harness.db-wal, harness.db-shm, .harness/changesets/**, scripts/schema/**,
the V0 operational binary, and V0 lifecycle documentation. A separately signed
bridge release may contain its bridge-only reader and fixtures; that exception
does not enter the V1 core index.

V1 core tests mechanically enforce seed-kit boundaries:

- manifest parsing rejects task/run/prompt/result and other operational-state
  fields;
- no core process is a daemon or scheduler;
- audit cannot execute a target command, test, compiler, CI job, deployment
  check, or runtime process;
- only install, update, and scaffold can change files, and each has an explicit
  preview/confirmation or deterministic non-interactive contract;
- status, version, and audit are read-only.

Repository Harness itself follows ports between CLI application logic,
filesystem/release/manifest infrastructure, and interface code. That is a
check on this product's implementation, not a target architecture template.

## Legacy V0 Conversion And Recovery

Decision 0011 makes conversion a separately versioned, time-bounded,
repository-local harness-v0-migrate artifact. Decision 0012 supplies its exact
window, retention, support, and retirement policy. The bridge is not a V1 core
command and does not make V0 operational behavior permanent.

### Detection And Supported Inputs

The bridge recognizes V0 only from a conservative signature: a readable
repository-root harness.db with the V0 schema_version table in the bridge's
supported range, plus any recognized companion .harness/changesets layout or
known V0 installer provenance. It must not claim arbitrary .harness files.
Unknown tool-local metadata is reported as unknown/unowned and preserved; it is
neither rejected nor adopted.

The first bridge release supports V0 schema_version 1 through 13 inclusive and
the documented V0 changeset grammar versions it can parse. A later bridge that
widens this range is a new versioned artifact with fixtures and an explicit
compatibility statement. The immutable reader opens the V0 database read-only,
does not run a V0 migration, and never writes the database or changesets.

### Export, Archive, And State Machine

The bridge produces a neutral, versioned repository-harness-v0-export/v1
document. It preserves source identifiers, source schema version, category,
payload digest, and disposition without making V0 task state part of V1.
Before any target mutation, it writes a checksummed archive of the V0 database,
recognized changesets, known V0 provenance, export, and archive manifest under
.harness/legacy/v0-conversion/<conversion-id>/. This archive is tool-local and
untracked; its digest is referenced, not copied, by the V1 receipt. It is
write-once recovery evidence retained indefinitely under repository-owner
custody. Automated product actions never delete, overwrite, truncate, or move
it; explicit manual deletion warns that V0 recovery will be lost.

A transient untracked operation journal records only conversion filesystem
operations and their before/after digests. It contains no task lifecycle
records. Its state machine is:

~~~text
discovered -> inspected -> exported -> archived -> prepared -> applying
    -> committed -> completed
                         ^
failure -----------------+ (resume or rollback from a recorded safe point)
~~~

The commit point is the atomic rename of a fully validated V1 manifest and
conversion receipt after export/archive verification, all selected filesystem
operations, and a deterministic V1 audit. Unresolved roles are allowed at this
point because they are valid but not ready. Before the commit point there is no
manifest that claims conversion success.

Apply is idempotent. Resume validates journal digests, repeats only incomplete
operations, and stops on a conflict. Rollback restores only journal-owned
created files or managed blocks whose post-image digests still match; it never
overwrites a subsequent target edit. It removes no archive and does not alter
the V0 database. A conflict is reject-and-preserve: leave all evidence in
place, mark the journal recovery-required, and require human selection.

Kill-point fixtures terminate after detection, export, archive, every planned
file operation, temporary-manifest write, and atomic commit. Each proves that
the V0 inputs remain intact, no false success manifest exists before commit,
and resume or safe rollback has the stated result.

### Mixed Versions And Downgrade

The bridge verifies V0 binary/schema/changeset compatibility before preview and
again before apply. V1 status detects active V0 state, completed archive state,
and incomplete/mixed state rather than guessing from a directory name.

There is no automatic V1-to-V0 downgrade. To recover, use the immutable
archive in a clean clone with a compatible V0 binary, or roll back
transaction-owned V1 changes before the bridge commit. V1-only manifest schema
transitions are owned by V1 install/update and follow their own supported
downgrade policy: reject unsupported schema downgrade while preserving the
repository. No operation reconstructs V0 database history from V1 content.

## Phased Delivery

Implementation is a separate high-risk initiative. Dependencies are linear so
no phase relies on a pilot introduced later.

### Phase 1: Contracts And Release Inventory

Define the role/asset model, manifest schemas, V0/V1 grammar matrix,
authenticated payload index and disposition ledger, Decision 0012's exact
compatibility/retention contracts, and V0 fixtures. Freeze new V0 operational
features. **Implemented and accepted:** Decision 0013, `docs/contracts/v1/`,
`release/contracts/v1/`, the US-106 packet, and deterministic Phase 1 fixtures
freeze this boundary. `scripts/verify-v1-phase1-contracts.sh` proves every
current payload path and V0 data category has one disposition and rejects
unindexed or forbidden V0 core paths. This Phase remains accepted and unchanged
under the evolved core-live/bridge-absent lifecycle.

### Phase 2: Pure V1 Core

Build only V1 install/update/audit/scaffold/status/version around filesystem,
release, and manifest ports. Acceptance: no operational database dependency,
no migrate grammar, deterministic audit, mechanical seed-kit boundary tests,
and no target tools executed by audit.

**Implemented, fully validated, and accepted:** US-107 adds
the separate `harness-core` package and native
`scripts/bin/harness[.exe]` identity. Forty-six Rust tests, eleven Phase 2
mechanical proof groups, the evolved nine-group Phase 1 verifier, 72
reproducible fixtures, 138 workspace Rust tests, workspace
check/test/clippy, and full premerge prove exact live/source/contract grammar
parity; independently pinned trust-bundle/release lifecycle; indexed core-only
payload planning; pinned Unix snapshot and race refusal; schema/CommonMark/
Unicode/output determinism; the executable canary plus unchanged-tree
no-spawn boundary; and no-op/refusal for writes that require Phase 3. This is
not described as universal syscall/event proof. The reserved bridge remains
absent and the release workflow remains present but unpromoted. Independent
security and behavior reviewers accepted exact candidate `1b1add5`, integrated
as `e77e028` with the identical Git tree. That accepted Phase 2 evidence is
unchanged; Phase 3 implementation and validation are recorded separately in
US-108. Production trust/promotion, safe non-macOS/Linux handle behavior,
portable event evidence, and five-platform artifact parity remain outside
Phase 2 and Phase 3 acceptance.

### Phase 3: Install/Update Recovery

Implement fresh installation, brownfield mapping, backups, atomic manifest
writes, preview, three-way review, idempotency, and V1 manifest transitions.
Acceptance: target-owned files are never automatically patched; failed work
leaves no claimed success; recovery operates through install/update under their
documented contracts.

**Implemented and locally validated; orchestrator acceptance pending:** US-108
adds exact preview/private-write binding; authenticated install/update/scaffold
planning; managed-file and managed-block mutation; target-owned preservation;
backups, staged images, full-plan recovery commitments, atomic no-replace/
exchange, fsync, and manifest-last commit; read-only recovery status; retained
hard-link witnesses for every `before_sha256=None` create that recovery may
later classify or remove; root-bound journals that commit the pinned repository
`st_dev`/`st_ino` before any copied recovery evidence is trusted; a canonical
public-operation digest that callers can recompute from emitted
`details.operations`; and deterministic rerun/resume/rollback. Recovery now
reapplies the normal monotonic payload rules before commit: release sequence
cannot regress, equal sequence cannot change digest, and the authenticated
release version must remain inside the authoritative compatibility range.
Probe now read-only validates required staged post-images and backups before it
advertises `prepared` or `applying` recovery actions; `rolling-back` remains an
explicit-only state and is intentionally excluded from status probes.
Forty-three focused Phase 3 tests cover all 18 install, 15 update, and 13
committed-update rollback checkpoints, including the gap immediately after
new-manifest removal, plus ownership/race/tamper, hard-link-witness, copied
cross-root replacement journals, fresh manifest/scaffold delete, preview-digest
recomputation from emitted operations, damaged staged/backup probe evidence,
and commit/resume payload-identity and downgrade attacks. `harness-core`
passes 89 tests, the workspace passes 181 tests, and the Phase 3 mechanical
verifier passes 11/11 groups. Rollback
remains deliberately dependent on matching live authenticated release authority
so forged local evidence cannot broaden ownership. Arbitrary same-UID malicious
processes remain out of scope because they can already delete or overwrite the
target directly; the retained hard-link witness plus pinned-root journal
identity closes only the in-scope crash/race/corruption boundary. The live
binary still uses unavailable production release/trust adapters. macOS/Linux
are the proven mutation boundary; other platforms fail closed and remain Phase
7 work. Phase 4 remains closed until this candidate receives fresh exact-hash
acceptance.

### Phase 4: Isolated V0 Bridge

Release the separately versioned reader/bridge with schema 1..=13 fixtures,
export/archive/journal state machine, resume/rollback, kill-point tests, and
mixed-version detection. Acceptance: V0 inputs remain immutable, the bridge is
not in the V1 core grammar, and unknown .harness metadata is preserved.

### Phase 5: Dogfood, Pilot Enrollment, And Baselines

Dogfood the V1 map in Repository Harness's current layout. Enroll at least two
unrelated target repositories, record immutable starting revisions and
eligibility, and run the fixed baseline scenario cards before capability
evaluation. Acceptance: no required path move, no ordinary-task Harness call,
and each enrolled pilot has a signed card set, environment lock, and baseline
or documented inapplicability.

### Phase 6: Capability Evaluation

Instantiate and evaluate the selected planning, invariant, feedback,
capability-improvement, and gardening contracts using the already enrolled
pilots. Acceptance: the fixed release-only cards meet their acceptance tests;
negative conditions fail the candidate rather than being explained away.

### Phase 7: Portability And Release Proof

Prove fresh, brownfield, nested instructions, docs-only, monorepo-shaped,
spaces/Unicode, line-ending, platform, custom-update, and bridge fixtures.
Compare pilot baseline/candidate outcomes under the protocol. Acceptance:
authenticated payload/install/update/audit behavior is equivalent across
supported platforms, no language manifests are interpreted, and release
criteria are met before tag promotion.

### Phase 8: V0 Removal After The Window

No earlier than `2028-01-01T00:00:00Z`, and only after all Decision 0012
support, recovery, security, archive-integrity, asset-retention, and separate
authorization/validation conditions pass, remove V0 operational code and
payload from the default product. Retain the complete bridge release asset set
through `2028-06-30T23:59:59Z`, inclusive, and every repository-owner local
conversion archive indefinitely. Acceptance: fresh V1 installs create no
SQLite database or changesets, the top-level V1 grammar remains the six
permanent commands, no known in-window recovery case remains unresolved, and
retained assets pass availability/integrity verification.

## Pilot Evaluation Protocol

This protocol is release-only evidence. It is not an ordinary-task requirement,
does not create a V1 task database, and does not require target repositories to
collect evaluation telemetry after a release decision.

Each card fixes the target repository, immutable starting revision, candidate
CLI/template/bridge identities, prompt, fixtures, acceptance tests, exact model
identifier, reasoning setting, tool versions, enabled tools, permissions,
evaluator, intervention log, and evidence locations. Baseline and candidate
runs use the same card, evaluator, model/reasoning/tools/permissions, target
revision or documented comparable revision, and acceptance test.

| Card | Scenario | Acceptance test |
| --- | --- | --- |
| P0 | Install or brownfield adoption | Manifest/paths are valid, target-owned content is preserved, and unresolved versus ready status is correctly reported. |
| P1 | V0 conversion, when the pilot has V0 | Export/archive digests, kill-point recovery, and no document move or V0 mutation. |
| P2 | Ordinary small task | Completes with no durable plan created merely for Harness and no Harness core command. |
| P3 | Interrupted complex task | A fresh agent resumes from a target durable plan without human reconstruction. |
| P4 | Native invariant repair | A seeded representative violation fails a named check, an agent repairs it using the output, and the check passes. |
| P5 | Direct feedback repair | From a clean worktree, the agent uses relevant target feedback: tests/compiler, CI/build status, review comments, rendered docs/links, runtime/UI/observability, deployment checks, or reset/recovery. |
| P6 | Capability inheritance | A repeated failure or correction becomes a durable target capability that a held-out agent discovers without the original discussion. |
| P7 | Gardening convergence | First run makes a bounded relevant repair; second run has no repeat drift or unrelated rewrite. |

Interventions use a fixed taxonomy: environment/setup, install, conversion,
instantiation, clarification, evidence relay, correction, conflict review,
authorization/permission, evaluator error, and gardening review. Every event
records actor, timestamp, reason, minutes, and whether it changed the task
outcome.

Total human attention is the sum of minutes and count of interventions for
install, migration, template instantiation, conflict review, corrections,
evidence relay, gardening review, setup, and evaluator work. Report it by card
and as a pilot total; do not claim a time reduction without these components.

Negative conditions fail the release candidate: a missing starting revision or
environment record; changed model/reasoning/tools/permissions without rerun;
an acceptance-test failure; unlogged human evidence relay or correction;
target-tool execution by audit; data loss or an ambiguous state overwritten;
candidate functional regression; a required card not applicable without a
written evaluator finding; or gardening churn outside its bounded scope.

## Verification And Exit Criteria

Deterministic proof covers manifest/role transitions; safe paths; marker
integrity; unresolved versus invalid outcomes; link/index checks; authenticated
payload ledger; mutation boundaries; three-way update; install/update recovery;
V0 bridge exports, archives, journals, kill points, resume/rollback; and
platform-equivalent installers.

Release promotion requires all of the following:

- no mandatory V1 CLI call in the ordinary-task path;
- no SQLite database or semantic changesets from a fresh V1 install;
- a committed V1 manifest sufficient for role mappings, without forbidden
  operational fields;
- authenticated payload index and CI path-ledger proof;
- deterministic audit never executes target tools;
- path-stable V0 conversion with archive/export/recovery proof;
- target-owned adopted/mapped files survive install, update, and recovery;
- all required active roles are ready or the release explicitly remains
  unresolved and is not promoted as ready;
- at least two unrelated enrolled pilots and all applicable fixed cards;
- no functional regression against baseline and a concrete, fully accounted
  human-attention or context/validation-discovery improvement in at least one
  pilot;
- supported platform, upgrade, and candidate-identity checks pass before tag
  promotion.

## Risks, Deferrals, And Authorization

| Risk | Mitigation |
| --- | --- |
| A template becomes generic prose | Require target-native commands, evidence routes, or an explicit unresolved/disabled state. |
| Brownfield or conversion loss | Preview, immutable reader, neutral export, pre-mutation archive, journal, kill points, and reject-and-preserve conflicts. |
| V0 support becomes permanent | Separate bridge identity, Decision 0012's exact window/support scope, and no V1 migrate grammar. |
| Audit grows into an orchestrator | Mechanical no-target-execution and mutation-boundary tests. |
| Pilots hide human labor | Fixed cards, exact environment, intervention taxonomy, and total attention accounting. |
| Dogfood biases a portable core | Unrelated pilots and no language/framework branches in core install/audit. |

Deferred from V1 core: hosted telemetry, cross-user traces, automatic task
classification, semantic context selection, language packs, universal scores,
issue tracking, PR automation, deployment automation, daemon scheduling, and
automatic conversion of unknown tool metadata.

Decision 0012 resolves Gate G0. Decision 0013 and US-106 now supply accepted
Phase 1 security, schema, grammar, inventory, fixture, and enforcement evidence.
That evidence includes strict vetted-library Ed25519 point/scalar rejection,
descriptor-anchored pre/copy/post capture, exact bootstrap/command/release
arrays, and complete-set calendar-month availability receipts. US-107 supplies
accepted Phase 2 evidence for the live six-command core, authenticated payload
boundary, deterministic structural audit, no-target-execution canary, and safe
mutation refusal. US-108 supplies the locally validated Phase 3 candidate and
exact evidence counts above; acceptance is pending. Phases 4-8 remain not
started and depend on preceding accepted evidence. No bridge conversion write,
production key, promoted release, pilot, tag, publish action, or V0 removal is
created or authorized by Phase 3. Phase 8
additionally requires Decision 0012's separate removal authorization and
validation.
