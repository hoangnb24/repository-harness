# P4 Native Invariant Repair Evidence

Outcome: `passed` with one disclosed evaluator-error intervention.

Named invariant and locked acceptance command:
`npm test -- --run benchmark/orchestrator/test/task-manifest.test.ts`.

Seeded path: `benchmark/tasks/manifest.json`.

- Starting SHA-256:
  `7427d30394712bada3a8bf723b7e14c9fd38a989f3f8b02bbee6a3504fb34989`
- Seeded SHA-256:
  `8b787d27e6049ad03f16d78e36897319a5a7c81e0839ee6c242236d606fcf42d`
- Seed: T4 authentication's `expectedLane` changed from `high_risk` to
  `normal`.

## Failing run

```text
$ npm test -- --run benchmark/orchestrator/test/task-manifest.test.ts
FAIL TaskManifestLoader > loads the committed T1-T6 manifest in dependency-valid order
Expected T4 expectedLane: "high_risk"
Received T4 expectedLane: "normal"
Test Files  1 failed (1)
Tests       1 failed | 2 passed (3)
exit_code=1
```

Cause and effect: authentication is a hard-gate high-risk task. The seeded
`normal` lane made the manifest loader return the wrong contract, so the native
manifest invariant failed at the exact T4 assertion.

## Repair and disclosed intervention

The intended repair was the one-field restoration to `high_risk`. The first
repair patch was under-contextualized and accidentally changed T2 from `normal`
to `high_risk` while leaving T4 seeded. The operator inspected the diff before
rerunning acceptance, recorded the evaluator error, and applied a contextual
repair restoring both T2 and T4. No hidden correction relay occurred.

## Passing identical run

```text
$ npm test -- --run benchmark/orchestrator/test/task-manifest.test.ts
Test Files  1 passed (1)
Tests       3 passed (3)
exit_code=0

$ shasum -a 256 benchmark/tasks/manifest.json
7427d30394712bada3a8bf723b7e14c9fd38a989f3f8b02bbee6a3504fb34989  benchmark/tasks/manifest.json
exit_code=0

$ git diff --no-ext-diff -- benchmark/tasks/manifest.json
exit_code=0
```

The final digest equals the starting digest and the final target diff is empty,
so the seeded violation and the mistaken intermediate edit were both fully
reversed without unrelated content changes.
