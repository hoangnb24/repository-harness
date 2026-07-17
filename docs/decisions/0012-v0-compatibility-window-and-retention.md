# 0012 V0 Compatibility Window And Retention

Date: 2026-07-17

## Status

Accepted

Decision 0014 changes cutover mechanics but preserves this decision's dates,
indefinite local-archive retention, bridge-asset retention, and Phase 8 gates.
Because the archive-only bridge creates no conversion journal, the historical
post-window journal clause applies only to any previously accepted journal; it
does not authorize new bridge recovery state.

## Context

Decision 0011 established a separate, time-bounded V0 conversion bridge but
left the exact compatibility dates, recovery-evidence retention, bridge-release
retention, and removal eligibility for a later human decision. US-105 therefore
kept Gate G0 closed: without those values, Phase 1 could not freeze honest
support, release, recovery, or retirement contracts.

The policy must also handle a delayed release without silently reducing the
promised support period. It must distinguish local recovery evidence, which is
under each repository owner's custody, from centrally published bridge release
assets, which release maintainers can verify and retain.

## Decision

Gate G0 is approved with the following compatibility policy:

- The V0 compatibility window starts at `2027-01-01T00:00:00Z` and ends at
  `2027-12-31T23:59:59Z`, inclusive.
- Window support covers security, data-loss, archive/recovery, and
  supported-input compatibility defects or mitigations. It does not include
  new V0 features.
- A conversion journal created before the window closes remains eligible for
  supported resume or rollback after the closing timestamp. A known unresolved
  in-window recovery case delays actual Phase 8 removal until it is closed.

The approved dates assume that the V1 core and bridge are generally available
on every declared platform by `2027-01-01T00:00:00Z`. If either is not, the
window must not silently shrink. A new explicit decision must shift the start,
end, bridge-asset-retention deadline, and Phase 8 eligibility together, reaffirm
the local-archive rule, and preserve at least 365 supported days.

Local conversion archives are retained indefinitely. Each archive is
write-once, checksum-verified recovery evidence under the repository owner's
custody. No install, update, audit, bridge command, uninstall, or Phase 8 action
may automatically delete, overwrite, truncate, or relocate it. Manual deletion
must be an explicit repository-owner action and must warn that deleting the
archive loses V0 recovery.

Bridge release assets are retained through `2028-06-30T23:59:59Z`, inclusive.
The retained set includes every supported-platform binary, checksum,
authenticated index or attestation, supported-input matrix, release notes,
source tag, and reproducible build instructions. Release maintainers own
periodic availability verification for that complete set.

Phase 8 is eligible no earlier than `2028-01-01T00:00:00Z`. That timestamp is
necessary but not sufficient. Actual removal also requires:

- Phase 7 acceptance and closure of all support and recovery obligations;
- no known unresolved in-window recovery case;
- no unresolved supported-range security, data-loss, or archive-integrity
  defect;
- verified retention and availability of all required bridge release assets;
  and
- separate removal authorization and validation.

Phase 8 never authorizes deletion or relocation of a local conversion archive.
It also cannot end retention of the enumerated bridge release assets before
`2028-06-30T23:59:59Z`.

Concrete cause and effect:

1. If one declared platform does not receive both generally available
   artifacts by `2027-01-01T00:00:00Z`, keeping the original end date would
   reduce supported time for that platform. A new decision must move all
   coupled dates and preserve at least 365 supported days before Phase 1 or a
   release can rely on a replacement schedule.
2. If a conversion begins at `2027-12-31T23:59:59Z` and its journal later
   requires resume or rollback, the closing timestamp does not terminate that
   recovery obligation. The case remains supported and blocks actual Phase 8
   removal until it is resolved.
3. If Phase 8 is separately authorized while a repository still has a local
   archive, removal may delete default V0 product code but must leave that
   archive at its existing path and bytes. Only the repository owner may
   explicitly delete it after receiving the V0-recovery-loss warning.

## Alternatives Considered

1. Start implementation without exact dates. Rejected because release metadata,
   support obligations, retention proof, and Phase 8 preconditions would remain
   undefined.
2. Keep the end date if general availability is late. Rejected because the
   compatibility promise would silently shrink on affected platforms.
3. Give local archives a finite automatic cleanup period. Rejected because the
   archives are the repository owner's recovery evidence and automated cleanup
   could make V0 recovery impossible.
4. Treat the Phase 8 eligibility timestamp as automatic removal authorization.
   Rejected because unresolved recovery, security, data-loss, archive-integrity,
   or asset-retention conditions still make removal unsafe.

## Consequences

Positive:

- Phase 1 can encode exact support, retention, and retirement contracts without
  inventing defaults.
- Repository owners retain durable recovery evidence, including for conversions
  that need supported recovery after the window closes.
- Users and maintainers can verify the complete bridge release after ordinary
  distribution and support activities begin to wind down.

Tradeoffs:

- Release maintainers must retain and periodically verify a complete
  multi-platform bridge release set through the approved deadline.
- Local archives have no automated lifecycle cleanup; repository owners bear
  custody and make any destructive decision manually.
- A delayed generally available release, unresolved supported case, or closure
  defect can move the practical retirement schedule beyond the earliest date.

## Follow-Up

- Phase 1 must encode these exact values in contracts, release metadata,
  fixtures, and disposition ledgers.
- Release maintainers must define and record the periodic bridge-asset
  availability check used through `2028-06-30T23:59:59Z`.
- Any replacement schedule caused by delayed general availability requires a
  new explicit decision; implementation must not infer one.
- Phase 8 requires its own authorization and validation record after every
  listed precondition passes.
