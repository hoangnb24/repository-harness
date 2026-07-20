# US-113 Proportional V1 Release Gate Design

Status: **Accepted design**

## Gate

`promotion = premerge + claimed-platform smoke + one dogfood comparison +
independent review + release-time provenance`

Each term is independently checkable. Missing proof narrows the support claim
or keeps promotion closed; it does not create a second evaluation program.

## Boundaries

- Dogfood fixes the starting revision, prompt, expected checks, and baseline
  before the candidate run.
- Platform proof covers build, install, `audit`, `status`, and `version` on the
  native runner for each claimed platform.
- Provenance is generated and verified by the workflow that publishes the
  actual artifact.
- The existing detailed diagnostic can be manually dispatched, but it has no
  promotion authority.
