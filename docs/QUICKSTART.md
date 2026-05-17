# Quickstart — First 3 Hours

You have just installed the harness into a fresh project. Follow this order. Each step links to authoritative docs — read them when you need depth, skip when the step is obvious.

## 0. Verify install

```bash
ls AGENTS.md docs/ scripts/install-harness.sh
```

All three exist → good. Otherwise re-run the installer (see project root `README.md`).

## 1. Drop raw inputs into `docs/discovery/`

Everything you have so far — client-provided spec, brainstorm notes you wrote with ChatGPT/Claude, mockup screenshots, meeting transcripts, sample CSVs — lands here, one file per artifact, date-prefixed:

```text
docs/discovery/YYYY-MM-DD-<kebab-slug>.<ext>
```

Convention: `docs/discovery/README.md`. There is **no** `SPEC.md` at repo root.

If you used `install-harness.sh --bootstrap --spec /path/to/file`, your initial spec is already in `docs/discovery/`.

## 2. Run Phase 1 spec intake

Open Claude Code (or any agent that reads `AGENTS.md`) and prompt:

> Read all files under `docs/discovery/`. Run Phase 1 Spec Intake per `docs/FEATURE_INTAKE.md` § Spec Approval Gate. Create `docs/intake/YYYY-MM-DD-spec-intake.md`. Stop after intake for human review.

The agent reads inputs + writes a structured restatement. Phase 1 is read-only against your `docs/product/` — no contract is created yet.

## 3. Human approval gate

Read `docs/intake/YYYY-MM-DD-spec-intake.md`. Verify:

- Project summary matches what you actually want to build.
- Candidate epics match the surface areas you expect.
- Architecture questions surface real ambiguities, not boilerplate.
- First-story candidates are scoped tight enough to start in week 1.

Reply with `approved`, `looks good`, or specific corrections + approval.

## 4. Phase 2 — derive product docs + first decisions

After approval, the agent proceeds to:

1. Populate `docs/product/*` (current product contract).
2. Write the **stack-selection decision** using `docs/templates/decisions/stack-selection.md`. This is the first decision — it gates every story below.
3. If UI is in scope, run Style Intake per `docs/playbooks/ui-design-system-contract.md` → produces `docs/design-guidelines.md`.
4. Slice initial story candidates into `docs/stories/epics/EXX-*/US-NNN-*.md`.
5. Populate `docs/code-standards.md` from `docs/templates/code-standards.md` once the stack is picked.

## 5. Pick your lane

`docs/FEATURE_INTAKE.md § Classification` decides which stages fire next:

| Lane | Next steps |
| --- | --- |
| Tiny | Skip to stage 8 (Build). Most stages are noise. |
| Normal | Walk stages 6 → 10 lightly. RPM + Status Flow optional. |
| High-Risk | Run all 13 stages. RPM + Status Flow strict per `docs/playbooks/visual-and-behavioral-modeling.md` § C.6. |

For paid client work: read `docs/playbooks/solo-dev-client-delivery.md` end-to-end before starting stage 4 (SOW). For internal / OSS: skip the meta-playbook; go straight from intake to story slicing.

## 6. First story — first commit

Before writing code:

- Stack-selection decision must exist (`docs/decisions/NNNN-stack-selection.md`).
- `docs/code-standards.md` populated.
- `validate:quick` script runs successfully (per `docs/playbooks/build-execution.md`).

Then: pick the lowest-ID story in `docs/stories/backlog.md`, follow `docs/playbooks/build-execution.md` for commit hygiene. Every commit body cites at least one `US-NNN.REQ-MMM` / `US-NNN.SC-MMM` token.

## 7. End of session — capture

If this session spanned 3+ commits OR multiple intake items, run `docs/playbooks/session-retrospective.md` and save the report to `plans/reports/retro-<date>-<slug>.md`.

## Where to go from here

| You want to | Read |
| --- | --- |
| Full 13-stage workflow map | `docs/WORKFLOW.md` |
| Operating model + token chain | `docs/HARNESS.md` |
| Risk classification + lanes | `docs/FEATURE_INTAKE.md` |
| Architecture rules | `docs/ARCHITECTURE.md` |
| All playbooks (recipes) | `docs/playbooks/README.md` |
| All templates (scaffolds) | `docs/templates/README.md` |
| All decisions (history) | `docs/decisions/README.md` |
| Friction → backlog | `docs/HARNESS_BACKLOG.md` |
