//! Host adapters for declared-file reads, strict manifests, and unavailable Phase 3 payloads.

#[cfg(all(test, unix))]
use std::fs;
#[cfg(unix)]
use std::fs::File;
#[cfg(unix)]
use std::io::{Read, Seek, SeekFrom};
use std::path::PathBuf;

use crate::domain::{Manifest, MANIFEST_SCHEMA};
use crate::path::validate_relative;
use crate::ports::{
    CompatibilityObservation, FileSystemPort, ManifestPort, PortError, ReleaseMaterial,
    ReleasePort, ReleaseTrustInput, TrustPort,
};
#[cfg(unix)]
use crate::strict_json::hex_sha256;
use crate::strict_json::parse;

pub struct OsFileSystem {
    #[cfg(unix)]
    root_path: PathBuf,
    #[cfg(unix)]
    root: std::os::fd::OwnedFd,
    #[cfg(unix)]
    root_stat: rustix::fs::Stat,
}

impl OsFileSystem {
    pub fn new(root: impl Into<PathBuf>) -> Result<Self, PortError> {
        let root_path = root.into();
        #[cfg(unix)]
        {
            use rustix::fs::{fstat, open, Mode, OFlags};

            let root = open(
                &root_path,
                OFlags::RDONLY | OFlags::DIRECTORY | OFlags::CLOEXEC | OFlags::NOFOLLOW,
                Mode::empty(),
            )
            .map_err(|error| map_errno(".", error))?;
            let root_stat = fstat(&root).map_err(|error| map_errno(".", error))?;
            Ok(Self {
                root_path,
                root,
                root_stat,
            })
        }
        #[cfg(not(unix))]
        {
            let _ = root_path;
            Ok(Self {})
        }
    }

    #[cfg(unix)]
    fn open_chain(&self, relative: &str) -> Result<Vec<std::os::fd::OwnedFd>, PortError> {
        use rustix::fs::{openat, Mode, OFlags};

        validate_relative(relative, true)?;
        let mut chain: Vec<std::os::fd::OwnedFd> = Vec::new();
        let components: Vec<&str> = relative.split('/').collect();
        for (index, component) in components.iter().enumerate() {
            let mut flags = OFlags::RDONLY | OFlags::CLOEXEC | OFlags::NOFOLLOW;
            if index + 1 < components.len() {
                flags |= OFlags::DIRECTORY;
            }
            let opened = if let Some(parent) = chain.last() {
                openat(parent, *component, flags, Mode::empty())
            } else {
                openat(&self.root, *component, flags, Mode::empty())
            }
            .map_err(|error| map_errno(relative, error))?;
            chain.push(opened);
        }
        Ok(chain)
    }
}

impl FileSystemPort for OsFileSystem {
    fn read_declared(&self, path: &str) -> Result<Vec<u8>, PortError> {
        #[cfg(unix)]
        {
            self.read_declared_unix(path)
        }
        #[cfg(not(unix))]
        {
            validate_relative(path, true)?;
            Err(PortError::Io {
                path: path.into(),
                message: "safe command-scoped filesystem snapshots are unavailable on this platform until Phase 7".into(),
            })
        }
    }

    fn exists_declared(&self, path: &str) -> Result<bool, PortError> {
        #[cfg(unix)]
        {
            match self.open_chain(path) {
                Ok(_) => Ok(true),
                Err(PortError::Missing(_)) => Ok(false),
                Err(error) => Err(error),
            }
        }
        #[cfg(not(unix))]
        {
            validate_relative(path, true)?;
            Err(PortError::Io {
                path: path.into(),
                message: "safe command-scoped filesystem snapshots are unavailable on this platform until Phase 7".into(),
            })
        }
    }

    fn validate_snapshot(&self) -> Result<(), PortError> {
        #[cfg(unix)]
        {
            self.validate_root_namespace()
        }
        #[cfg(not(unix))]
        {
            Err(PortError::Io {
                path: ".".into(),
                message: "safe command-scoped filesystem snapshots are unavailable on this platform until Phase 7".into(),
            })
        }
    }

