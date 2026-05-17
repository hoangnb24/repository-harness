# Phase 04 — Project Status Snapshot Playbook

> **Independence note:** Same-session authoring. Skeleton in body is
> canonical.

## Context Links

- Parent plan: `plan.md`
- Decision: `docs/decisions/0005-roadmap-execution-direction.md` § 6
  (project status is a PLAYBOOK, NOT a script).
- Source pattern: ck:project-status (Tier S item; rejected as script
  per decision 0005 § 6).
- Harness anchors:
  - `docs/HARNESS.md` § Source Hierarchy (sources the agent reads).
  - `docs/TEST_MATRIX.md` (proof state input).
  - `docs/stories/` (story state input).
  - `docs/decisions/` (architecture history).

## Overview

- **Priority:** Fourth in Plan D — read-only state observer.
- **Status:** pending.
- **Brief:** Ship a portable playbook that tells an agent how to
  produce a "where are we now" snapshot by reading the existing
  source-hierarchy files. No write side. Output is a markdown report
  plus a one-line summary the agent can echo at session start.

## Key Insights

- Decision 0005 § 6 explicitly rejected Python-script implementation —
  agent-read is the right shape until measured bottleneck appears.
- Status snapshot answers 4 questions: which stories are live? which
  proofs pass? which decisions still bind today's work? which playbooks
  are pending promotion?
- Output has two consumers: (a) full markdown report for archiving in
  `plans/reports/status-<date>-<slug>.md`, (b) one-line summary the
  agent can use at session start ("12 stories open, 3 blocked; matrix
  62% green; 2 experimental playbooks past 2-use threshold").
- The playbook is read-only by contract — any "fix the gap" action it
  surfaces becomes a separate task / backlog entry.

## Requirements

Functional:
- New playbook `docs/playbooks/project-status-snapshot.md` covering:
  - When to run (session start, weekly status, audit prep).
  - Inputs (story files, TEST_MATRIX, decisions, recent reports).
  - 4-section report shape (stories / proof / decisions /
    playbook lifecycle).
  - One-line summary template.
  - Hand-off (where to save report).
- Register in `docs/playbooks/README.md` under "Workflow recipe"
  group (multi-step sequenced read).

Non-functional:
- Playbook under 160 lines.
- Zero "run this script" instructions — strictly agent-read.
- Read-only contract explicitly stated in body.

## Architecture

```text
docs/playbooks/
├── project-status-snapshot.md       ← NEW
│   ├─ When to run (session start; weekly; pre-audit)
│   ├─ Inputs (4 source paths)
│   ├─ Report shape (4 sections + one-line summary)
│   ├─ One-line summary template
│   ├─ Read-only contract (explicit)
│   └─ Hand-off (save path + summary echo)
└── README.md (updated)

Outputs at use-time:
plans/reports/status-<YYYYMMDD>-<HHMM>-<scope-slug>.md
```

## Related Code Files

To modify:
- `docs/playbooks/README.md` — add row.

To create:
- `docs/playbooks/project-status-snapshot.md`.

## Implementation Steps

1. Draft playbook from skeleton.
2. Register in README.
3. Grep verify: `grep -l "project-status-snapshot" docs/playbooks/README.md`.
4. Confirm no "script" / "python" / "shell" instructions in body:
   `grep -iE "python|\\.sh|\\bbash\\b|\\bscript\\b" docs/playbooks/project-status-snapshot.md`
   returns nothing (or only inside the read-only-contract explanation).
5. Commit.

## Open Question Resolution

**Q1 (Plan D plan.md):** Output format — markdown only, or also
one-line summary? **A:** Both. Markdown for archive; one-line summary
for session-start echo. The playbook defines a template for each.

## Plan E Overlap Check

- A1 XRE validate: validates *requirements* state. Status snapshot
  reports *story+proof+decision* state. Adjacent but distinct.
- A2 feature register: tracks features explicitly. Status snapshot
  derives feature implicitly from story state. If status snapshot
  output is consistently consumed for "what features exist", that's a
  Plan E trigger — log as Plan E evidence if observed.
- A3 QA video evidence: no overlap.

**Action:** Document in phase body that "if status snapshot is being
manually post-processed to answer 'what features exist', that
signals Plan E A2 (feature register) friction. Log to
`plans/reports/plan-e-trigger-evidence.md`."

## Todo

- [ ] Draft playbook.
- [ ] Register in README.
- [ ] Grep verify (existence + no-script).
- [ ] Commit.

## Success Criteria

- File under 160 lines.
- 4 report sections defined (stories / proof / decisions / playbook
  lifecycle).
- One-line summary template present.
- Read-only contract explicitly stated.
- No "run this script" instruction; agent-read only.
- Registered in `docs/playbooks/README.md` under "Workflow recipe".

## Risk

Tiny. Docs only.

## Security Considerations

Status snapshot must not echo credentials or PII when reading story
files. Add one-line "redact secrets and PII before saving report"
warning.

## Next Steps

- If output is consistently post-processed for feature-listing, log
  as Plan E A2 trigger evidence per goal directive.
- Future plan may promote to script when speed becomes a measured
  bottleneck (decision 0005 § 6 escape clause).
