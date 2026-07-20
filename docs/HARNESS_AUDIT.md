# Harness Audit

> **Compatibility reference — not part of the default workflow.** This score
> audits optional control-plane records, not product quality. Default-path
> maintenance uses repository-specific mechanical checks and targeted cleanup
> described in `docs/WORKFLOW.md`.

`scripts/bin/harness-cli audit` detects drift in durable Harness state and
prints an entropy score. Lower is better.

## Checks

| Category | Meaning | Weight |
| --- | --- | --- |
| Orphaned stories | Planned or in-progress stories with no linked trace. | 10 |
| Unverified stories | Active or implemented stories with `verify_command` but no recorded verification result. Retired stories are historical records and are not counted. | 5 |
| Unverified decisions | Decisions with `verify_command` but no recorded verification result. | 5 |
| Open backlog without outcomes | Keyed implemented occurrences with no append-only outcome observation, plus unkeyed legacy implemented items with no `actual_outcome`. | 2 |
| Stale stories | Unimplemented stories whose latest linked trace is more than 30 days old. | 3 |
| Broken tools | Registered tools whose command is not found on disk or `PATH`. | 8 |

## Score

```text
score = orphaned_stories * 10
      + unverified_stories * 5
      + unverified_decisions * 5
      + backlog_without_outcomes * 2
      + stale_stories * 3
      + broken_tools * 8
```

The score is capped at 100.

| Range | Interpretation |
| --- | --- |
| 0 | Perfect: records are traced, verified, and healthy. |
| 1-25 | Healthy: minor housekeeping remains. |
| 26-50 | Attention needed: drift is accumulating. |
| 51-100 | Action required: stale state undermines Harness value. |

Audit findings feed `scripts/bin/harness-cli propose`, which can turn repeated
drift into proposed backlog items.

Implementation proof and measured impact are intentionally separate. For keyed
improvement occurrences, any row in `backlog_outcome_observation` satisfies the
audit check, including a neutral `legacy_recorded` row preserved by legacy
reconciliation. The mutable legacy `actual_outcome` column is consulted only
for unkeyed compatibility rows.
