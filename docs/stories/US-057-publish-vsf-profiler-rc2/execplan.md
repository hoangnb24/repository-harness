# Exec Plan

## Goal

Publish VSF Data Profiler `v0.2.0-rc2` to the public product GitHub repository
with US-055 table assessments and US-056 web demo UX redesign.

## Scope

In scope:

- Copy release-worthy product files to
  `/Users/jin/Auto-data-profilling-and-smart-eda-tools`.
- Update rc2 version metadata and release notes.
- Run local validation in the product checkout.
- Commit, tag `vsf-profiler-v0.2.0-rc2`, push, and create a GitHub prerelease.
- Verify README/release links after publishing.

Out of scope:

- Hosted deployment.
- New product features beyond US-055/US-056.
- Copying Harness-only local database or generated output directories.

## Risk Classification

Risk flags:

- External systems: GitHub push, tag, and release creation.
- Public contracts: published repo, tag, and release notes.
- Existing behavior: copies a validated product slice into the release repo.
- Weak proof if release links are not verified after publish.

Hard gates:

- External provider behavior.

## Work Phases

1. Discovery: inspect source and product repo state plus GitHub auth/release.
2. Design: define copy/version/release boundary.
3. Validation planning: use product repo tests, Ruff, node check, demo-full,
   story verify, and release link checks.
4. Implementation: copy files and update rc2 metadata/notes.
5. Verification: run gates and inspect release links.
6. Harness update: update story evidence, test matrix, trace, and audit.

## Stop Conditions

Pause for human confirmation if:

- Product repo remote does not match `Tan-Long/Auto-data-profilling-and-smart-eda-tools`.
- Local product checkout has unrelated user changes.
- Validation gates need to be weakened.
- GitHub push or release creation fails due to auth or permission problems.
