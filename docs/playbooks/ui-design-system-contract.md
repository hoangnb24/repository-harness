# UI Design System Contract

> Single living style guide per project. Code is source of truth; markdown is
> the readable contract that keeps tokens, primitives, and composition
> patterns from drifting out of sync.

## When this fits

Use when **any** of these is true:

- Project has > 1 page or > 5 reusable components and UI consistency matters.
- More than one agent (or human) will touch the UI layer over time.
- The product surface includes marketing pages, app screens, or admin UIs
  that must share a recognizable look.

Skip when:

- One-off internal tool, throwaway prototype, or single-page demo.
- The project intentionally has no shared visual identity (CLI, raw API).
- Stack is non-visual (worker, library, infra-only).

## What "design system" means in this contract

Not a component library product. Not Storybook. Just three things kept
in sync:

1. **Tokens** — color, spacing, radius, shadow, motion, typography. Defined
   in code (CSS vars, theme file, or framework token primitive).
2. **Primitives** — the reusable components everything else composes from.
   See §3 Component Coverage Matrix below for the full required set
   (~90 components across 11 functional groups). The absolute starting
   subset: button, input, card, badge, container, section, plus a
   state/feedback layer (modal, toast, spinner).
3. **Composition patterns** — named recipes for recurring surfaces (hero,
   section heading, card grid, closing CTA, page head). Each pattern is a
   copy-pasteable snippet, not an API doc.

If any of those three is missing, every new page re-invents the wheel and
visual drift compounds quickly.

## The Code-is-SoT rule

**Canonical token values live in code.** Markdown summaries are reference
only. This is the single most important rule in this playbook.

Why: markdown drifts silently. CSS does not — change a token, every consumer
updates. If the doc disagrees with the CSS, the CSS wins, full stop.

