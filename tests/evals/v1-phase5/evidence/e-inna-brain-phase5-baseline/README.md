# E-INNA Brain Phase 5 Baseline Evidence

This directory contains unsigned operator evidence for the frozen
`repository-harness` Phase 5 P0-P7 cards at catalog SHA-256
`678e00b103bf32dc6fbdd6617bba7eda710e65cdb1bf43b69467cff594f0a594`.

## Identity And Custody

- Pilot id: `e-inna-brain-phase5-baseline`
- Starting revision: `9be2b9b624f29c2c4f93bb576485fd8de2085af4`
- Worktree: `agent-phase5-pilot-einna`
- Evaluation subject: the pre-candidate repository-native Harness present at
  the starting revision
- Evidence owner: repository target; all writes are confined to this isolated
  worktree

This is not an authenticated live packet. It deliberately contains no owner
private key, owner signature, `authentication.json`, trusted-owner registry, or
claim that owner authentication has occurred. The orchestrator must supply
owner enrollment, an external trust registry, repository bundle, complete
manifest, and signature after reviewing these bytes.

## Trust Timing Correction

External per-repository evaluation trust was formally established at
`2026-07-18T06:40:32Z`. All activity before that instant is stored only below
`rehearsal/`; it is setup/rehearsal evidence and must not be cited as a final
P0-P7 result. Final `environment.json`, `eligibility.json`, card artifacts, and
baseline times are locked after the trust instant.

## Safety Boundary

The run is local and deterministic. It does not push, deploy, contact providers,
mutate a database, load secrets, or invoke a live external service. The
user-owned source-checkout paths `.harness-backup/` and
`docs/operations/production-environment-cost-guide.md` are excluded from every
inventory, copy, digest, diff, and commit.

The locally cached dependency graph was restored before the environment lock
with `pnpm install --frozen-lockfile --offline`: 472 packages were reused, zero
were downloaded. The locked runtime is Node `22.22.3`, which is below the
repository contract `>=24 <25`; every Node result must retain that warning.

## Digest Convention

For self-identifying JSON records, the stored digest is SHA-256 over canonical
JSON with the self-digest field removed, UTF-8 encoded, sorted keys, compact
separators, and one trailing newline. Packet assembly must re-check this
convention against the external verifier before publication.

## Card Lock

| Card | Disposition | Locked acceptance argv | Intended result |
| --- | --- | --- | --- |
| P0 | eligible | `git diff --check` | failed/unresolved if installed subject commands remain absent |
| P1 | eligible | `git diff --check` | failed if archive/export/receipt cannot be produced |
| P2 | eligible | `pnpm test:architecture` | pass with zero V1 core commands |
| P3 | eligible | `pnpm exec vitest run test/operational-metadata-adapter.spec.ts test/chat-contract.spec.ts test/mock-integration.spec.ts` | fresh-agent resume and pass |
| P4 | eligible | `pnpm test:architecture` | seeded failure, smallest repair, identical check pass |
| P5 | eligible | `pnpm typecheck` | compiler feedback, smallest repair, pass |
| P6 | eligible | `pnpm test:architecture` | durable dynamic-import enforcement plus held-out fresh-agent use |
| P7 | eligible | `pnpm exec prettier --check docs/evidence/phase5-pilot-einna/P7/garden-fixture.json` | first bounded repair, second no-op |

All `pnpm` commands resolve through the locked cached pnpm `10.30.1` binary
and local Node `22.22.3`; the executable token remains exactly `pnpm`.

## Cause And Effect

1. The installed Harness CLI is absent from the pinned revision, so P0 cannot
   truthfully report a ready installed subject and P1 cannot produce a V0
   archive/receipt through the documented operational path.
2. The application still has deterministic repository-native validation, so
   P2-P7 can exercise local architecture, compiler, test, and formatting
   feedback without providers or secrets.
3. P4 and P5 use removable untracked seeds, so the intended failure is proven
   while target-owned baseline bytes return to their original digests.
4. P6 retains only the reusable checker/test improvement. The held-out seed was
   absent when the fresh agent was interrupted, but the agent supplied no
   transcript, discovery path, environment comparison, or acceptance output;
   consequently inheritance failed and no repair credit is inferred.
5. P7 confines gardening to one evidence fixture, so the second run can prove
   convergence by an identical digest inventory.

## Final Card Outcomes

| Card | Outcome | Immediate cause |
| --- | --- | --- |
| P0 | failed | Documented Harness CLI path is absent. |
| P1 | failed | No CLI archive/export/receipt path or V1 receipt exists. |
| P2 | passed | Ordinary architecture check passed with zero V1 core commands. |
| P3 | failed | Fresh continuation timed out without independently usable resume evidence. |
| P4 | passed | Architecture seed failed, was removed, and the identical check passed. |
| P5 | passed | Compiler feedback identified the seed; removal restored typecheck. |
| P6 | failed | Durable capability passed locally, but held-out inheritance timed out without proof. |
| P7 | passed | First gardening run converged and the identical second run was a no-op. |
