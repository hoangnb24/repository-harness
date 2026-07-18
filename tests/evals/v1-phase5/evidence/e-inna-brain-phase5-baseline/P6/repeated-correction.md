# P6 Repeated-Correction Evidence

## Comparable Violations

At `2026-07-18T07:02:04Z`, two isolated literal dynamic-import seeds were
present under the existing locked architecture rule:

| Path | Forbidden direction | SHA-256 |
| --- | --- | --- |
| `src/domain/phase5-pilot-dynamic-seed-a.ts` | domain to application | `210676071f20c07df2d9396153705a822c2adc788c8035caa2f4983acbb95555` |
| `src/application/phase5-pilot-dynamic-seed-b.ts` | application to infrastructure | `13fbd382295f1aaf2ca7c3a8dabd40347e7d2f621fea48e8d393828f07eed04c` |

The current target-owned check returned exit 0 and printed `Architecture
boundary check passed.` This was a repeatable two-case false negative: the
dependency directions were forbidden, but changing static import syntax to
literal `import()` bypassed the feedback surface.

## Durable Correction

The smallest durable capability extended the existing import matcher with a
third capture for literal dynamic `import('specifier')` and used that capture in
the existing forbidden-module/layer logic. Two regression tests preserve the
domain and application cases. No second linter, package command, product path,
or provider behavior was added.

With the same two seeds still present, the identical command returned exit 1
at `2026-07-18T07:03:03Z` and named both seed paths and forbidden layers. After
only the seeds were removed, the command returned exit 0 at
`2026-07-18T07:03:23Z` and the focused regression suite passed 1 file/6 tests
at `2026-07-18T07:03:24Z`.

Targeted Prettier validation for the checker and regression file also returned
exit 0. The Node 22 versus required Node 24 engine mismatch remains explicit.

## Broader Validation Result

`pnpm validate:quick` ran from `2026-07-18T07:05:45Z` through
`2026-07-18T07:05:58Z`. Format, lint, and typecheck passed. The full Vitest run
reported 32 files passed, 1 failed, 5 skipped; 231 tests passed, 2 failed, 5
skipped. Both failures were outside this change in
`test/cicd-deploy-script.spec.ts`: macOS `/bin/bash` lacks the Bash 4 `mapfile`
builtin used by `check-schema-change.sh` and `check-platform-change.sh`.
Therefore `validate:quick` exited 1 before its later architecture and secret
steps. This unrelated platform blocker was preserved and not repaired in P6.

## Final Card Outcome

The durable capability was successfully created and validated, but the held-out
fresh agent timed out without recording its discovery path or final acceptance.
P6 therefore has outcome `failed`; seed cleanup and an evaluator architecture
pass are not promoted into inheritance proof.
