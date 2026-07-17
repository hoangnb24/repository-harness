-- Harness v0 schema - migration 003
-- Machine-readable registry for user-provided project tools.

CREATE TABLE tool (
    name           TEXT PRIMARY KEY,
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    provider       TEXT NOT NULL DEFAULT 'custom',
    command        TEXT NOT NULL,
    description    TEXT NOT NULL,
    args           TEXT,
    responsibility TEXT NOT NULL,
    since          TEXT NOT NULL DEFAULT 'registered'
);

INSERT INTO schema_version (version) VALUES (3);
