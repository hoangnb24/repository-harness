# Phase 03 — Project Closure Story Template

> **Independence note:** Same-session authoring. Skeletons in body are
> canonical.

## Context Links

- Parent plan: `plan.md`
- Decision: `docs/decisions/0005-roadmap-execution-direction.md`.
- Sibling templates:
  - `docs/templates/delivery-closure-story/` (Plan C output — per-release).
  - `docs/templates/high-risk-story/` (shape reference for both
    closure templates).
- Harness anchors:
  - `docs/HARNESS.md` § Traceability Tokens.
  - `docs/FEATURE_INTAKE.md` (registers story shapes).

## Overview

- **Priority:** Third in Plan D — consumes phase-01 + phase-02
  artifacts as inputs to handover documentation.
- **Status:** pending.
- **Brief:** Ship `docs/templates/project-closure-story/` — a new story
  shape mirroring `delivery-closure-story/` (4 files, same proportions)
  but scoped to end-of-PROJECT handover (not end-of-release).

## Key Insights

- Per-release closure = one story shipped, signoff for that increment.
- Per-project closure = handover of entire project ownership: docs,
  decisions, credentials, training. Distinct lifecycle event with
  distinct artifact set.
- Mirroring delivery-closure-story's 4-file shape keeps the index
  consistent (overview + 3 numbered files).
- No secrets in git: credentials handover uses encrypted references
  (e.g. "see vault at <path>", "see 1Password share `XXX`"), not raw
  values.

## Requirements

Functional:
- New directory `docs/templates/project-closure-story/` with 4 files:
  - `overview.md` — closure header (project name, owner change, dates).
  - `01-handover-docs.md` — README + decisions index (where to read).
  - `02-credentials-handover.md` — encrypted reference manifest.
  - `03-knowledge-transfer.md` — training resources, runbooks, sessions.
- Register the new shape in `docs/FEATURE_INTAKE.md` — single bullet
  added next to the existing `delivery-closure-story/` line (under
  High-Risk lane requirements).

Non-functional:
- Each template under 80 lines (matches delivery-closure-story
  proportions).
- All tokens placeholder (`US-NNN.REQ-MMM`, etc.) where applicable.
- No locale-specific words; no Telegram lock-in.
- One-line FEATURE_INTAKE registration.

## Architecture

```text
docs/templates/
├── high-risk-story/                    (existing)
├── delivery-closure-story/             (Plan C output — per-release)
│   ├── overview.md
│   ├── 01-uat-plan.md
│   ├── 02-signoff.md
│   └── 03-client-update.md
└── project-closure-story/              ← NEW (per-project)
    ├── overview.md
    ├── 01-handover-docs.md
    ├── 02-credentials-handover.md
    └── 03-knowledge-transfer.md

docs/FEATURE_INTAKE.md
└─ High-Risk Requirements — add 1-line bullet for project-closure-story
```

## Related Code Files

To modify:
- `docs/FEATURE_INTAKE.md` — single bullet.

To create:
- 4 files under `docs/templates/project-closure-story/`.

## Implementation Steps

1. Create directory + 4 files using skeletons below.
2. Register single bullet in FEATURE_INTAKE.md under High-Risk
   Requirements (next to existing delivery-closure-story line).
3. Grep verify:
   - `ls docs/templates/project-closure-story/ | wc -l` returns 4.
   - `grep -l "project-closure-story" docs/FEATURE_INTAKE.md` returns.
   - Each file cites at least one composite token placeholder where
     applicable.
   - No `Telegram` / `Vietnamese` / `VN` strings.
4. Commit.

## File Skeletons

### overview.md

```markdown
# Project Closure — <project-name>

## Project

Repo: <git url or clone path>
Production URL(s): <list>
Stack: <one-line stack summary>

## Handover Date Range

Start: YYYY-MM-DD · End: YYYY-MM-DD

## Outgoing Owner

Name: <name> · Role: <role> · Final day: YYYY-MM-DD

## Incoming Owner

Name: <name> · Role: <role> · First day owning: YYYY-MM-DD

## Outcome

handover-complete | partial | failed

## Required Artifacts

- [ ] `01-handover-docs.md` index complete
- [ ] `02-credentials-handover.md` cross-checked with vault
- [ ] `03-knowledge-transfer.md` sessions logged
- [ ] All in-flight `US-NNN.REQ-MMM` items either delivered or
      reassigned with new owner

## Open Threads

Bullet list. Each links to a story, backlog entry, or decision doc.
```

### 01-handover-docs.md

