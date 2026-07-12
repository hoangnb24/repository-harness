# Epic Story Packets

Create epic folders here only when work begins or when product decisions need a
durable home.

Suggested naming:

```text
E01-domain-name/
E02-domain-name/
E03-domain-name/
```

Create the real epic names from the user-provided spec, not from this template.

## Active Epic Sequence

| Epic | Theme | Exit Signal |
| --- | --- | --- |
| `E04-isolated-durable-state-and-semantic-replay` | Make `harness-cli` support copied DBs, semantic changesets, replay, and rebuild. | `harness.db` is a rebuildable local index over committed changesets. |
| `E09-self-improving-harness-lifecycle` | Carry evidence-backed Harness proposals through acceptance, verified closure, recurrence, and measured outcome. | Handled evidence stays explainable and suppressed; only new recurrence becomes human-reviewable work. |
| `E10-harness-signal-quality` | Retire obsolete or synthetic improvement signals and expose multidimensional Harness health. | Current signal quality and lane-aware trace health are visible without deleting history. |

Completed migration history, including the repository separation initiative,
remains under `E11-symphony-repository-separation` as provenance rather than an
active product epic.
