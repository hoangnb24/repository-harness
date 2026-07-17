-- Harness v0 schema - migration 006
-- Track semantic changesets already applied to this local harness database.

CREATE TABLE changeset_applied (
    id         TEXT PRIMARY KEY,
    path       TEXT,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT INTO schema_version (version) VALUES (6);
