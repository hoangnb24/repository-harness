# US-113 Proportional V1 Release Gate Exec Plan

Status: **Minimal contract implemented; supported-platform release evidence pending**

1. Record Decisions 0017 and 0018 with this high-risk story.
2. Update the refactor plan and Phase 6/7 story status to point to the minimal gate.
3. Replace the sentinel push trigger with bounded manual dispatch.
4. Add focused contract checks and run premerge validation.
5. Run the four initially supported Unix platform checks on the exact release
   candidate, then make the CI binaries, checksums, and attestations available
   for owner download and manual testing.

The first four steps change the contract only. Step 5 produces the real release
evidence. Dogfood and separate independent-review evidence are not required.
