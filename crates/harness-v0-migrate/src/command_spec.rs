//! Closed archive-only Phase 4 bridge grammar.

pub const BRIDGE_VERSION: &str = env!("CARGO_PKG_VERSION");

// BRIDGE_COMMAND_SPEC_JSON_BEGIN
pub const BRIDGE_COMMAND_SPEC_JSON: &str = r#"{
  "binary": ["scripts/bin/harness-v0-migrate", "scripts/bin/harness-v0-migrate.exe"],
  "top_level": ["inspect", "export", "archive", "version"],
  "commands": [
    {"name":"inspect","mutation":"none","options":["--archive-manifest","--age-identity-file","--json"],"exits":[0,3,4,5,64,70,74]},
    {"name":"export","mutation":"new-export-only","options":["--output","--archive-manifest","--age-identity-file"],"exits":[0,3,4,5,64,70,74]},
    {"name":"archive","mutation":"new-append-only-archive","options":["--age-recipient","--archive-plaintext","--acknowledge-plaintext-recovery-risk"],"exits":[0,3,4,5,64,70,74]},
    {"name":"version","mutation":"none","options":["--json"],"exits":[0,64,70]}
  ],
  "forbidden_top_level": ["preview", "apply", "resume", "rollback", "install", "update", "audit", "scaffold", "status", "migrate", "init", "query"]
}"#;
// BRIDGE_COMMAND_SPEC_JSON_END

pub fn help() -> String {
    format!("{BRIDGE_COMMAND_SPEC_JSON}\n")
}
