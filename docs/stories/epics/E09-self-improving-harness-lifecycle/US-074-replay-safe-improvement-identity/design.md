# Design

## Domain Model

- `ProposalKey`: versioned deterministic identity for the underlying issue.
- `IntakeUid`: stable identity for the approved work-intake record.
- `BacklogUid`: stable identity for one proposal/backlog occurrence.
- `EvidenceUid`: stable identity for a trace, intervention, or durable audit
  evidence snapshot.
- `OccurrenceKind`: original, regression, or reconsideration.

Proposal keys must be Unicode-safe, deterministic, conservative, and independent
from display order, confidence, occurrence count, and title truncation.

## Application Flow

1. Migrate the durable schema additively.
2. Generate stable uids for all new intake, backlog, trace, and intervention
   writes.
3. Serialize stable uids and original timestamps into semantic operations.
4. Apply later changesets by uid rather than assuming the same local integer id.
5. Reconcile explicit audit-evidence episodes without making proposal generation
   write.
6. Expose enough identity in queries for later lifecycle stories and debugging.

## Interface Contract

Existing human-readable integer ids remain visible for local convenience. Stable
uids and proposal keys are machine identity and must be available in detailed or
JSON query output. `audit` remains read-only; `audit --record-evidence` is the
explicit logged mutation that opens, retains, or clears audit-evidence episodes.
This story does not add proposal acceptance behavior.

## Data Model

Schema migration `009-improvement-identity.sql` adds:

```text
backlog.uid                  TEXT nullable for legacy rows, unique when present
backlog.proposal_key         TEXT nullable
backlog.predecessor_uid      TEXT nullable
backlog.occurrence_kind      TEXT nullable: original | regression | reconsideration
backlog.accepted_at          TEXT nullable
backlog.closed_at            TEXT nullable
backlog.resolution_evidence  TEXT nullable
backlog.outcome_schedule_kind TEXT nullable: manual | due_at | trace_count
backlog.outcome_due_at       TEXT nullable
backlog.outcome_after_traces INTEGER nullable, positive when present
backlog.outcome_baseline_trace_count INTEGER nullable, non-negative

intake.uid                   TEXT nullable for legacy rows, unique when present
trace.uid                    TEXT nullable for legacy rows, unique when present
trace.intake_uid             TEXT nullable
intervention.uid             TEXT nullable for legacy rows, unique when present

proposal_evidence_link(
  backlog_uid,
  source_kind,               -- trace | intervention | audit | legacy_snapshot
  evidence_uid,
  evidence_fingerprint,
  observed_at,
  PRIMARY KEY (backlog_uid, source_kind, evidence_uid)
)

audit_evidence_episode(
  uid,                       -- aud_<32 lowercase hex>
  finding_key,               -- <rule-id>:v<version>:<entity-kind>:<entity-key>
  evidence_fingerprint,      -- full 64-hex SHA-256
  opened_at,
  cleared_at,
  PRIMARY KEY (uid)
)

backlog_outcome_observation(
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  uid           TEXT NOT NULL UNIQUE, -- obs_<32 lowercase hex>
  backlog_uid   TEXT NOT NULL,
  ordinal       INTEGER NOT NULL CHECK (ordinal > 0),
  status        TEXT NOT NULL CHECK (
                  status IN ('confirmed', 'ineffective', 'reverted',
                             'legacy_recorded')),
  outcome       TEXT NOT NULL,
  evidence      TEXT nullable,
  observed_at   TEXT NOT NULL,
  UNIQUE (backlog_uid, ordinal),
  FOREIGN KEY (backlog_uid) REFERENCES backlog(uid)
)
```

New writes require opaque prefixed 128-bit lowercase-hex uids (`blg_`, `ink_`,
`trc_`, `int_`, `aud_`, and `obs_`) generated before insert and serialized into the
semantic operation. `changeset.header` remains version 1, while operation
versions are dispatched independently by `(op, version)`:

- `intake.add@v1`, `backlog.add@v1`, `trace.add@v1`, and
  `intervention.add@v1` keep null uids and existing legacy timestamp behavior.
  Apply never derives identity from local integer ids, filenames, line numbers,
  replay timestamps, or mutable text.
- New `add@v2` operations require a valid uid and source-generated timestamp;
  missing/malformed fields or unknown versions fail the whole transaction.
- `trace.add@v2` serializes `intake_uid`, and apply resolves it against
  `intake.uid`, never a source-local intake id.
- `intervention.add@v2` serializes `trace_uid`, and apply resolves it against
  `trace.uid`, never a source-local trace id.

Legacy rows remain visible but cannot be targeted by uid-based lifecycle commands
until `US-080` performs conservative reconciliation. Pre-E09 timestamps are
unknowable and excluded from live/rebuild parity; recurrence uses evidence
identity and coverage, never timestamp comparison.

Existing integer `trace.intake_id` remains a local compatibility/display field.
For v2 records, `trace.intake_uid` is the replay-safe relationship and must
reference an existing nonnull `intake.uid` when an intake is supplied.

