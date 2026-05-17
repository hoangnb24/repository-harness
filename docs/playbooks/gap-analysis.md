# Gap Analysis Playbook

**Lifecycle:** experimental · **First use:** TBD · **Verified by:** none

> BA technique. Compare client's current state (As-Is) to desired future state (To-Be), structure the gaps, propose solutions. Stage 3 sub-step of `docs/playbooks/solo-dev-client-delivery.md`, between discovery interview and SOW signing.

## Why This Playbook Exists

Without structured gap analysis:

- Scope creeps. Client adds "small" requests post-SOW because the brief never enumerated what was OUT.
- Solutions are speculative. Team builds features for a To-Be that nobody validated; later finds out the As-Is already handled it differently.
- MoSCoW priority is opinion, not analysis. Must / Should / Could decisions float depending on who's loudest in the meeting.
- BRD / FRD writing starts from a blank page. The gap-to-solution mapping is missing.

With it:

- Each in-scope feature traces to a specific gap (GAP-NNN), which traces to a specific As-Is pain or To-Be metric.
- Out-of-scope is documented WITH REASON, defending SOW § 5 in future disputes.
- Risks and open questions surface before pricing — pricing can include risk premiums or spike budget.

## When To Run

- **Primary:** Stage 3.B of `solo-dev-client-delivery.md`, after the discovery interview (3.A) has surfaced REQ list and decisions log.
- **Secondary:** Mid-project, when a change request touches multiple areas and the team needs to re-baseline.
- **Tertiary:** Pre-phase-2 SOW conversation — re-run with the new To-Be definition (where launched product brought the As-Is forward).

Skip when:

- Lane is tiny — inline narrative in the intake brief is enough.
- Project is greenfield with no prior system or process — there is no As-Is. Skip step 2; build To-Be directly from spec.
- Project is pure refactor / migration with no business-process change — As-Is and To-Be are technical, not behavioral. Document in a decision instead.

## Inputs

The playbook consumes:

1. `docs/intake/YYYY-MM-DD-discovery-summary.md` — REQ list from discovery interview.
2. `docs/intake/YYYY-MM-DD-intake-brief.md` — stated business problem + project type.
3. `docs/discovery/*.md` — raw inputs (meeting notes, screenshots, sample data).
4. Any prior gap analysis from a previous project phase, if mid-project.

If any input is missing, do not skip — pause and gather it. Gap analysis on incomplete inputs produces speculative gaps.

## The 4 Steps

### Step 1 — Define Future State (To-Be)

Make the target unambiguous. Restate the business goals from the intake brief in measurable form.

Outputs go into § 1 of `docs/templates/gap-analysis.md`:

- Business goals (one-line, measurable if possible).
- Success metrics with baseline + target + measurement window.
- Target users × target actions table.
- Constraints (deadline, budget, regulatory, existing-systems-must-keep-running).

Time-box: 30 min. If the To-Be is fuzzy after 30 min, escalate to client — do NOT guess.

### Step 2 — Assess Current State (As-Is)

Map what exists today. This is the step solo devs skip and then regret.

Sources to drain:

- Discovery interview notes (`docs/discovery/`) — process descriptions, tool names, pain points.
- Existing system access — log into the client's current tool, walk through one full workflow.
- Stakeholder roles in As-Is — who does what today.
- Workarounds users invent — the gap between "how the tool is meant to be used" and "how it's actually used".

Outputs go into § 2 of the template:

- Existing process map (numbered steps).
- Existing systems table (system × purpose × owner × integrates × pain).
- Pain points table with verbatim citations from `docs/discovery/`.
- Workarounds list.
- Stakeholder × current responsibility table.

Time-box: 60-90 min for medium-complexity projects. Multi-stakeholder enterprise projects: 4-8 hours over multiple sessions.

### Step 3 — Identify the Gap

Compare § 1 and § 2 dimension-by-dimension. Categorize each gap into one of six classes:

1. **Functional gaps** (features missing).
2. **Process gaps** (workflows missing or broken).
3. **Technology gaps** (systems not integrated).
4. **Data gaps** (data not captured or not accessible).
5. **Role / skill gaps** (people without access or training).
6. **Compliance gaps** (regulation not met).

Each gap gets a local-scope `GAP-NNN` token (`GAP-001`, `GAP-002`, ...). The token traces forward when REQs are written.

Severity per gap:

- **High** — blocks To-Be vision OR is regulatory.
- **Medium** — blocks a goal but workaround exists.
- **Low** — nice-to-have.