```markdown
# Handover Docs Index — <project-name>

## Read In This Order

1. `README.md` — project overview.
2. `docs/HARNESS.md` (if harnessed) — operating model.
3. `docs/product/*` — current product contract.
4. `docs/decisions/*` — why important choices were made.
5. `docs/stories/epics/*` — recent + open story packets.
6. `docs/TEST_MATRIX.md` — proof status.

## Key Decisions

| Decision | Why it matters today |
| --- | --- |
| `docs/decisions/NNNN-title.md` | <one-line consequence still in force> |

## Open Stories at Handover

| Story | Status | New owner |
| --- | --- | --- |
| `US-NNN-slug.md` | in progress / blocked / awaiting review | <name> |

## Maintenance Surfaces

- Dependencies last updated: YYYY-MM-DD.
- Known tech debt entries: link to backlog rows.
```

### 02-credentials-handover.md

```markdown
# Credentials Handover — <project-name>

> **No raw secrets in this file.** All entries are REFERENCES to a
> secret store. Verify access works before signoff.

## Secret Stores Used

| Store | Purpose | Access mechanism |
| --- | --- | --- |
| <vault name / 1Password vault / cloud KMS> | <prod, staging, dev> | <SSO group / shared invite> |

## Required Credential Categories

| Category | Reference (NOT the value) | Owner verified |
| --- | --- | --- |
| Database — prod | <vault path / item name> | [ ] |
| Database — staging | <vault path> | [ ] |
| Cloud provider root account | <vault path> | [ ] |
| Domain registrar | <vault path> | [ ] |
| SSL / TLS cert renewal | <vault path or service> | [ ] |
| Email / transactional sender | <vault path> | [ ] |
| Payment provider | <vault path> | [ ] |
| Monitoring / alerts | <vault path> | [ ] |
| CI/CD runner secrets | <vault path> | [ ] |
| Third-party API keys (per integration) | <vault path> | [ ] |

## Access Verification

Incoming owner attempted access (date + result) for each row above.
Block signoff on any failed verification.

## Rotation Schedule

Any credentials needing rotation in next 90 days:
```

### 03-knowledge-transfer.md

```markdown
# Knowledge Transfer — <project-name>

## Walkthrough Sessions

| Date | Topic | Outgoing | Incoming | Recording / notes link |
| --- | --- | --- | --- | --- |
| YYYY-MM-DD | Architecture tour | <name> | <name> | <link> |
| YYYY-MM-DD | Deploy + rollback live demo | <name> | <name> | <link> |
| YYYY-MM-DD | Incident playbook walkthrough | <name> | <name> | <link> |

## Runbooks To Read

- `docs/playbooks/*` — relevant entries (list specific files).
- Internal runbooks: <list with paths>.

## Recurring Operational Tasks

| Task | Cadence | Owner after handover | Reference |
| --- | --- | --- | --- |
| Dependency review | monthly | <name> | <link> |
| Backup verification | weekly | <name> | <link> |
| On-call rotation update | as needed | <name> | <link> |

## Open Questions From Incoming Owner

Bullet list. Each question gets a date + resolution before signoff.
```

## Open Question Resolution

**Q (Plan D plan.md unresolved):** Project status snapshot output
format — N/A, that's phase-04. No open question for phase-03.

## Plan E Overlap Check

- A1 XRE validate: no overlap.
- A2 feature register: handover-docs.md index touches "what features
  exist" but at link level, not register level. Note in § Related;
  no fold/punt.
- A3 QA video evidence: training-session recordings (`03-knowledge-
  transfer.md` Walkthrough Sessions) overlap with QA video evidence
  in capture format but differ in purpose (training vs proof). No
  fold/punt; separate concerns.

## Todo

- [ ] Create directory + 4 files.
- [ ] Register single bullet in FEATURE_INTAKE.md.
- [ ] Grep verify (file count, intake ref, token placeholders, no
      forbidden strings).
- [ ] Commit.

## Success Criteria

- 4 files exist, each ≤ 80 lines.
- FEATURE_INTAKE.md registers project-closure-story (single line).
- No Telegram / Vietnamese / VN strings.
- Composite token placeholders cited where applicable (overview +
  handover docs minimum).
- Shape mirrors delivery-closure-story (overview + 3 numbered files).

## Risk

Tiny. Docs only. Per-project closure carries credentials-handling
note; no real secrets enter git.

## Security Considerations

`02-credentials-handover.md` must explicitly forbid raw secret values
in the file. References only.

## Next Steps

- Phase 04 (project status snapshot) will use this template's overview
  + handover-docs as inputs to its read-current-state pass.
