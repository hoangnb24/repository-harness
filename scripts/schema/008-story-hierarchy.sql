-- Harness schema migration 008
-- Parent-child Harness story hierarchy for generic work-item grouping.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS story_hierarchy (
    parent_story_id TEXT NOT NULL REFERENCES story(id) ON DELETE CASCADE,
    child_story_id  TEXT NOT NULL REFERENCES story(id) ON DELETE CASCADE,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (parent_story_id, child_story_id),
    CHECK (parent_story_id <> child_story_id)
);

CREATE INDEX IF NOT EXISTS idx_story_hierarchy_child
    ON story_hierarchy(child_story_id);

INSERT INTO schema_version (version) VALUES (8);
