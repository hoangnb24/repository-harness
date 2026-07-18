# Repository Harness V1 Refactor Plan

Date: 2026-07-16

Status: Direction and Phases 1-5 accepted at the authenticated baseline gate;
Phase 6 framework accepted by owner with live efficacy experiments deferred;
Phase 7 engineering in progress with acceptance/promotion blocked; Phase 8 not
started

Planning stories: US-103 and US-104; implementation initiative: US-105;
Phase 2 implementation: US-107; Phase 3 implementation: US-108; Phase 4
implementation: US-109; Phase 5 baseline acceptance: US-110; Phase 6
capability evaluation: US-111; Phase 7 portability/release proof: US-112

Decision 0014 is the current Phase 4 authority. It supersedes the plan's former
automatic conversion/journal design with freeze, archive/export, and normal
fresh V1 install plus an authenticated receipt.

Decision 0015 is the current Phase 6 custody authority. It separates
`cold-clone` from isolated `warm-v0-copy`, fixes pre-candidate capture and
condition-versus-subject identity, and keeps raw runtime/signing material out
of Git.

Decision 0016 accepts the implemented Phase 6 framework for sequencing and
opens Phase 7 engineering. It does not mark the deferred live experiments as
passing: Phase 7 acceptance, release comparison, tag, publish, and promotion
remain blocked until the live P0-P7 obligation and complete Phase 7 proof pass
for the same candidate.

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
  version. V0 evidence capture is a separately versioned, time-bounded bridge,
  not a permanent V1 command; it never converts active operational state.
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

An archive support case opened before `2027-12-31T23:59:59Z` remains eligible
for supported inspection/export and repair. The calendar boundary does not
abandon an unresolved data-loss or archive-integrity case; any such case delays
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
| V0 archive bridge | scripts/bin/harness-v0-migrate or harness-v0-migrate.exe | inspect, export, archive, version | Reads frozen V0 state and publishes neutral export/archive evidence; never mutates V1 targets | Separate release and support window; not installed as the V1 core command. |

No alias maps harness to harness-cli, or harness-cli to a V1 grammar. The
installer may place V1 beside V0 during the compatibility window, but must
print both identities and require explicit archive capture before fresh install.
Shell wrappers may invoke the binary of the same identity only; they may not
translate one grammar into the other.

V1 CLI and template releases use semantic versions. A V1 CLI declares the
minimum and maximum manifest schema and template-release ranges it accepts.
Install/update own forward manifest schema transitions and refuse an
unsupported downgrade. A template release declares its required V1 CLI range.
Status reports the three identities and compatibility decision without changing
state.

Repository modes are `fresh-v1` and `brownfield-v1`; either may carry a
write-once authenticated V0 archive receipt. Receipt presence proves evidence
linkage only. It never claims that V0 operational rows were imported.

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

## Legacy V0 Archive-Only Cutover

Decision 0014 retains a separately versioned, time-bounded,
repository-local `harness-v0-migrate` artifact but supersedes automatic
conversion. Decision 0012 supplies its window/retention policy and Decision
0013 supplies exact capture/trust. The bridge is not a V1 core command.

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

### Export, Archive, And Fresh Install

The bridge produces a neutral versioned export that preserves WAL-only
committed data without making V0 task state part of V1. `archive` captures exact
DB+WAL+SHM, recognized changesets/provenance, standalone backup, and export.
It stages beneath authenticated `.harness-v0-archive` custody and atomically
publishes a unique final directory no-replace. A pre-publication crash leaves no
accepted archive; retry uses fresh unique staging without adopting foreign data.

The bridge never writes `.harness/manifest.json`, `.harness/recovery`, target
documents, or `harness-v1.db`. After archive publication, normal core install
initializes V1 from repository files. Its optional first-install
`--v0-archive-manifest` input binds exact archive/export digests into the
manifest using the existing Phase 3 transaction and recovery behavior.

### Mixed Versions And Downgrade

The bridge verifies V0 schema/changeset compatibility on every live capture.
Archive ownership is authenticated rather than guessed from a pathname.

There is no automatic V1-to-V0 downgrade. To recover, use the immutable
archive in a clean clone with a compatible V0 binary. V1-only manifest schema
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
under the evolved core-live/bridge-live-unpromoted lifecycle.

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
not described as universal syscall/event proof. Phase 4 later adds the isolated
bridge without changing this accepted core boundary; both release workflows
remain source-present and unpromoted. Independent
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