    fn observe_compatibility(&self) -> Result<CompatibilityObservation, PortError> {
        Ok(CompatibilityObservation {
            observed: true,
            legacy_artifact_present: self.exists_declared("harness.db")?,
            conversion_journal_present: self.exists_declared(".harness/recovery/v0-conversion")?,
            conversion_archive_present: self.exists_declared(".harness/legacy/v0-conversion")?,
        })
    }
}

impl OsFileSystem {
    #[cfg(unix)]
    fn read_declared_unix(&self, path: &str) -> Result<Vec<u8>, PortError> {
        self.read_declared_unix_with_hook(path, |_| {})
    }

    #[cfg(unix)]
    fn read_declared_unix_with_hook(
        &self,
        path: &str,
        mut checkpoint: impl FnMut(ReadCheckpoint),
    ) -> Result<Vec<u8>, PortError> {
        use rustix::fs::{fstat, openat, FileType, Mode, OFlags};

        let components: Vec<&str> = path.split('/').collect();
        let mut chain = self.open_chain(path)?;
        let mut pinned_stats = vec![self.root_stat];
        pinned_stats.extend(
            chain
                .iter()
                .map(|descriptor| fstat(descriptor).map_err(|error| map_errno(path, error)))
                .collect::<Result<Vec<_>, _>>()?,
        );
        let final_descriptor = chain.pop().expect("declared path has a final descriptor");
        let before = *pinned_stats
            .last()
            .expect("declared path has final metadata");
        if !FileType::from_raw_mode(before.st_mode).is_file() {
            return Err(PortError::Io {
                path: path.into(),
                message: "declared path is not a regular file".into(),
            });
        }
        let mut file = File::from(final_descriptor);
        let mut bytes = Vec::new();
        file.read_to_end(&mut bytes)
            .map_err(|error| map_io(path, error))?;
        checkpoint(ReadCheckpoint::AfterFirstRead);
        let after_first = fstat(&file).map_err(|error| map_errno(path, error))?;
        file.seek(SeekFrom::Start(0))
            .map_err(|error| map_io(path, error))?;
        let mut verification_bytes = Vec::new();
        file.read_to_end(&mut verification_bytes)
            .map_err(|error| map_io(path, error))?;
        checkpoint(ReadCheckpoint::AfterSecondRead);
        let after_second = fstat(&file).map_err(|error| map_errno(path, error))?;
        if !same_stat(&before, &after_first)
            || !same_stat(&before, &after_second)
            || after_second.st_size != bytes.len() as i64
            || hex_sha256(&bytes) != hex_sha256(&verification_bytes)
            || bytes != verification_bytes
        {
            return Err(PortError::Changed(path.into()));
        }

        // Reopen every namespace component through its still-pinned parent and
        // compare identity with the descriptor used for the read.
        for (index, component) in components.iter().enumerate() {
            let mut flags = OFlags::RDONLY | OFlags::CLOEXEC | OFlags::NOFOLLOW;
            if index + 1 < components.len() {
                flags |= OFlags::DIRECTORY;
            }
            let reopened = if index == 0 {
                openat(&self.root, *component, flags, Mode::empty())
            } else {
                openat(&chain[index - 1], *component, flags, Mode::empty())
            }
            .map_err(|error| map_errno(path, error))?;
            let reopened_stat = fstat(&reopened).map_err(|error| map_errno(path, error))?;
            let expected = pinned_stats[index + 1];
            if !same_stat(&reopened_stat, &expected) {
                return Err(PortError::Changed(path.into()));
            }
        }
        Ok(bytes)
    }

