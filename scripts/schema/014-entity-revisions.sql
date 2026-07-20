-- Harness schema migration 014
-- Entity-local optimistic revisions for deterministic semantic replay.

ALTER TABLE story ADD COLUMN revision INTEGER NOT NULL DEFAULT 0 CHECK(revision >= 0);
ALTER TABLE decision ADD COLUMN revision INTEGER NOT NULL DEFAULT 0 CHECK(revision >= 0);
ALTER TABLE backlog ADD COLUMN revision INTEGER NOT NULL DEFAULT 0 CHECK(revision >= 0);
ALTER TABLE tool ADD COLUMN revision INTEGER NOT NULL DEFAULT 0 CHECK(revision >= 0);
ALTER TABLE audit_evidence_episode ADD COLUMN revision INTEGER NOT NULL DEFAULT 0 CHECK(revision >= 0);

CREATE TRIGGER story_revision_after_update
AFTER UPDATE ON story
FOR EACH ROW WHEN NEW.revision = OLD.revision
BEGIN
    UPDATE story SET revision = OLD.revision + 1 WHERE id = OLD.id;
END;

CREATE TRIGGER decision_revision_after_update
AFTER UPDATE ON decision
FOR EACH ROW WHEN NEW.revision = OLD.revision
BEGIN
    UPDATE decision SET revision = OLD.revision + 1 WHERE id = OLD.id;
END;

CREATE TRIGGER backlog_revision_after_update
AFTER UPDATE ON backlog
FOR EACH ROW WHEN NEW.revision = OLD.revision
BEGIN
    UPDATE backlog SET revision = OLD.revision + 1 WHERE id = OLD.id;
END;

CREATE TRIGGER tool_revision_after_update
AFTER UPDATE ON tool
FOR EACH ROW WHEN NEW.revision = OLD.revision
BEGIN
    UPDATE tool SET revision = OLD.revision + 1 WHERE name = OLD.name;
END;

CREATE TRIGGER audit_evidence_episode_revision_after_update
AFTER UPDATE ON audit_evidence_episode
FOR EACH ROW WHEN NEW.revision = OLD.revision
BEGIN
    UPDATE audit_evidence_episode SET revision = OLD.revision + 1 WHERE uid = OLD.uid;
END;

INSERT INTO schema_version (version) VALUES (14);
