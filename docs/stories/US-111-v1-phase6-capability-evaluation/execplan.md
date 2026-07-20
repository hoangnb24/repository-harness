# US-111 V1 Phase 6 Capability Evaluation Exec Plan

> Decision 0017 supersedes the plan's mandatory-release role. Remaining P0-P7
> execution is optional unless a later decision explicitly requires it.

Status: **Framework accepted by owner for sequencing; live efficacy deferred**

## Goal

Provide Phase 6's durable custody decision and portable target-owned capability
framework while preserving the Phase 5 baselines. Decision 0016 later accepts
the framework for sequencing and opens Phase 7 engineering while keeping live
efficacy, Phase 7 acceptance/promotion, and Phase 8 closed.

## Scope

In scope:

- Decision 0015 and its decision-index entry.
- US-111 overview, design, exec plan, validation, and story-index entry.
- Neutral agent-map, story, validation-report, high-risk exec-plan, and
  high-risk validation templates.
- Agent-map path disposition.
- The original Phase 6 in-progress/framework-pending wording in the explicitly
  owned initiative and status documents, followed by Decision 0016's separate
  framework-accepted/live-efficacy-deferred status.
- Intake #8 and US-111 replay changesets.

Out of scope:

- Evaluator scripts/schemas, Rust, pilot repositories, private snapshots,
  keys, archives, raw databases, release workflows, tags, and publishing.
- Modification of Phase 5 artifacts or any US-110 byte.
- Live candidate results, live efficacy claims, Phase 7 acceptance/promotion,
  or Phase 8 work. US-112 separately owns opened Phase 7 engineering.

## Risk Classification

Risk flags:

- Audit/security: evaluation handles external trust and potentially sensitive
  V0 recovery inputs.
- Public contracts: portable templates shape installed target behavior.
- Existing behavior: Phase 5 evidence and V1 optionality must not change.
- Weak proof: no live candidate card exists yet.
- Multi-domain: custody, planning, feedback, maintenance, and phase gates meet.

Hard gates:

- Never mutate live V0 state or commit raw DB/archive/key material.
- Never use recovery-mutated staging as the warm condition master; seal the
  validated raw trio/standalone master and derive fresh baseline and candidate
  copies from that same master.
- Never let candidate-controlled bytes self-authorize evidence.
- Never claim a live card or later phase from documentation proof.

## Work Phases

1. Read authority, high-risk templates, Phase 5 evidence, and trust/capture
   decisions.
2. Bootstrap/query only the approved isolated planning database.
3. Freeze Decision 0015 and the US-111 framework contract, including immutable
   warm-master custody, fresh paired derivatives, immediate pre-run identity
   verification, and condition/subject digest binding.
4. Make portable templates neutral and target-owned while preserving existing
   V0 Harness fields as conditional guidance only.
5. Update only the approved phase-status surfaces and path ledger.
6. Create/rebuild changesets when the isolated CLI supports it.
7. Parse JSON, run docs/diff checks, scan neutrality, verify owned scope, and
   compare Phase 5/US-110 hashes to the starting revision.
8. Commit logical docs changes without release or remote mutation.

## Resume Capsule

- Objective: correct the Phase 6 authority/docs framework after independent
  review without rewriting reviewed commit `88a7a36`.
- Completed: original framework committed; independent review identified warm-
  master custody and legacy-template conditionality gaps.
- Remaining: apply the bounded corrections, validate preservation, and create a
  separate follow-up commit.
- Exact next action: verify Decision 0015 requires a sealed validated raw trio
  and standalone master, fresh baseline/candidate derivatives from that master,
  and immediate pre-run master/derivative identity checks.
- Validation ladder: parse owned JSON/JSONL; run documentation contract and
  `git diff --check`; scan template neutrality and required phrases; compare
  US-110 and Phase 5 hashes; inspect exact changed-file scope; rebuild/query the
  isolated changesets.
- Decisions and assumptions: corrected Decision 0015; Intake #8 and the
  independent review findings are authoritative.
- Blockers and owners: live candidate custody, trust, signatures, runs, and
  results remain with external repository owners/custodians.
- Working state: correction starts from reviewed commit
  `88a7a364fc92c73ecfe9a76072e1df09c5bd9b82`; Phase 5 and US-110 must still
  match `5d6e6bc516cd60e47c60ae3b516363cd99b433a5` byte-for-byte.

## Stop Conditions

Stop and request explicit authority if:

- A live pilot, snapshot, raw database, archive, trust registry, or key must be
  accessed or changed.
- A comparable warm run cannot create two fresh derivatives from one sealed,
  reverified standalone master or cannot bind their identities into evidence.
- A Phase 5 or US-110 byte would change.
- A production workflow, release, tag, publish, or push becomes necessary.
- A template would need a pilot, language, package manager, evaluator hint, or
  Harness-only ordinary-work requirement.
- Evidence is insufficient to distinguish framework completion from Phase 6
  acceptance.
