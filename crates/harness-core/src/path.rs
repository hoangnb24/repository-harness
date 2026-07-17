//! Platform-independent V1 safe-path and collision rules.

use unicode_normalization::{is_nfc, UnicodeNormalization};

use crate::ports::PortError;
use crate::unicode_casefold::{full_case_fold, UNICODE_CASEFOLD_VERSION};

pub const COLLISION_CASEFOLD_VERSION: &str = UNICODE_CASEFOLD_VERSION;

const WINDOWS_DEVICES: [&str; 22] = [
    "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8",
    "COM9", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
];

pub fn validate_relative(value: &str, allow_harness: bool) -> Result<String, PortError> {
    if value.is_empty()
        || !is_nfc(value)
        || value.starts_with('/')
        || value.starts_with("//")
        || value.contains('\\')
        || value.contains('\0')
        || value.chars().any(char::is_control)
        || value
            .as_bytes()
            .get(1)
            .is_some_and(|byte| *byte == b':' && value.as_bytes()[0].is_ascii_alphabetic())
    {
        return Err(PortError::UnsafePath(value.into()));
    }
    let components: Vec<&str> = value.split('/').collect();
    if components
        .iter()
        .any(|part| part.is_empty() || *part == "." || *part == "..")
    {
        return Err(PortError::UnsafePath(value.into()));
    }
    for component in &components {
        if component.contains(':')
            || component.ends_with([' ', '.'])
            || WINDOWS_DEVICES.contains(
                &component
                    .split('.')
                    .next()
                    .unwrap_or("")
                    .to_uppercase()
                    .as_str(),
            )
        {
            return Err(PortError::UnsafePath(value.into()));
        }
    }
    if components
        .iter()
        .any(|component| component.eq_ignore_ascii_case(".git"))
    {
        return Err(PortError::UnsafePath(value.into()));
    }
    if components[0].eq_ignore_ascii_case(".harness") {
        let declared = value == ".harness/manifest.json"
            || value.starts_with(".harness/recovery/")
            || value == ".harness/legacy/v0-conversion"
            || value.starts_with(".harness/legacy/v0-conversion/");
        if !allow_harness || !declared {
            return Err(PortError::UnsafePath(value.into()));
        }
    }
    Ok(collision_key(value))
}

pub fn validate_exact_destination(value: &str) -> Result<String, PortError> {
    if value.chars().any(|character| "*?[]{}$".contains(character)) {
        return Err(PortError::UnsafePath(value.into()));
    }
    validate_relative(value, false)
}

pub fn collision_key(value: &str) -> String {
    let normalized: String = value.nfc().collect();
    full_case_fold(&normalized).nfc().collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_cross_platform_unsafe_paths() {
        for path in [
            "/tmp/x",
            "C:/tmp/x",
            "docs\\x",
            "docs/../x",
            "docs/README.md:evil",
            "docs/NUL.txt",
            "docs/trailing. ",
            ".git/config",
            ".harness/changesets/x.jsonl",
        ] {
            assert!(validate_relative(path, true).is_err(), "accepted {path}");
        }
    }

    #[test]
    fn collision_keys_are_case_and_normalization_stable() {
        assert_eq!(
            collision_key("docs/Readme.md"),
            collision_key("docs/README.md")
        );
        assert_eq!(collision_key("Straße.md"), collision_key("STRASSE.md"));
        assert_eq!(collision_key("docs/ſ.md"), collision_key("docs/s.md"));
        assert_eq!(collision_key("docs/ﬀ.md"), collision_key("docs/ff.md"));
    }
}
