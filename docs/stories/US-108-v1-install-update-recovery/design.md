# US-108 V1 Install, Update, And Recovery Design

Status: **Implemented and locally validated; orchestrator acceptance pending**

## Domain Model

`PlannedMutation` is produced only from a private `VerifiedRelease` plus the
existing Phase 2 manifest/path/audit checks. It contains the command, stable
operation identifier, canonical preview digest, release identity, exact public
operations, candidate manifest bytes, and private write steps.

Each write step owns:

- one stable step ID and safe repository-relative path;
- expected before digest or an explicit absent expectation;
- exact after digest and a staged post-image;
- an exclusive backup path when before bytes exist;
- a deterministic retained hard-link witness path when `before_sha256=None`;
- whether the step is the manifest commit; and
- its journal state (`pending` or `applied`).

The tool-local journal is ignored by Git and contains only filesystem recovery
data. It is not a task lifecycle record. Its closed state is one of
`prepared`, `applying`, `committed`, or `rolled-back`. A digest over the
canonical journal body detects corruption but grants no recovery authority.
That canonical body also commits the pinned repository root identity
(`st_dev` plus `st_ino`) from the descriptor-anchored root handle, so a
byte-copied journal from repository A no longer authorizes recovery in
repository B even when both trees currently contain identical before or after
bytes.
The full operation ID is independently recomputed as a SHA-256 commitment to
the owner command, authenticated release identity, exact target operation rows,
and candidate-manifest digest. Public operations must be the exact projection
of private write path/kind/disposition and before/derived-after digests. Private
staged, backup, and temporary paths must also match the operation-owned layout.
Changing journal/staged/manifest bytes and recomputing the unkeyed body digest
therefore cannot retain the caller-supplied recovery authority.

Operation IDs and journal hashes are locators and commitments, not secrets. An
arbitrary same-UID malicious process is out of scope because it can already
delete or overwrite repository targets directly. Within the in-scope
crash/race/corruption model, a `before_sha256=None` create gains recovery
authority only from a retained hard link under the deterministic recovery root.
That link is created from the exact pre-rename temporary inode and pins that
inode against reuse, so recovery can later prove cause and effect: the live
target still names the same inode and still hashes to the authenticated
post-image.

Supported monotonic manifest transitions are:

- no manifest to `fresh-v1` for an authenticated install or scaffold, or to
  `brownfield-v1` when a no-prior-manifest install maps identical bytes;
- existing `fresh-v1`, `brownfield-v1`, or
  `converted-v1-with-archive` to the same repository mode;
- equal release sequence plus equal digest as an idempotent no-op; or
- a higher authenticated release sequence inside the existing compatibility
  range.

Lower sequence, equal sequence with a different digest, mode downgrade,
receipt loss, role removal, ownership broadening, or target-owned policy
weakening fails before mutation. Mapping a newly observed identical asset on
update retains the existing mode, including
`converted-v1-with-archive` and its conversion receipt.

## Application Flow

### Preview and confirmation

1. Parse the unchanged six-command grammar.
2. Load and structurally audit existing manifest state where present.
3. Authenticate release material through the independent Phase 2 release and
   trust ports.
4. Bind update to a supported monotonic manifest transition.
5. Read declared current bytes through the pinned Phase 2 root snapshot.
6. Apply ownership and update policy to produce exact after-images.
7. Add public operations for staged journal ownership, each required backup,
   each managed target write, and the manifest-last write.
8. Hash the canonical closed operation array and return it from `--preview`.
   The same canonical public-operation digest is the one a caller can
   recompute from the emitted `details.operations` array.
9. A non-preview command without the paired deterministic confirmation refuses
   with exit 4. A digest mismatch also refuses with zero mutation.

### Managed surfaces

- `managed-file` + `replace-if-base`: replace only when current exact bytes
  equal `base_sha256`. Otherwise emit the base/current/candidate digest tuple
  and stop.
- `managed-block`: locate exactly one declared opening/closing marker pair,
  compare the current interior digest with `base_sha256`, and replace only the
  interior. Bytes before the opening marker and after the closing marker are
  copied byte-for-byte.
- `three-way-review`: an unchanged base can advance to the candidate. A changed
  base emits deterministic review data and performs no automatic merge.
- `target-owned` or `never-auto-patch`: preserve current bytes, retain their
  digest in the manifest, and report the skipped candidate.
- `scaffold`: create one authenticated exact destination only when absent. An
  exact repeat after its matching manifest/path commit is an idempotent no-op;
  any different pre-existing path remains a conflict. It never overwrites,
  invokes a generator, or infers a language.

### Durable apply

1. Revalidate all expected before images.
2. Create the operation directory and exclusive backup/staged files.
3. Fsync every file and its containing directory.
4. Atomically persist the prepared journal, then mark it applying.
5. For each non-manifest write, recheck its before image and write/fsync an
   exclusive same-directory temporary. Any `before_sha256=None` step also
   creates a deterministic retained hard link from that temporary inode into
   `.harness/recovery/<operation-id>/creates/<step-id>.link`; cross-filesystem
   link failure therefore fails closed. Creation uses atomic `NOREPLACE`.
   Replacement pins the final inode, atomically exchanges target and
   temporary, verifies the displaced inode/digest, reverses the exchange on a
   race, removes only the proven displaced image, fsyncs both parents, and
   atomically persists the applied journal step.
6. Audit the candidate manifest against the resulting target bytes.
7. Recompute the canonical preview digest from the journal and compare the
   accepted digest immediately before commit.
8. Write/fsync the manifest temporary and commit it last with the same atomic
   no-replace/exchange defense.
