---
status: proposed
approved_by: ""
approved_at: ""
superseded_by: ""
---

# 0029 Measured Skills, Context Budget, And Approval Frontmatter

Date: 2026-11-02

## Context

Harness could not observe whether agents followed its skills or what they
cost, so guidance changes were judged without data. Text loaded every session
had one hard-coded size check and no shared budget. `$encode-invariant`
required accepted authority, but the agent alone judged whether a decision was
accepted. A team using Harness needs approval to be something a person writes,
not something an agent infers.

## Decision

1. Every distributed skill ends its final answer with one receipt line:
   `HARNESS_SKILL: <skill> | done|stopped|skipped | <artifact path or reason>`.
2. `harness skill-report <session.jsonl>...` reports, from Claude Code
   sessions the user names, explicit invocations, receipts, and the four token
   categories per skill. It is read-only, prints aggregates only, deduplicates
   repeated message records by `message.id`, and rejects other formats.
3. `scripts/context-budget.tsv` is the single source of limits for entry
   blocks, skill descriptions, and skill bodies, checked by
   `tests/docs/test-context-budget.sh` in pre-merge validation. Oversized
   existing skills are grandfathered at measured size and may only shrink.
4. Decision records carry frontmatter `status`, `approved_by`, `approved_at`,
   and `superseded_by`; status no longer appears in the body.
   `$encode-invariant` stops before edits unless a cited decision record has
   `status: accepted` and a named approver and date. Missing frontmatter means
   not approved.
5. Fail-closed evidence gates and the criteria for promoting guidance to a
   gate are documented in the encoding pattern. Harness ships no generic gate
   script, because evidence is repository-specific and an unwired gate creates
   false assurance.

## Alternatives Considered

1. Ship `done-gate.sh` in the payload. Rejected: nothing would invoke it, and
   a generic script cannot know what counts as evidence in a consumer.
2. Implement the checkers as payload shell scripts. Rejected: PowerShell
   parity would double the work; the installed binary already runs on every
   supported platform and owns path-safety rules.
3. Ship a `harness check-authority` command. Rejected for now: only the
   agent would invoke it, so it adds no enforcement beyond the skill rule,
   while adding CLI surface and release coupling.
4. Infer skill invocations from topic matches. Rejected: only an explicit
   invocation (Claude Code's skill-load record) counts.

## Consequences

Positive:

- Skill compliance and token cost become measurable before and after a
  guidance change, supporting `$improve-harness` baselines and reruns.
- Approval becomes a written act by a named person.
- Context growth needs an explicit, reviewed budget change.

Tradeoffs:

- Receipts are self-reported; they measure format compliance, not truth.
- Approval markers prove fields were filled, not that a review happened.
- Existing decisions without frontmatter do not count as approval until
  migrated.
- Approval is checked by the agent following the skill, not by a machine.
- Session parsing depends on Claude Code's JSONL shape and must be rechecked
  when that format changes. Codex sessions are not supported yet.

## Follow-Up

- Accept or revise this decision (set `status`, `approved_by`, `approved_at`).
- Migrate decisions that future invariants will cite.
- Add a machine check for approval frontmatter only when it is wired into CI,
  for example to require an accepted decision for each new guard.
- Revisit Codex session support when there is demand.
