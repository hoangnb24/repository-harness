# Improvement Protocol

Phase 5 starts the self-improvement loop:

```text
friction + interventions + audit findings
  -> harness-cli propose
  -> human accepts or rejects one stable proposal key
  -> accepted backlog occurrence plus outcome-review schedule
  -> implementation with predicted impact
  -> close with actual outcome
```

## Generate Proposals

```bash
scripts/bin/harness-cli propose
```

The command is rule-based. It looks for:

- repeated trace friction,
- repeated intervention patterns,
- non-zero audit categories.

Each proposal includes a stable versioned key, lifecycle state, title, component,
evidence, predicted impact, risk, suggested action, validation plan, and
confidence. Running `propose` without a decision flag is read-only.

## Decide One Proposal

```bash
scripts/bin/harness-cli propose --accept <proposal-key> --outcome-manual
scripts/bin/harness-cli propose --accept <proposal-key> --outcome-due <RFC3339>
scripts/bin/harness-cli propose --accept <proposal-key> --outcome-after-traces <positive-integer>

# Or retain a terminal human decision without creating implementation work.
scripts/bin/harness-cli propose --reject <proposal-key> --reason "Not worth the added complexity"
```

Acceptance creates or reuses one `accepted` backlog occurrence and prints the
next `harness_improvement` intake command. Rejection records one terminal reason
and covered evidence without creating an intake, story, or Symphony run.
`propose --commit` is intentionally rejected; Harness never bulk-writes every
currently displayed suggestion.

Humans review accepted work with:

```bash
scripts/bin/harness-cli query backlog --open
```

## Complete Accepted Work

After implementation, the resolving story follows one explicit sequence:

```text
story enters in_progress or changed
  -> implementation finishes
  -> matching completed implementation trace is recorded
  -> story complete runs fresh verification
  -> passing proof marks the story implemented
  -> eligible accepted resolver backlog occurrences close in the same transaction
```

```bash
scripts/bin/harness-cli story complete <US-NNN>
```

Failure leaves the story completion-eligible and closes nothing. Repeated or
concurrent completion is idempotent. Resolution evidence records the story,
proof command, completion identity, and completion time; it does not claim the
later measured outcome.

## Review Rules

- Tiny proposals may be implemented directly when they only clarify docs.
- Normal proposals need a story packet or clear backlog acceptance.
- High-risk proposals need a durable decision record before changing source
  hierarchy, architecture direction, validation requirements, or risk policy.
- Keyed accepted work is closed by the explicit story-completion lifecycle,
  not `backlog close`; later outcome observation remains separate from
  implementation proof.

## Validation

After implementation, compare the predicted impact with:

- `scripts/bin/harness-cli audit`,
- `scripts/bin/harness-cli query friction`,
- `scripts/bin/harness-cli query interventions`,
- benchmark trace quality and harness compliance when benchmark proof applies.
