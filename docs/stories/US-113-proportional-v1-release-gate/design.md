# US-113 Proportional V1 Release Gate Design

Status: **Accepted design**

## Gate

`promotion = premerge + claimed-platform smoke + ordinary PR approval +
CI binaries/checksums/attestations + explicit owner publish`

Each term is independently checkable. Missing proof narrows the support claim
or keeps promotion closed; it does not create a second evaluation program.

## Boundaries

- Platform proof covers build, install, `audit`, `status`, and `version` on the
  native runner for each claimed platform.
- Normal pull-request approval is the review record; no separate reviewer packet
  is required.
- CI generates downloadable binaries, checksums, and attestations. The owner may
  manually test them before explicit publication.
- Dogfood is optional and is not release evidence.
- The existing detailed diagnostic can be manually dispatched, but it has no
  promotion authority.
