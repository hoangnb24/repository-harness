use serde::Serialize;

use crate::application::SessionSkillReport;
use crate::domain::{SkillStats, TokenUsage};
use crate::interface::presenter::CommandExit;

pub const EXIT_FAILED: i32 = 1;
pub const EXIT_USAGE: i32 = 2;

#[derive(Serialize)]
struct SkillReportOutput<'a> {
    operation: &'static str,
    format: &'static str,
    sessions: &'a [String],
    skills: Vec<SkillOutput<'a>>,
    session_tokens: TokensOutput,
    assistant_messages: u64,
    malformed_lines: u64,
    sidechain_records_skipped: u64,
}

#[derive(Serialize)]
struct SkillOutput<'a> {
    skill: &'a str,
    invocations: u64,
    receipts: u64,
    compliance: Option<f64>,
    done: u64,
    stopped: u64,
    skipped: u64,
    tokens: TokensOutput,
}

#[derive(Serialize)]
struct TokensOutput {
    input: u64,
    cache_creation: u64,
    cache_read: u64,
    output: u64,
    total: u64,
}

fn tokens(usage: &TokenUsage) -> TokensOutput {
    TokensOutput {
        input: usage.input,
        cache_creation: usage.cache_creation,
        cache_read: usage.cache_read,
        output: usage.output,
        total: usage.total(),
    }
}

fn compliance(stats: &SkillStats) -> Option<f64> {
    (stats.invocations > 0).then(|| stats.receipts as f64 / stats.invocations as f64)
}

pub fn present_skill_report(result: &SessionSkillReport, json: bool) -> CommandExit {
    let report = &result.report;
    if json {
        let output = SkillReportOutput {
            operation: "skill-report",
            format: "claude-code-jsonl",
            sessions: &result.sessions,
            skills: report
                .skills
                .iter()
                .map(|(skill, stats)| SkillOutput {
                    skill,
                    invocations: stats.invocations,
                    receipts: stats.receipts,
                    compliance: compliance(stats),
                    done: stats.done,
                    stopped: stats.stopped,
                    skipped: stats.skipped,
                    tokens: tokens(&stats.tokens),
                })
                .collect(),
            session_tokens: tokens(&report.session_tokens),
            assistant_messages: report.assistant_messages,
            malformed_lines: result.malformed_lines,
            sidechain_records_skipped: result.sidechain_records,
        };
        return CommandExit {
            code: 0,
            stdout: format!("{}\n", serde_json::to_string_pretty(&output).unwrap()),
            stderr: String::new(),
        };
    }

    let mut out = format!(
        "Skill receipts across {} session(s):\n",
        result.sessions.len()
    );
    if report.skills.is_empty() {
        out.push_str("  no explicit skill invocations found (0/0)\n");
    }
    for (skill, stats) in &report.skills {
        let rate = compliance(stats)
            .map(|rate| format!("{:.0}%", rate * 100.0))
            .unwrap_or_else(|| "n/a".into());
        out.push_str(&format!(
            "  {skill}: {}/{} receipts ({rate}; done {}, stopped {}, skipped {})\n",
            stats.receipts, stats.invocations, stats.done, stats.stopped, stats.skipped
        ));
        out.push_str(&format!(
            "    tokens: input {}, cache creation {}, cache read {}, output {}\n",
            stats.tokens.input,
            stats.tokens.cache_creation,
            stats.tokens.cache_read,
            stats.tokens.output
        ));
    }
    let session = &report.session_tokens;
    out.push_str(&format!(
        "Session tokens: input {}, cache creation {}, cache read {}, output {} ({} assistant messages)\n",
        session.input, session.cache_creation, session.cache_read, session.output,
        report.assistant_messages
    ));
    out.push_str(&format!(
        "Skipped: {} malformed line(s), {} subagent (sidechain) record(s)\n",
        result.malformed_lines, result.sidechain_records
    ));
    out.push_str(
        "Receipts are self-reported: this measures format compliance, not whether the work was correct.\n",
    );
    CommandExit {
        code: 0,
        stdout: out,
        stderr: String::new(),
    }
}