**Implemented, fully validated, and accepted:** US-108
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
7 work. Independent security (`gpt-5.4`, high reasoning) and behavior
(`gpt-5.6-sol`, medium reasoning) reviewers accepted exact candidate `1f957ce`,
integrated as `8e67593` with identical Git tree `9cd22cdb24d2`. Phase 4 is
therefore unblocked but has not started; production promotion and Phase 7
platform claims remain closed.

### Phase 4: Isolated V0 Bridge

Release the separately versioned reader/bridge with schema 1..=13 fixtures,
exact live/archive export, append-only archive publication, receipt recovery,
and ownership/tamper tests. Acceptance: V0 inputs remain immutable, the bridge
never mutates V1, no bridge code enters the six-command core, and unknown
`.harness` metadata is preserved.

**Implemented, fully validated, and accepted:** US-109
adds the separate `harness-v0-migrate` crate and exact four-command binary,
descriptor-anchored read-only capture with SQLite writer quiescence and
DB/WAL/SHM evidence, neutral export, age/X25519 encrypted write-once archives,
unique no-replace custody, and Phase 3 manifest/receipt-last core recovery.
Focused bridge tests and the ten-group
`scripts/verify-v1-phase4-bridge.sh` proof pass on macOS. An independent
reviewer accepted exact candidate `880cb9b`, fast-forwarded to the primary
branch with identical Git tree `0f81d3f0f4c8`. Phase 5 subsequently passed its
authenticated live baseline gate through US-110. Windows safe capture/atomic
publication and promoted five-platform
artifact equivalence remain Phase 7 work; Phase 4 proves the controlled
unsupported exit 5.

### Phase 5: Dogfood, Pilot Enrollment, And Baselines

Dogfood the V1 map in Repository Harness's current layout. Enroll at least two
distinct canonical target repositories, record immutable starting revisions
and eligibility, and run the fixed baseline scenario cards before capability
evaluation. Acceptance: no required path move, no ordinary-task Harness call,
and each enrolled repository has its own repository-scoped authorization ID,
authenticated bundle digest, signed card set, environment lock, and baseline
or documented inapplicability. The same stable owner identity may authorize
both repositories.

**Accepted at the authenticated live baseline gate on exact commit `b2dd775`:**
US-110 maps accepted Phase 4 paths in place, freezes P0-P7, and verifies exact
ordinary argv. Its live command passed all six proof groups and rejected all
42 adversarial cases present at that commit. The corrected current gate rejects
four additional GitHub path/hostname alias attacks, for 46 total. Both offline
SSH Ed25519 signatures verified, both
authenticated bundles resolved their named revisions, and the corrected packet
manifests bind canonical digests while eight annotated P3/P6 artifacts preserve
the earlier source-run legacy digest truth. The independent reviewer who found
the prior digest-reference problem explicitly approved exact `b2dd775` with no
remaining findings; shared-owner alias hardening at exact `c928986` was also
independently approved.

The caller-pinned registry remains outside the candidate repository at SHA-256
`f55a117eb20df727ee21cb922345d62bce3f3afc4458ba5a8b057dc430c9bb6d`,
while tracked `tests/evals/v1-phase5/evidence/trusted-owners.json` remains empty.
The two authenticated packets use the same stable GitHub identity but distinct
repository-scoped owner IDs, canonical repositories, bundles, and external
Ed25519 keys: `harness-benchmark-phase5-pilot` resolves
`090f6d1c33d9f006cc8e95491badc33a8053c89f`, and
`e-inna-brain-phase5-baseline` resolves
`9be2b9b624f29c2c4f93bb576485fd8de2085af4`.

The recorded outcomes are honest pre-candidate measurements, not candidate
improvement evidence. Benchmark P1 is inapplicable and benchmark P6 failed;
e-inna P0, P1, P3, and P6 failed. Those outcomes do not block Phase 5 because
this phase freezes authenticated baselines before candidate evaluation.
Decision 0016 accepts the implemented Phase 6 framework for sequencing, while
live candidate cards remain a deferred efficacy obligation before Phase 7
acceptance or promotion.

### Phase 6: Capability Evaluation

**Status: framework accepted by the repository owner under Decision 0016;
live candidate cards and efficacy acceptance are deferred and still pending.**

