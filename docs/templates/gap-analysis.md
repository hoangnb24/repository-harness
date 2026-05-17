# Gap Analysis — <project name>

Date: YYYY-MM-DD · Status: draft | reviewed-by-client | accepted · Round: 1

> Vendor-produced brief that compares client's current state (As-Is) to desired future state (To-Be) and structures the gaps + solutions. Frozen before SOW § 4 in-scope is finalized.
>
> Lives at `docs/intake/YYYY-MM-DD-gap-analysis.md`. Produced by `docs/playbooks/gap-analysis.md` after `docs/playbooks/discovery-interview-playbook.md` has surfaced the REQ list.

## 1. To-Be (Future State)

What the client wants the world to look like once the project ships.

### Business goals

- Goal 1 (one-line, measurable if possible).
- Goal 2.

### Success metrics

How the client will know "it worked".

| Metric | Today (baseline) | Target | Measure by |
| --- | --- | --- | --- |
| <e.g. order fulfillment time> | <e.g. 24h avg> | <e.g. < 4h avg> | <e.g. 30 days after launch> |

### Target users × target actions

| Role | What they will be able to do (To-Be) |
| --- | --- |
| Customer | Self-service order status 24/7 on mobile app |
| Staff | Receive order notifications + update status from dashboard |

### Constraints

- Deadline: <date>
- Budget envelope: <range>
- Regulatory: <e.g. PCI-DSS, GDPR, none>
- Existing systems must keep running: <list>

## 2. As-Is (Current State)

What the client does today. Captured from discovery interview, source docs, and `docs/discovery/` raw inputs.

### Existing process map

Numbered steps, who does what, where pain shows up. If a Mermaid flowchart of the current process exists or will exist, reference it: `docs/visuals/diagrams/business-workflow-as-is.md`. At stage 3 (this brief), text is enough — the formal diagram lands at stage 6.

1. <Actor X> does <action> via <channel> → result.
2. <Actor Y> does <action> → handoff to <Actor Z>.
3. ...

### Existing systems

| System | Purpose | Owned by | Integrates with | Pain |
| --- | --- | --- | --- | --- |
| <e.g. Excel order log> | Manual order tracking | Sales staff | None — manual entry | Duplicate entries, lost orders |

### Pain points (verbatim where possible)

Cite source: `docs/discovery/2026-05-17-kickoff-notes.md § 4`.

- Pain 1: <one-line>. Cited: <source>.
- Pain 2: <one-line>. Cited: <source>.

### Workarounds users invent

- <e.g. customer calls hotline repeatedly to check order status because no tracking page exists>.

### Stakeholders in As-Is

| Role | Current responsibility | Affected by change? |
| --- | --- | --- |
| Customer service rep | Handles status-check calls | yes — workload drops with self-service |
| Sales staff | Enters orders manually in Excel | yes — replaced by automated capture |

## 3. The Gap

Categorized. Each row gets a `GAP-NNN` token local to this brief. The gap token traces forward to a REQ when stories are sliced.

### Functional gaps (features missing)

| GAP ID | Description | Severity | As-Is touch | To-Be touch |
| --- | --- | --- | --- | --- |
| GAP-001 | No customer-facing order status surface | High | Customer calls hotline | Customer opens app, sees status |
| GAP-002 | No real-time order notification to staff | Medium | Staff polls email | Push notification on phone |

### Process gaps (workflows missing or broken)

| GAP ID | Description | Severity | Plan-of-action linkage |
| --- | --- | --- | --- |
| GAP-010 | Order intake has no validation step before warehouse handoff | High | Add validation step in workflow + UI gate |

### Technology gaps (systems not integrated)

| GAP ID | Description | Severity | Plan-of-action linkage |
| --- | --- | --- | --- |
| GAP-020 | Excel order log not connected to inventory system | High | Replace Excel + integrate with new inventory API |

### Data gaps (data not captured / not accessible)

| GAP ID | Description | Severity | Plan-of-action linkage |
| --- | --- | --- | --- |
| GAP-030 | Customer satisfaction not tracked anywhere | Medium | Add post-fulfillment NPS survey |

### Role / skill gaps (people don't have access or training)

| GAP ID | Description | Severity | Plan-of-action linkage |
| --- | --- | --- | --- |
| GAP-040 | Staff has no admin account on existing tool — only owner has access | Low | Add staff role + training session at handover |

### Compliance gaps (regulation not met)

