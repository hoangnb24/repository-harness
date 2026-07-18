# P6 Held-Out Prompt

The fresh agent was spawned with no conversation fork and received exactly:

```text
You are the context-free fresh agent for a held-out comparable repository task. Work only in the current isolated worktree and read AGENTS.md. A stale active task-range statement has been seeded somewhere in the repository: it contradicts the current manifest-driven task count/range. Diagnose it using repository-owned instructions and feedback, make the smallest relevant repair, and run appropriate repository-native proof. You have no original correction discussion and must not ask the evaluator where any capability lives. Do not weaken or remove tests. Do not commit, and never push, deploy, mutate remotes, generate keys, or sign. Record an exact ordered transcript with UTC timestamps, commands, exit codes, outputs/observations, discovery path, changed paths, final diff, final target acceptance, and environment digest b69c81a8ec42c39d80b0b9f814675646c4f1e39f688aa5a72bab01265e480dde at docs/evidence/phase5-pilot-benchmark/cards/P6/held-out-transcript.md. Preserve unrelated existing changes.
```

Packet-normalization annotation (not part of the original held-out prompt):
the prompt above truthfully preserves the source-run legacy digest computed
with a trailing newline. Its verifier-canonical packet binding, computed
without that trailing newline, is
`b3a3067d79803aa6631ae7cd9f3424e13b102073bd9eb64123407a9ae43ef2dc`.

No capability path, test name, original correction discussion, or evaluator
repair pointer was supplied.
