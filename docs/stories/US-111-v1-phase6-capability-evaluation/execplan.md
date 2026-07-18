# US-111 V1 Phase 6 Capability Evaluation Exec Plan

Status: **Documentation/capability framework in progress; live cards pending**

## Goal

Start Phase 6 with a durable custody decision and portable target-owned
capability templates while preserving the Phase 5 baselines and keeping live
candidate evaluation, Phase 7, and Phase 8 closed.

## Scope

In scope:

- Decision 0015 and its decision-index entry.
- US-111 overview, design, exec plan, validation, and story-index entry.
- Neutral agent-map, story, validation-report, high-risk exec-plan, and
  high-risk validation templates.
- Agent-map path disposition.
- Phase 6 in-progress/framework-pending wording in the explicitly owned
  initiative and status documents.
- Intake #8 and US-111 replay changesets.

Out of scope:

- Evaluator scripts/schemas, Rust, pilot repositories, private snapshots,
  keys, archives, raw databases, release workflows, tags, and publishing.
- Modification of Phase 5 artifacts or any US-110 byte.
- Live candidate results, Phase 6 acceptance, Phase 7 proof, or Phase 8 work.

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
- Never let candidate-controlled bytes self-authorize evidence.
- Never claim a live card or later phase from documentation proof.

## Work Phases

1. Read authority, high-risk templates, Phase 5 evidence, and trust/capture
   decisions.
2. Bootstrap/query only the approved isolated planning database.
3. Freeze Decision 0015 and the US-111 framework contract.
4. Make portable templates neutral and target-owned.
5. Update only the approved phase-status surfaces and path ledger.
6. Create/rebuild changesets when the isolated CLI supports it.
7. Parse JSON, run docs/diff checks, scan neutrality, verify owned scope, and
   compare Phase 5/US-110 hashes to the starting revision.
8. Commit logical docs changes without release or remote mutation.

## Resume Capsule

- Objective: complete the Phase 6 authority/docs/portable-capability slice.
- Completed: authority read; isolated bootstrap/query complete; Intake #8 UID
  supplied; template and story framework drafted.
- Remaining: phase-status updates, changesets, validation, and commits.
- Exact next action: update `docs/REFACTOR_PLAN.md` Phase 6 status to
  in-progress/framework complete/live cards pending without changing its
  acceptance rule.
- Validation ladder: parse owned JSON/JSONL; run documentation contract and
  `git diff --check`; scan template neutrality and required phrases; compare
  US-110 and Phase 5 hashes; inspect exact changed-file scope; rebuild/query the
  isolated changesets.
- Decisions and assumptions: Decision 0015; user-supplied Intake #8 and owned
  file list are authoritative.
- Blockers and owners: live candidate custody, trust, signatures, runs, and
  results remain with external repository owners/custodians.
- Working state: exact starting commit `5d6e6bc516cd60e47c60ae3b516363cd99b433a5`;
  no Phase 5 or US-110 edits permitted.

## Stop Conditions

Stop and request explicit authority if:

- A live pilot, snapshot, raw database, archive, trust registry, or key must be
  accessed or changed.
- A Phase 5 or US-110 byte would change.
- A production workflow, release, tag, publish, or push becomes necessary.
- A template would need a pilot, language, package manager, evaluator hint, or
  Harness-only ordinary-work requirement.
- Evidence is insufficient to distinguish framework completion from Phase 6
  acceptance.