| GAP ID | Description | Severity | Plan-of-action linkage |
| --- | --- | --- | --- |
| GAP-050 | No PII consent capture for marketing emails | High (legal) | Add consent checkbox + retention policy |

Severity scale: **High** = blocks To-Be / regulatory risk. **Medium** = blocks goal but workaround exists. **Low** = nice-to-have.

## 4. Plan of Action

Each gap gets a solution row. MoSCoW priority directly informs SOW § 4 in-scope decisions.

| GAP ID | Solution shape | Owner | Effort | Priority (MoSCoW) | Story candidate | In SOW § 4? |
| --- | --- | --- | --- | --- | --- | --- |
| GAP-001 | Build "Order Status" page on customer app + status API | Vendor | L (16-40h) | **Must** | `US-001-order-status-view` | yes |
| GAP-002 | Push notification to staff phones via FCM | Vendor | M (4-16h) | **Should** | `US-002-staff-order-notif` | yes |
| GAP-010 | Add validation step in order-intake workflow | Vendor | M | **Must** | `US-003-order-validation-gate` | yes |
| GAP-020 | New inventory API + migrate Excel data | Vendor | XL (> 40h) | **Should** | `US-004-inventory-integration` | partial — phase 1 read-only, phase 2 write |
| GAP-030 | NPS survey post-fulfillment | Vendor | S (1-4h) | **Could** | `US-005-nps-survey` | no — phase 2 |
| GAP-040 | Staff role + training session | Both | S | **Must** | `US-006-staff-role-handover` | yes (in handover scope) |
| GAP-050 | Consent capture + retention policy doc | Vendor | M | **Must** | `US-007-consent-capture` | yes |

MoSCoW key:

- **Must** — blocking the To-Be vision OR regulatory. Must be in SOW § 4.
- **Should** — significant value but not blocking. SOW § 4 if budget allows.
- **Could** — nice-to-have. Default to SOW § 5 (out-of-scope) or phase 2.
- **Won't** — explicitly out of this project. Document why in `docs/decisions/`.

## Out-of-Scope From This Brief

Gaps the client mentioned but the team chose not to address now. Each cites a reason and where it will go (phase 2, alternative vendor, decline).

| GAP ID | Description | Why out | Disposition |
| --- | --- | --- | --- |
| GAP-099 | Multi-language UI (5 languages) | Beyond budget for phase 1 | Phase 2 SOW (post-launch) |

## Risks Identified

Risks the gap analysis surfaced (not the same as gaps — these are conditions that could derail closing the gap).

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Excel data quality is worse than client said | Med | High | Spike in week 1 — sample 100 rows, report findings |
| Staff training resistance | Low | Med | Handover includes 2 sessions, plus written guide |

## Open Questions

Questions the gap analysis could NOT resolve. These either get answered before SOW signs, or get logged in `docs/HARNESS_BACKLOG.md`.

- Q1: Does the existing PIM have an export API or will we scrape?
- Q2: What is the retention period regulators require for order data?

## Sign-Off

| Stage | Date | Approver | Notes |
| --- | --- | --- | --- |
| Vendor draft complete | YYYY-MM-DD | <vendor> | Round 1 |
| Client review | YYYY-MM-DD | <client name> | Round 1 — accepted with edits to GAP-020 priority |
| Frozen (pre-SOW § 4) | YYYY-MM-DD | <vendor + client> | Final |

Once frozen, gap changes route through `docs/templates/change-request-log.md`. Do not edit the analysis in place — annotate with pointer to the CR.

## Cross-References

- Discovery interview output: `docs/intake/YYYY-MM-DD-discovery-summary.md` (REQ list source).
- Client intake brief: `docs/intake/YYYY-MM-DD-intake-brief.md` (business problem source).
- Raw inputs cited: `docs/discovery/YYYY-MM-DD-<slug>.{ext}` rows.
- Forward: SOW § 4 in-scope (`docs/templates/proposal-sow.md`).
- Forward: story slicing (`docs/stories/epics/`).
- As-Is process diagram (stage 6, if UI project): `docs/visuals/diagrams/business-workflow-as-is.md`.

---

**Localization**

This template forks to `docs/templates/locale-vi/gap-analysis.md` per `docs/playbooks/bilingual-delivery-template-pattern.md`. Tokens (`GAP-NNN`, `US-NNN.REQ-MMM`), file paths, and code fences stay English in both locales.