Be ruthless. The cost of categorizing wrong is a wrong MoSCoW call in step 4. Re-read each gap once before stamping High.

### Step 4 — Propose Solutions (Plan of Action)

Each gap gets a solution row with: solution shape, owner (vendor / client / both), effort estimate (XS / S / M / L / XL), MoSCoW priority, linked story candidate, and "In SOW § 4?" disposition.

MoSCoW rules:

- **Must** = goes into SOW § 4 in-scope no matter what. Cutting a Must means renegotiating the To-Be vision.
- **Should** = SOW § 4 if budget / time allow. Drop into "phase 1.5" or "phase 2" if not.
- **Could** = default to SOW § 5 out-of-scope. Document as phase-2 candidate.
- **Won't** = explicit reject this project. Goes to `docs/decisions/` with reason.

Force the answer "in SOW § 4?" for each row. This is the single most useful column for SOW negotiation.

Time-box: 60-90 min for the Plan of Action table.

## Outputs

Save to:

```text
docs/intake/YYYY-MM-DD-gap-analysis.md
```

Filled from `docs/templates/gap-analysis.md`. VN fork exists at `docs/templates/locale-vi/gap-analysis.md`; use the locale-vi version when the client will read this brief directly.

The brief is the deliverable to the client. Even when the client does not directly read it, the SOW § 4 in-scope list is derived from § 4 of this brief — the audit trail must hold.

## Integration Rules

### Upstream — what feeds in

- Discovery interview REQ list → To-Be § 1.
- Client intake brief business problem → To-Be § 1.
- Raw discovery inputs → As-Is § 2.

### Downstream — what consumes the output

- SOW § 4 in-scope = all Must + selected Should rows.
- SOW § 5 out-of-scope = all Could + Should-not-in-scope + Won't rows.
- Story slicing: each Must / Should gets a story packet, REQ tokens trace to GAP-NNN in the story's Acceptance Criteria.
- Stage-6 As-Is process diagram references this brief's § 2 process map.
- Per-tier handover: this brief is part of `docs/templates/project-closure-story/01-handover-docs.md` § Key Decisions Still In Force as part of the project history.

## Anti-Patterns

- **Only To-Be, no As-Is.** The most common failure. Without As-Is, you do not actually know what the gap is — you have a wishlist. Forbid stage-3.B → stage-4 hand-off if § 2 of the brief is empty.
- **Gap too large to fit MVP.** Sometimes the gap reveals the project as written is impossibly scoped. Don't paper over — escalate to client, propose phase split, re-baseline SOW.
- **MoSCoW by vote.** Priority is set by gap severity + business value, not by who is loudest in the meeting. Severity High = Must by default; exceptions need a one-line reason.
- **Skipping the "Owner" column.** Solo dev assumes vendor owns everything; misses that client must do training, content prep, credential provisioning. List explicitly.
- **No "In SOW § 4?" disposition.** Every row needs a yes / no / partial answer. "TBD" is the same as "the SOW debate will happen with no anchor".
- **Treating gap-analysis as discovery-summary v2.** They are different artifacts. Discovery summary lists what the client said. Gap analysis says what it means.
- **No risk and open-questions sections.** Both sections force the team to write down what they don't yet know. Skipping them ships fragile estimates.
- **Frozen too early.** Gap analysis should iterate at least once with the client before freezing. Round 1 vendor draft → client review → round 2 → freeze.

## Per-Tier Application

| Lane | Application |
| --- | --- |
| Tiny | Skip. Inline narrative in intake brief is sufficient. |
| Normal | Required when client has any existing system or process being replaced or integrated with. |
| High-risk | Required. Plus a stakeholder validation round (the brief is read aloud with the client and edits captured live). |

## Variant Section

(Append a Variant block here when this playbook fails or partially works. Do not delete the original shape.)

## Related

- `docs/playbooks/solo-dev-client-delivery.md` — caller (stage 3.B).
- `docs/playbooks/discovery-interview-playbook.md` — produces the REQ list this playbook consumes.
- `docs/templates/gap-analysis.md` — the artifact this playbook produces.
- `docs/templates/locale-vi/gap-analysis.md` — VN fork.
- `docs/templates/proposal-sow.md` — downstream consumer (§ 4 in-scope derived).
- `docs/templates/change-request-log.md` — mid-project re-baseline trigger.
- `docs/decisions/0010-gap-analysis-stage.md` — adoption decision.
- `docs/playbooks/playbook-composition-pattern.md` — composition rules followed.
