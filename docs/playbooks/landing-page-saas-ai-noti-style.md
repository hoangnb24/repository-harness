# Landing Page — SaaS / AI / Digital Product, "noti.vn" Style

> Reusable structure for marketing landing pages that sell a SaaS app, AI
> product, or paid digital deliverable. Inspired by `noti.vn`. **Not** for
> government, education, enterprise-compliance, or other "trang nghiêm /
> formal" sites — those need denser typography, smaller CTAs, and more
> conservative color use; see `When NOT to use this playbook` below.

## When this fits

Use when **all** of these are true:

- Audience is consumer / SMB / indie developer / creator.
- Product is a paid app, AI tool, course, or template pack — bought through a
  short funnel.
- The visitor's first decision is "is this for me" rather than "is this
  trustworthy enough for procurement".
- Brand can be friendly, bold, and confident.

## When NOT to use this playbook

| Audience | Use instead |
|----------|-------------|
| Government, public sector | Conservative, dense, accessible-first layouts. Smaller H1, smaller CTAs, neutral palette, more text per page, formal tone. |
| Education (K-12, university), academic research | Trust-first, content-dense, slower visual rhythm. Avoid gradient washes and 3D mockups. |
| Enterprise procurement, regulated industries (banking, health) | Lean on logos, certifications, dense feature tables, white-paper downloads. Big CTAs feel pushy. |
| Personal portfolio, editorial blog | Editorial typography, narrow column, fewer surfaces. The bento grid here is overkill. |

If the audience straddles two buckets, default to the more conservative one
and lift only the patterns that carry over (typography hierarchy, anchor TOC).

## Source observation

The patterns below were extracted from `https://noti.vn/` and
`https://noti.vn/skill/content/` on 2026-05-16. Screenshots saved in the
discovering project; not duplicated here to keep the playbook portable.

## What makes noti feel "premium" — in priority order

The cheapest moves first. If you only adopt the top 5, you already cover
~80% of the visual lift.

1. **Full-width sections, end to end.** Every section spans 100% viewport
   width with the content centered in a max-width container (typically
   `~1200px`). Background color, gradient, or image bleeds to the page edges.
   Local sites that constrain the entire page to a narrow column read as
   "blog template". Full-width reads as "product".
2. **Big, bold display typography.** Hero H1 is 48-72px on desktop, weight
   700-800, tight tracking. Section H2 is 36-48px, weight 700. Numbers in
   stat panels are 56-72px. The default body stays 16-18px, but every
   headline, price, and stat is loud. Don't hedge.
3. **Big, high-contrast CTA buttons.** Primary CTA is **48-56px tall**,
   horizontal padding `24-32px`, weight 600, with a leading icon or a
   trailing arrow. Secondary CTA matches height, outlined or ghost. Pair
   them. Local sites that use small pill buttons lose immediately on
   click-rate signal.
4. **Hero radial gradient + 3D layered product tiles.** Soft brand-color
   radial wash bleeding from the top-right behind the hero. On top, 3 small
   rectangular product cards, slightly rotated and stacked with shadow, hint
   at what the product *is* without forcing a full screenshot.
5. **Section heading triplet: chip → big H2 → muted subhead.** Always the
   same three pieces. The chip carries the section's role
   (`PRODUCTS & SERVICES`, `COMMUNITY`, `PRICING`). The H2 carries the
   promise. The subhead in muted gray carries the one-line elaboration.
   Skipping the subhead is the most common mistake.
6. **Bento card grid, not a uniform tile grid.** One large feature card
   (gradient brand color, illustration, big headline) sits beside 4 smaller
   white cards (icon, title, 1-line description, link). Asymmetric weight =
   curated; uniform tiles = list dump.
7. **Closing CTA gets its own surface.** A pale-gray full-width strip with
   centered H2 and dual buttons sits between the last content section and
   the footer. Don't bury the closing CTA inside the last content card.
