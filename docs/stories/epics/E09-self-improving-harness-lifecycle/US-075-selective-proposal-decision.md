# US-075 Selective Proposal Decision

## Status

implemented

## Lane

normal

## Product Contract

`harness-cli propose` shows deterministic proposal keys and lifecycle state
without writing. A human can accept or reject exactly one currently displayed
key. Acceptance creates or reuses one `accepted` backlog occurrence and records
when its outcome must be reviewed; rejection records a terminal human decision
without creating implementation work.

## Relevant Product Docs

- `docs/stories/epics/E09-self-improving-harness-lifecycle/README.md`
- `docs/decisions/0008-self-improving-harness-lifecycle.md`
- `docs/IMPROVEMENT_PROTOCOL.md`
- `docs/TOOL_REGISTRY.md`

## Dependencies

- Blocked by: `US-074`.
- Blocks: `US-077`, `US-080`.

## Acceptance Criteria

- Default `propose` output is deterministically ordered and displays a stable,
  versioned proposal key plus its current lifecycle state.
- Running default `propose` twice against unchanged state produces identical
  output and no database or changeset mutation.
- Acceptance uses exactly one of these command forms:

  ```bash
  scripts/bin/harness-cli propose --accept <proposal-key> \
    --outcome-manual
  scripts/bin/harness-cli propose --accept <proposal-key> \
    --outcome-due <RFC3339>
  scripts/bin/harness-cli propose --accept <proposal-key> \
    --outcome-after-traces <positive-integer>
  ```

- Acceptance requires exactly one observation schedule. `--outcome-manual`
  records an intentional human review with no overdue deadline. A due timestamp
  must be later than acceptance. A trace-count schedule stores the positive count;
  its baseline remains null until `story complete` starts the post-change window.
- Acceptance creates status `accepted`, never the nonexistent status `open` and
  never every displayed proposal.
- A first decision creates `occurrence_kind=original` with null predecessor;
  recurrence kinds and predecessors are added only by `US-078`.
- If an already-keyed matching row is `proposed`, acceptance transitions that
  row to `accepted` instead of duplicating it.
- A plausible but unkeyed legacy match is refused with `requires legacy
  reconciliation`; acceptance never guesses or creates a parallel row.
- A proposal containing a current audit finding without an active recorded audit
  episode is refused with `run harness-cli audit --record-evidence`; acceptance
  and rejection never create audit evidence as a hidden side effect.
- Repeating the same acceptance with the same observation boundary returns the
  existing occurrence and writes nothing. A conflicting boundary fails and
  leaves the original acceptance unchanged.
- Rejection uses exactly:

  ```bash
  scripts/bin/harness-cli propose --reject <proposal-key> --reason <text>
  ```

- Rejection creates or transitions one occurrence to status `rejected`, sets its
  closure time, records the nonblank reason and currently covered evidence, and
  creates no observation schedule, intake, story, or orchestrated run.
- Repeating the same rejection returns `unchanged`. A different reason for an
  already rejected occurrence fails without rewriting history. An accepted
  occurrence cannot be rejected through this command.
- The partial uniqueness constraint established by `US-074` and one transaction
  prevent concurrent decisions from creating two proposed/accepted occurrences
  for the same key.
- Both decisions record covered evidence and use the normal
  logged-write/semantic-changeset path.
- Bare `propose --commit` exits with code `2`, writes nothing, and prints
  `use propose --accept <proposal-key> or propose --reject <proposal-key>`.
- `backlog close` refuses an implemented/rejected transition for a keyed
  lifecycle occurrence and directs the operator to `story complete` or
  `propose --reject`; existing unkeyed manual and legacy rows keep their current
  compatibility behavior until explicit reconciliation.
- Acceptance output provides the backlog id and exact next `harness_improvement`
  intake command shape.

## Design Notes

- Commands: read-only `propose`, `propose --accept <proposal-key>` with exactly one
  of `--outcome-manual`, `--outcome-due`, or `--outcome-after-traces`, and
  `propose --reject <proposal-key> --reason <text>`.
- Queries: reconcile generated keys only with already-keyed proposed, accepted,
  implemented, or rejected occurrences.
- API: CLI only; JSON output may be added for deterministic contract tests.
- Tables: consume the stable identity, evidence coverage, observation-plan
  fields, and one-open-occurrence index from `US-074`; this story adds no schema.
- Domain rules: proposal generation is advisory; accept/reject are explicit human
  gates; terminal history is immutable.
- UI surfaces: terminal output only.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Exact-key selection, accept/reject eligibility, boundary parsing, unknown/stale keys, legacy refusal, and exit-code contracts. |
| Integration | Read-only hash proof; due-date and trace-count acceptance; repeat/conflicting decisions; rejection; concurrent transaction safety; guarded legacy `backlog close`. |
| E2E | Already-keyed fixtures move through pending, accepted, and rejected states while a plausible unkeyed fixture is refused for reconciliation. |
| Platform | Decision operations, evidence coverage, and observation plans survive changeset apply and fresh rebuild. |
| Release | CLI help, docs, workspace fmt/test/clippy, and local installer smoke pass. |

Planned story verification:

```bash
sh -c 'cargo test -p harness-cli -- --list | rg "proposal_decision" && cargo test -p harness-cli proposal_decision -- --nocapture && scripts/validate-changeset-rebuild.sh'
```

## Harness Delta

Proposal review becomes a replay-safe decision surface instead of a bulk backlog
writer, and every accepted improvement leaves a concrete outcome-review trigger.

## Non-Goals

- Do not classify post-closure recurrence; `US-078` owns that behavior.
- Do not reconcile or mutate unkeyed legacy rows; `US-080` owns that behavior.
- Do not create intake, story, or orchestrated work automatically.
- Do not record measured outcome in this story.

## Evidence

Implemented deterministic proposal keys and lifecycle display, one-key
accept/reject commands, observation schedules, idempotency and legacy refusal,
keyed backlog-close protection, replayable decision operations, and focused
decision tests. Validation passed: `cargo fmt --check`, `cargo test --workspace`,
`cargo clippy --workspace -- -D warnings`, `scripts/validate-changeset-rebuild.sh`,
`harness-cli story verify US-075`, and `git diff --check`.