Instantiate and evaluate the selected planning, invariant, feedback,
capability-improvement, and gardening contracts using the already enrolled
pilots. Acceptance: the fixed release-only cards meet their acceptance tests;
negative conditions fail the candidate rather than being explained away.

The accepted framework defines bounded agent-map routes, proportional planning,
resume capsules with one exact next action and an ordered validation ladder,
and target-owned invariant, feedback, repeated-correction, and gardening
contracts. Decision 0015 requires externally authenticated pre-candidate
custody: a clean clone for ordinary cards or an isolated V0 copy for applicable
conversion cards. It forbids live database mutation and committing raw
database/archive/key material. None of these documents is a live-card result,
and owner framework acceptance does not convert it into one.

### Phase 7: Portability And Release Proof

**Status: engineering in progress under US-112 and Decision 0016. Phase 7
acceptance, tag, publish, and promotion remain blocked on both the deferred
Phase 6 live evidence and complete Phase 7 proof for the same candidate.**

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
V0 bridge exact exports, append-only archives, fresh-stage retry, and core
receipt recovery; and
platform-equivalent installers.

Release promotion requires all of the following:

- no mandatory V1 CLI call in the ordinary-task path;
- no SQLite database or semantic changesets from a fresh V1 install;
- a committed V1 manifest sufficient for role mappings, without forbidden
  operational fields;
- authenticated payload index and CI path-ledger proof;
- deterministic audit never executes target tools;
- path-stable V0 archive/export with fresh V1 receipt proof;
- target-owned adopted/mapped files survive install, update, and recovery;
- all required active roles are ready or the release explicitly remains
  unresolved and is not promoted as ready;
- at least two enrolled pilots with distinct canonical repositories,
  repository-scoped owner IDs, and authenticated bundle digests, plus all
  applicable fixed cards;
- no functional regression against baseline and a concrete, fully accounted
  human-attention or context/validation-discovery improvement in at least one
  pilot;
- supported platform, upgrade, and candidate-identity checks pass before tag
  promotion.

## Risks, Deferrals, And Authorization

| Risk | Mitigation |
| --- | --- |
| A template becomes generic prose | Require target-native commands, evidence routes, or an explicit unresolved/disabled state. |
| Brownfield or archive loss | Immutable reader, neutral export, authenticated append-only custody, no-replace publication, and Phase 3 receipt recovery. |
| V0 support becomes permanent | Separate bridge identity, Decision 0012's exact window/support scope, and no V1 migrate grammar. |
| Audit grows into an orchestrator | Mechanical no-target-execution and mutation-boundary tests. |
| Pilots hide human labor | Fixed cards, exact environment, intervention taxonomy, and total attention accounting. |
| Dogfood biases a portable core | Distinct pilot repositories and no language/framework branches in core install/audit. |

Deferred from V1 core: hosted telemetry, cross-user traces, automatic task
classification, semantic context selection, language packs, universal scores,
issue tracking, PR automation, deployment automation, daemon scheduling, and
automatic conversion of unknown tool metadata.

Decision 0012 resolves Gate G0. Decision 0014 fixes the archive-only cutover.
Decision 0013 and US-106 now supply accepted
Phase 1 security, schema, grammar, inventory, fixture, and enforcement evidence.
That evidence includes strict vetted-library Ed25519 point/scalar rejection,
descriptor-anchored pre/copy/post capture, exact bootstrap/command/release
arrays, and complete-set calendar-month availability receipts. US-107 supplies
accepted Phase 2 evidence for the live six-command core, authenticated payload
boundary, deterministic structural audit, no-target-execution canary, and safe
mutation refusal. US-108 supplies accepted Phase 3 mutation/recovery evidence
and the exact evidence counts above. US-109 supplies accepted archive-only
Phase 4 evidence. US-110 supplies accepted authenticated Phase 5 baseline
evidence at exact `b2dd775`; this accepts honest baseline custody, not any
candidate improvement. US-111 supplies the implemented Phase 6 framework;
Decision 0016 records owner framework acceptance, defers live efficacy, and
opens US-112 Phase 7 engineering while keeping Phase 7 acceptance and promotion
closed. Phase 8 remains not started.
Primary fast-forward integration and trust-enabled full
premerge passed on exact `b2dd775`; acceptance documentation was integrated at
`3a65768`. No
bridge conversion write,
production key, promoted release, pilot, tag, publish action, or V0 removal is
created or authorized by Phase 3. Phase 8
additionally requires Decision 0012's separate removal authorization and
validation.
