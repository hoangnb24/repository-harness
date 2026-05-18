# Prototype

> Stage 6 sub-step B output per `docs/playbooks/visual-and-behavioral-modeling.md`.
>
> **This file is a template shipped with the harness.** Fill in the placeholders below when sub-step B starts. After the prototype is frozen, this README is the entry point that stages 7-8 (build), 11 (UAT visual gate), and 13 (handover) all read.

## Tool used

- **Tool:** `<Claude Design (https://claude.ai/design) | Stitch | Artifacts | v0.dev | pencil.dev | Figma | other>`
- **Live URL:** `<https://...>` *(must survive past UAT — vendor-hosted backup if account-private)*
- **Version / project ID:** `<tool-side identifier, e.g. claude.ai/design project slug>`
- **Account-private?** `<yes / no — if yes, where is the vendor-hosted backup?>`

## Freeze status

- **Frozen?** `<yes | no — still in iteration>`
- **Freeze date:** `<YYYY-MM-DD>`
- **Frozen by:** `<name>`
- **Last regeneration:** `<YYYY-MM-DD — round N>`
- **Sign-off record:** `<link to feedback-final.md once written>`

## Inputs used

- Design tokens: `docs/design-guidelines.md` § 2 (commit `<sha>`)
- Component coverage: `docs/design-guidelines.md` § 3 (commit `<sha>`)
- Design direction decision: `docs/decisions/YYYY-MM-DD-design-direction.md`
- Sample data: `<paste source or link to docs/discovery/*.{csv,json}>`

## Screen Coverage

One row per screen. Filename column points at the export under `screens/`. Empty/error column is REQUIRED per the freeze gate (every screen must show at least 1 sample-data state AND 1 empty/error state).

| # | Screen | Sample export | Empty / error export | Source REQ tokens |
|---|---|---|---|---|
| 1 | `<Home – AI Dashboard>` | `screens/01-home.html` | `screens/01-home-empty.html` | `<F-026, US-MVP-026>` |
| 2 | `<Quick Capture>` | `screens/02-quick-capture.html` | `screens/02-quick-capture-empty.html` | `<ING-001..005>` |
| 3 | `<...>` | | | |

## Flow Coverage

One row per primary user journey. File or URL points at the recording / walk-through under `flows/`.

| # | Flow | Path / URL | Source story | Notes |
|---|---|---|---|---|
| 1 | `<Onboarding → first knowledge added>` | `flows/onboarding.mp4` | `<US-MVP-001, 003, 005>` | |
| 2 | `<...>` | | | |

## Known limitations

Bulleted list of things the prototype does **NOT** show or where it deviates from spec. Acceptable to ship if the limitation has a follow-up decision or change-request link.

- `<e.g. "Streaming chat response is shown as static for brevity — real product streams tokens.">`

## Feedback rounds

Each review round produces a dated feedback file in this folder. Bump freeze date when affected screens are regenerated.

- `feedback-YYYY-MM-DD.md` — round 1 (vendor → client → vendor)
- `feedback-YYYY-MM-DD.md` — round 2
- `feedback-final.md` — written sign-off

Time-box: 2 review rounds maximum before freeze. Beyond 2, scope is the problem → escalate via `docs/templates/change-request-log.md`.

## Triple-use map

Frozen prototype is consumed by 3 downstream stages — keep paths above stable:

- **Stage 7-8 Build:** story packets under `docs/stories/epics/E*/US-*.md` cite screens here as the visual target.
- **Stage 11 UAT:** `docs/templates/delivery-closure-story/01-uat-plan.md` "live matches prototype" gate.
- **Stage 13 Handover:** `docs/templates/project-closure-story/01-handover-docs.md` read-this-order index.

Do not regenerate the prototype post-freeze. Any change after freeze enters `docs/templates/change-request-log.md`.