    #[cfg(unix)]
    fn validate_root_namespace(&self) -> Result<(), PortError> {
        use rustix::fs::{fstat, open, Mode, OFlags};

        let reopened = open(
            &self.root_path,
            OFlags::RDONLY | OFlags::DIRECTORY | OFlags::CLOEXEC | OFlags::NOFOLLOW,
            Mode::empty(),
        )
        .map_err(|_| PortError::Changed(".".into()))?;
        let current = fstat(&reopened).map_err(|error| map_errno(".", error))?;
        if !same_stat(&self.root_stat, &current) {
            return Err(PortError::Changed(".".into()));
        }
        Ok(())
    }
}

#[cfg(unix)]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum ReadCheckpoint {
    AfterFirstRead,
    AfterSecondRead,
}

#[cfg(unix)]
fn same_stat(left: &rustix::fs::Stat, right: &rustix::fs::Stat) -> bool {
    left.st_dev == right.st_dev
        && left.st_ino == right.st_ino
        && left.st_mode == right.st_mode
        && left.st_size == right.st_size
        && left.st_mtime == right.st_mtime
        && left.st_mtime_nsec == right.st_mtime_nsec
        && left.st_ctime == right.st_ctime
        && left.st_ctime_nsec == right.st_ctime_nsec
}

#[cfg(unix)]
fn map_io(path: &str, error: std::io::Error) -> PortError {
    if error.kind() == std::io::ErrorKind::NotFound {
        PortError::Missing(path.into())
    } else {
        PortError::Io {
            path: path.into(),
            message: error.kind().to_string(),
        }
    }
}

#[cfg(unix)]
fn map_errno(path: &str, error: rustix::io::Errno) -> PortError {
    if error == rustix::io::Errno::NOENT || error == rustix::io::Errno::NOTDIR {
        PortError::Missing(path.into())
    } else if error == rustix::io::Errno::LOOP {
        PortError::Link(path.into())
    } else {
        PortError::Io {
            path: path.into(),
            message: error.to_string(),
        }
    }
}

#[derive(Default)]
pub struct JsonManifestPort;

impl ManifestPort for JsonManifestPort {
    fn load(&self, filesystem: &dyn FileSystemPort) -> Result<Option<Manifest>, PortError> {
        let bytes = match filesystem.read_declared(".harness/manifest.json") {
            Ok(bytes) => bytes,
            Err(PortError::Missing(_)) => return Ok(None),
            Err(error) => return Err(error),
        };
        self.parse_bytes(&bytes).map(Some)
    }

    fn parse_bytes(&self, bytes: &[u8]) -> Result<Manifest, PortError> {
        let value = parse(bytes).map_err(PortError::ManifestInvalid)?;
        reject_forbidden_fields(&value, "$")?;
        reject_schema_nulls(&value)?;
        let manifest: Manifest = serde_json::from_value(value)
            .map_err(|error| PortError::ManifestInvalid(error.to_string()))?;
        validate_manifest_schema(&manifest)?;
        Ok(manifest)
    }
}

fn reject_schema_nulls(value: &serde_json::Value) -> Result<(), PortError> {
    if value
        .get("conversion_receipt")
        .is_some_and(serde_json::Value::is_null)
    {
        return Err(PortError::ManifestInvalid(
            "conversion_receipt must be an object when present".into(),
        ));
    }
    if let Some(roles) = value.get("roles").and_then(serde_json::Value::as_array) {
        for (index, role) in roles.iter().enumerate() {
            for field in ["template", "template_release", "base_sha256", "marker"] {
                if role.get(field).is_some_and(serde_json::Value::is_null) {
                    return Err(PortError::ManifestInvalid(format!(
                        "roles[{index}].{field} must be a string when present"
                    )));
                }
            }
        }
    }
    if value
        .get("conversion_receipt")
        .and_then(|receipt| receipt.get("plaintext_risk_acknowledged"))
        .is_some_and(serde_json::Value::is_null)
    {
        return Err(PortError::ManifestInvalid(
            "conversion_receipt.plaintext_risk_acknowledged must be boolean when present".into(),
        ));
    }
    Ok(())
}

