# Design

## Domain Model

- Completion-eligible story: `in_progress` or `changed`, with a usable
  `verify_command`; when it is a resolver, it also has a linked improvement
  intake and a qualifying completed implementation trace.
- Resolution-eligible backlog occurrence: status `accepted`, linked to the story
  through `resolves`, and not already closed.
- Completion result: pass, fail, or unavailable.

## Application Flow

```text
story complete <id>
  -> load story and relationships
  -> reject planned, retired, or missing-proof state
  -> if resolver: require stable linked harness_improvement intake uid
  -> if resolver: require matching-intake-uid completed trace after newest link
  -> require every resolves target to be eligible or idempotently closed by self
  -> run verify command from repo root
  -> on failure: record failed verification only; remain incomplete
  -> on pass, one transaction:
       record fresh pass
       set story.status=implemented
       record resolver story and resolution evidence
       close each eligible accepted occurrence as implemented
       set each trace-count schedule baseline to current stable trace count
       leave actual_outcome and outcome observations unchanged
       emit ordered semantic operations
```

An external orchestrator must ensure its copied story enters `in_progress`,
perform the work, and record the detailed completed trace before completion is
attempted. If the current runner does not enforce this order, its run contract must be updated as
part of this story.

## Interface Contract

```bash
scripts/bin/harness-cli story complete US-077
```

Output lists the intake and implementation trace used, verification result,
resulting story status, backlog occurrences closed, self-closed links skipped,
and remaining referenced items.

`story verify` and `story verify-all` continue to record proof only.

## Data Model

Use fields introduced by `US-074` and relationships from `US-076`. Completion
writes one transaction. Changeset apply must preserve the same logical timestamp
or completion event identity for proof and closure.

## UI / Platform Impact

No application UI change. Orchestrated run preparation may change only enough to
establish completion-eligible copied story state and require the explicit CLI
completion path.

## Observability

Resolution evidence names the completing story, verification command/result,
completion event uid, and time. It is not stored as measured actual outcome.

## Alternatives Considered

1. Close on every `story verify` pass. Rejected because planned work and batch
   verification could close unexpectedly.
2. Mark implemented before running proof. Rejected because failed verification
   would leave a false implemented state.
3. Require manual backlog close after proof. Rejected because verification and
   closure can drift apart again.
