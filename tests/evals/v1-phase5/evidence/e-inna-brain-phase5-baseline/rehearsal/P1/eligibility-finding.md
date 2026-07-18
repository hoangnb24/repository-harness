# P1 Rehearsal Eligibility And Result Finding

Evaluated at `2026-07-18T06:33:20Z` by
`codex-phase5-pilot-operator`.

P1 is eligible, not inapplicable. The immutable starting revision contains the
recognized V0 durable schema sequence:

- `scripts/schema/001-init.sql`
- `scripts/schema/002-story-verify.sql`
- `scripts/schema/003-tool-registry.sql`
- `scripts/schema/004-intervention.sql`

`docs/HARNESS_AUDIT.md` also records the 2026-06-11 backup reconciliation and
names the restored source provenance. The inspected revision contains no
`harness.db`, no `scripts/bin/harness-cli`, no archive/export receipt, and no
available V1 cutover subject. Because the card is eligible, these missing
operational artifacts are recorded as a failed/blocking baseline result rather
than being mislabeled inapplicable.

No kill point was selected or exercised: there is no archive transaction to
interrupt and no receipt from which fresh V1 could initialize. Simulating those
identities would fabricate evidence. All four V0 schema bytes and paths remain
unchanged.
