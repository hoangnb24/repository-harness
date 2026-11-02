//! Skill receipt compliance and token accounting over normalized session
//! events. Session parsing lives in infrastructure; this module only counts.

use std::collections::{BTreeMap, HashSet};

pub const RECEIPT_PREFIX: &str = "HARNESS_SKILL:";

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct TokenUsage {
    pub input: u64,
    pub cache_creation: u64,
    pub cache_read: u64,
    pub output: u64,
}

impl TokenUsage {
    pub fn add(&mut self, other: TokenUsage) {
        self.input += other.input;
        self.cache_creation += other.cache_creation;
        self.cache_read += other.cache_read;
        self.output += other.output;
    }

    pub fn total(&self) -> u64 {
        self.input + self.cache_creation + self.cache_read + self.output
    }
}

/// One normalized record from an agent session.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SessionEvent {
    /// A human prompt. It ends the previous turn and starts a new one.
    Prompt,
    /// The agent runtime loaded a skill because it was explicitly invoked.
    SkillLoaded { skill: String },
    /// One record of an assistant message. A message may span several
    /// records that repeat the same id and usage; usage counts once per id.
    Assistant {
        id: String,
        text: Option<String>,
        usage: Option<TokenUsage>,
    },
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ReceiptOutcome {
    Done,
    Stopped,
    Skipped,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Receipt {
    pub skill: String,
    pub outcome: ReceiptOutcome,
    pub detail: String,
}

/// Parse `HARNESS_SKILL: <skill> | done|stopped|skipped | <reason or path>`.
pub fn parse_receipt(line: &str) -> Option<Receipt> {
    let rest = line.trim().strip_prefix(RECEIPT_PREFIX)?;
    let mut parts = rest.splitn(3, '|').map(str::trim);
    let skill = parts.next()?.trim_start_matches(['$', '/']);
    let outcome = match parts.next()? {
        "done" => ReceiptOutcome::Done,
        "stopped" => ReceiptOutcome::Stopped,
        "skipped" => ReceiptOutcome::Skipped,
        _ => return None,
    };
    let detail = parts.next()?;
    if skill.is_empty() || detail.is_empty() {
        return None;
    }
    Some(Receipt {
        skill: skill.to_string(),
        outcome,
        detail: detail.to_string(),
    })
}

/// Receipts form the trailing block of the final answer: the last non-empty
/// lines, all of which must parse as receipts. A receipt elsewhere is ignored.
pub fn trailing_receipts(text: &str) -> Vec<Receipt> {
    let mut receipts = Vec::new();
    for line in text.lines().rev().filter(|line| !line.trim().is_empty()) {
        match parse_receipt(line) {
            Some(receipt) => receipts.push(receipt),
            None => break,
        }
    }
    receipts.reverse();
    receipts
}

#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct SkillStats {
    pub invocations: u64,
    pub receipts: u64,
    pub done: u64,
    pub stopped: u64,
    pub skipped: u64,
    pub tokens: TokenUsage,
}

#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct SkillReport {
    pub skills: BTreeMap<String, SkillStats>,
    pub session_tokens: TokenUsage,
    pub assistant_messages: u64,
}

#[derive(Default)]
struct Turn {
    invocations: Vec<String>,
    final_text: Option<(String, String)>,
}

pub fn build_skill_report<I>(events: I) -> SkillReport
where
    I: IntoIterator<Item = SessionEvent>,
{
    let mut report = SkillReport::default();
    let mut counted_messages: HashSet<String> = HashSet::new();
    let mut turn = Turn::default();

    for event in events {
        match event {
            SessionEvent::Prompt => finish_turn(&mut report, std::mem::take(&mut turn)),
            SessionEvent::SkillLoaded { skill } => {
                report.skills.entry(skill.clone()).or_default().invocations += 1;
                turn.invocations.push(skill);
            }
            SessionEvent::Assistant { id, text, usage } => {
                if let Some(text) = text.filter(|text| !text.trim().is_empty()) {
                    turn.final_text = Some(match turn.final_text.take() {
                        Some((last_id, mut joined)) if last_id == id => {
                            joined.push('\n');
                            joined.push_str(&text);
                            (last_id, joined)
                        }
                        _ => (id.clone(), text),
                    });
                }
                if counted_messages.insert(id) {
                    report.assistant_messages += 1;
                    if let Some(usage) = usage {
                        report.session_tokens.add(usage);
                        if let Some(skill) = turn.invocations.last() {
                            report
                                .skills
                                .entry(skill.clone())
                                .or_default()
                                .tokens
                                .add(usage);
                        }
                    }
                }
            }
        }
    }
    finish_turn(&mut report, turn);
    report
}

