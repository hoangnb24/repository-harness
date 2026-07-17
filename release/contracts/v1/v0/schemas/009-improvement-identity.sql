-- Replay-safe identity foundation for the E09 improvement lifecycle.
ALTER TABLE intake ADD COLUMN uid TEXT;
ALTER TABLE backlog ADD COLUMN uid TEXT;
ALTER TABLE backlog ADD COLUMN proposal_key TEXT;
ALTER TABLE backlog ADD COLUMN predecessor_uid TEXT;
ALTER TABLE backlog ADD COLUMN occurrence_kind TEXT CHECK (occurrence_kind IS NULL OR occurrence_kind IN ('original','regression','reconsideration'));
ALTER TABLE backlog ADD COLUMN accepted_at TEXT;
ALTER TABLE backlog ADD COLUMN closed_at TEXT;
ALTER TABLE backlog ADD COLUMN resolution_evidence TEXT;
ALTER TABLE backlog ADD COLUMN outcome_schedule_kind TEXT CHECK (outcome_schedule_kind IS NULL OR outcome_schedule_kind IN ('manual','due_at','trace_count'));
ALTER TABLE backlog ADD COLUMN outcome_due_at TEXT;
ALTER TABLE backlog ADD COLUMN outcome_after_traces INTEGER;
ALTER TABLE backlog ADD COLUMN outcome_baseline_trace_count INTEGER;
ALTER TABLE trace ADD COLUMN uid TEXT;
ALTER TABLE trace ADD COLUMN intake_uid TEXT;
ALTER TABLE intervention ADD COLUMN uid TEXT;

-- SQLite foreign keys require a complete unique parent index; nullable legacy
-- rows remain allowed because SQLite permits multiple NULLs in a UNIQUE index.
CREATE UNIQUE INDEX IF NOT EXISTS intake_uid_unique ON intake(uid);
CREATE UNIQUE INDEX IF NOT EXISTS backlog_uid_unique ON backlog(uid);
CREATE UNIQUE INDEX IF NOT EXISTS trace_uid_unique ON trace(uid);
CREATE UNIQUE INDEX IF NOT EXISTS intervention_uid_unique ON intervention(uid);
CREATE UNIQUE INDEX IF NOT EXISTS backlog_one_open_proposal_key
  ON backlog(proposal_key) WHERE proposal_key IS NOT NULL AND status IN ('proposed','accepted');

CREATE TABLE proposal_evidence_link (
    backlog_uid TEXT NOT NULL,
    source_kind TEXT NOT NULL CHECK (source_kind IN ('trace','intervention','audit','legacy_snapshot')),
    evidence_uid TEXT NOT NULL,
    evidence_fingerprint TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    PRIMARY KEY (backlog_uid, source_kind, evidence_uid),
    FOREIGN KEY (backlog_uid) REFERENCES backlog(uid)
);

CREATE TABLE audit_evidence_episode (
    uid TEXT PRIMARY KEY,
    finding_key TEXT NOT NULL,
    evidence_fingerprint TEXT NOT NULL,
    opened_at TEXT NOT NULL,
    cleared_at TEXT
);
CREATE UNIQUE INDEX audit_one_active_finding
  ON audit_evidence_episode(finding_key) WHERE cleared_at IS NULL;

CREATE TABLE backlog_outcome_observation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT NOT NULL UNIQUE,
    backlog_uid TEXT NOT NULL,
    ordinal INTEGER NOT NULL CHECK (ordinal > 0),
    status TEXT NOT NULL CHECK (status IN ('confirmed','ineffective','reverted','legacy_recorded')),
    outcome TEXT NOT NULL,
    evidence TEXT,
    observed_at TEXT NOT NULL,
    UNIQUE (backlog_uid, ordinal),
    FOREIGN KEY (backlog_uid) REFERENCES backlog(uid)
);

INSERT INTO schema_version (version) VALUES (9);
