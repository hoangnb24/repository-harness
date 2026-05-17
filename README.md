# harness-experimental

## Current State

This repository is in Harness v0.

There is no application implementation and no baked-in product specification
yet. The current work is the reusable project harness: the file structure,
agent operating model, feature intake process, story templates, and validation
expectations that help humans and agents turn a future user-provided spec into
implementation work.

## Product Sources

No product contract is currently defined.

When a user provides a project specification, add or reference it as the input
spec for the first buildout, then derive smaller living artifacts from it:

- `docs/product/`: current product contract files, created from the spec.
- `docs/stories/`: story packets and backlog created from selected work.
- `docs/TEST_MATRIX.md`: behavior-to-proof control panel.
- `docs/decisions/`: durable decisions and tradeoffs.

Do not keep a project-specific spec or product breakdown in this harness until
a real project supplies one.

## Harness Sources

- `AGENTS.md`: agent entrypoint and operating rules.
- `docs/HARNESS.md`: human-agent collaboration model.
- `docs/FEATURE_INTAKE.md`: tiny, normal, and high-risk work classification.
- `docs/ARCHITECTURE.md`: generic architecture discovery and boundary rules.
- `docs/HARNESS_BACKLOG.md`: proposed harness improvements.
- `docs/playbooks/`: reusable recipes for recurring tooling, environment, and
  workflow problems. Read before fighting a familiar symptom. Includes
  patterns for localizing client templates (bilingual delivery) and
  composing multi-step playbooks.
- `docs/templates/`: reusable spec-intake, story, decision, and validation
  templates.

## Repository Structure

```text
project/
  AGENTS.md
  README.md
  docs/
    HARNESS.md
    FEATURE_INTAKE.md
    ARCHITECTURE.md
    TEST_MATRIX.md
    HARNESS_BACKLOG.md
    product/
    stories/
    decisions/
    playbooks/
    templates/
  scripts/
    README.md
```

## Working Rule

Implementation prompts do not go straight to code. They first pass through
feature intake, become story-sized work when needed, and then carry both
product validation and harness maintenance expectations.

## Greenfield Bootstrap (from raw inputs)

For a brand-new project, raw inputs (client-provided spec, brainstorm
notes written with ChatGPT/Claude, meeting transcripts, mockup
screenshots, sample data) all land under `docs/discovery/` per
`docs/decisions/0009-discovery-input-folder-convention.md`. There is no
special `SPEC.md` at repo root — the "spec" is the aggregate of
discovery inputs plus the vendor-produced intake artifacts under
`docs/intake/`.

### One-liner (recommended)

If you have a single spec file ready:

```bash
curl -fsSL "https://raw.githubusercontent.com/huunghiaish/harness-experimental/main/scripts/install-harness.sh?$(date +%s)" \
  | bash -s -- --bootstrap --spec /path/to/your-spec.md ./my-new-project
```

This: creates the target dir, copies the harness, runs `git init`,
places your spec at `docs/discovery/YYYY-MM-DD-initial-spec.md`, and
prints the next-step prompt for Claude Code. See
`docs/decisions/0011-bootstrap-installer-mode.md` for details.

### Multi-file or manual path

When you have multiple input artifacts (mockups, meeting notes, sample
data), the four-step manual path remains:

```bash
# 1. Empty folder for the new project
mkdir my-new-project && cd my-new-project

# 2. Install harness into it (one-liner — see "Install Harness Into A Project" below for options)
curl -fsSL "https://raw.githubusercontent.com/huunghiaish/harness-experimental/main/scripts/install-harness.sh?$(date +%s)" | bash -s -- --yes

# 3. Drop ALL raw input artifacts into docs/discovery/ (one file per artifact, date-prefixed)
mkdir -p docs/discovery
cp /path/to/your-spec.md           docs/discovery/$(date +%Y-%m-%d)-initial-spec.md
# cp /path/to/brainstorm-notes.md  docs/discovery/$(date +%Y-%m-%d)-brainstorm-notes.md
# cp /path/to/mockup.png           docs/discovery/$(date +%Y-%m-%d)-checkout-mockup.png
# ... repeat for every artifact you have

# 4. Initialize the project's own git history
git init && git add -A && git commit -m "chore: bootstrap from harness + add discovery inputs"
```

Then open Claude Code (or any agent that reads `AGENTS.md`) and prompt:

> Read all files under `docs/discovery/`. Run Phase 1 Spec Intake per
> `docs/FEATURE_INTAKE.md` § Spec Approval Gate. Create
> `docs/intake/YYYY-MM-DD-spec-intake.md`. Stop after intake for human review.

Approve the intake (see `docs/FEATURE_INTAKE.md` § Spec Approval Gate).
Only then does the agent derive `docs/product/*`, architecture
decisions, design-direction decisions, and first story packets. From
there, the agent follows the full Task Loop in `AGENTS.md` per story.

The single-command equivalent (planned `--bootstrap` flag — see
`docs/HARNESS_BACKLOG.md` entry) bundles steps 1+2+3+4 into one
invocation.

**Why curl install over `git clone`**: the installer copies only the
harness skeleton (AGENTS.md + docs/ + scripts/), not this repo's git
history, plans/, or in-progress work. Cleaner starting point.

If `curl` is not available or you want full file visibility before
running, use the manual fallback: clone, delete `.git`, re-init, drop
inputs into `docs/discovery/`, commit.

## Install Harness Into A Project

From a target project directory, run:

```bash
curl -fsSL "https://raw.githubusercontent.com/huunghiaish/harness-experimental/main/scripts/install-harness.sh?$(date +%s)" | bash -s -- --yes
```

If the target already has `AGENTS.md`, `docs/`, or `scripts/`, choose one:

```bash
# Keep existing files and add only missing Harness files
curl -fsSL "https://raw.githubusercontent.com/huunghiaish/harness-experimental/main/scripts/install-harness.sh?$(date +%s)" | bash -s -- --merge --yes

# Back up and replace AGENTS.md, docs/, and scripts/
curl -fsSL "https://raw.githubusercontent.com/huunghiaish/harness-experimental/main/scripts/install-harness.sh?$(date +%s)" | bash -s -- --override --yes
```

Or install into a specific path:

```bash
curl -fsSL "https://raw.githubusercontent.com/huunghiaish/harness-experimental/main/scripts/install-harness.sh?$(date +%s)" | bash -s -- --directory /path/to/project --yes
```

If the target already contains `AGENTS.md`, `docs/`, or `scripts/`, interactive
installs ask whether to `1. Merge`, `2. Override`, or `3. Stop`. Non-interactive
installs using `--yes` stop before writing unless `--merge` or `--override` is
provided. Use `--dry-run` to preview changes. The installer itself and this
repository's installer story are not copied into the target project.