Proposal identity separates persisted equality from a readable display label:

```text
persisted key: <rule-id>:v<rule-version>:<full-64-sha256-hex>
display label: <rule-id>:v<rule-version>:<readable-slug>:<first-12-sha256-hex>
```

The digest input is the rule id, rule version, and NFC-normalized Unicode
lowercase canonical issue input separated by NUL bytes. The full persisted key is
shown in detailed/JSON output and is the value accepted by mutation commands. The
label is for operators and never participates in storage or uniqueness. The
implementation may add small hashing and Unicode-normalization crates; it must
not use Rust's process-dependent default hasher.

Increment a rule version only when its equivalence relation changes: canonical
input, grouping membership, entity boundary, or evidence-newness facts. Title,
description, confidence, sort order, threshold, and suggested-action changes do
not bump it. A new version is a distinct visible lineage; old keys remain
queryable and are never auto-suppressed or auto-linked to it.

Trace and intervention evidence use their stable row uids. Audit evidence is an
explicit episode so the same defect can clear and later recur. Each audit
category owns a versioned rule id, and each current finding has:

```text
finding_key = <rule-id>:v<version>:<entity-kind>:<entity-key>
fingerprint = SHA-256(rule-id NUL version NUL entity-kind NUL entity-key
                     NUL canonical-facts)
```

`audit --record-evidence` compares current findings with active episodes in one
transaction. An unchanged active fingerprint writes nothing; a missing finding
sets `cleared_at`; a new/reappeared finding, or changed fingerprint, opens a new
opaque `aud_` uid. At most one uncleared episode exists per `finding_key`.
It emits `audit.evidence.open@v1` and `audit.evidence.clear@v1`; unchanged scans
emit no semantic operation. Proposal generation consumes active episode uids and
remains read-only. A current finding with no recorded active episode is displayed
as `unrecorded_evidence` with the exact record command and is not decision-
eligible. The initial rule ids are `audit.orphaned-story`, `audit.unverified-story`,
`audit.unverified-decision`, `audit.implemented-backlog-without-outcome`,
`audit.stale-story`, and `audit.broken-tool`. Canonical facts are stable domain
fields, never titles, counts, display ordering, or wall-clock evaluation time:

| Rule | Entity key | Canonical facts |
| --- | --- | --- |
| orphaned story | story id | story status |
| unverified story | story id | verify-command digest |
| unverified decision | decision id | verify-command digest |
| implemented backlog without outcome | backlog uid | predicted-impact digest |
| stale story | story id | latest stable trace uid |
| broken tool | tool name | kind, command, scan target, and current status |

All new semantic operations include original `created_at`, `opened_at`,
`cleared_at`, or `observed_at` values as applicable.

Unique indexes enforce backlog, intake, trace, intervention, audit episode, and
observation uid uniqueness. A partial index permits one active audit episode per
finding key. `proposal_key` is deliberately not globally unique because several
closed occurrences may represent the same recurring issue. Migration 009 owns
the exact open-occurrence invariant so the decision story adds no schema:

```sql
CREATE UNIQUE INDEX backlog_one_open_proposal_key
ON backlog(proposal_key)
WHERE proposal_key IS NOT NULL
  AND status IN ('proposed', 'accepted');

CREATE UNIQUE INDEX audit_one_active_finding
ON audit_evidence_episode(finding_key)
WHERE cleared_at IS NULL;
```

Exactly one observation schedule is stored for an accepted occurrence:

- `manual`: both boundary fields and the baseline count are null;
- `due_at`: `outcome_due_at` is canonical RFC3339 UTC and trace fields are null;
- `trace_count`: `outcome_after_traces` is positive, while the baseline remains
  null until explicit story completion records the total count of stable
  uid-bearing traces at that completion boundary.

Legacy/unclassified rows have a null schedule kind and null schedule fields.
`backlog_outcome_observation` is append-only source of truth and its per-backlog
ordinal provides deterministic order when timestamps tie. `legacy_recorded` is
reserved for `US-080` to preserve a nonblank legacy `actual_outcome` without
claiming whether it was confirmed, ineffective, or reverted. E09 commands never
write the existing legacy `actual_outcome` field. Observation semantic operations
contain uid, backlog uid, ordinal, status, outcome, evidence, and original time.

## UI / Platform Impact

No application UI change. Installed databases receive an additive migration and the
prebuilt CLI must understand it.

## Observability

Changeset rendering and detailed queries show stable identities, predecessor
links, and evidence coverage without requiring raw SQL.

## Alternatives Considered

1. Continue using integer ids. Rejected because they are not stable across
   separate changeset replay contexts.
2. Compare only `created_at > closed_at`. Rejected because current replay replaces
   original timestamps and second-resolution ties are ambiguous.
3. Delete old evidence. Rejected because it removes the audit trail instead of
   establishing stable identity.