fn validate_manifest_schema(manifest: &Manifest) -> Result<(), PortError> {
    if manifest.schema != MANIFEST_SCHEMA
        || manifest.payload.trust_domain != "repository-harness-core"
        || manifest.payload.role != "core-release"
        || manifest.payload.sequence == 0
        || !is_sha256(&manifest.payload.index_sha256)
        || manifest.roles.is_empty()
    {
        return Err(PortError::ManifestInvalid(
            "manifest top-level schema constraints are not satisfied".into(),
        ));
    }
    for role in &manifest.roles {
        if !is_lower_snake_schema(&role.role)
            || !is_lower_kebab_schema(&role.asset)
            || !is_sha256(&role.current_sha256)
            || role
                .base_sha256
                .as_deref()
                .is_some_and(|value| !is_sha256(value))
            || role
                .marker
                .as_deref()
                .is_some_and(|value| !is_lower_kebab_schema(value))
        {
            return Err(PortError::ManifestInvalid(
                "manifest role identifier or digest violates manifest-v1.schema.json".into(),
            ));
        }
    }
    if let Some(receipt) = &manifest.conversion_receipt {
        if receipt.schema != "repository-harness-conversion-receipt/v1"
            || !is_lower_kebab_schema(&receipt.conversion_id)
            || !is_sha256(&receipt.export_sha256)
            || !is_sha256(&receipt.standalone_backup_sha256)
            || !is_sha256(&receipt.archive_sha256)
            || !matches!(
                receipt.confidentiality_mode.as_str(),
                "encrypted-age-x25519" | "plaintext-explicit-override"
            )
        {
            return Err(PortError::ManifestInvalid(
                "conversion receipt violates manifest-v1.schema.json".into(),
            ));
        }
    }
    Ok(())
}

fn is_lower_snake_schema(value: &str) -> bool {
    value.as_bytes().first().is_some_and(u8::is_ascii_lowercase)
        && value
            .bytes()
            .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'_')
}

fn is_lower_kebab_schema(value: &str) -> bool {
    value
        .as_bytes()
        .first()
        .is_some_and(u8::is_ascii_alphanumeric)
        && value
            .bytes()
            .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'-')
}

fn is_sha256(value: &str) -> bool {
    value.len() == 64
        && value
            .bytes()
            .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
}

fn reject_forbidden_fields(value: &serde_json::Value, path: &str) -> Result<(), PortError> {
    const FORBIDDEN: [&str; 29] = [
        "task",
        "tasks",
        "run",
        "runs",
        "prompt",
        "prompts",
        "result",
        "results",
        "user",
        "users",
        "trace",
        "traces",
        "raw_command_output",
        "telemetry",
        "score",
        "scores",
        "scheduler",
        "schedule",
        "queue",
        "intake",
        "story",
        "backlog",
        "decision",
        "database",
        "sqlite",
        "changeset",
        "rawcommandoutput",
        "raw-command-output",
        "raw command output",
    ];
    match value {
        serde_json::Value::Object(values) => {
            for (key, child) in values {
                let normalized = key.to_lowercase().replace('-', "_");
                if FORBIDDEN.contains(&normalized.as_str()) {
                    return Err(PortError::ManifestInvalid(format!(
                        "{path}: forbidden operational field {key}"
                    )));
                }
                reject_forbidden_fields(child, &format!("{path}.{key}"))?;
            }
        }
        serde_json::Value::Array(values) => {
            for (index, child) in values.iter().enumerate() {
                reject_forbidden_fields(child, &format!("{path}[{index}]"))?;
            }
        }
        _ => {}
    }
    Ok(())
}

#[derive(Default)]
pub struct UnavailableReleasePort;

impl ReleasePort for UnavailableReleasePort {
    fn load(&self) -> Result<ReleaseMaterial, PortError> {
        Err(PortError::ReleaseUnavailable(
            "Phase 2 has no promoted payload; inject an authenticated release port for preview tests"
                .into(),
        ))
    }
}

