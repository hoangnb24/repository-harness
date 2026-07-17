-- Deterministic ordering and structured decisions for review finding closure.
ALTER TABLE trace ADD COLUMN recorded_at_unix_ns INTEGER;
ALTER TABLE story_backlog_link ADD COLUMN linked_at_unix_ns INTEGER;
ALTER TABLE backlog ADD COLUMN rejection_reason TEXT;

-- Preserve the structured meaning already recorded by pre-v12 rejection
-- notes. This uses the same first exact line rule as the runtime compatibility
-- reader, so an upgraded database and a clean semantic replay converge.
WITH RECURSIVE rejection_lines(backlog_id, rest, line, line_number) AS (
    SELECT id, COALESCE(notes, '') || char(10), '', 0
    FROM backlog
    WHERE status = 'rejected' AND rejection_reason IS NULL
    UNION ALL
    SELECT backlog_id,
           substr(rest, instr(rest, char(10)) + 1),
           substr(rest, 1, instr(rest, char(10)) - 1),
           line_number + 1
    FROM rejection_lines
    WHERE rest <> ''
)
UPDATE backlog
SET rejection_reason = (
    SELECT substr(line, length('rejection_reason: ') + 1)
    FROM rejection_lines
    WHERE rejection_lines.backlog_id = backlog.id
      AND substr(line, 1, length('rejection_reason: ')) = 'rejection_reason: '
    ORDER BY line_number
    LIMIT 1
)
WHERE status = 'rejected'
  AND rejection_reason IS NULL;

INSERT INTO schema_version (version) VALUES (12);
