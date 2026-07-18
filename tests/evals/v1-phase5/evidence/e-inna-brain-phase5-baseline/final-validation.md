# Final Local Validation

Final validation ran from `2026-07-18T07:17:34Z` through
`2026-07-18T07:17:37Z` under the locked Node 22.22.3 and pnpm 10.30.1
environment.

| Command | Exit | Concrete result |
| --- | ---: | --- |
| `pnpm typecheck` | 0 | TypeScript compiled without emitting files. |
| `pnpm test:architecture` | 0 | Strengthened static/dynamic boundary check passed. |
| `pnpm exec vitest run test/architecture-checker.spec.ts` | 0 | 1 file and 6 tests passed in 241ms. |
| `pnpm exec prettier --check docs/evidence/phase5-pilot-einna/P7/garden-fixture.json` | 0 | Fixture uses Prettier style. |
| `pnpm validate:secrets` | 0 | No high-confidence committed secret pattern found. |
| `git diff --check` | 0 | No whitespace error in tracked diffs. |

Every pnpm invocation retained the unsupported-engine warning because the
repository requests Node `>=24 <25`.

The broader `pnpm validate:quick` run from `07:05:45Z` through `07:05:58Z`
failed with exit 1 after format, lint, and typecheck passed: 2 existing CI/CD
script tests require Bash `mapfile`, unavailable in macOS Bash 3.2. It reported
32 test files passed, 1 failed, 5 skipped; 231 tests passed, 2 failed, 5
skipped. That unrelated platform failure was not repaired or hidden.
