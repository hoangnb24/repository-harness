-- Harness v0 schema - migration 004
-- Review, human, CI, or agent interventions separated from normal traces.

CREATE TABLE intervention (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    trace_id    INTEGER REFERENCES trace(id),
    story_id    TEXT,
    type        TEXT NOT NULL CHECK(type IN ('correction','override','escalation','approval')),
    description TEXT NOT NULL,
    source      TEXT NOT NULL CHECK(source IN ('human','reviewer','ci','agent')),
    impact      TEXT
);

INSERT INTO schema_version (version) VALUES (4);
