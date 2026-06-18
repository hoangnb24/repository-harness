# Design

## Domain Model

Release entities:

- Source workspace: `/Users/jin/repository-harness`, where US-055 and US-056
  are validated.
- Product repository: `/Users/jin/Auto-data-profilling-and-smart-eda-tools`,
  remote `Tan-Long/Auto-data-profilling-and-smart-eda-tools`.
- Version: `0.2.0-rc2` for package metadata and
  `vsf-profiler-v0.2.0-rc2` for the Git tag.
- GitHub prerelease: public release entry that points to the rc2 tag.

## Application Flow

1. Confirm product checkout, remote, current branch, and auth.
2. Copy release-worthy product files from the source workspace.
3. Bump version metadata from rc1 to rc2.
4. Validate in the product checkout.
5. Commit and tag.
6. Push `main` and tag.
7. Create GitHub prerelease and verify links/rendering.

## Interface Contract

No runtime API, route, artifact, or CLI command contract changes are introduced
by this release task.

## Data Model

No data model changes. The release contains prior US-055/US-056 behavior.

## UI / Platform Impact

The published product repo receives the US-056 local web runner console redesign
and `.interface-design/system.md` design memory.

## Observability

Harness story, trace, test matrix, local validation output, Git commit, Git tag,
and GitHub release URL provide release evidence.

## Alternatives Considered

1. Publish from the dirty harness repository directly. Rejected because the
   public product repo has a clean allow-list and no Harness durable layer.
2. Use the sibling `Auto-data-profilling-and-smart-eda-tools-1` checkout.
   Rejected because it has unrelated local dirt.
