# US-113 Proportional V1 Release Gate Validation

Status: **Minimal contract validation passed; platform release evidence pending**

## Required Checks

- `tests/docs/test-proportional-v1-release-gate.sh`
- `tests/release/test-v1-build-receipt-workflow.sh`
- `scripts/validate-premerge.sh`

## Release Evidence Still Pending

- Native build and smoke checks for macOS arm64/x64 and Linux arm64/x64.
- Ordinary pull-request approval of the exact candidate.
- CI-produced downloadable binaries, SHA-256 checksums, and GitHub/Sigstore
  attestations for owner testing before explicit publication.
- Explicit Windows unsupported documentation until native mutation works.

Passing the contract checks proves that the repository describes and enforces
the minimal gate consistently. It does not itself supply native release runs.
