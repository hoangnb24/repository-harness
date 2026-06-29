# Git Workflow

This workflow keeps feature and update work reviewable, traceable, and safe to
merge. It applies after the repository has a baseline commit on `main`.

Bootstrap exception: before the first commit exists, agents may finish the
initial repository setup on `main`, then create the baseline commit. After that
baseline, normal and high-risk work must happen on a branch.

## Branch Policy

| Lane | Branch requirement |
| --- | --- |
| Tiny | May stay on the current branch for narrow docs or copy edits if the user requested it or the repo is still in bootstrap. Prefer a branch in shared repos. |
| Normal | Must use a story-linked branch before implementation starts. |
| High-risk | Must use a story-linked branch and must not merge without human confirmation. |

Never make normal or high-risk changes directly on `main` after the baseline
commit exists.

## Branch Names

Use lowercase kebab-case:

```text
feature/US-012-short-title
fix/US-013-short-title
docs/US-014-short-title
harness/US-015-short-title
hotfix/US-016-short-title
```

Use the story id when one exists. For tiny work without a story, use a short
purpose name such as `docs/readme-typo` or `chore/tool-registry`.

## Start Work

1. Run feature intake and identify the lane.
2. Find or create the story packet for normal and high-risk work.
3. Check Git state:

```bash
git status --short --branch
```

4. If a remote exists, refresh `main` before branching:

```bash
git switch main
git pull --ff-only
```

If no remote exists, record that in the trace and branch from local `main`.

5. Create the work branch:

```bash
git switch -c feature/US-012-short-title
```

If the worktree is already dirty, inspect the changes before branching. Do not
overwrite or revert user changes. Either carry them onto the branch, ask the
user, or record why they are unrelated.

## During Work

- Keep commits scoped to the selected story or tiny change.
- Do not mix unrelated refactors with feature work.
- Do not commit local durable state such as `harness.db`.
- Do not commit secrets, credentials, local environment files, build output, or
  downloaded binaries.
- Update story proof, product docs, decisions, and trace evidence as the work
  changes.

Commit messages should identify the work item:

```text
US-012: add manager role update workflow
harness: document git branch workflow
fix/US-018: reject expired invite tokens
```

## Pre-Merge Gate

Before asking for review or merging:

1. Run story verification:

```bash
scripts/bin/harness-cli story verify-all
```

2. Run any story-specific or stack-specific checks listed in the story packet.
3. Run Validation integrity:

```bash
python3 scripts/validation-integrity-check.py --auto
```

The `--auto` mode uses bootstrap behavior only before the first baseline commit.

4. Check proof status:

```bash
scripts/bin/harness-cli query matrix
```

5. Check Harness drift:

```bash
scripts/bin/harness-cli audit
```

6. Review the Git diff and status:

```bash
git status --short --branch
git diff --check
```

7. Record the trace with the branch name, changed files, validation evidence,
   and remaining risk.

High-risk work also needs any required decision record and explicit human
confirmation before merge.

## Pull Request Or Merge Summary

Every PR or merge request should include:

- Story id or backlog id.
- Lane and risk flags.
- Product or harness contract changed.
- Validation commands and results.
- Decision records added or updated.
- Known follow-up work or skipped checks.

Prefer squash merges for single-story branches when the hosting platform
supports them. Use merge commits when preserving a multi-commit story history is
important. Avoid force-pushing shared branches unless the team explicitly
allows it.

## Protected Main

When the project has a remote or shared repository, protect `main` with the
strongest controls the host supports:

- Require a pull request before merge.
- Require passing validation checks before merge.
- Require at least one human review for normal work.
- Require explicit human approval for high-risk work.
- Block force pushes and branch deletion on `main`.
- Require branches to be up to date before merge when the host supports it.
- Require signed commits or verified authors if that is part of the team's
  security policy.

Do not bypass branch protection except for an urgent hotfix approved by the
human owner. If a bypass happens, record an intervention and a follow-up trace.

## Release And Hotfix Branches

Use `hotfix/<story-id>-<short-title>` only for urgent fixes that must bypass the
normal release cadence. Hotfixes still require intake, proof, trace, and a
post-merge follow-up if validation was narrowed for speed.

Use release branches only when the project has an actual release process. Until
then, do not create release branches just to satisfy process.

## Tool Registry

Version control is an inbound tool capability. Before a workflow step relies on
Git, check whether the project has registered it:

```bash
scripts/bin/harness-cli query tools --capability version-control --status present
```

If it is not registered but Git is available, register it:

```bash
scripts/bin/harness-cli tool register --name git --kind cli \
  --capability version-control --command git \
  --description "Version control for branch, status, commit, and merge workflows" \
  --responsibility "Tool access"
scripts/bin/harness-cli tool check --name git
```

Missing version-control tooling is a workflow blocker for normal and high-risk
implementation work unless the user explicitly narrows the task to docs-only
bootstrap work.
