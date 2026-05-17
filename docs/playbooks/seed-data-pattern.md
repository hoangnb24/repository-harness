# Seed Data Pattern

**Lifecycle:** experimental · **First use:** TBD · **Verified by:** none

> Deterministic, FK-valid demo data shape for DEV and TEST environments
> only. Ships the pattern, not the data. No locale-specific master
> data.

## When To Use

- Any DB-backed test (integration or E2E) that needs predictable rows.
- Local development bootstrap (`seed:dev`-style command in the
  project's package scripts).

Skip when:

- The test is unit-level and uses framework fixtures (Jest snapshots,
  pytest fixtures, etc.) — fixtures belong in framework docs, not this
  playbook.
- The environment is production. **Never seed production.**

## Deterministic ID Convention

Each seeded row has a stable, prefixed identifier so tests can
reference rows by symbolic name instead of generated UUID.

| Pattern | Example | When to use |
| --- | --- | --- |
| `seed-<entity>-<n>` | `seed-user-1`, `seed-order-3` | Unscoped entities (top-level domain objects). |
| `seed-<parent>-<entity>-<n>` | `seed-tenant-acme-user-1` | Entities scoped under a parent (multi-tenant, project-scoped, etc.). |

Persist the symbolic ID either as the primary key (when the schema
allows string IDs) or as a unique secondary column the seed code can
look up.

## FK-Valid Construction Order

Insert in dependency order. If A references B, insert B first.

```text
1. Roots: tenant, organisation, account (no inbound FKs).
2. Identity: user, role, permission (FK to roots).
3. Entities: project, document, asset (FK to identity / roots).
4. Relationships: membership, assignment, share (FK to entities).
5. State / events: audit log, notification, transaction (FK to anything).
```

A test that violates this order produces a confusing FK error rather
than a clear "missing parent" signal. Authoring the seed top-down
prevents this.

## Scoped Cleanup

Each seed run owns a scope tag (e.g. `seed:test-run-<uuid>` set on
every inserted row). Cleanup deletes only rows carrying that tag.

```text
cleanup(scope):
  for table in reverse(insertion_order):
    DELETE FROM table WHERE seed_scope = scope
```

Never use `TRUNCATE` or schema-level drops in shared environments —
they erase concurrent test runs.

## No Locale-Specific Data

The pattern explicitly excludes:

- Country / region master data (provinces, postal codes, area codes,
  tax IDs).
- Locale-specific names, addresses, or currency conventions.
- Region-specific compliance fields (national ID, VAT number formats).

Reason: locale data is owned by the org that runs the project. The
harness ships only the shape (deterministic IDs, FK order, scoped
cleanup). Each project provides its own locale fixture file outside
the seed playbook.

## Scope

This playbook covers **DB seed only**. Unit-test fixtures (Jest
snapshots, pytest fixtures, factory_bot definitions) are
framework-specific and out of scope.

## Hand-Off

- Seeded symbolic IDs (e.g. `seed-manager-1`) are referenced by name
  in `docs/playbooks/canonical-e2e-flow-playbook.md` skeletons.
- Seed run tag (`seed-scope`) appears in test logs so triage can map
  a failing test back to the seed batch that produced its data.

## Variant Section

(Append a Variant when this pattern fails or partially works. Do not
delete the original rules.)

## Related

- `docs/playbooks/canonical-e2e-flow-playbook.md` — consumes seed IDs.
- `docs/HARNESS.md` § Traceability Tokens — TC tokens cite seed IDs
  in test logs.
- `docs/playbooks/README.md` § Use Order — Variant convention.
