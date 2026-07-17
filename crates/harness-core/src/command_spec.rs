//! Frozen V1 command definitions used by both dispatch and mechanical source extraction.

use serde::{Deserialize, Serialize};

/// The verifier extracts this JSON literal directly from this source file. Keep the
/// `CORE_COMMAND_SPEC_JSON_BEGIN/END` markers and the array order stable.
// CORE_COMMAND_SPEC_JSON_BEGIN
pub const CORE_COMMAND_SPEC_JSON: &str = r#"{"binary":["scripts/bin/harness","scripts/bin/harness.exe"],"top_level":["install","update","audit","scaffold","status","version"],"version_alias":"--version","commands":[{"name":"install","mutation":"managed-files-manifest-and-archive-receipt","options":["--preview","--non-interactive","--accept-preview-sha256","--resume","--rollback","--v0-archive-manifest"],"exits":[0,2,3,4,64,70,74]},{"name":"update","mutation":"managed-files-and-manifest","options":["--preview","--non-interactive","--accept-preview-sha256","--resume","--rollback"],"exits":[0,2,3,4,64,70,74]},{"name":"audit","mutation":"none","options":["--json"],"exits":[0,2,3,64,70,74]},{"name":"scaffold","mutation":"one-explicit-neutral-artifact","options":["--template","--destination","--preview","--non-interactive","--accept-preview-sha256","--resume","--rollback"],"exits":[0,3,4,64,70,74]},{"name":"status","mutation":"none","options":["--json"],"exits":[0,3,64,70,74]},{"name":"version","mutation":"none","options":["--json"],"exits":[0,64,70]}],"forbidden_top_level":["migrate","inspect","export","archive","preview","apply","resume","rollback","init","intake","story","query","db"]}"#;
// CORE_COMMAND_SPEC_JSON_END

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
pub struct SurfaceSpec {
    pub binary: Vec<String>,
    pub top_level: Vec<String>,
    pub version_alias: String,
    pub commands: Vec<CommandSpec>,
    pub forbidden_top_level: Vec<String>,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
pub struct CommandSpec {
    pub name: String,
    pub mutation: String,
    pub options: Vec<String>,
    pub exits: Vec<u8>,
}

pub fn core_spec() -> SurfaceSpec {
    serde_json::from_str(CORE_COMMAND_SPEC_JSON).expect("embedded command spec is valid JSON")
}

pub fn machine_help() -> String {
    format!("{CORE_COMMAND_SPEC_JSON}\n")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn source_spec_has_exact_six_command_order() {
        let spec = core_spec();
        assert_eq!(
            spec.top_level,
            ["install", "update", "audit", "scaffold", "status", "version"]
        );
        assert_eq!(
            spec.top_level,
            spec.commands
                .iter()
                .map(|command| command.name.as_str())
                .collect::<Vec<_>>()
        );
    }
}
