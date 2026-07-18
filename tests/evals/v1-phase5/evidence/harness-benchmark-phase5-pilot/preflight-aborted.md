# Aborted Preflight Interval

Initial locks were recorded at `2026-07-18T07:03:56Z` through
`2026-07-18T07:03:58Z`, and a provisional baseline start was recorded at
`2026-07-18T07:06:48Z`.

The first P2 acceptance attempt then produced:

```text
$ npm run build

> harness-benchmark@1.0.0 build
> tsc

sh: tsc: command not found
exit_code=127
```

Cause and effect: `node_modules` was absent, so the declared repository-native
TypeScript acceptance surface was not equipped. Installing dependencies after
the environment lock would make the provisional interval invalid. The one-byte
source task was restored to the exact starting-revision content, the interval
was aborted before any P0-P7 result was claimed, and dependency setup was moved
before a new final environment/eligibility lock and baseline start.

The canonical `baseline-start.json`, `environment.json`, and `eligibility.json`
now contain the final locks. This document preserves the provisional timestamps
and failure without leaving ambiguous duplicate lock files.
