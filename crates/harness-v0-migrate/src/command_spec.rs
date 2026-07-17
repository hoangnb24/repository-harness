//! Closed Phase 4 bridge grammar, kept separate from the permanent core.

pub const BRIDGE_VERSION: &str = env!("CARGO_PKG_VERSION");

// BRIDGE_COMMAND_SPEC_JSON_BEGIN
pub const BRIDGE_COMMAND_SPEC_JSON: &str = r#"{
  "binary": ["scripts/bin/harness-v0-migrate", "scripts/bin/harness-v0-migrate.exe"],
  "top_level": ["inspect", "export", "preview", "apply", "resume", "rollback", "version"],
  "commands": [
    {"name":"inspect","mutation":"none","options":["--json"],"exits":[0,3,5,64,70,74]},
    {"name":"export","mutation":"new-export-and-archive-only","options":["--output","--age-recipient","--archive-plaintext","--acknowledge-plaintext-recovery-risk"],"exits":[0,3,5,64,70,74]},
    {"name":"preview","mutation":"none","options":["--json"],"exits":[0,2,3,4,5,64,70,74]},
    {"name":"apply","mutation":"journal-owned-conversion","options":["--non-interactive","--accept-preview-sha256","--age-recipient","--archive-plaintext","--acknowledge-plaintext-recovery-risk"],"exits":[0,2,3,4,5,64,70,74]},
    {"name":"resume","mutation":"remaining-journal-operations","options":["--conversion-id"],"exits":[0,2,3,4,5,64,70,74]},
    {"name":"rollback","mutation":"matching-journal-owned-post-images","options":["--conversion-id"],"exits":[0,3,4,5,64,70,74]},
    {"name":"version","mutation":"none","options":["--json"],"exits":[0,64,70]}
  ],
  "forbidden_top_level": ["install", "update", "audit", "scaffold", "status", "migrate", "init", "query"]
}"#;
// BRIDGE_COMMAND_SPEC_JSON_END

pub fn help() -> String {
    let mut output = BRIDGE_COMMAND_SPEC_JSON.to_owned();
    output.push('\n');
    output
}
