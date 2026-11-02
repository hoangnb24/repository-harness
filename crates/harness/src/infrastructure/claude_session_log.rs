//! Claude Code session JSONL reader.
//!
//! Field names were checked against real Claude Code session files
//! (`~/.claude/projects/<project>/<session>.jsonl`, November 2026):
//!
//! - every record has a top-level `type`; conversation records are `user` or
//!   `assistant` and carry a `message` object and an `isSidechain` flag;
//! - assistant `message.id` repeats across records of one message (one record
//!   per content block) and each repeat carries the same `message.usage`;
//! - `message.usage` holds `input_tokens`, `cache_creation_input_tokens`,
//!   `cache_read_input_tokens`, and `output_tokens`;
//! - an explicitly invoked skill, by slash command or by the `Skill` tool, is
//!   followed by a `user` record with `isMeta: true` whose text starts with
//!   `Base directory for this skill: <path>`; the skill name is the last path
//!   component. Topic matches without invocation produce no such record.

use std::fs;
use std::path::Path;

use serde_json::Value;

use crate::application::{ParsedSession, PortError, SessionLogError, SessionLogPort};
use crate::domain::{SessionEvent, TokenUsage};

const SKILL_BASE_PREFIX: &str = "Base directory for this skill:";

pub struct ClaudeSessionLog;

impl SessionLogPort for ClaudeSessionLog {
    fn read_session(&self, path: &Path) -> Result<ParsedSession, SessionLogError> {
        let content = fs::read_to_string(path).map_err(|error| {
            PortError::new(format!("cannot read session {}: {error}", path.display()))
        })?;
        let parsed = parse_session(&content);
        if parsed.conversation_records == 0 && parsed.valid_records > 0 {
            return Err(SessionLogError::Unsupported {
                path: path.display().to_string(),
            });
        }
        Ok(parsed.session)
    }
}

struct Parsed {
    session: ParsedSession,
    valid_records: u64,
    conversation_records: u64,
}

fn parse_session(content: &str) -> Parsed {
    let mut parsed = Parsed {
        session: ParsedSession::default(),
        valid_records: 0,
        conversation_records: 0,
    };
    for line in content.lines().filter(|line| !line.trim().is_empty()) {
        let Ok(record) = serde_json::from_str::<Value>(line) else {
            parsed.session.malformed_lines += 1;
            continue;
        };
        parsed.valid_records += 1;
        let kind = record.get("type").and_then(Value::as_str);
        let Some(message) = record.get("message").filter(|value| value.is_object()) else {
            continue;
        };
        if !matches!(kind, Some("user" | "assistant")) {
            continue;
        }
        parsed.conversation_records += 1;
        if record.get("isSidechain").and_then(Value::as_bool) == Some(true) {
            parsed.session.sidechain_records += 1;
            continue;
        }
        let event = match kind {
            Some("assistant") => assistant_event(message),
            _ => user_event(&record, message),
        };
        if let Some(event) = event {
            parsed.session.events.push(event);
        }
    }
    parsed
}

fn assistant_event(message: &Value) -> Option<SessionEvent> {
    let id = message.get("id").and_then(Value::as_str)?.to_string();
    let text = message
        .get("content")
        .and_then(Value::as_array)
        .map(|blocks| {
            blocks
                .iter()
                .filter(|block| block.get("type").and_then(Value::as_str) == Some("text"))
                .filter_map(|block| block.get("text").and_then(Value::as_str))
                .collect::<Vec<_>>()
                .join("\n")
        })
        .filter(|text| !text.is_empty());
    let usage = message.get("usage").map(|usage| {
        let count = |name: &str| usage.get(name).and_then(Value::as_u64).unwrap_or(0);
        TokenUsage {
            input: count("input_tokens"),
            cache_creation: count("cache_creation_input_tokens"),
            cache_read: count("cache_read_input_tokens"),
            output: count("output_tokens"),
        }
    });
    Some(SessionEvent::Assistant { id, text, usage })
}

fn user_event(record: &Value, message: &Value) -> Option<SessionEvent> {
    let content = message.get("content")?;
    let is_meta = record.get("isMeta").and_then(Value::as_bool) == Some(true);
    let texts: Vec<&str> = match content {
        Value::String(text) => vec![text.as_str()],
        Value::Array(blocks) => {
            if blocks
                .iter()
                .any(|block| block.get("type").and_then(Value::as_str) == Some("tool_result"))
            {
                return None;
            }
            blocks
                .iter()
                .filter(|block| block.get("type").and_then(Value::as_str) == Some("text"))
                .filter_map(|block| block.get("text").and_then(Value::as_str))
                .collect()
        }
        _ => return None,
    };
    if is_meta {
        return texts.iter().find_map(|text| skill_name(text));
    }
    (!texts.is_empty()).then_some(SessionEvent::Prompt)
}

fn skill_name(text: &str) -> Option<SessionEvent> {
    let first_line = text.trim_start().lines().next()?;
    let path = first_line.strip_prefix(SKILL_BASE_PREFIX)?.trim();
    let name = path
        .trim_end_matches(['/', '\\'])
        .rsplit(['/', '\\'])
        .next()
        .filter(|name| !name.is_empty())?;
    Some(SessionEvent::SkillLoaded {
        skill: name.to_string(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn meta_skill_base_directory_marks_an_invocation() {
        let content = concat!(
            r#"{"type":"user","isSidechain":false,"message":{"role":"user","content":"<command-name>/encode-invariant</command-name>"}}"#,
            "\n",
            r#"{"type":"user","isMeta":true,"isSidechain":false,"message":{"role":"user","content":[{"type":"text","text":"Base directory for this skill: /repo/.claude/skills/encode-invariant\n\n# Encode"}]}}"#,
            "\n",
        );
        let parsed = parse_session(content);
        assert_eq!(
            parsed.session.events,
            vec![
                SessionEvent::Prompt,
                SessionEvent::SkillLoaded {
                    skill: "encode-invariant".into()
                }
            ]
        );
    }

    #[test]
    fn tool_results_are_not_prompts_and_sidechains_are_counted() {
        let content = concat!(
            r#"{"type":"user","isSidechain":false,"message":{"role":"user","content":[{"type":"tool_result","content":"ok"}]}}"#,
            "\n",
            r#"{"type":"assistant","isSidechain":true,"message":{"id":"x","content":[]}}"#,
            "\n",
            "not json\n",
        );
        let parsed = parse_session(content);
        assert!(parsed.session.events.is_empty());
        assert_eq!(parsed.session.sidechain_records, 1);
        assert_eq!(parsed.session.malformed_lines, 1);
    }
}
