# P3 Rehearsal Fresh-Agent Transcript

## Resume Boundary And Safety

- Resumed from `resume-plan.md` after the first agent's fixed interruption
  point. The inherited focused result was 1 file and 11 tests passed, exit 0,
  from `2026-07-18T06:33:39Z` through `2026-07-18T06:33:46Z`.
- Read only the governing instructions, target-owned resume state, locked
  environment, CA-110 validation packet, and files needed to perform and
  document this validation.
- Made no product, test, deployment, provider, secret, database, backup, or
  production cost-guide change.
- Did not call a provider, perform live smoke/UAT, commit, push, or deploy.

## Locked Environment Comparison

Comparison recorded at `2026-07-18T06:38:25Z` (UTC). The comparison command
completed with exit code 0.

| Property | Locked | Observed | Result |
| --- | --- | --- | --- |
| Canonical environment SHA-256 | `aa2147d2628e1347381936565702b561f02030fb5a4d1a3a798495c677bf489c` | `aa2147d2628e1347381936565702b561f02030fb5a4d1a3a798495c677bf489c` | match |
| Catalog fixture SHA-256 | `678e00b103bf32dc6fbdd6617bba7eda710e65cdb1bf43b69467cff594f0a594` | `678e00b103bf32dc6fbdd6617bba7eda710e65cdb1bf43b69467cff594f0a594` | match |
| Operating system | macOS 26.4 build 25E246 | macOS 26.4 build 25E246 | match |
| Architecture | arm64 | arm64 | match |
| Git | 2.50.1 Apple Git-155 | 2.50.1 Apple Git-155 | match |
| Node | 22.22.3 | 22.22.3 | match |
| pnpm | 10.30.1 | 10.30.1 | match |

The digest was recomputed as the SHA-256 of the sorted compact JSON payload
after removing the self-referential `environment_sha256` member. The catalog
fixture was resolved relative to the evidence root, as
`docs/evidence/phase5-pilot-einna/contracts/cards/catalog.json`.

The default shell path did not expose `node` or `pnpm`. This was not a blocker:
the run prepended the locked Node directory
`/Users/tubakhuym/.hermes/node/bin` and the corresponding Corepack shim
directory
`/Users/tubakhuym/.hermes/node/lib/node_modules/corepack/shims`. No dependency
or environment file was changed.

## Commit Identity

The following read-only checks ran from `2026-07-18T06:39:09Z` through
`2026-07-18T06:39:09Z` (UTC):

| Ordered argv | Exit code | Output |
| --- | ---: | --- |
| `["git","rev-parse","9be2b9b624f29c2c4f93bb576485fd8de2085af4^{commit}"]` | 0 | `9be2b9b624f29c2c4f93bb576485fd8de2085af4` |
| `["git","rev-parse","HEAD"]` | 0 | `e6b8a3af83e55397011da121ed3278b9df11ac9d` |

Thus the required commit resolves, while the current locked worktree remains
at the separately recorded `HEAD`.

## Original Acceptance Run

- Ordered argv:
  `["pnpm","exec","vitest","run","test/operational-metadata-adapter.spec.ts","test/chat-contract.spec.ts","test/mock-integration.spec.ts"]`
- Start: `2026-07-18T06:38:37Z` (UTC)
- End: `2026-07-18T06:38:42Z` (UTC)
- Exit code: 0
- Standard output: 9 lines, 257 bytes
- Standard error: 0 lines, 0 bytes
- Vitest result: 3 files passed out of 3; 52 tests passed out of 52
- Vitest-reported duration: 4.64 seconds

Captured standard output:

```text

 RUN  v4.1.5 /Users/tubakhuym/.herdr/worktrees/e-inna-brain/agent-phase5-pilot-einna


 Test Files  3 passed (3)
      Tests  52 passed (52)
   Start at  13:38:38
   Duration  4.64s (transform 237ms, setup 0ms, import 1.34s, tests 4.70s, environment 0ms)

```

Captured standard error was empty.

`package.json` still requires Node `>=24 <25`, while the preserved lock uses
Node 22.22.3. Contrary to the historical validation note, this exact acceptance
run emitted no engine warning. The absence of emitted warning text does not
make the locked Node version satisfy the package engine contract.

## Blockers And Unattempted Work

- Genuine blockers: none.
- Live provider smoke, CA-102 UAT, E-INNA rendering verification, and owner
  sign-off were not attempted. They remain separate evidence gaps by design.
