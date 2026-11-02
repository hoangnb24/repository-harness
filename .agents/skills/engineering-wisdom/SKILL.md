---
name: engineering-wisdom
description: Use only when the user explicitly invokes `$engineering-wisdom`. Provide repository-grounded engineering advice using contextual heuristics. Advice does not establish repository policy or authorize an architecture rewrite.
---

# Engineering Wisdom

Give practical advice without treating a school of thought as universal law.
Repository intent, code, tests, and observed behavior remain authoritative.

## Establish Scope

1. Read `AGENTS.md`, `docs/WORKFLOW.md`, and only the repository material
   relevant to the request.
2. Confirm that the user explicitly invoked this skill. Installation alone is
   not activation.
3. Determine whether the request is advice/review or an authorized change.
   Keep reviews read-only. For changes, follow repository authority and
   validation rules before editing.
4. Read [references/heuristics.md](references/heuristics.md). Select only
   heuristics that match observed evidence. Read
   [references/sources.md](references/sources.md) when attribution or the
   intellectual basis matters.
5. When the request crosses a host boundary, inspect the composition root,
   external input, adapter semantics, shipped artifact, and cumulative state
   that are relevant. Do not assume isolated core tests prove those boundaries.

## Review From Evidence

For each material finding, keep these fields separate:

- **Observation:** A concrete repository fact with a path, symbol, test,
  command result, or behavior.
- **Heuristic:** One named rule of thumb from the catalog and why it may apply.
- **Trade-off:** Counter-pressure, cost, or a condition under which following
  the heuristic would make the system worse.
- **Proposed repository-owned enforcement:** Either `None`, or a separately
  labeled proposal naming the repository owner, authority still required,
  possible mechanism, and removal condition. Never describe advice as an
  existing rule unless repository evidence already establishes it.
- **Verification:** A focused observation or executable check that could
  confirm or falsify the recommendation. Match proof to the claim: test pure
  policy in isolation, startup at the composition root, and delivery through
  the artifact users actually load.

Rank findings by user impact and change risk. Prefer one concrete example over
several abstract claims.

## Advise Before Enforcing

- Do not rewrite application architecture merely because a heuristic suggests
  a different shape.
- Do not introduce interfaces, layers, tests, linters, size limits, coverage
  targets, or dependency rules without repository-owned authority.
- Propose the smallest reversible experiment when evidence is incomplete.
- Preserve a deliberate duplication, coupling, integration test, or framework
  dependency when its local benefit outweighs the heuristic.
- Say when no catalog heuristic materially improves the observed code.

If the user requests implementation and authority is sufficient, make the
smallest coherent change and run the repository's own proof. Keep the review
rationale separate from the evidence that the change works.

## Response Shape

Start with the outcome in one sentence. Then report only material findings:

```text
Finding: <specific effect>
Observation: <repository evidence>
Heuristic: <contextual rule of thumb and applicability>
Trade-off: <counter-pressure or harm condition>
Proposed repository-owned enforcement: None | <owner, missing authority,
mechanism, removal condition>
Verification: <command, test, measurement, or observation>
```

End with unresolved risks or `None`. Do not add a policy checklist by default.

## Receipt

End the final answer with exactly one last line:
`HARNESS_SKILL: engineering-wisdom | done|stopped|skipped | <artifact path or reason>`.
Use `stopped` when an authority gate or missing capability stops the work. The
third field is never empty, for example
`HARNESS_SKILL: engineering-wisdom | stopped | <missing authority or capability>`.
