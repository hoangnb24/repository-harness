# P1 Eligibility Finding

Evaluated at `2026-07-18T07:03:58Z` against starting revision
`090f6d1c33d9f006cc8e95491badc33a8053c89f`.

Inspected paths and facts:

- `harness.db` is absent from the locked worktree.
- `scripts/bin/harness-cli` is absent from the locked worktree.
- `scripts/schema/001-init.sql` through `scripts/schema/005-phase5-evolution.sql`
  are tracked implementation schemas, not a recognized live V0 durable-state
  instance with provenance.
- `docs/TEST_MATRIX.md` is a policy placeholder; it is not supported V0 state
  requiring archive-only cutover.

Cause and effect: because the immutable starting revision contains no recognized
V0 database or exportable V0 durable instance, there is no source state, kill
point, archive receipt, or V0 provenance that can be exercised without
inventing data. P1 is therefore inapplicable and remains represented by this
concrete finding rather than being omitted.
