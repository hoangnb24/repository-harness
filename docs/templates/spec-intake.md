# Spec Intake

Date: YYYY-MM-DD

## Source

Where did the spec come from?

- User prompt:
- Attached file:
- External reference:

## Project Summary

What product are we building, for whom, and why?

## Candidate Product Docs

List the product contract files that should be created under `docs/product/`.

| File | Purpose | Source sections |
| --- | --- | --- |
| `docs/product/overview.md` | | |

## Candidate Epics

List only the epics that are clear enough to name. Do not create every story
packet yet.

| Epic | Description | Status |
| --- | --- | --- |
| E01 | | unsliced |

## Architecture Questions

- Runtime stack:
- Product surfaces:
- Storage:
- External providers:
- Deployment target:
- Security model:

## Data Inventory (PII)

What personal data does this product collect, on what lawful basis, and how long is it kept? Required when the product touches user accounts, payments, or any identifiable individual. If clearly zero PII, write `none — public/anonymous content only` and skip the table.

| Field | Lawful basis | Retention | Deletion on request |
| --- | --- | --- | --- |
| `<e.g. email>` | `<contract / consent / legitimate interest>` | `<duration>` | `<yes / no — reason>` |
| `<e.g. payment method last4>` | contract | 7 years (tax) | no (legal hold) |

Jurisdictions to consider: project country (e.g. VN), client country, end-user country. For EU users, GDPR applies; for VN users, Nghị định 13/2023/NĐ-CP applies.

## Validation Shape

What proof will this project eventually need?

| Layer | Expected proof |
| --- | --- |
| Unit | |
| Integration | |
| E2E | |
| Platform | |
| Release | |

## Open Decisions

- Item.

## First Story Candidates

- Item.

## Harness Delta

What harness changes were made or should be proposed because of this spec?