**When markdown-as-SoT is the right call instead**: agent-handoff workflows
where the design system lives upstream of any single codebase (Stitch,
design-first agents shipping to multiple targets). See
[`google-labs-code/design.md`](https://github.com/google-labs-code/design.md)
for that pattern — YAML front matter holds tokens, prose holds rationale,
a CLI lints and exports to multiple frameworks. This playbook assumes
you're inside a codebase where CSS / theme files already exist — flip the
SoT only if that's not true.

Pattern:

```
src/styles/tokens.<ext>   # ← canonical token values
src/styles/primitives.<ext>   # ← .btn, .card, .badge, .input, .container
src/components/             # ← composed components
docs/design-guidelines.md   # ← the readable contract, points back to code
```

The doc must open with: "**Canonical values live in `<path>`. This file is
reference only — code wins on conflict.**"

## File: `docs/design-guidelines.md` (the contract)

One file per project. Lives in `docs/`. Keep under ~500 lines (the §3
Component Coverage Matrix is the largest section at ~180 lines). Below
is the section skeleton — every project that adopts this playbook should
ship all 12 sections, even if a section is "n/a, no dark mode" one-liner.

### Where-to-update routing table (REQUIRED, place at top)

The single biggest source of drift is people not knowing where to put a
change. Open with this table:

| Change | Update here |
|---|---|
| New token (color, radius, shadow, motion duration) | `<path-to-tokens-file>` — then update §2 cheat-sheet below if commonly referenced |
| New component category not yet covered | §3 Component Coverage Matrix — add row, then implement and add to §8 Inventory |
| New component implementation (file added) | `<path-to-components>` + add row to §8 Component Inventory + tick the §3 matrix entry |
| New composition recipe (hero variant, page-head, etc.) | §6 Composition Patterns of this file |
| Big direction change (drop dark mode, swap brand color) | New `docs/decisions/YYYY-MM-DD-<topic>.md` + update §2 here |

### Section skeleton

1. **Foundation Files** — list of token / primitive / layout files with paths.
2. **Token Cheat-Sheet** — quick reference, code is canonical.
3. **Component Coverage Matrix** — copy the matrix from this playbook
   verbatim. Tick rows as components ship; leave stubs (`TODO`) visible
   for unshipped ones. Drives §8 Inventory.
4. **Color & Contrast Rules** — semantic mapping, contrast minimums, "shadow
   tint" rule (e.g. shadows must be brand-tinted, not grey).
5. **Typography Rules** — clamp scale for display / H2 / H3 / body / subhead /
   eyebrow / button / micro. Always include subhead — most common skip.
6. **Composition Patterns** — copy-pasteable snippets for hero, section-head
   triplet, card grid (uniform + bento), closing CTA, page-head, forms.
7. **Motion Rules** — token → duration → curve → use, plus reduced-motion
   policy.
8. **Component Inventory** — table: file / role / notes. One row per
   shipped (or stubbed) §3 matrix entry. Mark load-bearing selectors and
   scripts ("do not rename").
9. **Adding a New Page** — 5-6 step recipe agents can follow without reading
   the rest of the doc.
10. **Dark Mode** — toggle mechanism, override surface, brand-stable promise.
    N/a one-liner if the project is light-only.
11. **Don'ts** — concrete anti-patterns observed in this codebase. Specific,
    not generic ("don't use `rgba(0,0,0,...)`, shadows are brand-tinted").
12. **Verification** — link to visual-diff script, structural lint, and
    coverage lint that prove the contract is met.

## Token taxonomy (the seven groups)

Every design system this playbook produces should expose at least these
seven token groups. Group names are conventional; the project chooses the
concrete values.

```
Brand        primary / primary-hover / secondary / gradient
Surfaces     bg-primary / bg-secondary / bg-tertiary  (+ dark variants if dark mode)
Text         text-primary / text-secondary / text-muted
Radius       sm / md / lg / xl / 2xl / pill
Shadow       cta / cta-hover / glass / card-hover / modal  ← all brand-tinted
Motion       transition-normal / -smooth / -slow
Font         font-sans (+ font-mono if code surfaces)
```

Why brand-tinted shadows: grey shadows read as "default framework". A
brand-tinted shadow on every elevated surface is the cheapest move that
makes a page feel intentional.

## Component Coverage Matrix

A design system that ships only a few primitives covers a marketing page.
A production app needs ~90 distinct component types. Define them up
front — even as stubs — so visual drift doesn't compound as scope grows.

**Rule**: every component below must have a corresponding entry in §6
Component Inventory before the design system claims "production-ready".
Placeholder rows ("TODO — not yet built") are allowed; silently-missing
rows are not. The gap should be visible.

### 11 functional groups (required for every project)

#### Actions
- Button — variants: primary / secondary / tertiary / destructive / ghost / link / icon-only / loading
- Icon Button
- Floating Action Button (FAB)
- Toggle / Toggle Group
- Segmented Control

**Two button styles is the recommended starting cap.** Adding a third
button style is the most common visual-drift trigger. If a designer wants
a third style, push back: either re-use one of the two, or add a
non-button affordance (link, icon button). Open more variants only when
3+ pages have a real shared need.

#### Inputs — Text & Number
- Text Input
- Textarea
- Number Input / Stepper
- Search Input
- Password Input (with visibility toggle)
- OTP / PIN Input
- Tag / Chip Input
- Rich Text Editor *(styling-only)*

#### Inputs — Selection
- Select
- Multi-Select
- Combobox / Autocomplete
- Checkbox
- Checkbox Group
- Radio / Radio Group
- Switch
- Slider / Range Slider

#### Inputs — Specialized
- Date Picker *(styling-only)*
- Date Range Picker *(styling-only)*
- Time Picker *(styling-only)*
- Color Picker *(styling-only)*
- File Upload / Dropzone *(styling-only)*

#### Forms
- Form / Field / Fieldset
- Label
- Helper Text / Hint
- Validation Message (error / success / warning, inline)

#### Data Display
- Table — sortable, paginated, expandable rows, row actions
- List
- Card
- Description List
- Tree View
- Tag / Chip / Pill / Badge
- Avatar
- Avatar Group
- Statistic / KPI
- Code Block (inline + block)
- Image
- Empty State

#### Feedback
- Toast / Snackbar
- Notification (persistent center)
- Alert / Banner (inline)
- Inline Message (form-level)
- Spinner / Loader
- Progress — linear + circular
- Skeleton Loader
- Status Indicator — dot, ping

#### Overlays
- Modal / Dialog
- Confirm Dialog
- Drawer / Side Panel
- Bottom Sheet
- Popover
- Tooltip
- HoverCard
- Context Menu

#### Navigation
- Top Nav / Header
- Sidebar
- Tab Bar (mobile bottom nav)
- Breadcrumb
- Tabs
- Pagination
- Stepper / Wizard
- Menu / Menubar
- Command Palette (cmd+k)
- Anchor / TOC (page-level)
- Footer

#### Layout
- Container
- Section
- Grid / Stack / Flex
- Divider / Separator
- Spacer
- Aspect Ratio
- Scroll Area
- Accordion / Collapsible
- Resizable / Splitter

#### Typography
- Display / H1-H6 / Body sm-md-lg / Caption / Label / Link / Code (inline) / Quote / List (ul/ol)

### Styling-only marker

Heavy widgets like Rich Text Editor, Color Picker, Date Picker, File
Upload — define **wrapper styling, container, focus ring, and state
classes** in the design system. The behavior usually comes from a
third-party library (TipTap, react-day-picker, react-dropzone, etc.).
The marker means: don't build behavior from scratch, but don't let the
wrapped widget escape your token system either. Focus rings, border
radii, error states, disabled treatments must all match the rest of the
system.

### Required states per component

Every component above must define all 8 states:

```
default · hover · active/pressed · focus (keyboard, visible ring)
disabled · loading · error · empty (where applicable)
```

Skipping `focus-visible` is the most common accessibility regression —
keyboard users need a visible ring. Don't rely on the browser default.

### Required size scale

Every component supports the 5-step scale:

```
xs · sm · md · lg · xl
```

Not every component needs all 5 (a Tooltip rarely has `xl`). But the
scale must be consistent across components so `sm` Button matches `sm`
Input matches `sm` Icon visually.

### Surface add-ons (apply only if the project ships that surface)

**Marketing surfaces** — Hero · Section heading triplet (badge + H2 +
subhead) · Bento grid · Pricing card · Testimonial · Logo cloud · Stats
panel · CTA strip · FAQ · Footer (marketing variant)

**Mobile-specific** — Pull-to-refresh · Swipe Action *(FAB and Bottom
Sheet covered in core categories above)*

### Reference benchmarks

The 90-component scope was triangulated against shipping design systems
while compiling this matrix:

- **Radix UI Primitives** — 30 accessible component primitives
- **Ant Design** — 70+ enterprise components
- **shadcn/ui** — Radix + Tailwind reference implementation
- **Material 3** — Google's app-focused system
- **Polaris** — Shopify's commerce-focused system

If a component appears in 2+ of the above but is missing from this
matrix, open an issue against this playbook.

## Composition Patterns format

Patterns are recipes, not component APIs. Each pattern in §4 should follow
this shape:

````markdown
### Pattern name

```<framework>
<copy-pasteable snippet, ≤ 15 lines>
```

- 2-4 bullets: critical detail (z-index, transform values, accessibility).
- Link to canonical implementation file in the codebase.
````

Don't document props or APIs in this section — those belong in the
component file's own header comment. Patterns describe **how to assemble**,
not what the API surface is.

## Component Inventory format

```markdown
| File | Role | Notes |
|---|---|---|
| `Header.<ext>` | Sticky glass nav | Theme + lang toggle right-anchored. |
| `PurchasePanel.<ext>` | Purchase form + QR | **Script + `data-*` selectors are load-bearing — do not rename.** |
```

The "load-bearing — do not rename" marker is the second-most-important
convention in this playbook. Without it, refactors silently break scripts
that select by class or `data-*` attribute.

**Variant naming**: name component states/variants as separate flat keys,
not nested objects: `button-primary`, `button-primary-hover`,
`button-primary-disabled`. Mirrors the DESIGN.md spec convention. Easier
to grep, easier to lint, easier for agents to enumerate states.

## Don'ts section

Always concrete, never generic. Bad: "don't write inconsistent code". Good:

- Don't use `box-shadow: rgba(0, 0, 0, ...)` — shadows are brand-tinted.
- Don't introduce a third button style — `.btn-primary` and `.btn-secondary`
  cover all use cases.
- Don't skip the subhead under H2 — visual rhythm flattens.
- Don't use tokens that were removed in the last redesign (list them by
  name so grep catches them).
