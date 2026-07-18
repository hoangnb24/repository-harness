# Phase 2 Current-Release Test Fixtures

These fixtures use the frozen Phase 1 unsafe deterministic test keys. They are
test-only and must never be used as production release material.

`current-core-payload-index.json` uses release sequence 44 because the frozen
Phase 1 fixtures already use sequences 42 and 43 for distinct identities. Its
2-of-3 detached signature authenticates the current `decision.md` and
Phase 6-expanded `story.md` bytes at source commit
`aeac84198bdfff9c815aabaa6e02ca89cd24e284`.

`historical-phase1-story.md` is a payload-byte copy used only by tests that
exercise the frozen Phase 1 rollback, revocation, and rotation identities. It
keeps those historical tests valid without modifying the immutable
`tests/fixtures/v1-phase1/**` fixture set.
