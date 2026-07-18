# P6 Capability Inheritance Evidence

Outcome: `failed` because the context-free held-out agent exceeded the fixed
five-minute completion window. The late artifacts are retained as negative
evidence and are not promoted to a pass.

## Repeated correction and durable capability

Observed repeated correction:

1. P2 corrected active `src/index.ts` guidance from T1-T6 to T1-T12.
2. `benchmark/orchestrator/test/task-manifest.test.ts` still described the
   committed twelve-task manifest as T1-T6 and was corrected to T1-T12.

The durable target-owned capability is
`benchmark/orchestrator/test/phase5-capability-inheritance.test.ts`, SHA-256
`df7593d54fb5f15ce8b9a340bd88b26d04fda99af2b9a1b1e37fd6a6c433cae8`.
It checks the three active task-range surfaces for the retired six-task range
and independently asserts 12 manifest entries from T1 to T12.

Pre-held-out proof at `2026-07-18T07:22:47Z`:

```text
$ npm test -- --run benchmark/orchestrator/test/phase5-capability-inheritance.test.ts
Test Files  1 passed (1)
Tests       1 passed (1)
exit_code=0
```

## Held-out comparable task

Seeded target: `README.md`.

- Clean SHA-256:
  `df9f67a1652a41d8e5d8661f000e4d811f734fd66d4c842e51966d13bbf48574`
- Seed SHA-256:
  `3ece615ee85f290ce12685ec73ae426b8522084e0b10c61056e32d35be8976a9`
- Comparable seed: the opening active guidance advertised T1-T6 while still
  claiming 12 manifest tasks.

The fresh agent received no conversation context, original correction
discussion, capability path, test name, or evaluator repair pointer. Its prompt
only described the held-out contradiction, required repository-native proof,
and named the transcript destination.

## Discovery and late result

The raw `held-out-transcript.md` shows this discovery path:

1. Search found the active README contradiction and the 12-entry manifest.
2. Repository search found the inherited capability without evaluator help.
3. The capability failed with `README.md still advertises the retired six-task
   range` (exit 1).
4. The fresh agent repaired only the seeded text.
5. The same capability passed 1/1 and README returned to its exact clean digest.

Environment digest:
`b69c81a8ec42c39d80b0b9f814675646c4f1e39f688aa5a72bab01265e480dde`.

Packet-normalization annotation (added after the source run): the value above
is the source-run legacy digest computed with a trailing newline. The
verifier-canonical packet environment digest, computed without that trailing
newline, is
`b3a3067d79803aa6631ae7cd9f3424e13b102073bd9eb64123407a9ae43ef2dc`.
The failed five-minute outcome remains unchanged.

## Five-minute timeout finding

- Held-out seed/dispatch preparation completed at `2026-07-18T07:23:15Z`.
- The agent's first recorded action was `2026-07-18T07:24:06Z`; this is the
  latest defensible start bound.
- Five minutes from that latest bound ended at `2026-07-18T07:29:06Z`.
- The agent's completed transcript/final verification is timestamped
  `2026-07-18T07:29:28Z`.

Cause and effect: although the inherited capability was discovered and the
target acceptance eventually passed, the required fresh-agent result arrived
after the fixed completion window. The operator did not reconstruct missing
state or convert the late result into success. P6 is therefore a preserved
timeout-negative result with useful late diagnostic evidence.
