# Session Retrospective — ClaudeKit Custom Port

**Date:** 2026-05-17 · **Commits in session:** 9 (so far) · **Branch:** main

This is the first run of `docs/playbooks/session-retrospective.md` —
applied as a worked example to validate the playbook shape.

## Tasks Completed

- `b7a4b27` — Decision 0004 (adopt selective ClaudeKit Custom patterns).
- `661df0f` — Plan A implementation: traceability tokens, patch
  extension protocol, bilingual pattern, composition pattern.
- `9ae7c4c` — Scaffolding: scan report, port-answers report,
  roadmap report, Plan A directory.
- `dbf308a` — Independence Principle + Playbook Lifecycle invariants
  added to HARNESS.md + template.
- `4914570` — Lifecycle markers applied to 3 Plan A playbooks.
- `8e93a2f` — Backlog promotion rule + 4 proposed items (B1-B5).
- `63acea0` — Decision 0005 (roadmap execution direction).
- `f93023c` — Plans B/C/D/E scaffolding (C full, B/D/E overview).
- `30ba703` — Backlog item B6 (existing playbook /ck:* refs cleanup).

Decision 0006 (this retro mechanic) + session-retrospective playbook
will commit after this report is saved.

## Friction Encountered

1. **Hidden coupling not visible until explicit question.**
   - **What:** ClaudeKit Custom port shipped 3 playbooks before user
     asked "what if claudekit-custom not installed?". That question
     surfaced the Independence Principle gap.
   - **Where:** session conversation, not in any docs.
   - **Root cause:** harness had no explicit invariant about external
     skill independence. Each playbook author was free to assume CK.
   - **Recurring?:** first-time, but the *kind* of friction (hidden
     assumption surfacing late) is recurring in any docs framework.
   - **Suggested capture:** done — `HARNESS.md` § Independence
     Principle (`dbf308a`).