#[derive(Default)]
pub struct UnavailableTrustPort;

impl TrustPort for UnavailableTrustPort {
    fn load(&self) -> Result<ReleaseTrustInput, PortError> {
        Err(PortError::ReleaseUnavailable(
            "Phase 2 has no independently provisioned production trust state".into(),
        ))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[cfg(unix)]
    #[test]
    fn os_adapter_rejects_symlinks() {
        use std::os::unix::fs::symlink;

        let temporary = tempfile::tempdir().unwrap();
        fs::write(temporary.path().join("outside"), b"secret").unwrap();
        symlink(
            temporary.path().join("outside"),
            temporary.path().join("linked"),
        )
        .unwrap();
        let filesystem = OsFileSystem::new(temporary.path()).unwrap();
        assert!(matches!(
            filesystem.read_declared("linked"),
            Err(PortError::Link(_))
        ));
    }

    #[cfg(unix)]
    #[test]
    fn command_snapshot_pins_root_and_rejects_root_namespace_replacement() {
        let temporary = tempfile::tempdir().unwrap();
        let root = temporary.path().join("repository");
        fs::create_dir(&root).unwrap();
        fs::write(root.join("declared.md"), b"old tree").unwrap();
        let filesystem = OsFileSystem::new(&root).unwrap();

        fs::rename(&root, temporary.path().join("repository-old")).unwrap();
        fs::create_dir(&root).unwrap();
        fs::write(root.join("declared.md"), b"new tree").unwrap();

        assert_eq!(
            filesystem.read_declared("declared.md").unwrap(),
            b"old tree"
        );
        assert!(matches!(
            filesystem.validate_snapshot(),
            Err(PortError::Changed(path)) if path == "."
        ));
    }

    #[cfg(unix)]
    #[test]
    fn synchronized_ancestor_and_final_swaps_fail_closed() {
        let temporary = tempfile::tempdir().unwrap();
        let docs = temporary.path().join("docs");
        fs::create_dir(&docs).unwrap();
        fs::write(docs.join("declared.md"), b"same bytes").unwrap();
        let filesystem = OsFileSystem::new(temporary.path()).unwrap();

        let ancestor_result =
            filesystem.read_declared_unix_with_hook("docs/declared.md", |checkpoint| {
                if checkpoint == ReadCheckpoint::AfterSecondRead {
                    fs::rename(&docs, temporary.path().join("docs-old")).unwrap();
                    fs::create_dir(&docs).unwrap();
                    fs::write(docs.join("declared.md"), b"same bytes").unwrap();
                }
            });
        assert!(matches!(ancestor_result, Err(PortError::Changed(_))));

        let final_path = docs.join("declared.md");
        let final_result =
            filesystem.read_declared_unix_with_hook("docs/declared.md", |checkpoint| {
                if checkpoint == ReadCheckpoint::AfterSecondRead {
                    fs::rename(&final_path, docs.join("declared-old.md")).unwrap();
                    fs::write(&final_path, b"same bytes").unwrap();
                }
            });
        assert!(matches!(final_result, Err(PortError::Changed(_))));
    }

    #[cfg(unix)]
    #[test]
    fn same_size_in_place_rewrite_between_exact_reads_fails_closed() {
        let temporary = tempfile::tempdir().unwrap();
        let path = temporary.path().join("declared.md");
        fs::write(&path, b"first-copy").unwrap();
        let filesystem = OsFileSystem::new(temporary.path()).unwrap();
        let result = filesystem.read_declared_unix_with_hook("declared.md", |checkpoint| {
            if checkpoint == ReadCheckpoint::AfterFirstRead {
                fs::write(&path, b"other-copy").unwrap();
            }
        });
        assert!(matches!(result, Err(PortError::Changed(_))));
    }
}
