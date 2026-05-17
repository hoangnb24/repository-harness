# Xia Compare: External Design-System References → Harness Playbook

> Source 1: `gztchan/awesome-design` (17.1k★, last push 2024-07)
> Source 2: `google-labs-code/design.md` (14.1k★, created 2026-04, very recent)
> Local target: `docs/playbooks/ui-design-system-contract.md` (created 2026-05-17, this session)
> Mode: `--compare` (no implementation, no plan)

## TL;DR

- `awesome-design` = curated link list. **Skip** as a methodology source; mention once as "asset discovery" reference at most.
- `google-labs-code/design.md` = **format spec** for describing visual identity to AI agents. Three concrete patterns worth porting, two worth comparing-and-rejecting, one open question.
- Our current playbook is **engineer/codebase-first** (code is SoT, markdown is contract). DESIGN.md is **agent-handoff-first** (markdown IS the SoT, tokens in YAML front matter). Different audience, both valid — we should make our stance explicit and link to DESIGN.md as an alternative.

## Source 1: gztchan/awesome-design

### What it is

A 17k-star "awesome list" — curated index of design resources organized by category: Stock photos, Icons & logos, Color tools, Typography, Toolkits (Sketch/Photoshop/Figma/XD/Zeplin), Prototyping, Mockup, User Testing, Styleguide & Branding, Books, Podcasts, Communities.

### What it is NOT

- Not a spec.
- Not a methodology.
- Not a contract format.
- Has no opinion on token taxonomy, primitive kits, file structure, or verification.

### Verdict for our playbook

**Skip.** Zero structural learnings. The only useful pointer: a designer or PM who needs to discover icon packs / color tools / stock photography could be sent here. Worth at most a one-line mention in the "Related Tools And Skills" section under a "discovery" sub-bullet — if at all.

Not worth amending the playbook for.

## Source 2: google-labs-code/design.md

### What it is

A format specification for a `DESIGN.md` file: **YAML front matter** (machine-readable design tokens) + **Markdown body** (human-readable rationale). Designed so that coding agents (Stitch, Claude, etc.) have a persistent, structured understanding of a design system across sessions.

Ships with an `npx @google/design.md` CLI:
- `lint` — structural + WCAG contrast checks → JSON findings
- `diff` — token-level regression check between two files → JSON
- `export` — emit `json-tailwind` (v3 theme), `css-tailwind` (v4 `@theme`), or `dtcg` (W3C Design Tokens Format)
- `spec` — output the spec itself for prompt injection

### Spec shape

```yaml
---
version: alpha
name: <string>
description: <string>          # optional
colors:
  <token-name>: "#hex"
typography:
  <token-name>:
    fontFamily / fontSize / fontWeight / lineHeight / letterSpacing
    fontFeature / fontVariation
rounded:
  <sm|md|lg|...>: <Dimension>
spacing:
  <xs|sm|md|...>: <Dimension | number>
components:
  <component-name>:
    backgroundColor / textColor / typography / rounded / padding / size / height / width
---
```

- **Token reference syntax**: `{colors.primary}` for cross-refs (lintable).
- **Component variants**: separate entries (`button-primary`, `button-primary-hover`) — flat, not nested.
- **Normative section order** (8 sections, fixed sequence):
  1. Overview / Brand & Style
  2. Colors
  3. Typography
  4. Layout / Layout & Spacing
  5. Elevation & Depth
  6. Shapes
  7. Components
  8. Do's and Don'ts
- **Forward-compat rules**: unknown section → preserve; unknown component property → warn; duplicate section → error.

## Head-to-head

| Aspect | Our playbook | DESIGN.md | Recommendation |
|---|---|---|---|
| **Primary audience** | Engineering teams maintaining a real codebase | Agents handing off design specs across sessions/tools | Keep ours engineer-first; **add explicit pointer** to DESIGN.md for agent-handoff use case |
| **Source of truth** | Code (CSS / theme file). Markdown is reference. | Markdown YAML front matter IS canonical | Keep our stance. **Add §1 note** explaining the trade-off |
| **Token storage** | Wherever the stack stores them (CSS vars, theme.ts, etc.) | YAML in same file as prose | Don't change. But mention DESIGN.md as an option when project has no opinionated token home yet |
| **Token taxonomy** | 7 groups (brand/surface/text/radius/shadow/motion/font) | 5 groups (colors/typography/rounded/spacing/components) — narrower | Ours is more honest about what real projects need (shadow + motion are missing from DESIGN.md) |
| **Section count + order** | 10 sections, "suggested" | 8 sections, **normative order** with aliases | **Port the normative-order discipline** — drift gets worse when section order is "vibes" |
| **Component model** | Inventory table (file / role / notes), no API | Typed component tokens with variants as separate entries | **Port the variant naming convention** (`button-primary-hover` flat, not nested) into our Component Inventory format |
| **Token references** | None (plain CSS vars) | `{colors.primary}` syntax, lintable | **Optional**. Only useful if we adopt the YAML pattern. Skip unless adopting DESIGN.md too |
| **Verification gate** | "Pick a script" — visual diff or grep-based lint | `npx @google/design.md lint` (structural + WCAG) + `diff` (regression) | **Port the recommendation**. Concretely point at DESIGN.md's CLI as one of the two recommended gate options |
| **Forward compat for unknown content** | None | Explicit table (preserve / warn / error per case) | **Worth adopting** as a "future-proofing" subsection in §11 Verification |
| **Export targets** | None | Tailwind v3 / Tailwind v4 / DTCG (W3C standard) | Useful if our project needs to feed Figma or other tools. Note as "if you need cross-tool tokens, export via DTCG" |
| **CLI tooling** | None | First-class CLI | Good — recommend in verification section, don't bake into playbook |

