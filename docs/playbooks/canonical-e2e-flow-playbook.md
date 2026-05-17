# Canonical E2E Flow Playbook

**Lifecycle:** experimental · **First use:** TBD · **Verified by:** none

> Phase-typed shape for designing E2E tests that mirror real user
> journeys. Each test cites its TC token; one journey per file.

## When To Run

- Per story phase, after SC tokens are stable and before writing the
  E2E test files.
- When refactoring an existing E2E suite that has degraded into
  step-by-step assertions instead of journey-based assertions.

Skip when the lane is tiny — unit + integration is sufficient.

## Flow Types

Pick ONE per E2E file. Mixed files become hard to debug and cap out
on assertion noise.

| Type | Shape | Use when |
| --- | --- | --- |
| Form | Render → fill → submit → assert visible result + persisted state | Single screen with input → output (signup, settings save, role update) |
| Workflow | Multi-screen sequence representing a user goal across N steps | User completes a task spanning ≥2 screens (checkout, onboarding, approval chain) |
| Readonly | Navigate → assert state matches expected snapshot | Dashboards, reports, search result pages — no mutation |
| Mixed | Workflow that includes one readonly verify step | Complete a workflow, then jump to a dashboard to verify the result appears |

## Per-Type Skeleton

### Form

```pseudo
test "US-NNN.TC-001 — manager updates own profile name":
  given: logged in as manager (seed user `seed-manager-1`)
  when:  navigate to /settings, fill name="New Name", click Save
  then:  assert toast "Saved"
         assert DB row users.id=<seed-manager-1>.name == "New Name"
```

### Workflow

```pseudo
test "US-NNN.TC-007 — member role update + audit log entry":
  given: logged in as manager
  steps:
    1. Navigate to /team
    2. Click member row
    3. Select role=admin from dropdown
    4. Click Confirm
    5. Navigate to /audit
  then:  assert audit row "role-changed by <manager>" visible
         assert member's role badge in /team shows "admin"
```

### Readonly

```pseudo
test "US-NNN.TC-010 — dashboard shows current period numbers":
  given: seeded period data via `seed-period-q1`
  when:  navigate to /dashboard
  then:  assert kpi "Active users" == 142
         assert chart series count == 3
```

### Mixed

```pseudo
test "US-NNN.TC-015 — invite teammate then verify in roster":
  given: logged in as admin
  steps:
    1-4. (Workflow) Open invite dialog, enter email, send
    5.   (Readonly) Navigate to /team, assert row appears
```

## Cap

- One user journey per E2E file. If the journey forks, write a sibling
  file (`<base-name>-fork-a.spec.<ext>`).
- Recommended ≤ 8 assertion calls per file. Beyond that, the test is
  doing two things — split.

## Hand-Off

- Each test's TC token (`US-NNN.TC-001`) becomes a
  `docs/TEST_MATRIX.md` row in the E2E column.
- The journey description in the test header is reusable as a video
  script if QA video evidence is required (Plan E A3 — flag if that
  hand-off becomes routine).

## Variant Section

(Append a Variant when this flow shape fails or partially works. Do
not delete the original 4 types.)

## Related

- `docs/HARNESS.md` § Traceability Tokens — TC token format.
- `docs/playbooks/scenario-taxonomy-playbook.md` — SC tokens that
  E2E tests prove.
- `docs/playbooks/seed-data-pattern.md` — provides the seed identifiers
  this playbook's skeletons reference.
- `docs/playbooks/README.md` § Use Order — Variant convention.
