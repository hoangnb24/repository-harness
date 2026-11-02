use std::fs;
use std::path::Path;
use std::process::{Command, Output};

fn harness(args: &[&str], directory: &Path) -> Output {
    Command::new(env!("CARGO_BIN_EXE_harness"))
        .args(args)
        .current_dir(directory)
        .output()
        .unwrap()
}

fn stderr(output: &Output) -> String {
    String::from_utf8_lossy(&output.stderr).into_owned()
}

fn stdout(output: &Output) -> String {
    String::from_utf8_lossy(&output.stdout).into_owned()
}

fn prompt(text: &str) -> String {
    serde_json::json!({"type":"user","isSidechain":false,"message":{"role":"user","content":text}})
        .to_string()
}

fn skill_loaded(skill: &str) -> String {
    serde_json::json!({"type":"user","isMeta":true,"isSidechain":false,"message":{"role":"user","content":[
        {"type":"text","text":format!("Base directory for this skill: /repo/.claude/skills/{skill}\n\n# Skill")}
    ]}})
    .to_string()
}

fn answer(id: &str, text: &str, output_tokens: u64) -> String {
    serde_json::json!({"type":"assistant","isSidechain":false,"message":{"id":id,"role":"assistant",
        "content":[{"type":"text","text":text}],
        "usage":{"input_tokens":2,"cache_creation_input_tokens":30,"cache_read_input_tokens":400,"output_tokens":output_tokens}}})
    .to_string()
}

fn write_session(directory: &Path, lines: &[String]) -> String {
    let path = directory.join("session.jsonl");
    fs::write(&path, format!("{}\n", lines.join("\n"))).unwrap();
    path.to_str().unwrap().to_string()
}

#[test]
fn three_invocations_and_two_receipts_report_two_of_three_with_tokens() {
    let directory = tempfile::tempdir().unwrap();
    let session = write_session(
        directory.path(),
        &[
            prompt("/encode-invariant first SECRET-TOKEN-123"),
            skill_loaded("encode-invariant"),
            answer(
                "m1",
                "Done.\nHARNESS_SKILL: encode-invariant | done | tests/a.sh",
                10,
            ),
            answer(
                "m1",
                "Done.\nHARNESS_SKILL: encode-invariant | done | tests/a.sh",
                10,
            ),
            prompt("/encode-invariant second"),
            skill_loaded("encode-invariant"),
            answer(
                "m2",
                "Stop.\nHARNESS_SKILL: encode-invariant | stopped | no accepted authority",
                20,
            ),
            prompt("/encode-invariant third"),
            skill_loaded("encode-invariant"),
            answer("m3", "No receipt here.", 30),
            prompt("please encode an invariant for me"),
            answer(
                "m4",
                "Talking about invariants without invoking the skill.",
                40,
            ),
            "{not json".into(),
        ],
    );
    let output = harness(&["skill-report", "--json", &session], directory.path());
    assert_eq!(output.status.code(), Some(0), "{}", stderr(&output));
    let text = stdout(&output);
    assert!(!text.contains("SECRET-TOKEN-123"), "prompt text leaked");
    let report: serde_json::Value = serde_json::from_str(&text).unwrap();
    let skill = &report["skills"][0];
    assert_eq!(skill["skill"], "encode-invariant");
    assert_eq!(skill["invocations"], 3);
    assert_eq!(skill["receipts"], 2);
    assert_eq!(skill["stopped"], 1);
    assert_eq!(
        skill["tokens"]["output"], 60,
        "repeated message id counts once"
    );
    assert_eq!(skill["tokens"]["cache_read"], 1200);
    assert_eq!(report["session_tokens"]["output"], 100);
    assert_eq!(report["malformed_lines"], 1);

    let human = harness(&["skill-report", &session], directory.path());
    assert!(stdout(&human).contains("encode-invariant: 2/3 receipts"));
    assert!(!stdout(&human).contains("SECRET-TOKEN-123"));
}

#[test]
fn no_invocations_report_zero_of_zero() {
    let directory = tempfile::tempdir().unwrap();
    let session = write_session(directory.path(), &[prompt("hi"), answer("m1", "hello", 1)]);
    let output = harness(&["skill-report", &session], directory.path());
    assert_eq!(output.status.code(), Some(0));
    assert!(stdout(&output).contains("(0/0)"));
}

#[test]
fn unsupported_session_format_is_a_usage_error() {
    let directory = tempfile::tempdir().unwrap();
    let session = write_session(
        directory.path(),
        &[r#"{"timestamp":"2026-11-02","payload":{"type":"message"}}"#.into()],
    );
    let output = harness(&["skill-report", &session], directory.path());
    assert_eq!(output.status.code(), Some(2));
    assert!(stderr(&output).contains("unsupported session format"));
}
