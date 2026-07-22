# 0025 Latest-Release Self-Update And Human-Directed Conflicts

Date: 2026-07-22

## Status

Accepted and implemented on the feature branch; release availability follows
merge and core publication.

## Context

The installed `harness` executable previously compared consumer files only
with the core embedded in that same executable. An installed v0.1.4 therefore
could not discover v0.1.8 even though the product documentation presented
`harness update` as the future-upgrade command. Re-running the mutable remote
bootstrap selected a newer binary, but that made the installed update command
misleading.

The transactional updater also stopped safely on overlapping edits but retained
no resolution workspace. A coding agent could explain a semantic conflict, yet
there was no resumable path for a human to authorize the choice and the agent
to provide the accepted merged document.

## Decision

1. The application layer owns one self-update use case. Infrastructure ports
   provide release download, checksum verification, candidate execution,
   durable retention, and executable replacement; `main.rs` only composes them.
2. `harness update` resolves the published `harness-v*` core-release pointer for
   the current platform, downloads the binary and SHA-256 sidecar from that
   exact versioned GitHub release, verifies the bytes, requires the candidate's
   reported version to equal the pointer version, and rejects a version older
   than either the installed core or executing binary. It does not
   use GitHub's global latest release because the independent `harness-cli`
   release train may be newer and does not contain core assets.
3. The candidate owns interpretation and installation of its embedded payload.
   Direct version jumps use the exact installed base and the candidate payload;
   a future incompatible provenance schema must reject explicitly rather than
   invent an upgrade graph in advance.
4. `harness status` and `harness doctor` remain local and network-free. Status
   reports `executable_outdated` when provenance is newer than the executable's
   embedded core.
5. A clean update uses the existing backup, journal, activation, and provenance
   transaction, then replaces the repository-local executing binary last. A
   normal self-update may mutate only when the repository executable and its
   repository path components are regular files rather than symlinks. The
   checksum-verified candidate subprocess and platform installer are explicit
   internal handoff paths.
6. An overlapping merge changes no managed file, installed provenance, or
   executable. It retains BASE, LOCAL, UPSTREAM, RESOLVED, and the complete
   frozen managed-file input set under `.harness-core/update/`; the candidate
   is retained separately under ignored `.harness-core/update-candidate/`.
7. Harness does not choose conflict semantics. An agent explains concrete
   behavioral differences, obtains human direction when a material choice
   exists, and edits the RESOLVED file.
8. A normal `harness update` always plans directly from installed provenance to
   the current release pointer. If a resolution is already pending, a mutating
   normal update replaces it with the new plan; dry-run previews the new plan
   without removing the pending session. `harness update --continue --dry-run`
   previews the accepted resolution for its exact pinned candidate;
   `--continue` remotely re-verifies the retained candidate and rejects
   remaining conflict markers, malformed staged inputs, or drift in any managed
   workspace path before verification and application under one lock. `--abort`
   removes only the staged session.
9. Platform installers run a staged candidate before replacing the installed
   binary. On conflict they retain the candidate and leave the old executable;
   rerunning the installer after resolution automatically continues the exact
   pending version. This also supports the one-time bootstrap boundary.
10. A verified candidate remains durable until executable replacement succeeds.
    If core activation succeeds but replacement fails or the parent process
    stops, the next update repairs the executable from that exact remotely
    re-verified core version before starting another core update.

## Alternatives Considered

1. **A custom signed channel with delegated keys and an upgrade graph.**
   Deferred because the current manually invoked, GitHub-hosted product does
   not yet justify that operational complexity. It remains a possible response
   to a stronger publisher-compromise threat model.
2. **Require users to rerun `curl | bash` for every upgrade.** Rejected because
   it keeps the installed update command unable to perform its documented job
   and repeatedly executes a mutable remote script.
3. **Write conflict markers into live managed files.** Rejected because a
   partially resolved `AGENTS.md` or `WORKFLOW.md` could immediately corrupt
   agent authority and would weaken the all-or-nothing update contract.
4. **Build an interactive merge editor into Harness.** Rejected because coding
   agents already have strong diff/edit tools; Harness should preserve inputs,
   enforce authority boundaries, and apply the result safely.

## Consequences

Positive:

- An installed executable can discover and install later releases directly.
- Conflicts become explainable and resumable without exposing partial policy
  files to agents or other repository users.
- Human judgment governs semantic choices while mechanical staging,
  verification, drift detection, and activation remain automated.
- The existing release assets, embedded payload, merge rules, and transaction
  engine remain the primary implementation.

Tradeoffs:

- Existing executables released before this decision cannot discover the first
  self-updating release and require one final platform-installer refresh.
- Updates require `curl` and network access; status and diagnostics do not.
- SHA-256 sidecars protect integrity relative to the selected GitHub release but
  do not establish an independent trust root against publisher compromise.
- Core activation and executable replacement remain two ordered filesystem
  phases, but the verified candidate is durable and a later update or installer
  run recovers version skew before applying another core version.
- Structural conflicts such as missing managed files are not representable as
  text resolution packets and must be corrected before restarting.
