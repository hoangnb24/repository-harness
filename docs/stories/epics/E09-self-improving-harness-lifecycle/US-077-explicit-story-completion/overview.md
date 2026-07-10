# Overview

## Status

implemented

## Lane

high-risk

## Product Contract

Only an explicit completion command may combine fresh passing proof, implemented
story status, resolution evidence, and eligible accepted backlog closure.

## Current Behavior

`story verify` records proof only. `story complete` is the explicit transition
that requires completion eligibility, runs fresh proof, and atomically records
implemented story state plus eligible resolver backlog closure. Completion
evidence and semantic operations replay with the same completion identity and
resolution evidence.

## Target Behavior

An explicit `story complete <id>` operation is the only automatic bridge from
fresh story proof to resolved Harness backlog closure. It refuses
completion-ineligible stories, runs the configured verification, and writes
proof, implemented story status, resolution evidence, and eligible backlog
closures atomically on pass.

## Affected Users

- Agents completing Harness improvement stories.
- Humans reviewing closure and proof.
- Symphony orchestrating isolated story runs and changesets.

## Affected Product Docs

- `docs/stories/epics/E09-self-improving-harness-lifecycle/README.md`
- `docs/decisions/0008-self-improving-harness-lifecycle.md`
- `docs/HARNESS.md`
- `docs/IMPROVEMENT_PROTOCOL.md`
- `docs/SYMPHONY_SCOPE.md`

## Dependencies

- Blocked by: `US-075`, `US-076`.
- Blocks: `US-078`.

## Acceptance Criteria

- `story complete <id>` refuses planned, retired, or missing-verification stories
  with actionable output; an already completed story returns its existing
  completion state without new writes.
- Symphony's required order is: establish `in_progress` copied-story state,
  implement the change, record its completed implementation trace, then invoke
  `story complete`.
- A story with any `resolves` link must have at least one
  `harness_improvement` intake whose `story_id` is that story.
- Before verification, a resolver story must have a completed, story-linked
  implementation trace whose stable `intake_uid` matches that intake, recorded at
  or after its newest resolver link. The trace must include nonblank actions and
  changed-file evidence; local integer intake ids are not proof identity.
- Missing intake, missing/early/incomplete trace, or an ineligible resolver target
  refuses completion before verification and writes nothing.
- Completion runs the configured verification command freshly from the repo
  root.
- Failure records failed proof, leaves the story completion-eligible, and closes
  no backlog occurrence.
- Passing completion writes verification, `story.status=implemented`, resolver
  provenance, resolution evidence, and eligible backlog closures in one
  transaction.
- For each trace-count outcome schedule, completion also records the current
  stable trace count as its post-implementation baseline in that same transaction. The
  baseline is the total number of uid-bearing trace rows visible to completion;
  a later count lower than the baseline is a schedule error.
- Every current `resolves` target must be either open `accepted` work or already
  implemented by this same resolver story. A proposed, rejected, otherwise
  closed, or differently resolved target aborts the whole completion before
  verification; references remain untouched.
- Open accepted targets close. A target already implemented by this same story is
  an idempotent no-op and retains its original closure evidence.
- Resolution evidence names the story and proof but does not populate measured
  actual outcome or an outcome observation.
- Ordinary `story verify` and `verify-all` remain proof-only commands.
- Repeated or concurrent completion is idempotent and cannot duplicate closure.
- Any write failure rolls back every completion transition.
- Later failed verification never reopens or rewrites historical closure.
- `backlog close --status implemented` refuses proposal-keyed lifecycle work and
  directs the operator to `story complete`; unkeyed manual/legacy compatibility
  remains unchanged.
- Live, changeset-applied, and rebuilt states agree.

## Non-Goals

- Do not make ordinary `story verify` or `verify-all` close work.
- Do not set measured `actual_outcome` from implementation proof.
- Do not reopen closed backlog history on later failure.
- Do not automatically create regression work.
- Do not require an improvement intake for ordinary stories with no `resolves`
  relationship.
