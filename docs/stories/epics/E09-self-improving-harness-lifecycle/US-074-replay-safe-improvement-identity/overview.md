# Overview

## Status

planned

## Lane

high-risk

## Product Contract

Every improvement issue, intake, backlog occurrence, and source evidence record
has stable identity that remains the same after semantic changeset apply and
fresh database rebuild.

## Current Behavior

Improvement proposals have display text but no stable proposal key. Intake,
backlog, trace, and intervention records rely on local numeric ids. Semantic replay
remaps those ids within one changeset and assigns replay-time timestamps, so
acceptance, relationships, closure, and recurrence cannot safely span separate
changesets or a fresh rebuild.

## Target Behavior

Harness has separate stable identity for an underlying improvement issue, one
backlog occurrence, and each evidence record. Semantic changesets preserve those
identities and original event times. Later stories can therefore accept, link,
close, suppress, and recur work without relying on local row numbers.

## Affected Users

- Humans reviewing Harness proposals and closed outcomes.
- Agents implementing and verifying Harness improvement stories.
- External consumers applying and rebuilding semantic changesets.
- Maintainers migrating installed Harness databases.

## Affected Product Docs

- `docs/stories/epics/E09-self-improving-harness-lifecycle/README.md`
- `docs/decisions/0008-self-improving-harness-lifecycle.md`
- `docs/IMPROVEMENT_PROTOCOL.md`
- `docs/TRACE_SPEC.md`
- `docs/TOOL_REGISTRY.md`

## Dependencies

- Blocked by: `US-073`.
- Blocks: `US-075`, `US-076`.

## Acceptance Criteria

- Proposal keys are deterministic, versioned, Unicode-safe, and independent of
  display order, confidence, and title truncation.
- Intakes, backlog occurrences, traces, and interventions receive stable uids on
  write; traces reference intake uid rather than replay-local intake id.
- Multiple closed occurrences may share one proposal key while retaining
  distinct occurrence uids and predecessor relationships.
- Accepted occurrences can retain structured coverage of trace, intervention,
  or audit evidence.
- Read-only `audit` findings enter durable identity only through explicit
  `audit --record-evidence`; unchanged findings write nothing, clear findings
  close their active episode, and later reappearance gets a new evidence uid.
- Audit episode open/clear operations are atomic, idempotent, semantic-change-set
  backed, and survive fresh rebuild with their original event times.
- The identity migration owns the one-open-occurrence constraint, observation
  plan fields, and append-only outcome-observation storage consumed by later
  stories; it does not expose their mutation behavior yet.
- Semantic operations persist stable uids and original event times.
- A relationship written in a later changeset resolves the same occurrence even
  when source and rebuilt databases assign different local integer ids.
- Migration is additive and does not delete, merge, accept, reject, implement,
  or otherwise reinterpret existing records.
- Detailed or machine-readable queries expose the stable identity needed for
  later E09 stories and debugging.
- Fresh rebuild reproduces the same new-record identity, predecessor, evidence,
  and source timestamp bytes as the live fixture; legacy local ids and replayed
  v1 timestamps are explicitly excluded.

## Non-Goals

- Do not accept proposals in this story.
- Do not add story-to-backlog relationships.
- Do not close backlog work.
- Do not classify regression or reconsideration yet.
- Do not record outcome observations yet.
- Do not make default `audit` or `propose` write.
- Do not rewrite ambiguous legacy identities; `US-080` owns reconciliation.