fn finish_turn(report: &mut SkillReport, turn: Turn) {
    if turn.invocations.is_empty() {
        return;
    }
    let mut receipts = turn
        .final_text
        .map(|(_, text)| trailing_receipts(&text))
        .unwrap_or_default();
    for skill in turn.invocations {
        let Some(index) = receipts.iter().position(|receipt| receipt.skill == skill) else {
            continue;
        };
        let receipt = receipts.remove(index);
        let stats = report.skills.entry(skill).or_default();
        stats.receipts += 1;
        match receipt.outcome {
            ReceiptOutcome::Done => stats.done += 1,
            ReceiptOutcome::Stopped => stats.stopped += 1,
            ReceiptOutcome::Skipped => stats.skipped += 1,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn usage(output: u64) -> Option<TokenUsage> {
        Some(TokenUsage {
            input: 1,
            cache_creation: 10,
            cache_read: 100,
            output,
        })
    }

    fn answer(id: &str, text: &str) -> SessionEvent {
        SessionEvent::Assistant {
            id: id.into(),
            text: Some(text.into()),
            usage: usage(5),
        }
    }

    fn load(skill: &str) -> SessionEvent {
        SessionEvent::SkillLoaded {
            skill: skill.into(),
        }
    }

    #[test]
    fn receipt_parsing_requires_outcome_and_detail() {
        assert!(parse_receipt("HARNESS_SKILL: encode-invariant | done | docs/x.md").is_some());
        assert!(parse_receipt("HARNESS_SKILL: encode-invariant | finished | x").is_none());
        assert!(parse_receipt("HARNESS_SKILL: encode-invariant | done | ").is_none());
        assert!(parse_receipt("HARNESS_SKILL: encode-invariant | done").is_none());
    }

    #[test]
    fn three_invocations_with_two_receipts_report_two_of_three() {
        let events = vec![
            SessionEvent::Prompt,
            load("encode-invariant"),
            answer(
                "a",
                "Work.\nHARNESS_SKILL: encode-invariant | done | tests/x.sh",
            ),
            SessionEvent::Prompt,
            load("encode-invariant"),
            answer(
                "b",
                "Stopped.\nHARNESS_SKILL: encode-invariant | stopped | no authority",
            ),
            SessionEvent::Prompt,
            load("encode-invariant"),
            answer("c", "Forgot the receipt."),
        ];
        let stats = &build_skill_report(events).skills["encode-invariant"];
        assert_eq!((stats.invocations, stats.receipts), (3, 2));
        assert_eq!((stats.done, stats.stopped), (1, 1));
    }

    #[test]
    fn receipt_must_be_trailing_and_name_the_invoked_skill() {
        let events = vec![
            SessionEvent::Prompt,
            load("improve-harness"),
            answer(
                "a",
                "HARNESS_SKILL: improve-harness | done | x\nMore text after.",
            ),
            SessionEvent::Prompt,
            load("improve-harness"),
            answer("b", "HARNESS_SKILL: encode-invariant | done | x"),
        ];
        let stats = &build_skill_report(events).skills["improve-harness"];
        assert_eq!((stats.invocations, stats.receipts), (2, 0));
    }

    #[test]
    fn repeated_message_records_count_usage_once() {
        let events = vec![
            SessionEvent::Prompt,
            load("onboard-repository"),
            SessionEvent::Assistant {
                id: "m".into(),
                text: None,
                usage: usage(7),
            },
            SessionEvent::Assistant {
                id: "m".into(),
                text: Some("HARNESS_SKILL: onboard-repository | done | report".into()),
                usage: usage(7),
            },
        ];
        let report = build_skill_report(events);
        let stats = &report.skills["onboard-repository"];
        assert_eq!(stats.receipts, 1);
        assert_eq!(
            stats.tokens,
            TokenUsage {
                input: 1,
                cache_creation: 10,
                cache_read: 100,
                output: 7
            }
        );
        assert_eq!(report.assistant_messages, 1);
    }

    #[test]
    fn tokens_before_any_skill_are_session_only() {
        let events = vec![SessionEvent::Prompt, answer("a", "hello")];
        let report = build_skill_report(events);
        assert!(report.skills.is_empty());
        assert_eq!(report.session_tokens.output, 5);
    }
}
