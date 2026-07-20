# Design

## CI Gate

Checkout starts without ignored state. CI explicitly tests that condition,
runs platform bootstrap, then executes the existing pre-merge contract. The
contract independently verifies the snapshot, materialized durable-table
parity, worktree conflict behavior, and compaction procedure.

## Replacement Compare-And-Swap

```text
operator reads current manifest logical hash
  -> publish --replace --expected-logical-sha <hash>
  -> verify current tuple and precondition
  -> create and verify candidate snapshot + manifest
  -> retain previous pair while activating candidate pair
  -> reverify active pair
  -> discard previous pair only after success
```

A process failure restores the previous pair. A machine crash during the short
two-file activation window fails checksum validation rather than accepting a
mixed tuple; the retained `.publish.*` directory contains the recoverable prior
pair until the next explicit operator action.

Compaction records all current JSONL identities and hashes as incorporated. It
does not remove those files; deletion is a separate history-retention decision.
