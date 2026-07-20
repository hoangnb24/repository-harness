# US-113 Proportional V1 Release Gate Validation

Status: **Contract validation passed; release evidence pending**

## Required Checks

- `tests/docs/test-proportional-v1-release-gate.sh`
- `tests/release/test-v1-build-receipt-workflow.sh`
- `scripts/validate-premerge.sh`

## Release Evidence Still Pending

- One fixed-condition dogfood baseline/candidate comparison with no regression.
- Native build and smoke checks for every platform claimed as supported.
- Independent review of the exact candidate.
- Provenance generated and verified by the actual release workflow.

Passing the contract checks proves that the repository describes and enforces
the smaller gate consistently. It does not itself satisfy those release gates.