- Don't reject a contract file that has unknown sections or unknown
  component properties — preserve unknowns with a warning, reject only on
  duplicate sections or broken token references. (Forward-compat rule
  ported from the DESIGN.md spec.)

Each don't should be specific enough that a code reviewer can grep for
violations.

## Verification gate

The contract is only enforceable if you can prove it holds. The gate must
be a script, not a checklist. Pick at least one of the three primary
options below, then layer the always-required coverage lint on top.

1. **Structural + contrast lint** — if the project adopts a YAML front
   matter token pattern, run
   `npx @google/design.md lint <contract-file>`. Catches broken token
   references and WCAG contrast violations. Free, structured JSON output.
   See [`google-labs-code/design.md`](https://github.com/google-labs-code/design.md).
2. **Visual diff vs baseline** — capture viewport screenshot of each
   major page, diff against a committed reference. Failing diff blocks
   merge. Pair with `headless-browser-blank-screenshot.md` for the
   capture step.
3. **Grep token-lint** — fail CI on banned patterns (`rgba(0, 0, 0`,
   removed token names, hardcoded hex outside the tokens file).
   Cheapest, most project-specific.

**Coverage lint (always required)** — diff the §3 Component Coverage
Matrix against §6 Component Inventory. Every matrix entry must have a
corresponding inventory row (placeholder allowed, silently-missing not).
Fail CI if any matrix entry has no row. Cheapest implementation: a
50-line script that parses both sections and compares names.

Document the gate commands in §12 of the contract file.

## Reference implementation

`nguyenhuunghia.vn` ships a real version of this contract:

- Contract file: `docs/design-guidelines.md` (~200 lines, all 10 sections).
- Tokens: `src/styles/global.css` (Tailwind 4 `@theme` + `:root` vars +
  primitives).
- Motion: `src/styles/motion.css`.
- Verification: `scripts/visual-verify-screenshots-v2.mjs`.

Useful to skim when adopting this playbook in a new project — the structure
generalizes, the teal/Inter/Astro specifics do not.

## Minimum viable adoption

If you only do the bare minimum to claim "this project has a design system":

1. Create `<path-to-tokens-file>` with the seven token groups.
2. Define the **core action + form layer** as the absolute starting set:
   `.btn-primary`, `.btn-secondary`, `.card`, `.badge`, `.input-field`,
   `.container-page`, `.section`. Add stubbed `TODO` rows in §6 for every
   remaining §3 Component Coverage Matrix entry — the gap should be
   visible from day one.
3. Write `docs/design-guidelines.md` with the §1 Foundation Files paths,
   §2 Token Cheat-Sheet, §3 Component Coverage Matrix (copy from this
   playbook with all rows stubbed), §6 Component Inventory (with the
   stubs), and §10 Don'ts.
4. Open the file with "Canonical values live in `<path>`. Reference only."

Other sections can grow as patterns emerge. The routing table at the top
plus the visible §3 ↔ §6 gap is what keeps growth disciplined.

## Anti-patterns

- Treating Storybook or a component library as a substitute for the
  contract file. Storybook documents APIs; the contract documents
  intentions, don'ts, and routing. Both have a place, but the contract is
  cheaper and more durable.
- Markdown that duplicates token values instead of pointing at code.
  Drifts within a week.
- A contract file with no don'ts. The don'ts are the highest-signal section
  for new contributors.
- A contract file with no verification gate. Without a script, the contract
  is decorative.
- Burying primitives inside component files. Buttons / cards / badges must
  be addressable by class name from any component, or composition patterns
  cannot stay consistent.
- Letting individual pages define their own shadow / radius / spacing
  scales. Every such drift adds a token nobody else can find.

## Related Tools And Skills

- `/ck:ui-styling` — Tailwind + shadcn-style implementation help.
- `/ck:ui-ux-pro-max` — color, font, system selection when starting fresh.
- `/ck:web-design-guidelines` — accessibility / UX audit of an existing
  page against best-practice heuristics.
- `/ck:frontend-design` — replicate a mockup or screenshot in code.
- Adjacent playbooks:
  - `landing-page-saas-ai-noti-style.md` — surface-specific recipe; this
    playbook is the stack-agnostic frame around recipes like that one.
  - `headless-browser-blank-screenshot.md` — needed for the verification
    gate's screenshot capture step.

## History

- `2026-05-17`: created. Extracted from `nguyenhuunghia.vn`'s
  `docs/design-guidelines.md` (which had already been derived from a
  side-by-side audit of `noti.vn`). Generalized the 10-section skeleton,
  the seven-token taxonomy, the primitives kit, the "code is SoT + routing
  table" pattern, the Component-Inventory "load-bearing — do not rename"
  marker, and the verification-gate requirement. Stack-agnostic so a new
  project on any frontend stack (Astro, Next.js, SvelteKit, Vue, plain
  HTML) can adopt without rewriting.
- `2026-05-17` (same day, amendment): replaced the 7-primitive "minimum
  kit" with §3 **Component Coverage Matrix** (~90 components in 11
  functional groups + 8 required states + 5-step size scale), triangulated
  against Radix UI / Ant Design / shadcn/ui / Material 3 / Polaris.
  Marketing and mobile surfaces moved to add-on groups. Added
  forward-compat don't, concretized §11 Verification with three named
  options plus an always-required coverage lint, documented when
  markdown-as-SoT is the right inversion (§1), and ported the flat
  variant-naming convention (`button-primary-hover`) from DESIGN.md. See
  `plans/reports/xia-compare-260517-0954-design-system-references.md` for
  the compare report this amendment is based on.
