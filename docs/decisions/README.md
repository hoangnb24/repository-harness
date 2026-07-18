# Decisions

Decision records explain why important product, architecture, or harness choices
were made.

Use `docs/templates/decision.md` when adding a new decision.

After adding or updating a markdown decision file, also add or refresh the
durable decision row:

```bash
scripts/bin/harness-cli decision add \
  --id 0008-auth-boundary \
  --title "Auth Boundary" \
  --doc docs/decisions/0008-auth-boundary.md
```

Trace fields such as `--decisions` summarize task-level choices. They do not
count as the Harness decision log.

## Current V1 Decisions

- `docs/decisions/0015-phase6-cold-warm-evaluation-custody.md` fixes
  clean-clone versus isolated-V0-copy custody, evidence identities, external
  trust, sensitive-byte exclusions, and deferred live-card evidence.
- `docs/decisions/0016-phase6-framework-acceptance-and-phase7-opening.md`
  accepts the Phase 6 framework for sequencing and opens Phase 7 engineering
  while keeping efficacy claims, Phase 7 acceptance, and release promotion
  blocked on the deferred experiments plus complete portability proof.

Add a decision when:

- A locked technical choice changes.
- A product rule changes meaningfully.
- A validation requirement is added, removed, or weakened.
- A high-risk feature chooses one design over another.
- Auth, authorization, data ownership, audit/security, or API behavior changes.
- The source-of-truth hierarchy changes.