8. **Dark navy footer with 4 columns.** Brand block (logo + tagline + social
   row) on the left; 3 link columns (Explore / Connect / Contact) on the
   right.
9. **Trust strip in the hero.** Three short proof items immediately under
   the CTA pair: members count, rating, security badge. Tiny icon + label.
   Even modest numbers help anchor credibility.
10. **Long-scroll product page with sticky anchor TOC.** Detail / pricing /
    skill / "what's inside" pages run long, divided by chip-headed sections,
    with a sticky table of contents on the right rail (or top, on mobile).
    Tabs hide content and break linking; anchors don't.

## Product / skill detail page additions

For pages that sell one specific item (course, skill pack, AI agent), add:

11. **Hero proof: a high-fidelity static screenshot of the actual deliverable**
    (the chat UI, the diagram, the final document). Skip video unless you
    already have a tight 30-60s demo; static screenshots load instantly and
    don't fight the eye.
12. **Pricing block needs a frame**, not three plain text columns. Card with
    a `PRICING` chip, the big primary number (56-72px), 1-line value framing
    underneath, and the primary CTA inside the card.
13. **Sticky right-rail order form** for desktop, collapsing into a
    sticky-bottom CTA bar on mobile. Mirrors what noti's skill page does.
14. **"What's inside" / "before vs after"** section with screenshots or a
    numbered checklist, never plain bullet text alone.

## Patterns to consciously skip

These are tempting but underperform on this audience:

- Stats panel with sub-1k numbers. Skip the panel until a number reads
  impressive (≥1k members / installs / paying users). Replace with a
  testimonial strip, customer logos, or a feature spotlight.
- Inline tabs on a long-scroll page. They hide content and break deep
  linking — use anchored sections + a TOC.
- Auto-playing hero video. Hurts LCP, often blocked, rarely watched.
  Static screenshot first, click-to-play video only if you need the demo.

## Typography token sketch

Concrete sizes that match the noti feel. Adjust ±2px to taste; do not
shrink the headline scale below the floor or the page deflates.

```
Display (hero H1):     56-72px / 700-800 / -1% tracking / 1.05 line-height
Section H2:            36-48px / 700     / -0.5%        / 1.15
Card H3:               20-24px / 600     / 0%           / 1.3
Stat number:           56-72px / 700     / -2%          / 1
Body:                  16-18px / 400     / 0%           / 1.6
Subhead under H2:      18-20px / 400     / 0%           / 1.5  (muted color)
Chip (uppercase):      11-12px / 600     / +8%          / 1    (uppercase, brand-tinted bg)
Button label:          15-16px / 600     / 0%           / 1
Footer / micro:        13-14px / 400     / 0%           / 1.5
```

## Color token sketch

`--brand` is whatever accent the project picks (noti uses a saturated blue;
a teal / emerald accent works equally well). Keep the rest neutral.

```
--brand-600           main accent (CTA bg, link, chip text)
--brand-500           gradient stop 1
--brand-400           gradient stop 2 (lighter, for hero radial)
--brand-50            subtle brand-tinted background for chips and surfaces
--ink-900             headline text
--ink-700             body text
--ink-500             muted / subhead
--ink-200             borders, dividers
--surface-0           page background
--surface-100         pale-gray closing-CTA strip and section dividers
--surface-900         dark navy footer
```

CTA button: filled `--brand-600` background, white text, `12-14px` border
radius, soft shadow on hover. Outline button: `1.5px` `--ink-200` border,
`--ink-900` text.

## Layout token sketch

```
Container max-width:       1200px (1280px max for hero with floating tiles)
Section vertical padding:  80-120px desktop, 56-72px mobile
Card padding:              24-32px
Card border radius:        16-20px
Button radius:             999px (full pill) or 12px (rounded-rect) — pick
                           one and use globally
```

## Minimum viable page

If you only build five sections, build these in this order:

