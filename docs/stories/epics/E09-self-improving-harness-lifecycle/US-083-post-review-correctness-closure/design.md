# Design

## Resolver Ordering

Select the newest resolver link by durable wall-clock boundary. When that
boundary has nanosecond identity, require a trace with a greater nanosecond
identity. Only a newest legacy boundary uses strict second-resolution fallback.

## Migration Parity

Migration 012 extracts the exact first `rejection_reason: ` notes line into the
structured column for rejected rows. Clean replay and in-place upgrade then
converge on the same representation.

## Validation Boundary

The rebuild script requires an explicit `HARNESS_CLI`. It prints the selected
executable and checks semantic proof (`pass` plus a timestamp) rather than
duplicating mutable verification timestamps. Exact timestamp replay remains
covered by focused Rust tests.

## Compatibility

- Fully legacy resolver histories keep the conservative strict-seconds rule.
- Fully precise histories retain strict nanosecond ordering.
- Existing notes remain intact during rejection-reason backfill.
