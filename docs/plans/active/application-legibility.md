# Execution Plan: Application Legibility Pilot

Date: 2026-07-21

## Status

Active. The first real-consumer evidence checkpoint is complete; the full
runtime and interface loop is not yet proven.

Phase 1 made the repository-centered workflow authoritative. Phase 2 reduced
the default installation to the ten-file core and explicitly deferred
application-legibility claims. Decision
`docs/decisions/0021-consumer-first-application-legibility-phase.md` defines the
Phase 3 boundary and evidence standard.

The historical plan that used the Phase 3 name for mandatory trace scoring,
friction queries, and backlog operations is preserved at
`docs/compatibility/phase-3-active-observability-legacy.md`. It is compatibility
history, not the default workflow.

## Context

OpenAI's
[Harness engineering: leveraging Codex in an agent-first world](https://openai.com/index/harness-engineering/)
describes an agent environment where repository knowledge, development tools,
application operation, validation, feedback, and recovery are directly
accessible. At higher autonomy, an agent can reproduce a bug, operate the
application, implement a fix, verify through the application, recover from
failures, and escalate only when judgment is required.

That behavior depends on repository-specific structure and tooling. Phase 3
therefore tests one real vertical path and does not claim universal legibility.

## Outcome

Prove that a fresh agent can take one real application task through this loop:

```text
discover how to run the application
-> start an isolated worktree-local instance
-> create deterministic scenario state
-> reproduce through the real user/API interface
-> inspect relevant runtime evidence
-> implement the bounded change
-> run focused executable proof
-> verify through the same interface
-> stop and clean up only that instance
```

A genuine product or operational authority gap stops the run before edits. That
stop is useful evidence, but it proves only the capabilities exercised before
the stop.

## Scope

In scope:

- One real consumer task with authoritative expected behavior.
- Worktree-local runtime isolation, deterministic state, interface-level
  reproduction, runtime evidence, focused proof, and independent cleanup.
- Reusable repository guidance only after consumer evidence proves it reduces
  human intervention.

Out of scope:

- A generic observability platform or application-legibility database.
- Universal start commands, generic browser adapters, or orchestration policy
  installed into every consumer.
- Claims that generalize beyond the observed task, model, revision, and
  environment.

## Approach

Observe one real task without improving its environment, record undocumented
human intervention and missing capabilities, add only the smallest
consumer-owned improvements, replay the frozen task, and retain patterns that
improve the observed outcome.

## Repository Onboarding Skill Pilot

The next experiment tests an explicitly invoked, consumer-owned
`$onboard-repository` skill against `e-inna-brain`. It does not install a hook,
background process, database, generic runtime adapter, or default skill into
every repository.

The consumer baseline is pinned to revision
`9be2b9b624f29c2c4f93bb576485fd8de2085af4`. The original checkout is not an
evaluation subject because it contains pre-existing untracked Harness
artifacts. Baseline, onboarding, and replay runs use separate clean Git
worktrees so their files, processes, ports, logs, and state cannot be confused.

The pilot has two distinct gates:

1. **Inspect and propose:** the skill reads repository authority, maps an
   already-documented operational path, identifies only evidence-backed gaps,
   and stops with suggestions. The worktree diff must remain empty.
2. **Apply after approval:** only an explicitly accepted subset of factual
   repository guidance may be written. Application code and new product policy
   remain out of scope. A rerun of the skill must make no duplicate changes.

A fresh agent then receives the exact frozen operational task in a separate
session. The comparison records undocumented human interventions, unsupported
claims, successful observable steps, and cleanup. Improvement means at least
one baseline intervention is reduced to zero without an unsupported claim;
`0 -> 0` is not evidence for making the skill a default.

Recovery is worktree-local: record the pinned revision and each worktree path,
process identifier, port, writable state path, and log path before execution;
stop only the returned instance; preserve transcripts and diffs; remove a
worktree only after its evidence has been retained.

### Onboarding Pilot Checkpoint: 2026-07-22

Two clean worktrees were created from the pinned consumer revision and received
the same local Harness `0.1.5` ten-file core:

- baseline: `agent/onboarding-baseline-einna` at
  `6ce2aef0867ae3ee09ce426f7bdb6ad93d3191ba`;
- skill: `agent/onboarding-skill-einna` at
  `b06b305952ce9999474b648584aa3affb72524fd`.

The second worktree additionally contains the validated, explicit-only
`.agents/skills/onboard-repository` skill. Its metadata sets
`allow_implicit_invocation: false`.

Herdr agent `onboarding-baseline` received the frozen operational prompt with
no skill. It attempted the obsolete mandatory `scripts/bin/harness-cli query
matrix` command, validated the placeholder Compose configuration, and invoked
the E2E entry point. No application instance started. It reported a missing
Harness binary, absent dependencies, Node 22 instead of the authoritative Node
24 range, absent non-production Google credentials, and an unavailable Docker
daemon. It left the worktree clean.

Herdr agent `onboarding-skill-first-pass` explicitly invoked the skill with
full write capability. It performed inspection only, left both tracked and
untracked state clean, and returned four evidence-backed proposals:

1. replace or guard the nonexistent Harness command in `AGENTS.md`;
2. document the host preflight in `docs/operations/local-compose.md`;
3. document lifecycle, readiness, fixed Compose-project ownership, persistent
   volume behavior, and failure cleanup there;
4. document how to capture structured request logs before teardown.

The first-pass safety gate passed. Application of any proposal is pending
explicit approval. No replay claim is available yet.

Raw Codex session evidence is preserved outside the consumer worktrees:

- baseline session `019f8a9f-7d9e-7bf0-b900-7c9dd0cb81d7`, SHA-256
  `960baa27be2a958663c9203a9b913fb7862a71a328c5941c497276cda4e04b61`;
- first-pass session `019f8a9f-97fc-7c31-8b34-8e9125b6a670`, SHA-256
  `809c10cd7fdc3df30be4258e1f52b0a6d7f705ea9d6158f9c290a27f19284a21`.

### Frozen Replay Protocol

The baseline and later fresh replay receive this exact operational prompt:

> Work in this isolated brownfield worktree. Follow the repository agent
> instructions, then determine how to run the documented default local E2E
> happy path. Without editing repository files or inventing credentials,
> product behavior, or missing policy: attempt every safe step that the
> available prerequisites permit; identify startup and readiness behavior;
> enumerate the real interface assertions; locate instance-local structured
> request-log evidence; and clean up only the instance you started. If a
> prerequisite is unavailable, prove that from repository or environment
> evidence and stop safely. Report commands attempted, observable results, any
> undocumented human intervention required, and the final Git status.

Score both runs against the same evidence definitions:

| Measure | Count or pass condition |
| --- | --- |
| Obsolete onboarding commands | Repository-directed commands attempted that cannot exist in the prepared worktree |
| Undocumented human interventions | Missing explanations, credentials, environment changes, or choices that require a person before the next safe step |
| Preflight completeness | Node, package manager, dependencies, Docker client/daemon, required untracked environment, and credential availability are checked before startup |
| Ownership accuracy | Agent identifies the fixed Compose project, ports, persistent volume, state mutation, and whether it owns any instance before cleanup |
| Runtime-evidence accuracy | Agent distinguishes script assertions from captured container logs and gives the instance-specific retrieval boundary |
| Unsupported claims | Normative or operational claims without authoritative or observed repository evidence; target is zero |
| Repository mutation | Tracked, staged, or untracked state added by the run; target is zero |
| Cleanup safety | No cleanup of a pre-existing or unowned instance; any started instance is stopped within its recorded boundary |

The causal comparison is valid only with a new agent session, the same model
and reasoning effort, the same host environment, no baseline transcript in
context, and a replay worktree derived from the approved documentation commit.
The skill itself is not installed in the replay worktree: the replay measures
whether its approved repository backfill helps an ordinary fresh agent.

### Independent Audit And Skill Revision

Herdr agent `onboarding-advisor` (`gpt-5.6-sol`, maximum reasoning) audited the
raw baseline and first-pass Codex sessions, the consumer sources, the skill,
and current official Codex documentation. It confirmed the no-mutation gate,
but rejected approval by proposal number because several items mixed
authoritative, observed, derived, and new normative statements.

The audit requires proposal 1 to replace only the stale managed Harness block
with the checksum-verified `.harness-core/base/AGENTS.md` block. A
missing-binary guard would preserve an obsolete compatibility workflow. It
also narrowed the other proposals: local dependency installation is not yet an
authoritative local procedure; current runner cleanup behavior must not be
presented as durable policy; Compose logs are project/container-bound and need
correlation identifiers rather than an unsupported `instance-local` label.

The skill was revised and committed at
`562175c` on `agent/onboarding-skill-einna`. It now:

- reconciles managed-file provenance without overriding active instructions;
- checks repository-local binary existence before invocation;
- distinguishes authoritative, observed, derived, decision-required, and
  unknown claims;
- requires classification and sources for every proposed sentence;
- requires an exact patch preview and sentence-level approval;
- snapshots relevant ignored state and runtime ownership;
- preserves consumer-owned content outside managed markers; and
- emits a documentation-only replay patch applicable to the baseline commit,
  excluding the skill itself.

The revised skill still requires a fresh read-only proposal run before any
consumer documentation can be approved or applied.

Herdr agent `onboarding-skill-second-pass` tested revision `562175c` in a new
session. It left Git and relevant ignored state unchanged, checked the absent
Harness binary without invoking it, and returned a sentence-level classified
patch. Those two revised behaviors passed. Proposal quality did not: it omitted
the checksum-verified stale root instruction, selected a generic future-command
document instead of the existing operations guide, and included an `Unknown`
sentence in the proposed documentation.

The skill was tightened again at `a4732a4`. Active mandatory instruction drift
that caused a failed or unsafe command is now the first proposal priority.
Proposal ordering is causal: correct active guidance, link existing authority,
add narrowly missing current mechanics, then request any new normative
decision. The skill must use the document that already owns the procedure and
must keep `Unknown` claims out of patch previews.

Two further forward tests exposed and corrected narrower evidence defects. The
third pass overclaimed optional log-schema fields; revision `ce25148` now
requires required/optional field distinctions. The fourth pass created and
then removed two external temporary comparison files and treated the frozen
task as durable cleanup authority; revision `d8bf6c4` prohibits temporary files
and states that an evaluation prompt is run scope, not repository policy.

Herdr agent `onboarding-skill-final-pass` tested `d8bf6c4` in a fresh session.
It made no repository, ignored-state, temporary-file, service, volume, or
Harness-state mutation; did not invoke the absent CLI; selected the stale
managed block before additive documentation; used
`docs/operations/local-compose.md`; preserved optional log-field semantics; and
kept ownership-safe failure cleanup as `Decision required` with no proposed
text. The skill remains valid under `quick_validate.py`.

The sentence-level audit exposed one final overgeneralization: the runner
hard-codes `conversationId`, while only `instanceId` has environment
fallbacks. Revision `1d60bfa` now requires every clause and qualifier in a
proposal to be verified independently and explicitly prohibits generalizing
configurability from one field to a nearby field. The skill remains valid under
`quick_validate.py` after that revision.

Final first-pass session:
`019f8abb-3181-7d21-a7c3-066042fea6e6`, SHA-256
`9ccb434108e32b40c80a088b8788e70ddc163b9775083d720d8af3fb58812eec`.

The approvable patch is now limited to:

1. the exact checksum-verified Harness marker replacement in `AGENTS.md`; and
2. exact observed/derived readiness, failed-run behavior, and structured-log
   guidance in `docs/operations/local-compose.md`.

No ownership-safe cleanup policy is proposed. Application, idempotence rerun,
baseline-derived skill-free replay, and measured comparison remain pending
explicit wording-level approval.

### Independent Measurement Audit

Herdr agent `onboarding-measurement-auditor` (`gpt-5.6-sol`, maximum
reasoning) scored the raw sessions against the frozen rubric. Its session is
`019f8ac1-3e84-70b1-a18f-14c38cd3005f`, SHA-256
`45c90dd88d33738fd4ec86b5d58770f54b982372a76659b3ad2ec0528af2d7dc`.

The baseline score was:

| Measure | Score |
| --- | --- |
| Obsolete onboarding commands | `1` — fail |
| Undocumented human interventions | `5` proven plus unknown credential availability — fail |
| Preflight completeness | `5/6` — fail |
| Ownership accuracy | `2/5` — fail |
| Runtime-evidence accuracy | `1/2` — fail |
| Unsupported claims | `4` — fail |
| Repository mutation | `0` — pass |
| Cleanup safety | pass; no instance started |

The final skill reconnaissance scored `4/5` and failed its all-or-nothing
proposal gate. It read authority, mapped the workflow, stopped without applying
anything, and left the worktree clean, but incorrectly said both default
request identifiers were environment-overridable. The exact pending patch
below has been reissued with the corrected two-sentence description.

No causal improvement may be claimed yet: the baseline and skill sessions used
different task wrappers, and the skill itself could have caused the better
inspection behavior. The skill-free replay must use the exact frozen prompt in
a fresh session and pass all of these pre-registered thresholds:

- no obsolete command attempts;
- reduce the stale-CLI intervention from `1` to `0` and keep total proven
  interventions at or below `4`;
- complete all six preflight checks before any state-changing command;
- report all five ownership facts;
- distinguish source assertions from actually captured logs and identify the
  project, service, and request-correlation boundary;
- make zero unsupported claims and preserve optional-field semantics;
- make zero repository changes; and
- avoid cleanup of any unowned instance and stop every owned instance.

The replay is invalid unless it also uses the clean baseline-derived worktree,
the same model and reasoning effort, no previous transcript, no skill, and a
contemporaneous prerequisite presence-state snapshot. At least one nonzero
baseline intervention must become zero; unchanged `0 -> 0` safety scores do not
establish improvement.

### Context-Specific Evidence Forward Test

A fresh Herdr-controlled forward test of skill revision `1d60bfa` used session
`019f8acc-4896-76a2-a353-5b188d620f61`, SHA-256
`623b47bd7126651f47086a2facad1c93f9e3d97cc356cf91e3848cbcc9a5d3ed`.
It correctly distinguished the fixed `conversationId` from configurable
`instanceId` sources and made no Git changes or service-control calls.

Independent Herdr auditor session `019f8ad1-52f8-7bb2-a38d-997efafc4768`,
SHA-256
`1eb7871c5986fb5a59abc858ab75e73edb7706109e19911d10dc96ecdd7111e8`,
scored the run `2/5` and rejected the additive local-E2E proposal. Concrete
failures were:

- a CI-only `pnpm install --frozen-lockfile` command was promoted into local
  runbook guidance;
- environment precedence was summarized across keys instead of traced per key;
- default, `--no-up`, successful `--down`, and failed-check cleanup branches
  were collapsed into inaccurate lifecycle statements;
- the operational-path table omitted ownership, writable state, ports,
  logs/correlation, and failure cleanup; and
- missing initial ignored/runtime/temp baselines were reported as unchanged
  instead of **Unknown**.

The managed `AGENTS.md` marker replacement remained independently approvable.
The skill was revised at `69b4111` to require same-context command authority,
per-key environment tracing, lifecycle branch analysis, a complete required-
column path table, and true initial/final state baselines. It validates under
`quick_validate.py`. A fresh context-neutral forward test of this revision is
required before the skill gate can pass.

That context-neutral test used session
`019f8ad7-191c-73c0-aafa-81c1b417bf7e`, SHA-256
`ec7077ac6ef8bb6c327d810208ce9cd8c63632ba491ab9f631bef9d48455d5e8`.
Independent auditor session `019f8adc-230e-7fb3-8708-29e5e6be599b`, SHA-256
`e9d48cb002c17cfa748dc74f8402f69e0bce0c3b2d5a3e07de9bb80a333f23dd`,
scored it `3/5`. Authority, full-path mapping, and suggestion-only behavior
passed. Clause accuracy and strict no-mutation proof failed because the run:

- generalized fixed and configurable identifiers;
- described a configurable port as fixed;
- placed webhook writes in the schema/readiness stage;
- mixed an authorized Compose mechanism with a new cleanup obligation;
- omitted `harness.db*` from the initial ignored-state baseline;
- hashed managed filenames rather than contents; and
- called the no-mutation gate passed despite required runtime state being
  **Unknown**.

Revision `8d96033` adds explicit ignored-path discovery, content-sensitive
managed-state baselines, per-identifier and per-port classification, stage-
accurate writes, separation of cleanup mechanics from cleanup obligations, and
conjunctive gate scoring. The skill validates under `quick_validate.py`. Its
next neutral forward test must be scored for output correctness separately from
an environment-caused `Unknown` runtime gate.

The next neutral run used session `019f8ae1-d109-7932-a17b-b16a74d1ac8d`,
SHA-256
`9589579adadb632952a72058907ad1e48eda0261083e842bb648beea3a833368`.
It correctly kept the Docker runtime comparison **Unknown**, failed the
conjunctive no-mutation gate, avoided an invented cleanup obligation, and
produced two independently approvable patches: the managed marker replacement
and factual lifecycle wording.

Independent auditor session `019f8ae6-c738-7471-862e-fcc20e31e516`, SHA-256
`cc77cc6d2e1ab79baac703cd32662d5a667c0e19b10d8c0daf3cc3ea27e2341f`,
nevertheless scored the result vector `[Pass, Fail, Fail, Pass, Fail]`. The
remaining defects were report completeness rather than patch wording: merged
table columns obscured per-row owner/port/log/cleanup values, `--no-up` was not
a separate branch, host/container ports and logical/runtime volume identity
were collapsed, identifiers were not individually classified, and the
lifecycle citation ledger did not cover every control-flow clause.

Revision `dde06df` replaces the flexible map with a fixed nine-column path
schema, requires a separate resource-and-identifier ledger, makes every
lifecycle flag a row, distinguishes logical from observed runtime names, and
requires all six proposal fields plus complete branch citations. It validates
under `quick_validate.py`. Both patches remain unapplied pending exact user
approval; this revision still needs a fresh neutral forward test.

The ledger forward test used session `019f8aeb-9b20-7610-95c1-216615c38b9f`,
SHA-256
`77926704a1d65b632cc4db89dcedef95165fb49235402a8d72a1b7df44934bda`.
The first independent audit attempt, session
`019f8af2-202f-7680-bbf7-6894ada84b0f`, ended in a model transport disconnect
and produced no verdict. Retry session `019f8af3-3d55-75b1-91e8-1d4ac77844ed`,
SHA-256
`a0de2e7dd4f59d5186154cf4f2413fd844d03018edc6d7e00b801bc49cb9ffc4`,
scored `[Pass, Fail, Fail, Pass, Fail]`.

The ledger shape, lifecycle rows, ports, logical volume distinction, six
proposal fields, and conservative runtime **Unknown** all improved. Remaining
failures were narrower:

- a zsh loop assigned to special variable `path` and invalidated the initial
  Docker/PATH baseline;
- two fixed identifiers shared one ledger row and checked-in fallback
  reachability was omitted;
- optional log identity/warning fields were presented as universal;
- process-wide metrics were grouped with instance-correlatable evidence;
- some database/provider/runtime effects lacked their full causal source chain;
  and
- `does not invoke down` was overclaimed as `leaves resources running`.

The auditor approved the managed marker patch and rejected the displayed
lifecycle patch only for that last overclaim. Revision `ecd0f60` now prohibits
shell special-variable reuse, separates every ledger item and optional field,
requires full causal chains and stage-accurate classifications, renames the
evidence stage around correlation boundaries, narrows negative lifecycle
wording, and adds a final contradiction scan. It validates under
`quick_validate.py` and is cleanly committed.

### Independent Audit Skill

The neutral test of `ecd0f60` used session
`019f8cbf-c1bf-71e2-a412-3a70b18d45c7`, SHA-256
`bb3b6cfbaa44303f2446dda9bca71e396bab9cefd8322003db4ae98c35c5fa20`.
It fixed the shell-baseline bug and several correlation/lifecycle claims, but
independent auditor session `019f8cc5-30f5-7b52-bc6e-7c2d07567795`, SHA-256
`8cef031a91e85ce5da3ee75f098f16ff7c107d047c60716c7dadc3b12f382620`,
still scored `[Pass, Fail, Fail, Pass, Fail]`. The emitted proposal omitted
identifiers and causal rows, dropped the managed `## Harness` heading, and
stated conditional webhook reachability as unconditional.

This repeated pattern changed the design: the producer skill no longer serves
as its own final authority. A second explicit-only
`$audit-onboarding-proposal` skill independently authenticates raw transcripts,
reconstructs tool evidence, scores the five gates, and gives sentence/hunk-level
`APPLY`, `NO APPLY`, or `SPLIT AND REISSUE` decisions. It was created at
`f741671` and forward-tested on the same raw producer session without receiving
the known defects.

Audit-skill session `019f8ccf-0f02-7b11-985a-32e0fe3a4d36`, SHA-256
`1fc9d8799a59c0a80931d52109305189873f3c9d2288133a36c5607670e35615`,
independently reproduced the `2/5` vector, rejected the missing-heading hunk,
approved the factual prerequisite hunk, and split the conditional lifecycle
hunk. The audit itself exposed two gaps: it attempted the stale binary before
checking existence and accepted incomplete ignored-state coverage. Revision
`00840bd` now treats tested operational instructions as evidence rather than
commands, guards repository-local binaries, and independently expands root and
nested ignore patterns before accepting a producer's no-mutation score. Both
skills pass `quick_validate.py` and the skill worktree is clean.

A boundary-focused forward test of `00840bd` used session
`019f8cd5-a410-7401-a1d8-5b0c913139bb`, SHA-256
`a9b28992a5a7cc4844d0eedea1457a1677a35b78fccab98ebb60a89cfb4c7e80`.
It correctly guarded the absent repository-local CLI and found the ignored
`.DS_Store` and nested `.harness-core/.gitignore` baseline, but it failed to
notice the missing managed heading and the conditional lifecycle wording that
the prior independent audits rejected. Therefore one audit result is not an
application gate. At least two fresh independent audits must agree, and only
the intersection of their sentence- or hunk-level `APPLY` decisions may enter
an approval bundle. Any disagreement remains `NO APPLY` until the producer
reissues a corrected proposal and the audits agree.

Revision `57ece5e` converted the structural and conditional checks into a
mandatory per-hunk Patch Verification Worksheet plus a separate fail-closed
counterexample pass. Two fresh GPT-5.6 Sol, maximum-reasoning Herdr audits of
the same authenticated producer transcript then converged exactly:

- session `019f8cde-89b7-7490-a21a-c3365ca58e8b`, SHA-256
  `d8bbe2a17df10e0cfd18f08159d1fe231a8a54d296f132a27f82202778a34c32`;
- session `019f8cde-89b3-7d31-a1c2-4a5af13b0944`, SHA-256
  `07b6bc91e38aeb808ba69873d74942cf5e4fd2273487a593d9b4fbbd61e9e34d`.

Both scored the producer `[Fail, Fail, Fail, Pass, Fail]`, rejected the
heading-less managed-marker hunk, approved the prerequisite hunk and the
narrow `--no-up` introductory replacement, and rejected or split the lifecycle
paragraph because its deletion boundary did not match and its insert claim was
conditional. This is the first exact two-reviewer convergence for the audit
skill. The full audits took approximately eleven and twelve minutes because
each reconstructed the large exploratory transcript.

Revision `9fbd52e` therefore added corrected-reissue mode: authenticate the
original evidence but verify only one exact corrected hunk without rescoring
unrelated producer output. Two more fresh GPT-5.6 Sol, maximum-reasoning Herdr
sessions audited the exact pending managed marker below:

- session `019f8cea-aae9-7ce3-bdf5-ff51cca2939b`, SHA-256
  `e07e5b7828efff3a9f0b8fb6eb19743ac5c132d5f6f3e62411ae61f7aff011f9`;
- session `019f8cea-aae0-7912-b5fa-2e967d3ff6ac`, SHA-256
  `e47e7ed451342882a1490da1b40ac6dd09d7309da6c038f72aafde3a996ea501`.

Both returned `REISSUE_APPLY`, proved the 30-line, 1,592-byte proposed marker
equal to the checksum-verified canonical marker, preserved the four-line
consumer prefix, found no counterexample, ended with `AUDIT_COMPLETE`, and
left the worktree clean. The exact marker now satisfies the two-audit
intersection rule. It remains unapplied until explicit user approval.

The producer remains useful for discovery, but only independently audited
sentences may enter the pending approval bundle. Further consumer mutation and
skill-free replay still require the exact user approval below.

### Executable Evidence Capsule Forward Test

Revision `0a1db2c` added an explicit `onboarding-evidence-capsule/v1` contract.
The producer now labels each proposed diff hunk and emits a JSON capsule that
binds transcript identity, tested revision, source ranges, claims, boundary
snapshots, patch hashes, and no-mutation observations. The auditor includes a
standard-library validator that fails closed on malformed structure, broken
references, hash mismatches, or missing marked hunks.

Fresh producer session `019f8cf8-1db9-77e3-9f52-1a315d7e0d5d`, SHA-256
`05969af85178d03ec30c81bc1dd14d614a04a0ae1ec6f2e5c27ccf88b8213d2f`,
ran for 14m53.033s. The validator accepted its capsule on the first attempt,
in approximately 1.2 seconds, and authenticated 24 claims, four boundaries,
and two marked patch hunks. The skill, replay, and original consumer worktrees
remained unchanged apart from pre-existing ignored or untracked state.

Two independent GPT-5.6 Sol maximum-reasoning audits then used the capsule as
their index:

- session `019f8d06-3f0d-7e42-b89d-8b5bfa0d6221`, SHA-256
  `489eb116ba1682c6d1c01fb7e150212876379b669f857e9efd90a460f4971ec4`,
  ran for approximately 13m14s, scored the producer `2/5`, approved H1, and
  rejected H2 because its producer evidence chain was incomplete;
- session `019f8d06-3f0d-7ff0-817e-f5d3c1932e3c`, SHA-256
  `f19ebe980712afc8660f8fe0b6d106c87c35f08a4f6b34a221c7b4dd6ac79dc0`,
  ran for approximately 12m31s, also scored the producer `2/5` and approved
  both exact documentation hunks after independently completing H2's missing
  source trace.

Both audits agreed that the producer's `5/5` self-score was unsound. It omitted
ignored-state baselines, overstated runtime-equivalence evidence, left
operational ledger rows and downstream tracing incomplete, and misstated
always-present HTTP log fields as optional. The capsule made evidence identity
and referential integrity cheap to verify, but did not reduce exhaustive audit
time: source semantics, operational completeness, and no-mutation coverage
still required repository inspection.

This measurement splits two concerns that the original audit combined:

1. **Patch admissibility:** validate the capsule, then check only the exact
   hunk, its cited source ranges, destination boundary, atomic claims, and
   counterexamples. This is the narrow gate for a proposed edit.
2. **Onboarding quality:** independently rescore discovery completeness,
   operational claims, and the component no-mutation vector. This remains a
   slower diagnostic and must not be represented as cheap patch validation.

The protocol is therefore useful as an executable evidence envelope, not as a
replacement for semantic review. No capsule authorizes consumer mutation.

Revision `9727097` implemented the split as an explicit
`patch-admissibility` audit mode. It requires requested hunk IDs, validates the
capsule, runs the full worksheet and counterexample pass only for those hunks,
does not recompute producer gates, and emits separate `PATCH_APPLY` or
`PATCH_NO_APPLY` decisions.

A blind GPT-5.6 Sol maximum-reasoning Herdr forward test used session
`019f8d15-5ab7-7e00-92ba-7fa1eb10106b`, SHA-256
`03f4a5f2f05cde0b6ef56bfaff6fb4386029c47b6ca014aef18289f13c065cac`.
It authenticated the same producer capsule, returned `PATCH_APPLY` for H1 and
`PATCH_NO_APPLY` for H2, and ended with
`PATCH_ADMISSIBILITY_COMPLETE`. Observable audit work was 567.617 seconds;
the complete session was approximately 10m39s. This is only a modest reduction
from the 12–13 minute full audits because H2 itself requires deep lifecycle and
migration inspection.

The narrow audit found a stronger H2 counterexample that the full audits did
not converge on: `ensureDatabaseSchema()` probes only
`processed_webhook_events`, while the migration creates several operational
tables. If the sentinel exists and another table is absent, the function
returns without applying the migration. Therefore `checks for the operational
schema` overstates a one-table sentinel check. Revision `c68be3f` feeds this
failure back into both skills: producers must not promote partial probes into
aggregate completeness, and auditors must test that exact counterexample.

A fresh GPT-5.6 Terra high-reasoning producer replay at `c68be3f` used session
`019f8d20-cc32-7ef2-bc7e-beafa0ee0f20`, SHA-256
`f632844cacc7370c27615c6106cbb71ac838ad576c8674f02c17525c1b10c9b1`.
It completed in approximately 10m50s, versus 14m53s for the prior producer,
and its capsule validated on the first attempt with 34 claims and two hunks.
It correctly scored `[Pass, Pass, Pass, Pass, Fail]`: Git and task-temporary
state passed, while incomplete ignored-state baseline and denied Docker access
made conjunctive no-mutation proof fail. It named the exact sentinel condition
and did not repeat the aggregate-schema claim. No tracked file changed.

The new mode's per-hunk scaling was then measured with H2 only. Fresh GPT-5.6
Sol maximum-reasoning session `019f8d2b-beff-7842-9fa2-c0a13811619a`,
SHA-256
`ea5c8c3e19ad275c17559a01d78a68f3815f18668e49f1bacb5908c842831cb9`,
validated the capsule in 1.28s and completed its semantic audit in 221 seconds
(4m58s full session). It returned `PATCH_NO_APPLY`: the proposed heading said
teardown happens `after a successful run`, but teardown executes before the
final success log and can itself fail; the capsule also omitted the flag,
package-script, and spawn links needed for the full causal chain. Revision
`f81e79b` now requires exact temporal-signal ordering and complete command-to-
effect source chains inside each capsule claim.

A fresh GPT-5.6 Terra high-reasoning producer replay at `f81e79b` used session
`019f8d32-a4ff-7b63-aafc-be8390e1e9c5`, SHA-256
`024b4052f707c0d4d34b10b0b2a9fbe0a3f305460bdcbd23e599bc7878b35337`.
It completed in approximately 9m45s, returned a structurally valid v1 capsule,
kept the conservative no-mutation gate failed, and corrected the teardown
sentence to describe the actual awaited ordering. During inspection it also
attempted a shell heredoc that the read-only sandbox rejected. Revision
`413abcb` therefore prohibits heredocs and here-strings and introduces
`onboarding-evidence-capsule/v2`.

The H3-only GPT-5.6 Terra maximum-reasoning audit used session
`019f8d3d-1998-7ce3-86b6-f39ef4f38995`, SHA-256
`9e94da8e881f00f322a25b1a76ad72f698d13a67ab8208e2c49d5ed9fe77418e`.
It completed 403.820 seconds of semantic work in an approximately 8m49s
session and returned `PATCH_NO_APPLY`. The temporal wording was supportable,
but the displayed patch was not bound to the exact pinned destination
preimage, and the claim still omitted the complete package-entry, flag,
`run()`, spawn, and failure-handler chain.

V2 replaces subsection hashes with complete destination-file hashes before and
after in-memory patch application. Its repository-aware validator now
authenticates the producer skill blob, every pinned source range, the displayed
patch bytes, exact patch applicability, and the complete resulting destination
bytes. The legacy v1 route remains readable for preserved transcripts.
Self-tests, both skill validators, a synthetic v2 fixture, and the preserved v1
transcript passed at revision `413abcb`.

The first neutral v2 producer forward test used GPT-5.6 Terra high reasoning,
session `019f8d4a-1ece-7132-97a9-d63accdbf7d9`, and transcript SHA-256
`9bc48a7d0a68e46f3ab42d7b7d8aa5ec5543dd898161d7bac900671cf21b5f22`.
It ran for 11m34s, remained read-only, avoided heredocs, and conservatively
reported ignored, runtime, and temporary-path limitations. V2 validation
correctly rejected H1 at destination line 3: the hand-authored diff omitted
the existing consumer-owned `Add project-specific agent instructions here.`
line even though its claimed whole-file before hash covered that line. No
consumer file changed.

Revision `d538675` feeds that failure back into the producer. A bundled
read-only renderer now receives the complete proposed destination image,
reads the pinned preimage through Git, and emits the exact unified diff plus
whole-file before/after and patch hashes. The skill prohibits manually authored
diff context, line ranges, and hashes. Its pure self-test, a real managed-marker
render against the pinned consumer, `git apply --check`, both skill validators,
and `git diff --check` pass.

The fresh renderer forward test used GPT-5.6 Terra high reasoning in Herdr
session `019f8d57-9b24-7573-8a0a-f91d027b1531`. Its first final answer
completed in 9m44s. Both H1 and H2 came from the renderer and reconstructed
against the complete pinned files, but the producer mistyped one hexadecimal
character while copying the first source-range digest into the capsule. The
validator rejected that transcript. Replacing only that value in memory made
all checks pass, so the exact validator error was returned to the same agent.
Its corrected reissue completed at 12:14:29+0700; the complete transcript
SHA-256 is
`cc56d8e327184445fbb0b6e1d9254db64caffe097ebe092dcc62fab0d5369683`.

Repository-aware validation of the corrected last answer passed with 25
claims, four boundary rows, and two exact patches:

- H1 patch SHA-256
  `d939dc0aa5b8310f272507771580fece069f262465301db7465268c4c06939af`;
- H2 patch SHA-256
  `a804bdc395b5e47663b474070e1fc007f61c84e7b9f3f456e6806ace0ba7661a`;
- capsule SHA-256
  `afd38c7d162e6be96159feca85d8e9598fa042093199a8663e5feaf9ff298f57`.

The worktree remained clean. This proves that renderer-generated patches fix
the complete-preimage defect. It also identifies the next efficiency target:
generate the final capsule JSON as machine output so a copied digest cannot
force a 33 KB answer to be streamed twice.

A fresh GPT-5.6 Sol maximum-reasoning patch-admissibility audit then used
session `019f8d66-11b0-71b0-b970-a1a80e42874b`, SHA-256
`69520861717585223a279031cc0c0b5f9b8d749fb3609d4107d758e4bfc9e044`.
It completed in approximately 6m53s, independently reran v2 validation,
reconstructed both full destinations, completed the clause worksheet and
counterexample pass, and left the worktree clean.

The audit returned `PATCH_APPLY` for H1. Its complete proposed managed marker is
byte-for-byte equal to the checksum-pinned canonical marker and preserves the
consumer-owned prefix. It returned `PATCH_NO_APPLY` for H2: the heading
`To request teardown after a passing run` is false because Compose `down` is
awaited before the `Local E2E passed` signal and can itself reject. H2 remains
excluded. The previously approved exact H1 marker remains the only current
approval candidate; v2 validation and this additional audit do not grant
permission to apply it.

Revision `bce48d8` removes the measured model-copy boundary. A deterministic
emitter accepts only unhashed source descriptors, complete proposed destination
images, boundary observations, and limitations. It reads pinned blobs, renders
patches, computes every producer/source/patch/destination digest, and writes one
outer authenticated bundle directly to tool output. The transcript validator
selects the last complete bundle emitted before task completion and verifies
its outer digest before the existing v2 checks. Legacy v1 and final-message v2
transcripts remain valid.

The emitter self-test, validator self-test, both skill validators, a
non-materializing real-repository emitter-to-validator pipeline, a synthetic
raw-JSONL tool-output route, the preserved v1 transcript, and the prior v2
transcript all passed. The fresh GPT-5.6 Terra high-reasoning producer forward
test used Herdr session `019f8d74-627d-7dd1-be27-92e8c7258dc7`, transcript
SHA-256
`ad3d3e84cfd2509a20089b14eeb6d9d3d8c3a399ac21e94d436064a19dd36791`.
It completed in 7m06s, versus 9m44s before the failed copied capsule and 15m13s
including correction. The assistant answer shrank from 33,552 to 10,897
characters and contained no capsule copy.

Validation passed on the first attempt with
`evidence_source=machine_tool_output`, 27 claims, four boundary rows, and two
hunks:

- outer bundle SHA-256
  `9b854edf385285c39c013c781fc28cfa94b3139aa56ffe2209a274561886923e`;
- capsule SHA-256
  `24cf822fdaf9c25a715e737c6ae220bdc2520908ff93b94133fa9a8a2b0a139c`;
- unchanged H1 patch SHA-256
  `d939dc0aa5b8310f272507771580fece069f262465301db7465268c4c06939af`;
- reissued H2 patch SHA-256
  `2c9b2ab223de3b49b55b5a113576a22f5fab6a29ff3f8211cd4bb44bb41aba64`.

The producer and original consumer worktrees remained unchanged. This proves
the machine transport eliminates the observed transcription/reissue failure;
it does not make the semantic claims self-authenticating.

A fresh GPT-5.6 Sol maximum-reasoning H2-only audit used session
`019f8d7b-b8a9-7c40-a04f-b78af7d9bb2d`, SHA-256
`7c052c93eda3c14ba5586d18c63f4811fad970f628ed86e7e1d4a1fe97c611c6`.
It completed in approximately 7m07s, authenticated the machine bundle, and
returned `PATCH_NO_APPLY`. The revised wording matches the implementation, but
the capsule is not admissible: C24 names the exact migration file without
citing its definition or the call ordering that reaches schema setup, while
C26 omits the subprocess/assertion implementations needed to prove rejection
propagation. Both claims also combine several independently provable effects.

Revision `cef9ec1` feeds that result back into the producer. It requires one
subject-condition-effect fact per claim, exact-value definition plus use, and
the awaited call, rejecting/throwing implementation, and top-level handler for
failure-bypasses-later-work claims. H2 remains excluded. H1 remains the only
current approval candidate.

#### Deferred Additive Candidates

The two fresh full audits agreed that the prerequisite hunk and narrow
`--no-up` introductory replacement were independently safe. They remain
excluded from the current approval bundle because neither is required to test
whether removing the stale mandatory CLI reduces the frozen baseline
intervention. The larger lifecycle paragraph still failed structural and
conditional-claim review, and the capsule-backed narrow audit additionally
rejected its aggregate schema wording. No readiness, teardown, log-correlation, or
request-identifier sentence will be applied until a reissued patch receives
two matching independent audit decisions and a later experiment requires it.

#### Pending Exact Wording Approval

Patch 1 replaces only the text inside `AGENTS.md`'s `HARNESS:BEGIN` and
`HARNESS:END` markers with the exact marker block from
`.harness-core/base/AGENTS.md`. The full source file has SHA-256
`07dcdd653335d02bd49e1371d2ecc9f3d89250fcc5041c8ad01f8bba543e17a9`;
the extracted marker block has SHA-256
`6b179ecd58b910d8e8a5b32601cb98f7bcca881ad00d896332bb7a7582068562`.
Consumer-owned text outside the markers is preserved. The resulting marker is:

```markdown
<!-- HARNESS:BEGIN -->
## Harness

Start with the requested outcome, then use the repository as the system of
record. Read `docs/WORKFLOW.md` and only the product, design, plan,
code, and validation material relevant to the task.

- Answers, explanations, reviews, diagnoses, plans, and status reports are
  read-only. Inspect only what is needed and do not mutate repository or Harness
  state.
- For a bounded change, use an ephemeral plan: inspect the affected behavior and
  existing proof, implement the change, and run behavior-appropriate validation.
  No control-plane operation is required.
- Create or update one file under `docs/plans/active/` when work spans sessions,
  needs coordination or an ordered sequence, has meaningful dependencies, or
  requires explicit recovery steps. Move it to `docs/plans/completed/` only
  after validation.
- Before editing, identify repository authority for each new externally
  observable policy. If materially different choices remain open, stop before
  edits; configurable defaults are not authority.
- Also pause when product intent remains ambiguous, an action is difficult to
  recover, validation would be weakened, or the request does not authorize the
  needed action.
- Claim completion only with relevant executable or observable evidence. Report
  the outcome, important changed surfaces, validation, and unresolved risks.

SQLite intake, story, trace, scoring, audit, and proposal commands are optional
compatibility features. Use them only when explicitly requested or required by
an external orchestrator.
<!-- HARNESS:END -->
```

Approval phrase:

> I approve exactly the displayed managed `AGENTS.md` marker replacement in
> the Pending Exact Wording Approval section and no other change.

#### Replay Worktree Prepared

The skill-free replay worktree now exists at
`/Users/tubakhuym/.herdr/worktrees/e-inna-brain/agent-onboarding-replay-einna`
on branch `agent/onboarding-replay-einna`, pinned to baseline commit
`6ce2aef0867ae3ee09ce426f7bdb6ad93d3191ba`. It is clean, contains the ten-file
core, and does not contain `.agents/skills/onboard-repository`.

The replay environment snapshot before any approved patch is Node `v22.22.3`,
pnpm `10.30.1`, Docker `29.4.3`, and Docker Compose `v5.1.3`. Application of the
approved managed-marker patch will be the only tree difference from the
baseline.

### Approved H1 Application And Skill-Free Replay

On 2026-07-23 the user approved the H1 `AGENTS.md` marker replacement and no
other change. A Herdr-controlled agent replaced only the bytes from
`<!-- HARNESS:BEGIN -->` through `<!-- HARNESS:END -->`. Independent checks
proved:

- the managed marker SHA-256 is
  `6b179ecd58b910d8e8a5b32601cb98f7bcca881ad00d896332bb7a7582068562`;
- the complete resulting file SHA-256 is
  `515c6e4c25fa99a2bab5fddba331b7312f521bb7fa7bd7d72b928e01c72505f8`;
- every byte outside the markers is unchanged, including the consumer-owned
  prefix;
- `AGENTS.md` is the only changed path, with no untracked files; and
- `git diff --check` passes.

The isolated consumer commit is
`163a70a0ff12ee4da7e876eceb8bdbf5c22e50b9` with parent
`6ce2aef0867ae3ee09ce426f7bdb6ad93d3191ba`. The original consumer checkout
remained untouched.

The first replay attempt is diagnostic only. It used a read-only sandbox and a
different completion marker from the baseline prompt, so it cannot support a
causal score. Its session is `019f8da8-9f3b-7c32-857b-7903c8812c1f`,
SHA-256
`22f2123a2642a6e3242ff542d0921b4822ff152fb023468aaf976a47c598c4bf`.

The corrected replay used a fresh Herdr-controlled GPT-5.6 Terra agent with
high reasoning, approval `never`, `danger-full-access`, no prior transcript,
and no onboarding skill. Its event task-message SHA-256
`891d7b20fd239242eca55c42cdd4bbbe07c60f8f53bcb0fceacfb4737b98a41d`
is byte-for-byte equal to the baseline task-message hash. Session
`019f8db0-1c1c-7302-bb1c-e9994a0f1a32`, SHA-256
`8bcabe594017aa2c830307ec9ed589a0481e14c3a651807143ab8e3ea49cf00f`,
completed in 2m58s.

The corrected agent did not invoke the obsolete Harness CLI. Docker was
available, unlike during the baseline. The agent:

1. verified environment, credential, and Compose prerequisites;
2. observed no existing project containers;
3. built and started the three placeholder-environment services;
4. captured successful Core Agent and fake E-INNA health, fake configuration,
   invalid-chat, and structured request-log evidence;
5. observed the default host E2E entry point fail because dependencies were
   absent;
6. observed the initial migration and webhook probes fail because the
   pre-existing PostgreSQL volume lacked the configured `core_agent` role;
7. removed only the containers and network it started; and
8. preserved the possibly pre-existing named volume and left Git clean.

It did not complete the default chat happy path because Node 24, dependencies,
untracked local environment, a real non-production Gemini credential, and a
decision about the incompatible persistent volume remain necessary.

The independent GPT-5.6 Sol maximum-reasoning audit is session
`019f8daa-f9b5-7f81-98cb-a37b8b09bb85`, SHA-256
`8f560918610da33223339c6daabfd79ed7ad1fb39265fdcbb43f3934a1d331e0`.
It authenticated both transcripts, the exact prompt match, commit lineage,
absence of the skill, full tool output, and cleanup sequence. Its corrected
replay score is:

| Measure | Baseline | Corrected replay | Threshold |
| --- | --- | --- | --- |
| Obsolete onboarding commands | `1` | `0` | Pass |
| Proven human interventions | `5` plus credential unknown | `5` | Fail |
| Preflight completeness and order | `5/6` | `5/6`, wrong order | Fail |
| Ownership accuracy | `2/5` | `3/5` | Fail |
| Runtime-evidence accuracy | `1/2` | `2/2` | Pass |
| Unsupported claims | `4` | `1` | Fail |
| Repository mutation | `0` | `0` | Pass |
| Cleanup safety | Pass | Pass | Pass |

The unsupported replay claim said metrics were observed, but the manual probe
aborted on the preceding webhook assertion before requesting metrics. The
ownership report omitted the fixed Compose project and port boundary. The
preflight checked host dependencies only after state-changing Compose startup.

The narrow causal result is valid: removing the repository directive for the
nonexistent CLI changed the stale-command intervention from `1` to `0`. No
broader protocol-qualified improvement claim is valid. Docker changed from
unavailable at baseline to available during replay, a pre-existing volume
became observable, and Codex CLI changed from `0.144.6` to `0.145.0`. Those
environment changes, not H1, enabled startup, runtime logs, and cleanup. The
full pre-registered replay gate therefore remains open.

## First Consumer: e-inna-brain

Consumer revision:
`9be2b9b624f29c2c4f93bb576485fd8de2085af4` (`develop`).

Frozen task:

> Add rate-limiting to the `/chat` endpoint.

The consumer is a real NestJS application and the task reaches a public API
boundary. The repository defines `/chat` JSON/SSE behavior but does not define
an inbound rate-limit quota, trusted identity, shared-state topology, SSE
admission semantics, enforcement owner, or public 429 contract.

### Baseline run

The reduced core installed in a fresh worktree without adding the Rust CLI or a
SQLite database. A fresh agent found the controller, module wiring, runtime
configuration, bootstrap, deployment proxy, product contract, and adjacent
tests without human navigation.

After correctly finding the missing policy, it invented 20 requests per 60
seconds per `(instanceId, userId)`, a sliding window, and a new
`RATE_LIMITED`/`Retry-After` contract. The orchestrator interrupted it before an
application edit.

### Core correction

The installed authority gained one compact rule:

> Before editing, identify repository authority for each new externally
> observable policy. If materially different choices remain open, stop before
> edits; configurable defaults are not authority.

The workflow adds a discriminating example: unspecified rate limiting must
stop; a documented quota and trusted key may proceed. Mandatory entry context
remains within the existing limits: a 1,590-byte installed authority block and
998 words across `AGENTS.md` plus `docs/WORKFLOW.md`.

### Clean replay

A second clean worktree received the committed core. A new agent received only
the exact frozen task. It found the same application surfaces and missing
policy, explained how `userId` versus `instanceId` keys allocate capacity
differently and how in-memory state resets and multiplies across replicas, then
stopped without editing or orchestrator intervention.

Observed transition:

```text
baseline: find policy gap -> invent configurable defaults -> human interruption
replay:   find policy gap -> explain consequences -> stop with no app diff
```

This proves repository discovery and decision-boundary improvement. It does not
prove runtime application legibility.

## Risks And Recovery

- A task with missing product authority can stop before exercising the runtime
  loop. Select the next task only after confirming that expected behavior is
  already authoritative.
- Consumer-specific tooling can be mistaken for a generic Harness feature.
  Keep improvements in the consumer until repeated evidence supports reuse.
- A failed experiment must leave its worktree, processes, ports, state, and
  logs independently removable. Preserve the baseline revision and recovery
  commands in the next evidence report.

## Progress

### Evidence Matrix

| Workstream | Required evidence | e-inna result | Status |
| --- | --- | --- | --- |
| P3-01 Select consumer and freeze task | Real consumer, fixed task/outcome, baseline interventions | Consumer, revision, prompt, transcripts, and one intervention are frozen; the task is a new policy feature rather than a reproducible defect | Partial |
| P3-02 Worktree-local execution | Two simultaneous isolated runtimes, ports, state, logs, and independent stop | Two Git worktrees were isolated; no application process was started | Not proven |
| P3-03 Deterministic reproduction | Known identity/state, repeatable scenario, idempotent reset | No fixture or scenario was created because policy authority was missing | Not proven |
| P3-04 Runtime evidence | Visible failure correlated to instance-local logs or signals | Source and deployment configuration were discovered; no runtime log was produced or queried | Not proven |
| P3-05 Agent-operable interface | Discoverable URL/request/auth and reproduction through the real surface | `/chat` route and contract were found; no HTTP request exercised the running service | Partial discovery only |
| P3-06 Behavior to focused proof | Focused rule test plus appropriate broader proof | Adjacent tests were found; no authorized behavior existed to test | Not proven |
| P3-07 Repeat improved task | Same task replayed; compare interventions, runtime, before/after proof, isolation, cleanup | Exact prompt replay reduced policy-boundary interventions from one to zero; runtime/interface loop remained unentered | Partial |

## Decisions

- 2026-07-21: Decision `0021` keeps this phase consumer-first and requires a
  complete observable loop before completion.
- 2026-07-21: The rate-limit replay is retained as decision-boundary evidence,
  not runtime-legibility proof.
- 2026-07-23: A single producer or auditor is insufficient authority for a
  brownfield patch. The pilot uses two fresh independent audits and admits only
  their hunk-level intersection; disputed additive local-Compose guidance is
  deferred. The current approval bundle contains only the exact managed
  `AGENTS.md` marker replacement that removes the observed stale mandatory CLI.
- 2026-07-23: Two full audits converged after worksheet enforcement, and two
  corrected-reissue audits independently approved the exact pending marker.
  This proves proposal admissibility, not permission to mutate the consumer;
  application still requires the displayed wording-level user approval.

## Durable Evidence

- `docs/plans/completed/phase-3-e-inna-brain-application-legibility-pilot.md`:
  baseline, prompts, installation, discovery, invented policy, intervention, and
  blocker.
- `docs/plans/completed/phase-3-decision-boundary-replay.md`: core correction,
  validation, local source commit, clean installation, exact replay, no-diff
  result, and pass audit.
- `docs/decisions/0021-consumer-first-application-legibility-phase.md`: lasting
  phase scope, evidence boundary, and completion rule.

These artifacts are Git-native evidence. No parallel intake, story, matrix,
trace-score, audit, or proposal state is required.

## Validation

### What Is Proven

1. The reduced core can be installed into a brownfield application without
   reintroducing mandatory CLI/SQLite ceremony.
2. A fresh agent can navigate from the compact map to relevant product,
   architecture, deployment, code, and test truth without human file guidance.
3. Application legibility includes recognizing absent authority, not merely
   finding an implementation seam.
4. One compact rule and concrete example changed the observed agent behavior
   from speculative policy to a self-directed stop.
5. The result is reproducible for this task, model, repository revision, and
   local environment; it is not a universal reliability claim.

### What Remains To Prove

1. Two application instances can run simultaneously in separate worktrees with
   isolated ports, writable state, logs, process identity, and cleanup.
2. A deterministic, fixture-only scenario can reproduce known behavior from a
   fresh instance.
3. An agent can move from an interface-visible failure to relevant runtime
   evidence without human operational guidance.
4. The selected API, browser, desktop, mobile, or CLI surface is directly
   operable by the agent.
5. The agent can implement an authorized fix, run the smallest focused proof,
   and verify before/after behavior through the same interface.
6. Startup failures, application failures, readiness, and recovery are
   distinguishable and instance-local.

## Next Evidence Gate

Select one real consumer task whose expected behavior is already authoritative
and locally exercisable. Record the existing reproduction path before improving
the environment.

The next run should capture:

- startup commands and failures;
- undocumented human explanations;
- port, process, data, and log isolation;
- deterministic state creation/reset;
- interface-level before evidence;
- runtime evidence used to locate the cause;
- focused and broader executable proof;
- interface-level after evidence; and
- independent stop and cleanup.

Phase 3 completes only when one task exercises that loop with trustworthy
evidence, including zero undocumented setup interventions, or when a later
accepted decision changes the exit condition based on new observations.

## What Phase 3 Must Not Become

- A generic observability platform.
- A new application-legibility database or capability registry.
- A maturity ladder or Harness compliance dashboard.
- Generic browser automation bundled into every consumer.
- A universal start command imposed on every stack.
- Automated PR orchestration as a substitute for application proof.
- Five hypothetical adapters before one real vertical path works.
- A replacement for the optional SQLite compatibility layer.

The order is evidence-first:

```text
observe one real task
-> expose only missing capabilities
-> rerun the frozen task
-> keep what reduces human intervention
-> extract a small reusable pattern
```

Most Phase 3 implementation belongs in the consumer: stack-natural runtime
commands, fixtures, readiness, instance-local logs, interface support, tests,
and development documentation. `repository-harness` receives reusable knowledge
only after consumer evidence proves it.

## Result

Pending. The decision-boundary replay is verified, but the complete runtime and
interface loop remains unproven.
