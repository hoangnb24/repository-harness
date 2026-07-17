use std::collections::BTreeSet;
use std::ffi::OsString;

use crate::command_spec::help;

#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct ArchiveOptions {
    pub age_recipient: Option<String>,
    pub plaintext: bool,
    pub plaintext_risk_acknowledged: bool,
}

#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct SourceOptions {
    pub archive_manifest: Option<String>,
    pub age_identity_file: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Command {
    Help,
    Inspect {
        json: bool,
        source: SourceOptions,
    },
    Export {
        output: String,
        source: SourceOptions,
    },
    Archive {
        archive: ArchiveOptions,
    },
    Version {
        json: bool,
    },
}

#[derive(Clone, Debug, PartialEq, Eq, thiserror::Error)]
#[error("{0}")]
pub struct UsageError(pub String);

pub fn parse(arguments: impl IntoIterator<Item = OsString>) -> Result<Command, UsageError> {
    let arguments = arguments
        .into_iter()
        .map(|value| {
            value
                .into_string()
                .map_err(|_| UsageError("arguments must be UTF-8".into()))
        })
        .collect::<Result<Vec<_>, _>>()?;
    match arguments.as_slice() {
        [value] if value == "--help" => return Ok(Command::Help),
        [] => {
            return Err(UsageError(
                "one of four top-level commands is required".into(),
            ))
        }
        _ => {}
    }
    let options = &arguments[1..];
    match arguments[0].as_str() {
        "inspect" => parse_inspect(options),
        "export" => parse_export(options),
        "archive" => parse_archive(options),
        "version" => Ok(Command::Version {
            json: parse_json_only(options)?,
        }),
        name => Err(UsageError(format!(
            "unknown top-level command {name:?}; expected inspect, export, archive, or version"
        ))),
    }
}

fn parse_inspect(options: &[String]) -> Result<Command, UsageError> {
    let mut json = false;
    let mut filtered = Vec::new();
    for option in options {
        if option == "--json" {
            if json {
                return Err(UsageError("duplicate option --json".into()));
            }
            json = true;
        } else {
            filtered.push(option.clone());
        }
    }
    Ok(Command::Inspect {
        json,
        source: parse_source(&filtered)?,
    })
}

fn parse_export(options: &[String]) -> Result<Command, UsageError> {
    let mut output = None;
    let mut source_options = Vec::new();
    let mut index = 0;
    while index < options.len() {
        if options[index] == "--output" {
            if output.is_some() {
                return Err(UsageError("duplicate option --output".into()));
            }
            output = Some(option_value(options, &mut index, "--output")?);
        } else {
            source_options.push(options[index].clone());
            if matches!(
                options[index].as_str(),
                "--archive-manifest" | "--age-identity-file"
            ) {
                let value = options
                    .get(index + 1)
                    .ok_or_else(|| UsageError(format!("{} requires a value", options[index])))?;
                source_options.push(value.clone());
                index += 2;
            } else {
                index += 1;
            }
        }
    }
    Ok(Command::Export {
        output: output.ok_or_else(|| UsageError("export requires --output <path>".into()))?,
        source: parse_source(&source_options)?,
    })
}

fn parse_source(options: &[String]) -> Result<SourceOptions, UsageError> {
    let mut parsed = SourceOptions::default();
    let mut seen = BTreeSet::new();
    let mut index = 0;
    while index < options.len() {
        let option = options[index].as_str();
        if !seen.insert(option.to_owned()) {
            return Err(UsageError(format!("duplicate option {option}")));
        }
        let value = option_value(options, &mut index, option)?;
        match option {
            "--archive-manifest" => parsed.archive_manifest = Some(value),
            "--age-identity-file" => parsed.age_identity_file = Some(value),
            _ => return Err(UsageError(format!("unknown option {option}"))),
        }
    }
    if parsed.age_identity_file.is_some() && parsed.archive_manifest.is_none() {
        return Err(UsageError(
            "--age-identity-file requires --archive-manifest".into(),
        ));
    }
    Ok(parsed)
}

fn parse_archive(options: &[String]) -> Result<Command, UsageError> {
    let mut archive = ArchiveOptions::default();
    let mut seen = BTreeSet::new();
    let mut index = 0;
    while index < options.len() {
        let option = options[index].as_str();
        if !seen.insert(option.to_owned()) {
            return Err(UsageError(format!("duplicate option {option}")));
        }
        match option {
            "--age-recipient" => {
                archive.age_recipient = Some(option_value(options, &mut index, option)?);
            }
            "--archive-plaintext" => {
                archive.plaintext = true;
                index += 1;
            }
            "--acknowledge-plaintext-recovery-risk" => {
                archive.plaintext_risk_acknowledged = true;
                index += 1;
            }
            _ => return Err(UsageError(format!("unknown option {option}"))),
        }
    }
    validate_archive_options(&archive)?;
    Ok(Command::Archive { archive })
}

fn option_value(options: &[String], index: &mut usize, option: &str) -> Result<String, UsageError> {
    let value = options
        .get(*index + 1)
        .filter(|value| !value.starts_with("--"))
        .ok_or_else(|| UsageError(format!("{option} requires a value")))?
        .clone();
    *index += 2;
    Ok(value)
}

fn validate_archive_options(options: &ArchiveOptions) -> Result<(), UsageError> {
    if options.plaintext != options.plaintext_risk_acknowledged {
        return Err(UsageError(
            "plaintext requires both --archive-plaintext and --acknowledge-plaintext-recovery-risk"
                .into(),
        ));
    }
    if options.plaintext && options.age_recipient.is_some() {
        return Err(UsageError(
            "--age-recipient cannot be combined with plaintext override".into(),
        ));
    }
    if !options.plaintext && options.age_recipient.is_none() {
        return Err(UsageError(
            "encrypted archives require --age-recipient <age1...>".into(),
        ));
    }
    Ok(())
}

fn parse_json_only(options: &[String]) -> Result<bool, UsageError> {
    match options {
        [] => Ok(false),
        [option] if option == "--json" => Ok(true),
        _ => Err(UsageError("the only command option is --json".into())),
    }
}

pub fn machine_help() -> String {
    help()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn arguments(values: &[&str]) -> Vec<OsString> {
        values.iter().map(OsString::from).collect()
    }

    #[test]
    fn parser_accepts_exactly_the_archive_only_grammar() {
        for accepted in [
            vec!["--help"],
            vec!["inspect"],
            vec!["inspect", "--json"],
            vec![
                "inspect",
                "--archive-manifest",
                ".harness-v0-archive/a/archive-manifest.json",
            ],
            vec!["export", "--output", "v0-export.json"],
            vec!["archive", "--age-recipient", "age1fixture"],
            vec![
                "archive",
                "--archive-plaintext",
                "--acknowledge-plaintext-recovery-risk",
            ],
            vec!["version", "--json"],
        ] {
            assert!(parse(arguments(&accepted)).is_ok(), "rejected {accepted:?}");
        }
        for forbidden in [
            "preview", "apply", "resume", "rollback", "migrate", "install",
        ] {
            assert!(
                parse(arguments(&[forbidden])).is_err(),
                "accepted {forbidden}"
            );
        }
        assert!(parse(arguments(&["--version"])).is_err());
    }

    #[test]
    fn archive_confidentiality_and_archive_source_options_are_closed() {
        assert!(parse(arguments(&["archive"])).is_err());
        assert!(parse(arguments(&["archive", "--archive-plaintext"])).is_err());
        assert!(parse(arguments(&[
            "inspect",
            "--age-identity-file",
            "identity.txt"
        ]))
        .is_err());
    }
}
