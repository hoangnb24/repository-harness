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
mod secure_fs;
mod strict_json;

use std::path::PathBuf;

use capture::{capture_members_digest, hex_sha256, source_digest, Capture};
use harness_core::domain::{
    Activation, Compatibility, ConversionReceipt, Manifest, ManifestRepositoryMode, Origin,
    Ownership, PayloadIdentity, Role, UpdatePolicy, MANIFEST_SCHEMA,
};
use harness_core::infrastructure::JsonManifestPort;
use harness_core::ports::ManifestPort;
use interface::{ArchiveOptions, Command};
use journal::{Journal, JournalState};
use secure_fs::SecureRoot;
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
            Self::Io(_) => 74,
            Self::Sqlite(_) | Self::Json(_) | Self::Age(_) => 70,
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
        let root = SecureRoot::open(&self.root)?;
        let capture = capture::capture_pinned(&root)?;
        let mut report = self.capture_report("inspect", &capture);
        report.notices.push(
            "source opened read-only; DB/WAL/SHM and recognized inputs passed same-handle pre/copy/post checks"
                .into(),
        );
        Ok(report)
    }

    fn preview(&self) -> Result<Report> {
        let root = SecureRoot::open(&self.root)?;
        let capture = capture::capture_pinned(&root)?;
        let preview = preview_digest(&root, &capture)?;
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
        let root = SecureRoot::open(&self.root)?;
        let capture = capture::capture_pinned(&root)?;
        let conversion_id = conversion_id(&capture);
        let journal_path = journal::relative_path(&conversion_id);
        let preview = if root.exists(&journal_path)? {
            let existing = journal::load_pinned(&root, &conversion_id)?;
            preview_digest_with_manifest(&root, &capture, existing.manifest_before_sha256.clone())?
        } else {
            preview_digest(&root, &capture)?
        };
        let (_, export_bytes, export_sha256) = export::build(&capture)?;
        root.preflight_new_file(output)?;
        let mut journal = Journal::new(
            root.identity(),
            conversion_id.clone(),
            capture.schema_version,
            source_digest(&capture),
            capture_members_digest(&capture),
            capture.standalone_backup_sha256.clone(),
            preview,
        );
        bind_archive_decision(&mut journal, options);
        journal.archive_staging_path = Some(archive::new_staging_path(&conversion_id)?);
        journal::save_pinned(&root, &journal)?;
        journal.state = JournalState::Inspected;
        journal::save_pinned(&root, &journal)?;
        journal.export_sha256 = Some(export_sha256.clone());
        journal.state = JournalState::Exported;
        journal::save_pinned(&root, &journal)?;
        let (evidence, published) =
            archive::prepare_or_verify(&root, &journal, &capture, &export_bytes, options)?;
        bind_archive(&mut journal, &evidence);
        journal::save_pinned(&root, &journal)?;
        if !published {
            archive::publish(
                &root,
                &conversion_id,
                journal.archive_staging_path.as_deref().ok_or_else(|| {
                    BridgeError::Invalid("journal lacks archive staging intent".into())
                })?,
            )?;
        }
        archive::verify_published(&root, &journal, &capture, &export_bytes, options)?;
        journal.state = JournalState::Archived;
        journal::save_pinned(&root, &journal)?;
        root.write_new(output, &export_bytes)?;
        let mut report = self.capture_report("export", &capture);
        report.mutation = "new-export-and-archive-only".into();
        report.conversion_id = Some(conversion_id);
        report.export_sha256 = Some(export_sha256);
        report.archive_sha256 = Some(evidence.archive_sha256);
        report.journal_state = Some(state_name(journal.state).into());
        Ok(report)
    }

    fn apply(&self, accepted: &str, options: &ArchiveOptions) -> Result<Report> {
        let root = SecureRoot::open(&self.root)?;
        let capture = capture::capture_pinned(&root)?;
        let conversion_id = conversion_id(&capture);
        let journal_path = journal::relative_path(&conversion_id);
        let preview = if root.exists(&journal_path)? {
            let existing = journal::load_pinned(&root, &conversion_id)?;
            preview_digest_with_manifest(&root, &capture, existing.manifest_before_sha256.clone())?
        } else {
            preview_digest(&root, &capture)?
        };
        if accepted != preview {
            return Err(BridgeError::Conflict(
                "accepted preview digest does not match current compatibility/input plan".into(),
            ));
        }
        if let Some(report) = self.completed_idempotent(&root, &conversion_id, &capture, options)? {
            return Ok(report);
        }
        if root.exists(&journal_path)? {
            let existing = journal::load_pinned(&root, &conversion_id)?;
            ensure_archive_decision(&existing, options)?;
            return self.advance(&root, existing, capture, options.clone());
        }
        reject_preexisting_manifest(&root)?;
        let mut journal = Journal::new(
            root.identity(),
            conversion_id,
            capture.schema_version,
            source_digest(&capture),
            capture_members_digest(&capture),
            capture.standalone_backup_sha256.clone(),
            preview,
        );
        bind_archive_decision(&mut journal, options);
        journal.archive_staging_path = Some(archive::new_staging_path(&journal.conversion_id)?);
        journal::save_pinned(&root, &journal)?;
        kill("detection")?;
        self.advance(&root, journal, capture, options.clone())
    }

    fn resume(&self, requested_conversion_id: &str) -> Result<Report> {
        let root = SecureRoot::open(&self.root)?;
        let journal = journal::load_pinned(&root, requested_conversion_id)?;
        if journal.rolled_back {
            return Err(BridgeError::Conflict(
                "journal was rolled back; a new explicit apply is required".into(),
            ));
        }
        let capture = capture::capture_pinned(&root)?;
        if source_digest(&capture) != journal.source_sha256
            || capture_members_digest(&capture) != journal.capture_members_sha256
            || capture.standalone_backup_sha256 != journal.standalone_backup_sha256
            || conversion_id(&capture) != journal.conversion_id
            || preview_digest_with_manifest(
                &root,
                &capture,
                journal.manifest_before_sha256.clone(),
            )? != journal.preview_sha256
        {
            return Err(BridgeError::Conflict(
                "resume source identity differs from journal-bound input".into(),
            ));
        }
        let options = archive_options_from_journal(&journal)?;
        self.advance(&root, journal, capture, options)
    }

    fn advance(
        &self,
        root: &SecureRoot,
        mut journal: Journal,
        capture: Capture,
        options: ArchiveOptions,
    ) -> Result<Report> {
        if journal.state == JournalState::Completed {
            preflight_journal_source(root, &journal, &capture)?;
            let (_, export_bytes, export_sha256) = export::build(&capture)?;
            if journal.export_sha256.as_deref() != Some(export_sha256.as_str()) {
                return Err(BridgeError::Conflict(
                    "completed journal export witness drifted".into(),
                ));
            }
            archive::verify_published(root, &journal, &capture, &export_bytes, &options)?;
            validate_live_manifest(root, &journal)?;
            return self.completed_report(&journal, &capture, "resume");
        }
        if journal.state == JournalState::RecoveryRequired {
            return Err(BridgeError::Conflict(
                "journal is recovery-required and cannot resume automatically".into(),
            ));
        }
        if journal.state < JournalState::Inspected {
            journal.state = JournalState::Inspected;
            journal::save_pinned(root, &journal)?;
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
            journal.state = JournalState::Exported;
            journal::save_pinned(root, &journal)?;
            kill("export")?;
        }
        if journal.state < JournalState::Archived {
            let (evidence, published) =
                archive::prepare_or_verify(root, &journal, &capture, &export_bytes, &options)?;
            bind_archive(&mut journal, &evidence);
            journal::save_pinned(root, &journal)?;
            if !published {
                archive::publish(
                    root,
                    &journal.conversion_id,
                    journal.archive_staging_path.as_deref().ok_or_else(|| {
                        BridgeError::Invalid("journal lacks archive staging intent".into())
                    })?,
                )?;
            }
            archive::verify_published(root, &journal, &capture, &export_bytes, &options)?;
            journal.state = JournalState::Archived;
            journal::save_pinned(root, &journal)?;
            kill("archive")?;
        } else {
            let evidence =
                archive::verify_published(root, &journal, &capture, &export_bytes, &options)?;
            if journal.archive_sha256.as_deref() != Some(&evidence.archive_sha256) {
                return Err(BridgeError::Conflict(
                    "archive digest differs from journal".into(),
                ));
            }
        }

        let manifest_bytes = build_manifest(root, &capture, &journal)?;
        let manifest_sha256 = hex_sha256(&manifest_bytes);
        let receipt_bytes = serde_json::to_vec(
            &serde_json::from_slice::<Manifest>(&manifest_bytes)
                .map_err(|error| {
                    BridgeError::Invalid(format!("conversion receipt is malformed: {error}"))
                })?
                .conversion_receipt
                .expect("candidate has receipt"),
        )?;
        let receipt_sha256 = hex_sha256(&receipt_bytes);
        if let Some(expected) = &journal.manifest_after_sha256 {
            if expected != &manifest_sha256
                || journal.receipt_sha256.as_deref() != Some(receipt_sha256.as_str())
            {
                return Err(BridgeError::Conflict(
                    "candidate manifest or receipt digest changed".into(),
                ));
            }
        } else {
            journal.manifest_before_sha256 = manifest_digest(root)?;
            if journal.manifest_before_sha256.is_some() {
                return Err(BridgeError::Invalid(
                    "V0 plus a V1 manifest without this completed receipt is mixed-invalid".into(),
                ));
            }
            journal.manifest_after_sha256 = Some(manifest_sha256.clone());
            journal.receipt_sha256 = Some(receipt_sha256);
            journal.state = JournalState::Prepared;
            journal::save_pinned(root, &journal)?;
        }
        validate_candidate(root, &manifest_bytes)?;
        let recovery = format!(".harness/recovery/v0-conversion/{}", journal.conversion_id);
        root.write_exact_or_new(&format!("{recovery}/receipt.staged.json"), &receipt_bytes)?;
        kill("temporary-receipt")?;
        let temporary_manifest = format!("{recovery}/manifest.staged.json");
        root.write_exact_or_new(&temporary_manifest, &manifest_bytes)?;
        kill("temporary-manifest")?;

        journal.state = JournalState::Applying;
        journal::save_pinned(root, &journal)?;
        if let Some(live) = root.read_optional(".harness/manifest.json")? {
            if hex_sha256(&live) != manifest_sha256 {
                return Err(BridgeError::Conflict(
                    "target manifest is not the journal-owned post-image".into(),
                ));
            }
        } else {
            root.rename_no_replace(&temporary_manifest, ".harness/manifest.json")?;
        }
        kill("operation-1")?;
        kill("atomic-commit")?;
        journal.state = JournalState::Committed;
        journal::save_pinned(root, &journal)?;
        validate_live_manifest(root, &journal)?;
        journal.state = JournalState::Completed;
        journal::save_pinned(root, &journal)?;
        self.completed_report(&journal, &capture, "apply")
    }

    fn rollback(&self, conversion_id: &str) -> Result<Report> {
        let root = SecureRoot::open(&self.root)?;
        let mut journal = journal::load_pinned(&root, conversion_id)?;
        if journal.state == JournalState::RecoveryRequired {
            return Err(BridgeError::Conflict(
                "journal is already recovery-required; human selection is required".into(),
            ));
        }
        if journal.state == JournalState::RolledBack {
            return Err(BridgeError::Conflict(
                "conversion is already rolled back".into(),
            ));
        }
        let capture = capture::capture_pinned(&root)?;
        preflight_journal_source(&root, &journal, &capture)?;
        let options = archive_options_from_journal(&journal)?;
        let (_, export_bytes, export_sha256) = export::build(&capture)?;
        if journal.export_sha256.as_deref() != Some(export_sha256.as_str()) {
            return Err(BridgeError::Conflict(
                "rollback export witness differs before mutation".into(),
            ));
        }
        archive::verify_published(&root, &journal, &capture, &export_bytes, &options)?;
        let manifest_bytes = build_manifest(&root, &capture, &journal)?;
        let expected_manifest = journal.manifest_after_sha256.as_deref().ok_or_else(|| {
            BridgeError::Conflict("rollback journal lacks a target witness".into())
        })?;
        if hex_sha256(&manifest_bytes) != expected_manifest {
            return Err(BridgeError::Conflict(
                "rollback target plan differs before mutation".into(),
            ));
        }
        validate_candidate(&root, &manifest_bytes)?;
        let recovery = format!(".harness/recovery/v0-conversion/{conversion_id}");
        let staged_receipt = root.read(&format!("{recovery}/receipt.staged.json"))?;
        if journal.receipt_sha256.as_deref() != Some(hex_sha256(&staged_receipt).as_str()) {
            return Err(BridgeError::Conflict(
                "rollback staged receipt evidence drifted".into(),
            ));
        }
        let live = root.read_optional(".harness/manifest.json")?;
        if journal.state != JournalState::RollingBack
            && live.as_deref().map(hex_sha256).as_deref() != Some(expected_manifest)
        {
            journal.state = JournalState::RecoveryRequired;
            journal::save_pinned(&root, &journal)?;
            return Err(BridgeError::Conflict(
                "rollback target precondition drifted before mutation".into(),
            ));
        }
        if journal.state == JournalState::RollingBack
            && live
                .as_deref()
                .is_some_and(|bytes| hex_sha256(bytes) != expected_manifest)
        {
            return Err(BridgeError::Conflict(
                "rollback crash recovery found an unowned target".into(),
            ));
        }
        root.validate_root()?;
        if journal.state != JournalState::RollingBack {
            journal.state = JournalState::RollingBack;
            journal::save_pinned(&root, &journal)?;
        }
        if live.is_some() {
            root.remove_exact(".harness/manifest.json", expected_manifest)?;
        }
        journal.state = JournalState::RolledBack;
        journal.rolled_back = true;
        journal::save_pinned(&root, &journal)?;
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
        root: &SecureRoot,
        conversion_id: &str,
        capture: &Capture,
        options: &ArchiveOptions,
    ) -> Result<Option<Report>> {
        let path = journal::relative_path(conversion_id);
        if !root.exists(&path)? {
            return Ok(None);
        }
        let journal = journal::load_pinned(root, conversion_id)?;
        if journal.state == JournalState::Completed {
            preflight_journal_source(root, &journal, capture)?;
            let (_, export_bytes, export_sha256) = export::build(capture)?;
            if journal.export_sha256.as_deref() != Some(export_sha256.as_str()) {
                return Err(BridgeError::Conflict(
                    "completed journal export witness drifted".into(),
                ));
            }
            ensure_archive_decision(&journal, options)?;
            archive::verify_published(root, &journal, capture, &export_bytes, options)?;
            validate_live_manifest(root, &journal)?;
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

fn preview_digest(root: &SecureRoot, capture: &Capture) -> Result<String> {
    preview_digest_with_manifest(root, capture, manifest_digest(root)?)
}

fn preview_digest_with_manifest(
    root: &SecureRoot,
    capture: &Capture,
    manifest_before_sha256: Option<String>,
) -> Result<String> {
    #[derive(Serialize)]
    struct Preview<'a> {
        schema: &'static str,
        repository_root: secure_fs::RootIdentity,
        source_schema: u32,
        source_sha256: String,
        capture_members_sha256: String,
        capture_members: Vec<PreviewMember<'a>>,
        standalone_backup_sha256: &'a str,
        manifest_before_sha256: Option<String>,
        adopted_targets: Vec<AdoptedTargetWitness>,
        confidentiality_choices: [&'static str; 2],
        operations: [PreviewOperation; 1],
    }
    #[derive(Serialize)]
    struct PreviewMember<'a> {
        path: &'a str,
        category: &'a str,
        sha256: &'a str,
        bytes: u64,
    }
    #[derive(Serialize)]
    struct PreviewOperation {
        operation_id: &'static str,
        kind: &'static str,
        path: &'static str,
        disposition: &'static str,
        before_sha256: Option<String>,
        after_witness: &'static str,
    }
    let adopted_targets = adopted_target_witnesses(root)?;
    let value = Preview {
        schema: "repository-harness-v0-conversion-preview/v1",
        repository_root: root.identity(),
        source_schema: capture.schema_version,
        source_sha256: source_digest(capture),
        capture_members_sha256: capture_members_digest(capture),
        capture_members: capture
            .members
            .iter()
            .map(|member| PreviewMember {
                path: &member.path,
                category: &member.category,
                sha256: &member.sha256,
                bytes: member.bytes,
            })
            .collect(),
        standalone_backup_sha256: &capture.standalone_backup_sha256,
        manifest_before_sha256: manifest_before_sha256.clone(),
        adopted_targets,
        confidentiality_choices: [
            "encrypted-age-x25519-with-exact-recipient-bound-at-apply",
            "plaintext-explicit-override-with-risk-acknowledgement",
        ],
        operations: [PreviewOperation {
            operation_id: "commit-manifest-receipt-last",
            kind: "create",
            path: ".harness/manifest.json",
            disposition: "managed-v1",
            before_sha256: manifest_before_sha256,
            after_witness: "exact-digest-bound-in-authenticated-journal-before-first-target-write",
        }],
    };
    Ok(hex_sha256(&serde_json::to_vec(&value)?))
}

fn adopted_target_witnesses(root: &SecureRoot) -> Result<Vec<AdoptedTargetWitness>> {
    let candidates = [
        ("AGENTS.md", "agent_map", true),
        ("README.md", "repository_readme", false),
        ("docs/ARCHITECTURE.md", "architecture", false),
    ];
    candidates
        .into_iter()
        .map(|(path, role, required)| {
            let digest = root.read_optional(path)?.map(|bytes| hex_sha256(&bytes));
            Ok(AdoptedTargetWitness {
                path,
                role,
                required,
                before_sha256: digest.clone(),
                after_sha256: digest,
            })
        })
        .collect()
}

#[derive(Serialize)]
struct AdoptedTargetWitness {
    path: &'static str,
    role: &'static str,
    required: bool,
    before_sha256: Option<String>,
    after_sha256: Option<String>,
}

fn build_manifest(root: &SecureRoot, _capture: &Capture, journal: &Journal) -> Result<Vec<u8>> {
    let candidates = [
        ("agent_map", "agent-map", "AGENTS.md"),
        ("repository_readme", "repository-readme", "README.md"),
        ("architecture", "architecture-map", "docs/ARCHITECTURE.md"),
    ];
    let mut roles = Vec::new();
    for (role_id, asset, path) in candidates {
        if let Some(bytes) = root.read_optional(path)? {
            let digest = hex_sha256(&bytes);
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
            standalone_backup_sha256: journal.standalone_backup_sha256.clone(),
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

fn validate_candidate(root: &SecureRoot, bytes: &[u8]) -> Result<()> {
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
        let actual = root.read_optional(&role.path)?;
        if actual.as_deref().map(hex_sha256).as_deref() != Some(role.current_sha256.as_str()) {
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

fn validate_live_manifest(root: &SecureRoot, journal: &Journal) -> Result<()> {
    let bytes = root.read(".harness/manifest.json")?;
    if journal.manifest_after_sha256.as_deref() != Some(&hex_sha256(&bytes)) {
        return Err(BridgeError::Conflict(
            "committed manifest differs from journal-owned post-image".into(),
        ));
    }
    validate_candidate(root, &bytes)
}

fn reject_preexisting_manifest(root: &SecureRoot) -> Result<()> {
    if root.exists(".harness/manifest.json")? {
        return Err(BridgeError::Invalid(
            "V0 artifacts plus a V1 manifest without a completed matching receipt are mixed-invalid"
                .into(),
        ));
    }
    Ok(())
}

fn manifest_digest(root: &SecureRoot) -> Result<Option<String>> {
    Ok(root
        .read_optional(".harness/manifest.json")?
        .map(|bytes| hex_sha256(&bytes)))
}

fn bind_archive(journal: &mut Journal, evidence: &archive::ArchiveEvidence) {
    journal.archive_sha256 = Some(evidence.archive_sha256.clone());
    journal.archive_manifest_sha256 = Some(evidence.manifest_sha256.clone());
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

fn preflight_journal_source(root: &SecureRoot, journal: &Journal, capture: &Capture) -> Result<()> {
    root.validate_root()?;
    if journal.root != root.identity()
        || journal.conversion_id != conversion_id(capture)
        || journal.source_schema != capture.schema_version
        || journal.source_sha256 != source_digest(capture)
        || journal.capture_members_sha256 != capture_members_digest(capture)
        || journal.standalone_backup_sha256 != capture.standalone_backup_sha256
        || preview_digest_with_manifest(root, capture, journal.manifest_before_sha256.clone())?
            != journal.preview_sha256
    {
        return Err(BridgeError::Conflict(
            "journal source, root, snapshot, member set, or complete plan witness drifted".into(),
        ));
    }
    Ok(())
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
        JournalState::RollingBack => "rolling-back",
        JournalState::RolledBack => "rolled-back",
        JournalState::RecoveryRequired => "recovery-required",
    }
}

#[cfg(test)]
mod exit_tests {
    use super::*;

    #[test]
    fn frozen_error_classes_have_exhaustive_exit_mappings() {
        assert_eq!(BridgeError::Usage("fixture".into()).exit_code(), 64);
        assert_eq!(BridgeError::Unsupported("fixture".into()).exit_code(), 5);
        assert_eq!(BridgeError::Conflict("fixture".into()).exit_code(), 4);
        assert_eq!(BridgeError::KillPoint("fixture".into()).exit_code(), 4);
        assert_eq!(BridgeError::Invalid("fixture".into()).exit_code(), 3);
        assert_eq!(BridgeError::Manifest("fixture".into()).exit_code(), 3);
        assert_eq!(
            BridgeError::Io(std::io::Error::other("fixture")).exit_code(),
            74
        );
        assert_eq!(
            BridgeError::Sqlite(rusqlite::Error::InvalidQuery).exit_code(),
            70
        );
        let json = serde_json::from_slice::<serde_json::Value>(b"{").unwrap_err();
        assert_eq!(BridgeError::Json(json).exit_code(), 70);
        #[cfg(unix)]
        assert_eq!(BridgeError::Errno(rustix::io::Errno::IO).exit_code(), 74);
    }
}
