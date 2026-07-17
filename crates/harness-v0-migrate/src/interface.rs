use std::ffi::OsString;

use crate::command_spec::help;

#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct ArchiveOptions {
    pub age_recipient: Option<String>,
    pub plaintext: bool,
    pub plaintext_risk_acknowledged: bool,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Command {
    Help,
    Inspect {
        json: bool,
    },
    Export {
        output: String,
        archive: ArchiveOptions,
    },
    Preview {
        json: bool,
    },
    Apply {
        accepted_preview_sha256: String,
        archive: ArchiveOptions,
    },
    Resume {
        conversion_id: String,
    },
    Rollback {
        conversion_id: String,
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
        [value] if value == "--version" => return Ok(Command::Version { json: false }),
        [] => {
            return Err(UsageError(
                "one of seven top-level commands is required".into(),
            ))
        }
        _ => {}
    }
    let name = &arguments[0];
    let options = &arguments[1..];
    match name.as_str() {
        "inspect" => Ok(Command::Inspect {
            json: parse_json_only(options)?,
        }),
        "export" => parse_export(options),
        "preview" => Ok(Command::Preview {
            json: parse_json_only(options)?,
        }),
        "apply" => parse_apply(options),
        "resume" => Ok(Command::Resume {
            conversion_id: parse_conversion_id(options)?,
        }),
        "rollback" => Ok(Command::Rollback {
            conversion_id: parse_conversion_id(options)?,
        }),
        "version" => Ok(Command::Version {
            json: parse_json_only(options)?,
        }),
        _ => Err(UsageError(format!(
            "unknown top-level command {name:?}; expected inspect, export, preview, apply, resume, rollback, or version"
        ))),
    }
}

fn parse_json_only(options: &[String]) -> Result<bool, UsageError> {
    match options {
        [] => Ok(false),
        [option] if option == "--json" => Ok(true),
        _ => Err(UsageError("the only command option is --json".into())),
    }
}

fn parse_export(options: &[String]) -> Result<Command, UsageError> {
    let (output, accepted, archive) = parse_mutating_options(options, true)?;
    if accepted.is_some() {
        return Err(UsageError("export does not accept a preview digest".into()));
    }
    Ok(Command::Export {
        output: output.ok_or_else(|| UsageError("export requires --output <path>".into()))?,
        archive,
    })
}

fn parse_apply(options: &[String]) -> Result<Command, UsageError> {
    let (output, accepted, archive) = parse_mutating_options(options, false)?;
    if output.is_some() {
        return Err(UsageError("apply does not accept --output".into()));
    }
    Ok(Command::Apply {
        accepted_preview_sha256: accepted.ok_or_else(|| {
            UsageError(
                "apply requires --non-interactive and --accept-preview-sha256 <digest>".into(),
            )
        })?,
        archive,
    })
}

fn parse_mutating_options(
    options: &[String],
    allow_output: bool,
) -> Result<(Option<String>, Option<String>, ArchiveOptions), UsageError> {
    let mut output = None;
    let mut accepted = None;
    let mut non_interactive = false;
    let mut archive = ArchiveOptions::default();
    let mut seen = std::collections::BTreeSet::new();
    let mut index = 0;
    while index < options.len() {
        let option = &options[index];
        if !seen.insert(option.clone()) {
            return Err(UsageError(format!("duplicate option {option}")));
        }
        match option.as_str() {
            "--output" if allow_output => {
                output = Some(option_value(options, &mut index, option)?);
            }
            "--age-recipient" => {
                archive.age_recipient = Some(option_value(options, &mut index, option)?);
            }
            "--accept-preview-sha256" => {
                let digest = option_value(options, &mut index, option)?;
                if !is_sha256(&digest) {
                    return Err(UsageError(
                        "--accept-preview-sha256 requires 64 lowercase hex characters".into(),
                    ));
                }
                accepted = Some(digest);
            }
            "--non-interactive" => {
                non_interactive = true;
                index += 1;
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
    if accepted.is_some() != non_interactive {
        return Err(UsageError(
            "--non-interactive and --accept-preview-sha256 must be supplied together".into(),
        ));
    }
    validate_archive_options(&archive)?;
    Ok((output, accepted, archive))
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

fn parse_conversion_id(options: &[String]) -> Result<String, UsageError> {
    match options {
        [option, value]
            if option == "--conversion-id"
                && !value.is_empty()
                && value.bytes().all(|byte| {
                    byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'-'
                }) =>
        {
            Ok(value.clone())
        }
        _ => Err(UsageError(
            "recovery requires --conversion-id <lowercase-id>".into(),
        )),
    }
}

fn is_sha256(value: &str) -> bool {
    value.len() == 64
        && value
            .bytes()
            .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
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
    fn parser_accepts_only_the_closed_bridge_grammar() {
        assert!(parse(arguments(&["inspect"])).is_ok());
        assert!(parse(arguments(&["preview", "--json"])).is_ok());
        assert!(parse(arguments(&["version"])).is_ok());
        assert!(parse(arguments(&["resume", "--conversion-id", "v0-abc"])).is_ok());
        for forbidden in [
            "install", "update", "audit", "scaffold", "status", "migrate", "init", "query",
        ] {
            assert!(
                parse(arguments(&[forbidden])).is_err(),
                "accepted {forbidden}"
            );
        }
    }

    #[test]
    fn plaintext_needs_both_explicit_flags_and_encryption_needs_a_recipient() {
        assert!(parse(arguments(&[
            "export",
            "--output",
            "export.json",
            "--archive-plaintext"
        ]))
        .is_err());
        assert!(parse(arguments(&[
            "export",
            "--output",
            "export.json",
            "--archive-plaintext",
            "--acknowledge-plaintext-recovery-risk"
        ]))
        .is_ok());
        assert!(parse(arguments(&["export", "--output", "export.json"])).is_err());
    }
}