## What to port into our playbook (concrete edits)

Three small amendments to `docs/playbooks/ui-design-system-contract.md`. None invalidate the current shape.

### 1. §1 Code-is-SoT — add a "when to invert" note

After the "Why" paragraph, add ~3 lines:

> **When markdown-as-SoT is the right call instead**: agent-handoff workflows
> where the design system lives upstream of any single codebase (Stitch,
> design-first agents shipping to multiple targets). See
> [`google-labs-code/design.md`](https://github.com/google-labs-code/design.md)
> for that pattern. This playbook assumes you're inside a codebase where
> CSS / theme files already exist — flip the SoT only if that's not true.

This makes our stance principled, not blind.

### 2. §6 Component Inventory — adopt flat-variant naming

Add one paragraph after the inventory table example:

> **Variant naming**: name component variants as separate flat keys, not
> nested objects: `button-primary`, `button-primary-hover`, `button-primary-disabled`.
> Mirrors the DESIGN.md spec convention. Easier to grep, easier to lint,
> easier for agents to enumerate states.

### 3. §11 Verification — make it concrete with two named options

Replace the current "pick at least one" with:

> Pick at least one:
>
> 1. **Structural + contrast lint** — `npx @google/design.md lint <contract-file>`
>    catches broken token refs and WCAG contrast violations. Free, structured
>    JSON output. Best fit when you adopt the YAML front matter pattern.
> 2. **Visual diff vs baseline** — capture viewport screenshot per major page,
>    diff against committed reference. Pair with
>    `headless-browser-blank-screenshot.md`. Best fit when token discipline
>    is informal but visual regressions are the real risk.
> 3. **Grep token-lint** — fail CI on banned patterns
>    (`rgba(0, 0, 0`, removed token names, hardcoded hex outside the tokens
>    file). Cheapest, project-specific.

### 4. §10 Don'ts — add forward-compat rule

Add one bullet:

> - Don't reject a contract file that has unknown sections or unknown
>   component properties — preserve unknowns with a warning, reject only on
>   duplicate sections or broken token refs. (Forward-compat rule from
>   DESIGN.md.)

## What NOT to port

- **YAML front matter as primary token store**. Creates a second source of truth if the project also has CSS tokens. The whole point of our playbook is "code is SoT" — adopting front-matter tokens would contradict it. (Different story if a project has no opinionated token home; then DESIGN.md is the better starting point and our playbook should defer to it.)
- **Normative 8-section order that drops shadow & motion**. DESIGN.md folds shadow into "Elevation & Depth" and has no motion section at all — workable for design handoffs, lossy for production code. Keep our 10-section taxonomy with shadow + motion as first-class.
- **`@google/design.md` as a hard dependency**. We're stack-agnostic; recommending a vendor CLI is fine, requiring it is not.
- **`awesome-design`'s curated lists**. Not in our scope.

## Open questions

1. Should we ship a **second** playbook for the agent-handoff case (`ui-design-spec-for-agents.md` that wraps DESIGN.md), or just a pointer from this one? Trade-off: more surface vs cleaner separation of audiences.
2. The DESIGN.md "Component" model maps tokens → component property keys. Ours uses prose composition patterns. Worth a small companion file `docs/templates/design-system/component-tokens.example.yaml` to show both forms side-by-side? Or YAGNI until a project asks?
3. Our §2 token cheat-sheet lists 7 groups. DESIGN.md has 5. Worth a one-line mapping table in our playbook so projects migrating from DESIGN.md know where shadow + motion go in our taxonomy?

## Risk score: low

No code changes required. Four small markdown amendments to one file. Reversible.

## Sources accessed

- `https://api.github.com/repos/gztchan/awesome-design` — metadata
- `https://raw.githubusercontent.com/gztchan/awesome-design/master/README.md` — first 200 lines (full file is the curation list, no methodology beyond the index)
- `https://api.github.com/repos/google-labs-code/design.md` — metadata
- `https://raw.githubusercontent.com/google-labs-code/design.md/main/README.md` — full README (CLI, schema, linting rules)
- `https://raw.githubusercontent.com/google-labs-code/design.md/main/docs/spec.md` — first 250 lines (Overview, Colors, Typography, Layout, Elevation, partial Shapes)
