# US-001 Install Harness Into A Project

## Status

implemented

## Lane

normal

## Product Contract

A user can apply the Harness v0 operating files and folder structure to a
target project directory without introducing an application stack, package
scripts, CI, tests, or product implementation.

## Relevant Product Docs

- `README.md`
- `docs/HARNESS.md`
- `docs/FEATURE_INTAKE.md`
- `scripts/README.md`

## Acceptance Criteria

- The installer defaults to the current directory when no target is provided.
- The installer accepts a specific target path through a command-line option or
  positional argument.
- If `AGENTS.md`, `docs/`, or `scripts/` already exists in the target, an
  interactive install shows a warning and asks whether to `1. Merge`,
  `2. Override`, or `3. Stop`.
- If `AGENTS.md`, `docs/`, or `scripts/` already exists in the target, a
  non-interactive install stops before writing files unless `--merge` or
  `--override` is provided.
- A piped `curl | bash` install can still ask interactive questions through the
  controlling terminal when `--yes` is not provided.
- Existing non-protected files are not overwritten by default.
- Forced overwrites create a timestamped backup before replacing non-protected
  files.
- A dry-run mode reports planned file operations without writing files.
- The installer copies only Harness v0 operating files and does not scaffold
  application code, package scripts, CI, or validation commands.
- The installer script and this installer story are not copied into target
  projects.

## Design Notes

- Commands: `scripts/install-harness.sh [--directory path] [--yes] [--force] [--dry-run]`
- Remote install: `curl -fsSL "https://raw.githubusercontent.com/huunghiaish/harness-experimental/main/scripts/install-harness.sh?$(date +%s)" | bash -s -- --yes`
- Queries: none.
- API: none.
- Tables: none.
- Domain rules: preserve Harness v0 as a generic, spec-intake-first operating
  framework.
- UI surfaces: terminal prompts and summary output only.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Shell syntax check for `scripts/install-harness.sh`. |
| Integration | Dry-run into a temporary target reports expected file creation. |
| E2E | Install into a temporary target creates the harness file structure. |
| Platform | POSIX shell execution on the local macOS environment. |
| Release | Not applicable until packaging exists. |

## Harness Delta

Adds the first real harness automation script while keeping installer internals
out of target projects and preserving the Harness v0 rule that application
implementation surfaces are not scaffolded.

## Evidence

- `bash -n scripts/install-harness.sh`
- `scripts/install-harness.sh --directory "$LOCAL_TARGET" --yes`
- `scripts/install-harness.sh --directory "$README_TARGET" --yes` after adding a
  custom `README.md` in the target
- `scripts/install-harness.sh --directory "$AGENTS_CONFLICT" --yes`
- `scripts/install-harness.sh --directory "$DOCS_CONFLICT" --yes`
- `scripts/install-harness.sh --directory "$SCRIPTS_CONFLICT" --yes --force`
- `scripts/install-harness.sh --directory "$NONINTERACTIVE_MERGE" --merge --yes`
- `scripts/install-harness.sh --directory "$NONINTERACTIVE_OVERRIDE" --override --yes`
- interactive conflict prompt with `1` choice to merge missing files
- interactive conflict prompt with `2` choice to back up and override protected
  paths
- interactive conflict prompt with `3` or default choice to stop without writing
  files
- `HARNESS_SOURCE_BASE_URL="file:///Users/themrb/Documents/personal/harness-experimental" bash -s -- --directory "$REMOTE_TARGET" --yes < scripts/install-harness.sh`
- `curl -fsSL "file:///Users/themrb/Documents/personal/harness-experimental/scripts/install-harness.sh" | HARNESS_SOURCE_BASE_URL="file:///Users/themrb/Documents/personal/harness-experimental" bash -s -- --directory "$TARGET" --yes`
- `HARNESS_SOURCE_BASE_URL="file:///Users/themrb/Documents/personal/harness-experimental" bash -s -- --directory "$DRY_TARGET" --yes --dry-run < scripts/install-harness.sh`

Validated behaviors: dry-run writes no files, real install creates the harness
structure, existing `README.md` is left untouched by default, non-interactive
targets containing `AGENTS.md`, `docs/`, or `scripts/` stop with a warning
before writing files unless `--merge` or `--override` is provided, interactive
users can stop, merge missing files, or back up and override protected paths
even when the script is piped into Bash, remote-source mode works when the
script is piped into Bash, and target projects do not receive
`scripts/install-harness.sh` or this installer story.
