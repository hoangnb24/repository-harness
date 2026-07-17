-- Harness v0 schema — migration 001
-- Durable layer for operational harness data.
-- Policy docs (HARNESS.md, FEATURE_INTAKE.md, ARCHITECTURE.md) stay as
-- human-readable references. This database stores the operational records
-- that agents produce and query during work.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

----------------------------------------------------------------------
-- Schema version
----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER PRIMARY KEY,
    applied_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

INSERT INTO schema_version (version) VALUES (1);

----------------------------------------------------------------------
-- Intake: classifying incoming work
----------------------------------------------------------------------
CREATE TABLE intake (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    input_type    TEXT    NOT NULL
                         CHECK(input_type IN (
                           'new_spec','spec_slice','change_request',
                           'new_initiative','maintenance','harness_improvement'
                         )),
    summary       TEXT    NOT NULL,
    risk_lane     TEXT    NOT NULL
                         CHECK(risk_lane IN ('tiny','normal','high_risk')),
    risk_flags    TEXT,          -- JSON array, e.g. ["auth","data_model"]
    affected_docs TEXT,          -- JSON array of doc paths
    story_id      TEXT,          -- links to story.id when one is created
    notes         TEXT
);

----------------------------------------------------------------------
-- Story: work packets and their validation status
-- Replaces hand-edited TEST_MATRIX.md rows.
----------------------------------------------------------------------
CREATE TABLE story (
    id               TEXT PRIMARY KEY,   -- e.g. US-001
    title            TEXT NOT NULL,
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    risk_lane        TEXT NOT NULL
                     CHECK(risk_lane IN ('tiny','normal','high_risk')),
    contract_doc     TEXT,               -- path to product doc
    status           TEXT NOT NULL DEFAULT 'planned'
                     CHECK(status IN (
                       'planned','in_progress','implemented','changed','retired'
                     )),
    unit_proof       INTEGER NOT NULL DEFAULT 0,
    integration_proof INTEGER NOT NULL DEFAULT 0,
    e2e_proof        INTEGER NOT NULL DEFAULT 0,
    platform_proof   INTEGER NOT NULL DEFAULT 0,
    evidence         TEXT,
    notes            TEXT
);

----------------------------------------------------------------------
-- Decision: durable records with optional verification
----------------------------------------------------------------------
CREATE TABLE decision (
    id                    TEXT PRIMARY KEY,  -- e.g. 0001
    title                 TEXT NOT NULL,
    created_at            TEXT NOT NULL DEFAULT (datetime('now')),
    status                TEXT NOT NULL DEFAULT 'proposed'
                          CHECK(status IN (
                            'proposed','accepted','superseded','rejected'
                          )),
    doc_path              TEXT,              -- path to the markdown ADR
    verify_command        TEXT,              -- optional check command
    last_verified_at      TEXT,
    last_verified_result  TEXT
                          CHECK(last_verified_result IN ('pass','fail') OR
                                last_verified_result IS NULL),
    predicted_impact      TEXT,
    actual_outcome        TEXT,
    notes                 TEXT
);

----------------------------------------------------------------------
-- Backlog: harness improvement proposals with evidence loop
----------------------------------------------------------------------
CREATE TABLE backlog (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at            TEXT    NOT NULL DEFAULT (datetime('now')),
    title                 TEXT    NOT NULL,
    discovered_while      TEXT,
    current_pain          TEXT,
    suggested_improvement TEXT,
    risk                  TEXT    CHECK(risk IN ('tiny','normal','high_risk')),
    status                TEXT    NOT NULL DEFAULT 'proposed'
                          CHECK(status IN (
                            'proposed','accepted','implemented','rejected'
                          )),
    predicted_impact      TEXT,
    actual_outcome        TEXT,
    implemented_at        TEXT,
    notes                 TEXT
);

----------------------------------------------------------------------
-- Trace: agent task execution records (observability foundation)
----------------------------------------------------------------------
CREATE TABLE trace (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    task_summary    TEXT    NOT NULL,
    intake_id       INTEGER REFERENCES intake(id),
    story_id        TEXT    REFERENCES story(id),
    agent           TEXT,
    actions_taken   TEXT,       -- JSON array
    files_read      TEXT,       -- JSON array
    files_changed   TEXT,       -- JSON array
    decisions_made  TEXT,       -- JSON array
    errors          TEXT,       -- JSON array
    outcome         TEXT
                    CHECK(outcome IN (
                      'completed','blocked','partial','failed'
                    )),
    duration_seconds INTEGER,
    token_estimate   INTEGER,
    harness_friction TEXT,
    notes            TEXT
);