```
1. Hero
   - Full-width with brand-tinted radial gradient bleed top-right
   - H1 (display) + 1-line subhead + dual CTA + 3-item trust strip
   - 3D layered product tiles on the right (or below on mobile)

2. Bento feature grid
   - Chip "PRODUCTS" + H2 + muted subhead
   - 1 large gradient feature card + 4 white tiles in 2x2

3. How it works / "what's inside" (3 steps or 4 numbered cards)

4. Closing CTA strip
   - Pale-gray full-width
   - Centered H2 + dual buttons

5. Footer
   - Dark navy, 4 columns
```

Stats panel and testimonials are nice-to-have; add only when the numbers /
quotes are strong enough to carry their own surface.

## Implementation hints

Stack-agnostic, but a few rules of thumb regardless of framework:

- Use the project's existing icon library if it has one. If not, install
  **lucide** (`lucide-react`, `lucide-vue`, `@lucide/svelte`, etc.) — clean
  monoline icons, MIT-licensed, ships well with shadcn-style systems.
- Render the chip as a `span` with brand-tinted background and `--brand-600`
  text, never as an actual button.
- The hero radial gradient is one CSS `radial-gradient` on a positioned
  pseudo-element, not an image. This keeps it crisp on retina and avoids a
  network round trip.
- The 3D layered tiles can be three absolutely-positioned `div`s with small
  rotation transforms and box-shadows. No 3D library needed.
- For the bento grid, use CSS Grid with explicit `grid-template-areas` so
  the large feature card and small tiles fall in the right slots without
  fragile flex hacks.
- Keep the footer simple. A 4-column grid that collapses to a 2-column on
  tablet and 1-column on mobile is the standard.

## Anti-patterns

- Constraining the entire page to `max-w-3xl` (~768px). Reads as a blog,
  not a product. Use full-width sections with centered containers.
- Replacing every card image with a placeholder rectangle. Either ship the
  real image or ship a custom SVG illustration; never ship a grey box.
- Mixing pill buttons (`radius: 999px`) and rounded-rect buttons
  (`radius: 12px`) on the same page. Pick one shape and use it everywhere.
- Section headings without the chip + subhead pair. Visual rhythm flattens.
- Tabs to hide long-form content. Use anchored sections instead.
- Tiny CTAs (32-40px tall). On a marketing page, the CTA is the product;
  size it like one.

## Adapting to other audiences

When repurposing for non-SaaS contexts, override these specific points:

| Override | Government / Education | Enterprise procurement |
|----------|------------------------|------------------------|
| Hero H1 | 36-48px (smaller, denser) | 36-44px |
| CTA buttons | 40-44px tall, single primary | 40-44px, "Talk to sales" instead of "Buy now" |
| Color | Conservative palette (navy, slate, ink) | Brand color used sparingly |
| Hero visual | Photo or seal, not 3D mockup | Logo grid of customers |
| Bento feature grid | Replace with denser feature table | Replace with ROI calculator + case studies |
| Stats panel | Use only with audited / cited numbers | Same |
| Closing CTA | Newsletter signup or contact form | "Talk to sales" + calendar embed |

When in doubt: shrink the type, calm the color, and lean on dense content
over visual flourish.

## Related Tools And Skills

- `/ck:frontend-design` — replicate a mockup or screenshot in code.
- `/ck:ui-styling` — Tailwind + shadcn implementation help.
- `/ck:ui-ux-pro-max` — color, font, system selection.
- `/ck:web-design-guidelines` — accessibility and UX audit of an existing
  page.
- Adjacent playbooks: `headless-browser-blank-screenshot.md` for capturing
  reference screenshots of competitor sites.

## History

- `2026-05-16`: created. Extracted from a side-by-side audit of
  `nguyenhuunghia.vn` (Astro) vs `noti.vn`. User confirmed scope is
  SaaS / AI / digital-product landing pages; gov / edu / enterprise covered
  via the override table. Added the "full-width sections + big typography +
  big CTA" emphasis after the user pointed out that the local page felt
  cramped and the typography too small relative to noti.
