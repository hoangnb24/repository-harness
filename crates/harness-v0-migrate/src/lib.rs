//! Isolated Repository Harness V0 conversion bridge.
//!
//! V0 SQLite, changeset, capture, archive, and conversion semantics live here;
//! dependency direction is bridge -> pure V1 core and never the reverse.

pub mod archive;
pub mod capture;
pub mod command_spec;
pub mod export;
pub mod interface;
pub mod journal;
mod strict_json;

use std::fs::{File, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};

use capture::{hex_sha256, source_digest, Capture};
use harness_core::domain::{
    Activation, Compatibility, ConversionReceipt, Manifest, ManifestRepositoryMode, Origin,
    Ownership, PayloadIdentity, Role, UpdatePolicy, MANIFEST_SCHEMA,
};
use harness_core::infrastructure::JsonManifestPort;
use harness_core::ports::ManifestPort;
use interface::{ArchiveOptions, Command};
use journal::{Journal, JournalState};
use serde::Serialize;

pub type Result<T> = std::result::Result<T, BridgeError>;

#[derive(Debug, thiserror::Error)]
pub enum BridgeError {
    #[error("usage: {0}")]
    Usage(String),
    #[error("unsupported V0 input: {0}")]
    Unsupported(String),
    #[error("conversion evidence conflict: {0}")]
    Conflict(String),
    #[error("invalid repository state: {0}")]
    Invalid(String),
    #[error("injected kill point: {0}")]
    KillPoint(String),
    #[error("I/O: {0}")]
    Io(#[from] std::io::Error),
    #[error("SQLite: {0}")]
    Sqlite(#[from] rusqlite::Error),
    #[error("JSON: {0}")]
    Json(#[from] serde_json::Error),
    #[error("age encryption: {0}")]
    Age(#[from] age::EncryptError),
    #[cfg(unix)]
    #[error("descriptor operation: {0}")]
    Errno(#[from] rustix::io::Errno),
    #[error("V1 manifest: {0}")]
    Manifest(String),
}

impl BridgeError {
    pub fn exit_code(&self) -> u8 {
        match self {
            Self::Usage(_) => 64,
            Self::Unsupported(_) => 5,
            Self::Conflict(_) | Self::KillPoint(_) => 4,
            Self::Invalid(_) | Self::Manifest(_) => 3,
            Self::Io(_) | Self::Sqlite(_) | Self::Json(_) | Self::Age(_) => 70,
            #[cfg(unix)]
            Self::Errno(_) => 70,
        }
    }
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
pub struct Report {
    pub schema: String,
    pub command: String,
    pub outcome: String,
    pub mutation: String,
    pub repository_mode: String,
    pub conversion_id: Option<String>,
    pub source_schema: Option<u32>,
    pub source_sha256: Option<String>,
    pub export_sha256: Option<String>,
    pub archive_sha256: Option<String>,
    pub preview_sha256: Option<String>,
    pub journal_state: Option<String>,
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
            repository_mode: "v0-legacy".into(),
            conversion_id: None,
            source_schema: None,
            source_sha256: None,
            export_sha256: None,
            archive_sha256: None,
            preview_sha256: None,
            journal_state: None,
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
            Command::Inspect { .. } => self.inspect(),
            Command::Preview { .. } => self.preview(),
            Command::Export { output, archive } => self.export(output, archive),
            Command::Apply {
                accepted_preview_sha256,
                archive,
            } => self.apply(accepted_preview_sha256, archive),
            Command::Resume { conversion_id } => self.resume(conversion_id),
            Command::Rollback { conversion_id } => self.rollback(conversion_id),
        }
    }

    fn inspect(&self) -> Result<Report> {
        let capture = capture::capture(&self.root)?;
        let mut report = self.capture_report("inspect", &capture);
        report.notices.push(
            "source opened read-only; DB/WAL/SHM and recognized inputs passed same-handle pre/copy/post checks"
                .into(),
        );
        Ok(report)
    }

    fn preview(&self) -> Result<Report> {
        let capture = capture::capture(&self.root)?;
        let preview = preview_digest(&self.root, &capture)?;
        let conversion_id = conversion_id(&capture);
        let mut report = self.capture_report("preview", &capture);
        report.conversion_id = Some(conversion_id);
        report.preview_sha256 = Some(preview);
        report.notices.push(
            "operation 1: atomically create .harness/manifest.json containing the completed receipt last"
                .into(),
        );
        Ok(report)
    }

    fn export(&self, output: &str, options: &ArchiveOptions) -> Result<Report> {
        let capture = capture::capture(&self.root)?;
        let conversion_id = conversion_id(&capture);
        let preview = preview_digest(&self.root, &capture)?;
        let (_, export_bytes, export_sha256) = export::build(&capture)?;
        let output_path = capture::safe_output_path(&self.root, output)?;
        write_new(&output_path, &export_bytes)?;
        let evidence =
            archive::create(&self.root, &conversion_id, &capture, &export_bytes, options)?;
        let mut journal = Journal::new(conversion_id.clone(), source_digest(&capture), preview);
        journal.state = JournalState::Archived;
        journal.export_sha256 = Some(export_sha256.clone());
        journal.standalone_backup_sha256 = Some(capture.standalone_backup_sha256.clone());
        bind_archive(&mut journal, &evidence);
        journal::save(&self.root, &journal)?;
        let mut report = self.capture_report("export", &capture);
        report.mutation = "new-export-and-archive-only".into();
        report.conversion_id = Some(conversion_id);
        report.export_sha256 = Some(export_sha256);
        report.archive_sha256 = Some(evidence.archive_sha256);
        report.journal_state = Some(state_name(journal.state).into());
        Ok(report)
    }

    fn apply(&self, accepted: &str, options: &ArchiveOptions) -> Result<Report> {
        let capture = capture::capture(&self.root)?;
        let conversion_id = conversion_id(&capture);
        if let Some(report) = self.completed_idempotent(&conversion_id, &capture)? {
            return Ok(report);
        }
        let preview = preview_digest(&self.root, &capture)?;
        if accepted != preview {
            return Err(BridgeError::Conflict(
                "accepted preview digest does not match current compatibility/input plan".into(),
            ));
        }
        let journal_path = journal::path(&self.root, &conversion_id);
        if journal_path.exists() {
            let existing = journal::load(&self.root, &conversion_id)?;
            ensure_archive_decision(&existing, options)?;
            return self.advance(existing, capture, options.clone());
        }
        reject_preexisting_manifest(&self.root)?;
        let mut journal = Journal::new(conversion_id, source_digest(&capture), preview);
        bind_archive_decision(&mut journal, options);
        journal::save(&self.root, &journal)?;
        kill("detection")?;
        self.advance(journal, capture, options.clone())
    }

    fn resume(&self, requested_conversion_id: &str) -> Result<Report> {
        let journal = journal::load(&self.root, requested_conversion_id)?;
        if journal.rolled_back {
            return Err(BridgeError::Conflict(
                "journal was rolled back; a new explicit apply is required".into(),
            ));
        }
        let capture = capture::capture(&self.root)?;
        if source_digest(&capture) != journal.source_sha256
            || conversion_id(&capture) != journal.conversion_id
        {
            return Err(BridgeError::Conflict(
                "resume source identity differs from journal-bound input".into(),
            ));
        }
        let options = archive_options_from_journal(&journal)?;
        self.advance(journal, capture, options)
    }

    fn advance(
        &self,
        mut journal: Journal,
        capture: Capture,
        options: ArchiveOptions,
    ) -> Result<Report> {
        if journal.state == JournalState::Completed {
            return self.completed_report(&journal, &capture, "resume");
        }
        if journal.state == JournalState::RecoveryRequired {
            return Err(BridgeError::Conflict(
                "journal is recovery-required and cannot resume automatically".into(),
            ));
        }
        if journal.state < JournalState::Inspected {
            journal.state = JournalState::Inspected;
            journal::save(&self.root, &journal)?;
        }
        let (_, export_bytes, export_sha256) = export::build(&capture)?;
        if let Some(expected) = &journal.export_sha256 {
            if expected != &export_sha256 {
                return Err(BridgeError::Conflict(
                    "neutral export digest changed".into(),
                ));
            }
        } else {
            journal.export_sha256 = Some(export_sha256.clone());
            journal.standalone_backup_sha256 = Some(capture.standalone_backup_sha256.clone());
            journal.state = JournalState::Exported;
            journal::save(&self.root, &journal)?;
            kill("export")?;
        }
        if journal.state < JournalState::Archived {
            let evidence = archive::create(
                &self.root,
                &journal.conversion_id,
                &capture,
                &export_bytes,
                &options,
            )?;
            bind_archive(&mut journal, &evidence);
            journal.state = JournalState::Archived;
            journal::save(&self.root, &journal)?;
            kill("archive")?;
        } else {
            let evidence = archive::create(
                &self.root,
                &journal.conversion_id,
                &capture,
                &export_bytes,
                &options,
            )?;
            if journal.archive_sha256.as_deref() != Some(&evidence.archive_sha256) {
                return Err(BridgeError::Conflict(
                    "archive digest differs from journal".into(),
                ));
            }
        }

        let manifest_bytes = build_manifest(&self.root, &capture, &journal)?;
        let manifest_sha256 = hex_sha256(&manifest_bytes);
        if let Some(expected) = &journal.manifest_after_sha256 {
            if expected != &manifest_sha256 {
                return Err(BridgeError::Conflict(
                    "candidate manifest digest changed".into(),
                ));
            }
        } else {
            journal.manifest_before_sha256 = manifest_digest(&self.root)?;
            if journal.manifest_before_sha256.is_some() {
                return Err(BridgeError::Invalid(
                    "V0 plus a V1 manifest without this completed receipt is mixed-invalid".into(),
                ));
            }
            journal.manifest_after_sha256 = Some(manifest_sha256.clone());
            journal.state = JournalState::Prepared;
            journal::save(&self.root, &journal)?;
        }
        validate_candidate(&self.root, &manifest_bytes)?;
        let recovery = journal::path(&self.root, &journal.conversion_id)
            .parent()
            .expect("journal parent")
            .to_path_buf();
        let receipt_bytes = serde_json::to_vec(
            &serde_json::from_slice::<Manifest>(&manifest_bytes)?
                .conversion_receipt
                .expect("candidate has receipt"),
        )?;
        write_exact_or_new(&recovery.join("receipt.staged.json"), &receipt_bytes)?;
        kill("temporary-receipt")?;
        let temporary_manifest = recovery.join("manifest.staged.json");
        write_exact_or_new(&temporary_manifest, &manifest_bytes)?;
        kill("temporary-manifest")?;

        journal.state = JournalState::Applying;
        journal::save(&self.root, &journal)?;
        let manifest_path = self.root.join(".harness/manifest.json");
        if manifest_path.exists() {
            let live = std::fs::read(&manifest_path)?;
            if hex_sha256(&live) != manifest_sha256 {
                journal.state = JournalState::RecoveryRequired;
                journal::save(&self.root, &journal)?;
                return Err(BridgeError::Conflict(
                    "target manifest is not the journal-owned post-image".into(),
                ));
            }
        } else {
            rename_no_replace(&temporary_manifest, &manifest_path)?;
            File::open(self.root.join(".harness"))?.sync_all()?;
        }
        kill("operation-1")?;
        kill("atomic-commit")?;
        journal.state = JournalState::Committed;
        journal::save(&self.root, &journal)?;
        validate_live_manifest(&self.root, &journal)?;
        journal.state = JournalState::Completed;
        journal::save(&self.root, &journal)?;
        self.completed_report(&journal, &capture, "apply")
    }

    fn rollback(&self, conversion_id: &str) -> Result<Report> {
        let mut journal = journal::load(&self.root, conversion_id)?;
        if journal.state == JournalState::RecoveryRequired {
            return Err(BridgeError::Conflict(
                "journal is already recovery-required; human selection is required".into(),
            ));
        }
        let manifest_path = self.root.join(".harness/manifest.json");
        if let Some(expected) = &journal.manifest_after_sha256 {
            if manifest_path.exists() {
                let actual = hex_sha256(&std::fs::read(&manifest_path)?);
                if &actual != expected {
                    journal.state = JournalState::RecoveryRequired;
                    journal::save(&self.root, &journal)?;
                    return Err(BridgeError::Conflict(
                        "target edit refusal: live manifest differs from journal-owned post-image"
                            .into(),
                    ));
                }
                std::fs::remove_file(&manifest_path)?;
                File::open(self.root.join(".harness"))?.sync_all()?;
            }
        }
        journal.state = JournalState::Prepared;
        journal.rolled_back = true;
        journal::save(&self.root, &journal)?;
        let capture = capture::capture(&self.root)?;
        let mut report = self.capture_report("rollback", &capture);
        report.outcome = "rolled-back".into();
        report.mutation = "matching-journal-owned-post-images".into();
        report.conversion_id = Some(conversion_id.into());
        report.archive_sha256 = journal.archive_sha256;
        report.journal_state = Some(state_name(journal.state).into());
        Ok(report)
    }

    fn completed_idempotent(
        &self,
        conversion_id: &str,
        capture: &Capture,
    ) -> Result<Option<Report>> {
        let path = journal::path(&self.root, conversion_id);
        if !path.exists() {
            return Ok(None);
        }
        let journal = journal::load(&self.root, conversion_id)?;
        if journal.state == JournalState::Completed {
            validate_live_manifest(&self.root, &journal)?;
            return self.completed_report(&journal, capture, "apply").map(Some);
        }
        Ok(None)
    }

    fn completed_report(
        &self,
        journal: &Journal,
        capture: &Capture,
        command: &str,
    ) -> Result<Report> {
        let mut report = self.capture_report(command, capture);
        report.outcome = "completed".into();
        report.mutation = if command == "apply" {
            "journal-owned-conversion"
        } else {
            "remaining-journal-operations"
        }
        .into();
        report.repository_mode = "converted-v1-with-archive".into();
        report.conversion_id = Some(journal.conversion_id.clone());
        report.export_sha256 = journal.export_sha256.clone();
        report.archive_sha256 = journal.archive_sha256.clone();
        report.preview_sha256 = Some(journal.preview_sha256.clone());
        report.journal_state = Some(state_name(journal.state).into());
        Ok(report)
    }

    fn capture_report(&self, command: &str, capture: &Capture) -> Report {
        let mut report = Report::empty(command);
        report.source_schema = Some(capture.schema_version);
        report.source_sha256 = Some(source_digest(capture));
        report.unknown_unowned = capture.unknown_metadata.clone();
        report
    }
}

fn version_report() -> Report {
    let mut report = Report::empty("version");
    report.repository_mode = "not-inspected".into();
    report.notices = vec![
        format!(
            "harness-v0-migrate {}; supports V0 schema 1..=13 and frozen changeset grammar v1/v2",
            command_spec::BRIDGE_VERSION
        ),
        "compatibility window 2027-01-01T00:00:00Z through 2027-12-31T23:59:59Z; live-unpromoted Phase 4 artifact"
            .into(),
    ];
    report
}

fn conversion_id(capture: &Capture) -> String {
    format!("v0-{}", &source_digest(capture)[..24])
}

fn preview_digest(root: &Path, capture: &Capture) -> Result<String> {
    #[derive(Serialize)]
    struct Preview<'a> {
        schema: &'static str,
        source_schema: u32,
        source_sha256: String,
        standalone_backup_sha256: &'a str,
        manifest_before_sha256: Option<String>,
        operations: [PreviewOperation; 1],
    }
    #[derive(Serialize)]
    struct PreviewOperation {
        operation_id: &'static str,
        kind: &'static str,
        path: &'static str,
        disposition: &'static str,
    }
    let value = Preview {
        schema: "repository-harness-v0-conversion-preview/v1",
        source_schema: capture.schema_version,
        source_sha256: source_digest(capture),
        standalone_backup_sha256: &capture.standalone_backup_sha256,
        manifest_before_sha256: manifest_digest(root)?,
        operations: [PreviewOperation {
            operation_id: "commit-manifest-receipt-last",
            kind: "create",
            path: ".harness/manifest.json",
            disposition: "managed-v1",
        }],
    };
    Ok(hex_sha256(&serde_json::to_vec(&value)?))
}

fn build_manifest(root: &Path, _capture: &Capture, journal: &Journal) -> Result<Vec<u8>> {
    let candidates = [
        ("agent_map", "agent-map", "AGENTS.md"),
        ("repository_readme", "repository-readme", "README.md"),
        ("architecture", "architecture-map", "docs/ARCHITECTURE.md"),
    ];
    let mut roles = Vec::new();
    for (role_id, asset, path) in candidates {
        let full = root.join(path);
        if full.is_file() {
            let digest = hex_sha256(&std::fs::read(full)?);
            roles.push(Role {
                role: role_id.into(),
                asset: asset.into(),
                activation: Activation::Active,
                ownership: Ownership::TargetOwned,
                origin: Origin::V0Adopted,
                required: role_id == "agent_map",
                path: path.into(),
                template: None,
                template_release: None,
                base_sha256: None,
                current_sha256: digest,
                marker: None,
                update_policy: UpdatePolicy::NeverAutoPatch,
                unresolved_markers: Vec::new(),
            });
        }
    }
    if roles.is_empty() {
        return Err(BridgeError::Invalid(
            "conversion needs at least one useful existing repository document to adopt".into(),
        ));
    }
    let receipt =
        ConversionReceipt {
            schema: "repository-harness-conversion-receipt/v1".into(),
            conversion_id: journal.conversion_id.clone(),
            bridge_release: command_spec::BRIDGE_VERSION.into(),
            archive_path: journal.archive_path.clone().ok_or_else(|| {
                BridgeError::Invalid("archive path is absent from journal".into())
            })?,
            export_sha256: journal.export_sha256.clone().ok_or_else(|| {
                BridgeError::Invalid("export digest is absent from journal".into())
            })?,
            standalone_backup_sha256: journal.standalone_backup_sha256.clone().ok_or_else(
                || BridgeError::Invalid("snapshot digest is absent from journal".into()),
            )?,
            archive_sha256: journal.archive_sha256.clone().ok_or_else(|| {
                BridgeError::Invalid("archive digest is absent from journal".into())
            })?,
            confidentiality_mode: journal.confidentiality_mode.clone().ok_or_else(|| {
                BridgeError::Invalid("archive mode is absent from journal".into())
            })?,
            recipient_fingerprints: journal.recipient_fingerprints.clone(),
            plaintext_risk_acknowledged: journal.plaintext_risk_acknowledged,
        };
    let manifest = Manifest {
        schema: MANIFEST_SCHEMA.into(),
        repository_mode: ManifestRepositoryMode::ConvertedV1WithArchive,
        compatibility: Compatibility {
            cli_min: "1.0.0".into(),
            cli_max: "1.0.0".into(),
            template_release_min: "1.0.0".into(),
            template_release_max: "1.0.0".into(),
        },
        payload: PayloadIdentity::unbound(),
        roles,
        conversion_receipt: Some(receipt),
    };
    let mut bytes = serde_json::to_vec(&manifest)?;
    bytes.push(b'\n');
    Ok(bytes)
}

fn validate_candidate(root: &Path, bytes: &[u8]) -> Result<()> {
    let port = JsonManifestPort;
    let manifest = port
        .parse_bytes(bytes)
        .map_err(|error| BridgeError::Manifest(error.to_string()))?;
    if manifest.repository_mode != ManifestRepositoryMode::ConvertedV1WithArchive
        || manifest.conversion_receipt.is_none()
    {
        return Err(BridgeError::Manifest(
            "candidate is not converted-v1-with-archive".into(),
        ));
    }
    for role in manifest.roles {
        let path = root.join(&role.path);
        if !path.is_file() || hex_sha256(&std::fs::read(path)?) != role.current_sha256 {
            return Err(BridgeError::Conflict(format!(
                "V1 structural audit found target drift at {}",
                role.path
            )));
        }
        if role.ownership != Ownership::TargetOwned
            || role.update_policy != UpdatePolicy::NeverAutoPatch
        {
            return Err(BridgeError::Manifest(
                "converted existing documents must stay target-owned/never-auto-patch".into(),
            ));
        }
    }
    Ok(())
}

fn validate_live_manifest(root: &Path, journal: &Journal) -> Result<()> {
    let bytes = std::fs::read(root.join(".harness/manifest.json"))?;
    if journal.manifest_after_sha256.as_deref() != Some(&hex_sha256(&bytes)) {
        return Err(BridgeError::Conflict(
            "committed manifest differs from journal-owned post-image".into(),
        ));
    }
    validate_candidate(root, &bytes)
}

fn reject_preexisting_manifest(root: &Path) -> Result<()> {
    if root.join(".harness/manifest.json").exists() {
        return Err(BridgeError::Invalid(
            "V0 artifacts plus a V1 manifest without a completed matching receipt are mixed-invalid"
                .into(),
        ));
    }
    Ok(())
}

fn manifest_digest(root: &Path) -> Result<Option<String>> {
    let path = root.join(".harness/manifest.json");
    if path.exists() {
        Ok(Some(hex_sha256(&std::fs::read(path)?)))
    } else {
        Ok(None)
    }
}

fn bind_archive(journal: &mut Journal, evidence: &archive::ArchiveEvidence) {
    journal.archive_sha256 = Some(evidence.archive_sha256.clone());
    journal.archive_path = Some(evidence.path.clone());
    journal.confidentiality_mode = Some(evidence.confidentiality_mode.clone());
    journal.recipient_fingerprints = evidence.recipient_fingerprints.clone();
    journal.plaintext_risk_acknowledged = evidence.plaintext_risk_acknowledged;
}

fn bind_archive_decision(journal: &mut Journal, options: &ArchiveOptions) {
    if options.plaintext {
        journal.confidentiality_mode = Some("plaintext-explicit-override".into());
        journal.plaintext_risk_acknowledged = Some(true);
        journal.recipient_fingerprints.clear();
    } else {
        journal.confidentiality_mode = Some("encrypted-age-x25519".into());
        journal.plaintext_risk_acknowledged = None;
        journal.recipient_fingerprints = options.age_recipient.iter().cloned().collect();
    }
}

fn ensure_archive_decision(journal: &Journal, options: &ArchiveOptions) -> Result<()> {
    if journal.confidentiality_mode.is_none() {
        return Ok(());
    }
    let expected = if options.plaintext {
        "plaintext-explicit-override"
    } else {
        "encrypted-age-x25519"
    };
    if journal.confidentiality_mode.as_deref() != Some(expected)
        || (!options.plaintext
            && journal.recipient_fingerprints
                != vec![options.age_recipient.clone().unwrap_or_default()])
    {
        return Err(BridgeError::Conflict(
            "apply archive options differ from the journal-bound decision".into(),
        ));
    }
    Ok(())
}

fn archive_options_from_journal(journal: &Journal) -> Result<ArchiveOptions> {
    match journal.confidentiality_mode.as_deref() {
        Some("plaintext-explicit-override") => Ok(ArchiveOptions {
            age_recipient: None,
            plaintext: true,
            plaintext_risk_acknowledged: true,
        }),
        Some("encrypted-age-x25519") => Ok(ArchiveOptions {
            age_recipient: journal.recipient_fingerprints.first().cloned(),
            plaintext: false,
            plaintext_risk_acknowledged: false,
        }),
        None => Err(BridgeError::Conflict(
            "journal stopped before an archive decision was bound; rerun apply with its options"
                .into(),
        )),
        Some(_) => Err(BridgeError::Invalid(
            "journal has an unknown confidentiality mode".into(),
        )),
    }
}

fn write_new(path: &Path, bytes: &[u8]) -> Result<()> {
    if let Some(parent) = path.parent() {
        if !parent.exists() {
            std::fs::create_dir_all(parent)?;
        }
    }
    let mut file = OpenOptions::new().write(true).create_new(true).open(path)?;
    file.write_all(bytes)?;
    file.sync_all()?;
    Ok(())
}

fn write_exact_or_new(path: &Path, bytes: &[u8]) -> Result<()> {
    if path.exists() {
        if std::fs::read(path)? == bytes {
            return Ok(());
        }
        return Err(BridgeError::Conflict(format!(
            "staged evidence differs at {}",
            path.file_name()
                .and_then(|name| name.to_str())
                .unwrap_or("unknown")
        )));
    }
    write_new(path, bytes)
}

#[cfg(unix)]
fn rename_no_replace(source: &Path, destination: &Path) -> Result<()> {
    use rustix::fs::{renameat_with, RenameFlags, CWD};
    renameat_with(CWD, source, CWD, destination, RenameFlags::NOREPLACE)?;
    Ok(())
}

#[cfg(not(unix))]
fn rename_no_replace(_source: &Path, _destination: &Path) -> Result<()> {
    Err(BridgeError::Unsupported(
        "atomic no-replace manifest commit is unavailable until Phase 7".into(),
    ))
}

fn kill(name: &str) -> Result<()> {
    if std::env::var("HARNESS_V0_MIGRATE_TEST_KILL_AFTER").as_deref() == Ok(name) {
        return Err(BridgeError::KillPoint(name.into()));
    }
    Ok(())
}

fn state_name(state: JournalState) -> &'static str {
    match state {
        JournalState::Discovered => "discovered",
        JournalState::Inspected => "inspected",
        JournalState::Exported => "exported",
        JournalState::Archived => "archived",
        JournalState::Prepared => "prepared",
        JournalState::Applying => "applying",
        JournalState::Committed => "committed",
        JournalState::Completed => "completed",
        JournalState::RecoveryRequired => "recovery-required",
    }
}
