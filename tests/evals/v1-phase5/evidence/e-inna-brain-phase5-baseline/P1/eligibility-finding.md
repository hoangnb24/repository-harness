# P1 Final Eligibility And Result Finding

Final evaluation ran from `2026-07-18T06:45:08Z` through
`2026-07-18T06:45:08Z`.

P1 is eligible. The immutable starting revision contains the recognized V0
durable schema sequence `scripts/schema/001-init.sql` through
`004-intervention.sql`, and `docs/HARNESS_AUDIT.md` records source provenance.
The inspected revision contains no `harness.db`, no
`scripts/bin/harness-cli`, no archive/export receipt, and no available V1
cutover subject.

Outcome: `failed`. No archive transaction existed, so no kill point could be
truthfully selected or recovered. Simulating an archive or receipt identity
would fabricate evidence. All V0 schema bytes and document paths remain
unchanged; `git diff --check` exited 0.
