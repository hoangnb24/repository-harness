# Design

## Independent Case

```text
worktree A: story A revision 0 -> 1
worktree B: story B revision 0 -> 1
Git merge: two unique JSONL files
replay: both guards match -> converged state
```

## Conflict Case

```text
worktree A: story A expected revision 1 -> intent A
worktree B: story A expected revision 1 -> intent B
Git merge: both unique files survive
replay A: revision 1 -> 2
replay B: expected 1, actual 2 -> CONFLICT; whole file rolls back
```

## Agent Recovery

The agent reads both operations and the current entity. If intent is clear, it
removes only its own stale, not-yet-shared generated changeset, rebuilds from
merged tracked state, and reruns the normal CLI command. The new file observes
revision `2`. If choosing intent is ambiguous, the agent asks the user.
