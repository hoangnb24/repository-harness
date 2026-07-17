//! Closed six-command CLI parsing and deterministic rendering.

use std::ffi::OsString;

use crate::command_spec::{core_spec, machine_help};
use crate::domain::{Command, Envelope, MutatorOptions, ScaffoldOptions};

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Parsed {
    Help,
    Command(Command),
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct UsageError(pub String);

pub fn parse(arguments: impl IntoIterator<Item = OsString>) -> Result<Parsed, UsageError> {
    let arguments: Vec<String> = arguments
        .into_iter()
        .map(|argument| {
            argument
                .into_string()
                .map_err(|_| UsageError("arguments must be UTF-8".into()))
        })
        .collect::<Result<_, _>>()?;
    match arguments.as_slice() {
        [argument] if argument == "--help" => return Ok(Parsed::Help),
        [argument] if argument == "--version" => {
            return Ok(Parsed::Command(Command::Version { json: false }));
        }
        [] => {
            return Err(UsageError(
                "one of six top-level commands is required".into(),
            ))
        }
        _ => {}
    }
    let command = &arguments[0];
    if !core_spec().top_level.contains(command) {
        return Err(UsageError(format!(
            "unknown top-level command {command:?}; expected install, update, audit, scaffold, status, or version"
        )));
    }
    let options = &arguments[1..];
    match command.as_str() {
        "install" => Ok(Parsed::Command(Command::Install(parse_mutator(options)?))),
        "update" => Ok(Parsed::Command(Command::Update(parse_mutator(options)?))),
        "audit" => Ok(Parsed::Command(Command::Audit {
            json: parse_json_only(options)?,
        })),
        "scaffold" => Ok(Parsed::Command(Command::Scaffold(parse_scaffold(options)?))),
        "status" => Ok(Parsed::Command(Command::Status {
            json: parse_json_only(options)?,
        })),
        "version" => Ok(Parsed::Command(Command::Version {
            json: parse_json_only(options)?,
        })),
        _ => unreachable!("command membership was checked against the frozen spec"),
    }
}

fn parse_json_only(options: &[String]) -> Result<bool, UsageError> {
    match options {
        [] => Ok(false),
        [option] if option == "--json" => Ok(true),
        _ => Err(UsageError("the only command option is --json".into())),
    }
}

fn parse_scaffold(options: &[String]) -> Result<ScaffoldOptions, UsageError> {
    let mut scaffold = ScaffoldOptions::default();
    let mut remaining = Vec::new();
    let mut index = 0;
    while index < options.len() {
        match options[index].as_str() {
            "--template" | "--destination" => {
                let name = options[index].clone();
                let value = options
                    .get(index + 1)
                    .ok_or_else(|| UsageError(format!("{name} requires a value")))?
                    .clone();
                let slot = if name == "--template" {
                    &mut scaffold.template
                } else {
                    &mut scaffold.destination
                };
                if slot.replace(value).is_some() {
                    return Err(UsageError(format!("duplicate option {name}")));
                }
                index += 2;
            }
            _ => {
                remaining.push(options[index].clone());
                if matches!(
                    options[index].as_str(),
                    "--accept-preview-sha256" | "--resume" | "--rollback"
                ) {
                    let value = options.get(index + 1).ok_or_else(|| {
                        UsageError(format!("{} requires a value", options[index]))
                    })?;
                    remaining.push(value.clone());
                    index += 2;
                } else {
                    index += 1;
                }
            }
        }
    }
    if scaffold.template.is_none() || scaffold.destination.is_none() {
        return Err(UsageError(
            "scaffold requires --template <id> and --destination <path>".into(),
        ));
    }
    scaffold.mutation = parse_mutator(&remaining)?;
    Ok(scaffold)
}

fn parse_mutator(options: &[String]) -> Result<MutatorOptions, UsageError> {
    let mut parsed = MutatorOptions::default();
    let mut seen = std::collections::BTreeSet::new();
    let mut index = 0;
    while index < options.len() {
        let option = options[index].as_str();
        if !seen.insert(option.to_string()) {
            return Err(UsageError(format!("duplicate option {option}")));
        }
        match option {
            "--preview" => {
                parsed.preview = true;
                index += 1;
            }
            "--non-interactive" => {
                parsed.non_interactive = true;
                index += 1;
            }
            "--accept-preview-sha256" | "--resume" | "--rollback" => {
                let value = options
                    .get(index + 1)
                    .ok_or_else(|| UsageError(format!("{option} requires a value")))?
                    .clone();
                if value.starts_with("--") {
                    return Err(UsageError(format!("{option} requires a value")));
                }
                match option {
                    "--accept-preview-sha256" => {
                        if !is_sha256(&value) {
                            return Err(UsageError(
                                "--accept-preview-sha256 requires 64 lowercase hex characters"
                                    .into(),
                            ));
                        }
                        parsed.accept_preview_sha256 = Some(value);
                    }
                    "--resume" => parsed.resume = Some(value),
                    "--rollback" => parsed.rollback = Some(value),
                    _ => unreachable!(),
                }
                index += 2;
            }
            _ => return Err(UsageError(format!("unknown option {option}"))),
        }
    }
    if parsed.non_interactive != parsed.accept_preview_sha256.is_some() {
        return Err(UsageError(
            "--non-interactive and --accept-preview-sha256 must be supplied together".into(),
        ));
    }
    if parsed.resume.is_some() && parsed.rollback.is_some() {
        return Err(UsageError(
            "--resume and --rollback are mutually exclusive".into(),
        ));
    }
    if (parsed.resume.is_some() || parsed.rollback.is_some())
        && (parsed.preview || parsed.non_interactive)
    {
        return Err(UsageError(
            "recovery options cannot be combined with preview/confirmation options".into(),
        ));
    }
    Ok(parsed)
}

fn is_sha256(value: &str) -> bool {
    value.len() == 64
        && value
            .bytes()
            .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
}

pub fn render(envelope: &Envelope, json: bool) -> Result<String, serde_json::Error> {
    if json {
        return serde_json::to_string(envelope).map(|line| format!("{line}\n"));
    }
    let mut output = String::new();
    output.push_str("Repository Harness V1\n");
    output.push_str(&format!("schema: {}\n", envelope.schema));
    output.push_str(&format!("command: {}\n", envelope.command));
    output.push_str(&format!("outcome: {}\n", envelope.outcome.as_str()));
    output.push_str(&format!("exit-code: {}\n", envelope.exit_code));
    output.push_str(&format!("mutation: {}\n", envelope.mutation.as_str()));
    output.push_str(&format!(
        "repository-mode: {}\n",
        envelope.repository_mode.as_str()
    ));
    output.push_str(&format!("release-role: {}\n", envelope.release.role));
    output.push_str(&format!(
        "release-sequence: {}\n",
        envelope.release.sequence
    ));
    output.push_str(&format!(
        "release-index-sha256: {}\n",
        envelope.release.index_sha256
    ));
    output.push_str(&format!(
        "details-readiness: {}\n",
        envelope.details.readiness.as_str()
    ));
    for notice in &envelope.notices {
        let path = notice
            .path
            .as_ref()
            .map(|path| format!(" [{path}]"))
            .unwrap_or_default();
        output.push_str(&format!(
            "notice {}{path}: {}\n",
            notice.code, notice.message
        ));
    }
    for violation in &envelope.details.violations {
        output.push_str(&format!("violation: {violation}\n"));
    }
    if let Some(operations) = &envelope.details.operations {
        for operation in operations {
            output.push_str(&format!("operation-id: {}\n", operation.operation_id));
            output.push_str(&format!("operation-kind: {}\n", operation.kind.as_str()));
            output.push_str(&format!("operation-path: {}\n", operation.path));
            output.push_str(&format!(
                "operation-disposition: {}\n",
                operation.disposition.as_str()
            ));
            output.push_str(&format!(
                "operation-before-sha256: {}\n",
                operation.before_sha256.as_deref().unwrap_or("null")
            ));
            output.push_str(&format!(
                "operation-after-sha256: {}\n",
                operation.after_sha256.as_deref().unwrap_or("null")
            ));
        }
    }
    Ok(output)
}

pub fn help() -> String {
    machine_help()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn strings(values: &[&str]) -> Vec<OsString> {
        values.iter().map(OsString::from).collect()
    }

    #[test]
    fn accepts_exact_six_commands_and_version_alias() {
        for command in ["install", "update", "audit", "status", "version"] {
            assert!(parse(strings(&[command])).is_ok(), "rejected {command}");
        }
        assert!(parse(strings(&[
            "scaffold",
            "--template",
            "decision-template",
            "--destination",
            "docs/templates/decision.md"
        ]))
        .is_ok());
        assert_eq!(
            parse(strings(&["--version"])),
            Ok(Parsed::Command(Command::Version { json: false }))
        );
    }

    #[test]
    fn rejects_v0_bridge_and_extra_commands() {
        for command in [
            "migrate", "init", "intake", "story", "query", "db", "inspect", "export", "preview",
            "apply", "resume", "rollback", "help",
        ] {
            assert!(parse(strings(&[command])).is_err(), "accepted {command}");
        }
    }

    #[test]
    fn enforces_confirmation_and_recovery_pairs() {
        assert!(parse(strings(&["install", "--non-interactive"])).is_err());
        assert!(parse(strings(&[
            "install",
            "--non-interactive",
            "--accept-preview-sha256",
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        ]))
        .is_ok());
        assert!(parse(strings(&[
            "update",
            "--resume",
            "op-1",
            "--rollback",
            "op-1"
        ]))
        .is_err());
    }

    #[test]
    fn human_output_is_a_case_preserving_projection_of_the_json_envelope() {
        use crate::domain::{
            Disposition, Mutation, Notice, Operation, OperationKind, Outcome, Readiness,
            RepositoryMode, UNBOUND_RELEASE_SHA256,
        };

        let mut envelope = Envelope::new("audit");
        envelope.outcome = Outcome::Ready;
        envelope.mutation = Mutation::Preview;
        envelope.repository_mode = RepositoryMode::FreshV1;
        envelope.details.readiness = Readiness::Ready;
        envelope.notices.push(Notice {
            code: "case-sensitive-path".into(),
            path: Some("Docs/CaseSensitive.md".into()),
            message: "Preserves Case".into(),
        });
        envelope.details.operations = Some(vec![Operation {
            operation_id: "create-case-sensitive".into(),
            kind: OperationKind::Create,
            path: "Docs/CaseSensitive.md".into(),
            disposition: Disposition::ManagedV1,
            before_sha256: None,
            after_sha256: Some("a".repeat(64)),
        }]);
        let human = render(&envelope, false).unwrap();
        let expected = format!(
            "Repository Harness V1\n\
             schema: repository-harness-output/v1\n\
             command: audit\n\
             outcome: ready\n\
             exit-code: 0\n\
             mutation: preview\n\
             repository-mode: fresh-v1\n\
             release-role: core-release\n\
             release-sequence: 1\n\
             release-index-sha256: {UNBOUND_RELEASE_SHA256}\n\
             details-readiness: ready\n\
             notice case-sensitive-path [Docs/CaseSensitive.md]: Preserves Case\n\
             operation-id: create-case-sensitive\n\
             operation-kind: create\n\
             operation-path: Docs/CaseSensitive.md\n\
             operation-disposition: managed-v1\n\
             operation-before-sha256: null\n\
             operation-after-sha256: {}\n",
            "a".repeat(64)
        );
        assert_eq!(human, expected);
    }
}
