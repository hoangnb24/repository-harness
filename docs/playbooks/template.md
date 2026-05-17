# Playbook Title

**Lifecycle:** experimental · **First use:** TBD · **Verified by:** none

> One-sentence problem statement an agent can grep for.

> **Shape variants** — this template is the canonical shape for a
> **Tooling fix** playbook. Other shapes exist in this folder:
>
> - **Structural framework** (e.g. `ui-design-system-contract.md`) —
>   opens with "When this fits" + "What this means", then a contract
>   skeleton + token taxonomy + verification gate. No Symptoms section.
> - **Surface recipe** (e.g. `landing-page-saas-ai-noti-style.md`) —
>   opens with "When this fits" + "When NOT to use", then numbered
>   patterns in priority order + token sketches + anti-patterns.
> - **Workflow recipe** (e.g. `e2e-recording-user-guide-quality.md`) —
>   keeps Symptoms + Root Cause but Fix expands to a recipe with helper
>   modules, multiple sections, and an acceptance gate.
>
> Pick the shape matching your purpose. Don't force a fix recipe into a
> framework, or vice versa.

## Symptoms

How does the problem present? List concrete signals an agent will see:

- Exact error message or output substring.
- Tool exit code or absence of output.
- Visual symptoms (blank screenshot, frozen UI, etc.).
- File-size, timing, or log patterns that hint at the root cause.

## When This Hits

Environments, tools, frameworks, or workflows where this is known to occur.
Mention versions if version-sensitive.

## Root Cause

Short explanation. One paragraph max. Link upstream issues if known.

## Fix

The minimum working recipe. Prefer copy-pasteable commands or a small code
snippet over prose. Use placeholders like `<project-root>`, `<url>`,
`<output-path>` so the recipe is portable.

```bash
# Example command
```

```js
// Example snippet
```

## Variants

Only add this section when the primary fix has a known failure mode and a
secondary recipe exists. Each variant should explain when it applies before
showing the recipe.

### Variant: <when this applies>

Steps.

## Related Tools And Skills

- Tool / skill that exposed the problem.
- Tool / skill used in the fix.
- Adjacent playbooks or decisions, if any.

## History

- `YYYY-MM-DD`: created. Discovered while …
- `YYYY-MM-DD`: variant added for …