9. Fsync `.harness`, verify the committed manifest digest, and mark the journal
   committed.

No error path returns exit 0 or 2 unless the manifest commit is coherent.

### Resume and rollback

Resume first reauthenticates the release and requires exact command, operation,
release, journal-body digest, preview digest, backup, staged-image, and current
image matches. Recovery also requires the journal's committed root identity to
match the currently opened repository root before probe, status, resume,
rollback, or reconciliation trusts it at all. Recovery then reapplies the
normal payload monotonicity checks:
release sequence cannot regress, equal sequence cannot change digest, and the
authenticated release version must remain inside the authoritative manifest
compatibility range. Applied steps are verified but not replayed. Pending steps
run once. A manifest already at its recorded after digest means the atomic
commit occurred; resume verifies all post-images and completes journal
bookkeeping.

The journal also binds command scope. Install/update are limited to authenticated
release destinations. Scaffold binds one authenticated template and exact
destination; status emits that complete parser-valid recovery command. Recovery
validates the candidate transition against the backed-up authoritative
pre-operation manifest, so target-owned and `never-auto-patch` roles cannot be
reclassified by a recomputed journal. A `before_sha256=None` step is promoted to
`applied` only when the live target and retained hard link still name the same
inode and that pinned inode still hashes to the authenticated post-image.

Recovery also compares full-file creates with authenticated asset digests and
reconstructs a managed-block post-image from authenticated candidate interior
bytes plus the backed-up prefix/suffix. Unknown fields are rejected at the
journal, step, and nested operation levels.

Rollback validates every affected current post-image before changing any
target byte. It then durably records `rolling-back`. For an already committed
operation it first removes the new manifest from the authoritative path, then
restores assets in reverse order, and restores the old manifest last only when
that manifest step was actually applied. Every rollback boundary is resumable,
including a crash immediately after new-manifest removal. A created path is
removed only while it still has the exact journal after digest and still shares
its inode with the retained hard-link witness. That same witness rule covers
release-asset installs, scaffold-created destinations, and a fresh manifest
create. Any human edit causes exit 4 and leaves all remaining evidence intact.

Rollback continues to require the matching live authenticated release before
local evidence is trusted. This is deliberate: without a separately
authenticated durable authority, treating a self-consistent local journal as
sufficient would let fabricated evidence bypass ownership policy. Temporary
release unavailability therefore blocks rollback without mutating the tree.

## Interface Contract

No command or option changes. Install, update, and scaffold retain their frozen
options. Recovery remains `--resume <operation-id>` or
`--rollback <operation-id>` on the owning command.

Public outcomes use the existing envelope:

- preview: exit 0, `mutation=preview`;
- committed ready: exit 0, `mutation=committed`;
- committed unresolved install/update: exit 2, `mutation=committed`;
- safe conflict or interrupted recovery: exit 4,
  `mutation=recovery-required` when a journal exists;
- read-only status with an incomplete valid journal: exit 3,
  `mutation=recovery-required`, retaining authoritative manifest mode and
  declared readiness when a manifest exists;
- invalid trust/manifest/path/state: exit 3, no claimed mutation success;
- host I/O/durability failure: exit 74, no claimed success; and
- completed rollback: exit 0, `mutation=rolled-back`.

## Data Model

The committed manifest remains exactly `repository-harness-manifest/v1`; this
story adds no schema field. Recovery state is untracked and lives at:

```text
.harness/recovery/<operation-id>/
  journal.json
  backups/<step-id>.bak
  creates/<step-id>.link
  staged/<step-id>.after
```

Temporary files are placed beside their final destination and use an
operation/step-derived name. They are not authority by themselves. For any
`before_sha256=None` create, recovery trusts only a live target whose exact
inode still matches the retained hard-link witness and whose bytes still hash
to the authenticated post-image. The journal is retained after a commit or
rollback as idempotency/recovery evidence and may be removed only by an
explicit future policy outside this story.

Backups never include a target-owned write because target-owned bytes are never
written. Existing conversion archives are outside the recovery root and are
never touched.

## UI / Platform Impact

Phase 3 implements and proves descriptor-anchored mutation on macOS and Linux,
where atomic no-replace and exchange primitives are available. Other Unix and
non-Unix targets fail closed before replacement. Windows safe handles and
five-platform artifact/installer behavior remain Phase 7 gates; this is an
explicit boundary, not a portability claim.

The repository-local production CLI continues to use unavailable release and
trust adapters. Therefore adding the mutation engine does not promote fixture
keys or create a production install path.

## Observability

The deterministic envelope reports only closed operation rows, preview digest,
backup/recovery paths, conflict digests, readiness, and next action. It reports
no absolute path, time, random identifier, environment value, target command
output, task record, or telemetry.

The local journal contains operation recovery evidence only. It is not emitted
as a Harness trace and is not written to `.harness/changesets`.
Operation IDs and journal hashes remain visible because they are commitments,
not authentication secrets; repository-root identity and retained hard links
provide the structural authority boundary inside the in-scope model.

## Alternatives Considered

1. Add a `recover` command. Rejected because it would violate the permanent
   six-command grammar.
2. Store recovery in the committed manifest. Rejected because a pre-commit
   crash could make an incomplete operation appear successful.
3. Patch target-owned files after taking a backup. Rejected because a backup
   does not grant ownership.
4. Auto-merge a changed managed block. Rejected because ambiguous human edits
   require explicit three-way review.
5. Commit the manifest before target files. Rejected because a crash would
   leave a success manifest that names bytes not durably present.
6. Activate the live CLI with fixture release material. Rejected because Phase
   3 does not satisfy production promotion or Phase 7 artifact gates.
