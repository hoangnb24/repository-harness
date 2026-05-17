# Story Backlog

This backlog will be populated after a user provides a project spec or selects a
specific initiative.

Do not create every possible story packet up front. Create story packets when
the work is selected or when a product decision needs a durable place to land.

## Candidate Epics

| Epic | Description | Sequence | Depends on | Status |
| --- | --- | --- | --- | --- |
| TBD | Add candidate epics after spec intake | 0 | — | unsliced |

## Ordering Rule

Pick the lowest-sequence epic whose `Depends on` is satisfied (all
dependency epics in `implemented` status). Epics at the same sequence
can run in parallel only when their stories don't overlap file
ownership. When a story unlocks a previously blocked epic, bump the
unblocked epic to the top of the next sprint, not back to the bottom.
