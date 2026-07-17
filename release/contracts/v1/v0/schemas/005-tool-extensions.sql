-- Harness v0 schema - migration 005
-- Inbound tool registry: kind-aware presence + capability binding.
-- These columns turn the tool table from "declared intent" into
-- "intent + last-scanned reality" without breaking existing rows.

ALTER TABLE tool ADD COLUMN kind TEXT NOT NULL DEFAULT 'cli';
ALTER TABLE tool ADD COLUMN capability TEXT;
ALTER TABLE tool ADD COLUMN scan_target TEXT;
ALTER TABLE tool ADD COLUMN status TEXT NOT NULL DEFAULT 'unknown';
ALTER TABLE tool ADD COLUMN checked_at TEXT;

-- Backfill kind for tools registered before kinds existed, inferring it from
-- the agent-neutral command prefix convention so an upgrade does not mis-type
-- (and then falsely flag as broken) MCP servers or skills that are not on PATH.
UPDATE tool SET kind = 'mcp' WHERE command LIKE 'mcp:%';
UPDATE tool SET kind = 'skill' WHERE command LIKE 'skill:%';

INSERT INTO schema_version (version) VALUES (5);
