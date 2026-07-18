# P3 Rehearsal CA-110 Validation Report

## Scope

This validation re-ran the original credential-free CA-110 acceptance against
the locked repository. It exercised the operational metadata adapter, chat
contract, and mock integration tests together. It did not exercise a live
provider, external service, production environment, or owner UAT.

## Result

**PASS for deterministic local acceptance.** From
`2026-07-18T06:38:37Z` through `2026-07-18T06:38:42Z` (UTC), the exact locked
argv completed with exit code 0:

```text
pnpm exec vitest run test/operational-metadata-adapter.spec.ts test/chat-contract.spec.ts test/mock-integration.spec.ts
```

Vitest reported 3 of 3 files passed and 52 of 52 tests passed. The captured
output was 9 stdout lines (257 bytes) and 0 stderr lines (0 bytes).

The canonical environment digest remained
`aa2147d2628e1347381936565702b561f02030fb5a4d1a3a798495c677bf489c`,
the catalog fixture digest matched, and the locked OS, architecture, Git, Node,
and pnpm identities all matched `environment.json`. The required commit
`9be2b9b624f29c2c4f93bb576485fd8de2085af4` resolved with exit code 0; current
`HEAD` was `e6b8a3af83e55397011da121ed3278b9df11ac9d`.

## Cause And Effect

The passing combined suite provides concrete local evidence for the readiness
transition:

1. When an accepted data-library job leaves an instance with unfinished sync
   work, the metadata adapter exposes that state; the chat boundary therefore
   returns the in-progress warning in both JSON and SSE paths.
2. When the worker marks the job successful and the store becomes active, the
   unfinished condition clears; the next chat response therefore clears the
   warning and can use the active store.
3. When sync fails permanently, readiness is not falsely upgraded; the chat
   path therefore continues to warn.
4. Because readiness is resolved per instance, one tenant's unfinished job
   does not add a warning to another tenant's response.

These cause/effect claims are bounded by the credential-free fixtures covered
by the three passing test files. They do not prove real provider behavior.

## Caveats And Remaining Gap

- The preserved Node 22.22.3 lock is below the package engine requirement of
  Node `>=24 <25`. The acceptance run emitted no engine warning, so no warning
  is claimed in the transcript; the version mismatch nevertheless remains.
- No live-provider smoke was attempted, no CA-102 end-to-end UAT was run, no
  E-INNA rendering was observed, and no owner sign-off was produced.
- Therefore this pass supports the credential-free RAG readiness transition
  only. It does not replace the separate live/UAT release gate.

Genuine blockers encountered: none.