2. **Per-task self-improvement was not enough.**
   - **What:** Even after running step 9 across many tasks, the
     session-level insight (e.g. "always audit assumptions before
     extending playbooks") had no home.
   - **Where:** entire session — no retro existed until the user
     asked about it.
   - **Root cause:** Task Loop step 9 is per-task; insight that
     emerges only after multiple tasks compose is invisible.
   - **Recurring?:** first-time observed, but structurally guaranteed
     to recur on any multi-task session.
   - **Suggested capture:** done — Decision 0006 + this playbook.

3. **Tier S items silently dropped during decision 0004 drafting.**
   - **What:** Decision 0004 wrapped 5 patterns (Q1-Q5) but failed to
     account for the other Tier S items (E2E flow, code review
     scoring, handover/project-status). User caught the gap.
   - **Where:** decision 0004 drafting.
   - **Root cause:** decision umbrella scope was narrower than the
     scan inventory.
   - **Recurring?:** first-time, but easy to recur if next decision
     wraps a subset of a larger scan without explicit "items not
     covered" list.
   - **Suggested capture:** roadmap report (`f93023c`) recovered all
     items. Pattern worth promoting to a playbook for "decision
     scoping": always list "items in scan not covered by this
     decision" before publishing.

4. **Lifecycle of new playbooks had no status until asked.**
   - **What:** 3 Plan A playbooks shipped with no indication that
     they were unverified.
   - **Where:** Plan A playbook files.
   - **Root cause:** harness had no lifecycle convention.
   - **Recurring?:** structurally guaranteed without convention.
   - **Suggested capture:** done — `HARNESS.md` § Playbook Lifecycle
     (`dbf308a`).

## Playbooks Used

- `docs/playbooks/template.md` — referenced when writing the 3 new
  playbooks. UX: worked as written. Lifecycle: shape-guide template,
  no lifecycle line itself. **Promote?:** not applicable.
- `docs/playbooks/PATCH-EXTENSION-PROTOCOL.md` — used as the
  authoritative spec for `HARNESS:EXT` markers; referenced from
  decision 0004. Lifecycle: experimental. UX: not yet exercised on
  a real install — too early to promote. **Promote?:** not-yet.
- `docs/playbooks/bilingual-delivery-template-pattern.md` — same
  status. **Promote?:** not-yet.
- `docs/playbooks/playbook-composition-pattern.md` — same status.
  **Promote?:** not-yet.

No existing playbook was exercised on a real story this session, so
no Variant section was added.

## Lifecycle Promotion Candidates

None. All `experimental` playbooks shipped this session are still
awaiting their first real use on a non-meta story. The retro
playbook itself is also `experimental` and this run is a meta
worked-example, not a real-use exercise.

## Backlog Candidates

| Title | One-line problem | Demand evidence | Promotion check |
|-------|------------------|-----------------|-----------------|
| B1 file-naming convention | Discovery artifacts have no portable file-name shape | 0 hits | no — proposed, awaiting threshold |
| B2 persona discovery process | No canonical persona artifact short of Plan C RRI playbook | 0 hits | no — defer until Plan C ships |
| B3 brand-direction discovery process | UI design system playbook covers UI; non-UI surfaces lack shape | 0 hits | no — proposed |
| B5 multi-image / multi-artifact analysis | Multi-artifact discovery batches have no analysis shape | 0 hits | no — proposed |
| B6 existing playbook /ck:* cleanup | 5 playbooks inline /ck:* refs in core logic, violates Independence Principle | 1 hit (this session's audit) | no — needs 1+ more or 3+ hits |

All five sit at `proposed` with no auto-promotion this session.

**New candidate from this session's friction analysis:**

| Title | One-line problem | Demand evidence | Action |
|-------|------------------|-----------------|--------|
| B7 (potential) "decision scoping playbook" | New decisions wrapping a subset of a larger scan should explicitly list items NOT covered | 1 hit (decision 0004 silently dropped Tier S items #4, #7, #8) | Defer — single hit. If a future decision repeats the gap, add to backlog. |

Hold B7 off the backlog for now (single hit). Document in this retro so
it surfaces if it recurs.

## Decisions Made

- **0004** — Adopt ClaudeKit Custom patterns (selective). Consequence
  ladder: Plan A executed; Plans B/C/D/E scaffolded; 5 patterns now
  the canonical reference for adoption shape.
- **0005** — Roadmap execution direction. Consequence ladder: Plan C
  is next-to-execute; Plan B awaits trigger; Plan E conditional;
  backlog promotion rule live.
- **0006** — Session retrospective mechanic (this commit pending).
  Consequence ladder: AGENTS.md Task Loop step 9 gains 3 bullets;
  session-retrospective playbook becomes a required step for
  multi-task sessions going forward.

## Recommendations For The Next Agent

1. **Run the retro playbook again next multi-task session.** This
   retro is the first run and a worked example. The next run will
   reveal whether the playbook shape is usable or needs a Variant
   section.

2. **Before executing Plan C, re-read decisions 0005 and 0006.** Plan
   C is the next sequential plan per 0005. Plan C's phase files
   already carry Independence notes per Plan A work, but the agent
   should still confirm.

3. **Before executing Plan B, check trigger conditions** (decision
   0005 § 3). Do not start Plan B speculatively.

4. **When writing the next decision umbrella, run "items not
   covered" check.** Friction #3 above predicts this could recur.

5. **The patch-extension protocol is honour-system until Plan B
   installer work lands.** Document that explicitly when touching
   `install-harness.sh` next time.

## Open Threads

- **Plan C execution** — `plans/260517-1242-discovery-and-delivery-loop/`
  is ready with full phases. Awaiting user go.
- **Plan B trigger watchlist** — monitor for installer override use
  or high-risk story moving to prod.
- **Plan D scope** — drafts at execution time per 0005.
- **Plan E gating** — 6-month time-box from when Plans C and D ship.
- **B6 cleanup** — 5 existing playbooks have inline `/ck:*` refs;
  awaiting demand evidence to promote.
- **Lifecycle promotion** — 3 Plan A playbooks + this retro
  playbook + session-retrospective all sit `experimental`. Next
  session that uses any without modification should promote.
