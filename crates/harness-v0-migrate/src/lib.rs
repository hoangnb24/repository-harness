//! Isolated archive-only Repository Harness V0 bridge.
//!
//! SQLite, WAL recovery, and V0 recognition remain in this temporary crate.
//! The bridge never creates or mutates V1 state; dependency direction is used
//! only to share the permanent core's frozen safe-path validator.

pub mod archive;
pub mod capture;
pub mod command_spec;
pub mod export;
pub mod interface;
mod secure_fs;
mod strict_json;

use std::path::PathBuf;

use capture::{hex_sha256, source_digest, Capture};
use interface::{Command, SourceOptions};
use secure_fs::SecureRoot;
use serde::Serialize;

pub type Result<T> = std::result::Result<T, BridgeError>;

#[derive(Debug, thiserror::Error)]
pub enum BridgeError {
    #[error("usage: {0}")]
    Usage(String),
    #[error("unsupported V0 input: {0}")]
    Unsupported(String),
    #[error("archive or capture conflict: {0}")]
    Conflict(String),
    #[error("invalid archive or repository state: {0}")]
    Invalid(String),
    #[error("I/O: {0}")]
    Io(#[from] std::io::Error),
    #[error("SQLite: {0}")]
    Sqlite(#[from] rusqlite::Error),
    #[error("JSON: {0}")]
    Json(#[from] serde_json::Error),
    #[error("age encryption: {0}")]
    AgeEncrypt(#[from] age::EncryptError),
    #[error("age decryption: {0}")]
    AgeDecrypt(#[from] age::DecryptError),
    #[cfg(unix)]
    #[error("descriptor operation: {0}")]
    Errno(#[from] rustix::io::Errno),
}

impl BridgeError {
    pub fn exit_code(&self) -> u8 {
        match self {
            Self::Usage(_) => 64,
            Self::Unsupported(_) => 5,
            Self::Conflict(_) => 4,
            Self::Invalid(_) => 3,
            Self::Io(_) => 74,
            Self::Sqlite(_) | Self::Json(_) | Self::AgeEncrypt(_) | Self::AgeDecrypt(_) => 70,
            #[cfg(unix)]
            Self::Errno(_) => 74,
        }
    }
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
pub struct Report {
    pub schema: String,
    pub command: String,
    pub outcome: String,
    pub mutation: String,
    pub source: String,
    pub source_schema: Option<u32>,
    pub source_sha256: Option<String>,
    pub export_sha256: Option<String>,
    pub archive_id: Option<String>,
    pub archive_manifest_path: Option<String>,
    pub archive_manifest_sha256: Option<String>,
    pub archive_payload_sha256: Option<String>,
    pub confidentiality_mode: Option<String>,
    pub unknown_unowned: Vec<String>,
    pub notices: Vec<String>,
}

impl Report {
    fn empty(command: &str) -> Self {
        Self {
            schema: "repository-harness-v0-bridge-output/v1".into(),
            command: command.into(),
            outcome: "ready".into(),
            mutation: "none".into(),
            source: "not-inspected".into(),
            source_schema: None,
            source_sha256: None,
            export_sha256: None,
            archive_id: None,
            archive_manifest_path: None,
            archive_manifest_sha256: None,
            archive_payload_sha256: None,
            confidentiality_mode: None,
            unknown_unowned: Vec::new(),
            notices: Vec::new(),
        }
    }
}

pub struct Bridge {
    root: PathBuf,
}

impl Bridge {
    pub fn new(root: impl Into<PathBuf>) -> Self {
        Self { root: root.into() }
    }

    pub fn execute(&self, command: &Command) -> Result<Report> {
        match command {
            Command::Help => Err(BridgeError::Usage(
                "help is rendered by the interface".into(),
            )),
            Command::Version { .. } => Ok(version_report()),
            Command::Inspect { source, .. } => self.inspect(source),
            Command::Export { output, source } => self.export(output, source),
            Command::Archive { archive } => self.archive(archive),
        }
    }

    fn inspect(&self, source: &SourceOptions) -> Result<Report> {
        let root = SecureRoot::open(&self.root)?;
        if let Some(manifest_path) = &source.archive_manifest {
            let (manifest, export) = archive::verify_manifest(
                &root,
                manifest_path,
                source.age_identity_file.as_deref(),
            )?;
            let mut report = Report::empty("inspect");
            report.source = "preserved-archive".into();
            report.source_schema = Some(manifest.source_schema);
            report.source_sha256 = Some(manifest.source_sha256);
            report.export_sha256 = Some(manifest.export_sha256);
            report.archive_id = Some(manifest.archive_id);
            report.archive_manifest_path = Some(manifest_path.clone());
            report.archive_manifest_sha256 = Some(hex_sha256(&root.read(manifest_path)?));
            report.archive_payload_sha256 = Some(manifest.payload_sha256);
            report.confidentiality_mode = Some(manifest.confidentiality_mode);
            report.notices.push(if export.is_some() {
                "archive payload and every inner member passed digest verification".into()
            } else {
                "encrypted archive manifest and ciphertext passed outer verification; provide --age-identity-file for inner-member verification".into()
            });
            return Ok(report);
        }
        let capture = capture::capture_pinned(&root)?;
        let mut report = capture_report("inspect", &capture);
        report.notices.push(
            "live V0 source opened read-only; DB/WAL/SHM and recognized inputs passed same-handle pre/copy/post checks"
                .into(),
        );
        Ok(report)
    }

    fn export(&self, output: &str, source: &SourceOptions) -> Result<Report> {
        let root = SecureRoot::open(&self.root)?;
        root.preflight_new_output(output)?;
        let (bytes, mut report) = if let Some(manifest_path) = &source.archive_manifest {
            let (manifest, export) = archive::verify_manifest(
                &root,
                manifest_path,
                source.age_identity_file.as_deref(),
            )?;
            let export = export.ok_or_else(|| {
                BridgeError::Usage(
                    "export from an encrypted archive requires --age-identity-file".into(),
                )
            })?;
            let mut report = Report::empty("export");
            report.source = "preserved-archive".into();
            report.source_schema = Some(manifest.source_schema);
            report.source_sha256 = Some(manifest.source_sha256);
            report.archive_id = Some(manifest.archive_id);
            report.archive_manifest_path = Some(manifest_path.clone());
            report.archive_payload_sha256 = Some(manifest.payload_sha256);
            report.confidentiality_mode = Some(manifest.confidentiality_mode);
            (export, report)
        } else {
            let capture = capture::capture_pinned(&root)?;
            let (_, bytes, _) = export::build(&capture)?;
            (bytes, capture_report("export", &capture))
        };
        root.write_new(output, &bytes)?;
        report.outcome = "exported".into();
        report.mutation = "new-export-only".into();
        report.export_sha256 = Some(hex_sha256(&bytes));
        report
            .notices
            .push(format!("neutral read-only export created at {output}"));
        Ok(report)
    }

    fn archive(&self, options: &interface::ArchiveOptions) -> Result<Report> {
        let root = SecureRoot::open(&self.root)?;
        let capture = capture::capture_pinned(&root)?;
        let (_, export_bytes, _) = export::build(&capture)?;
        let evidence = archive::create(&root, &capture, &export_bytes, options)?;
        let mut report = capture_report("archive", &capture);
        report.outcome = "archived".into();
        report.mutation = "new-append-only-archive".into();
        report.export_sha256 = Some(evidence.export_sha256);
        report.archive_id = Some(evidence.archive_id);
        report.archive_manifest_path = Some(evidence.manifest_path);
        report.archive_manifest_sha256 = Some(evidence.manifest_sha256);
        report.archive_payload_sha256 = Some(evidence.payload_sha256);
        report.confidentiality_mode = Some(evidence.confidentiality_mode);
        report.notices.push(
            "unique staging was verified and atomically published with no-replace; no V1 target file was mutated"
                .into(),
        );
        Ok(report)
    }
}

fn capture_report(command: &str, capture: &Capture) -> Report {
    let mut report = Report::empty(command);
    report.source = "live-frozen-v0".into();
    report.source_schema = Some(capture.schema_version);
    report.source_sha256 = Some(source_digest(capture));
    report.unknown_unowned = capture.unknown_metadata.clone();
    report
}

fn version_report() -> Report {
    let mut report = Report::empty("version");
    report.notices = vec![
        format!(
            "harness-v0-migrate {}; archive-only commands inspect/export/archive/version; V0 schema 1..=13",
            command_spec::BRIDGE_VERSION
        ),
        "compatibility window 2027-01-01T00:00:00Z through 2027-12-31T23:59:59Z; live-unpromoted Phase 4 artifact"
            .into(),
    ];
    report
}

#[cfg(test)]
mod exit_tests {
    use super::*;

    #[test]
    fn error_classes_have_exhaustive_exit_mappings() {
        assert_eq!(BridgeError::Usage("fixture".into()).exit_code(), 64);
        assert_eq!(BridgeError::Unsupported("fixture".into()).exit_code(), 5);
        assert_eq!(BridgeError::Conflict("fixture".into()).exit_code(), 4);
        assert_eq!(BridgeError::Invalid("fixture".into()).exit_code(), 3);
        assert_eq!(
            BridgeError::Io(std::io::Error::other("fixture")).exit_code(),
            74
        );
        assert_eq!(
            BridgeError::Sqlite(rusqlite::Error::InvalidQuery).exit_code(),
            70
        );
        #[cfg(unix)]
        assert_eq!(BridgeError::Errno(rustix::io::Errno::IO).exit_code(), 74);
    }
}
