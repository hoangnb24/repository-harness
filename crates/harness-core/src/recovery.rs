//! Phase 3 descriptor-anchored mutation, durability, and bounded recovery.

use std::collections::{BTreeMap, BTreeSet};
#[cfg(unix)]
use std::fs::File;
#[cfg(unix)]
use std::io::{Read, Write};
use std::path::PathBuf;
#[cfg(unix)]
use std::sync::atomic::{AtomicUsize, Ordering};

use serde::{Deserialize, Serialize};

use crate::domain::{Disposition, Manifest, Operation, OperationKind, PayloadIdentity};
use crate::path::validate_relative;
use crate::ports::{MutationPort, PortError};
use crate::strict_json::{canonical, digest, hex_sha256, parse};

const JOURNAL_SCHEMA: &str = "repository-harness-recovery-journal/v1";
const MANIFEST_PATH: &str = ".harness/manifest.json";
type ManagedBlockParts = (Vec<u8>, Vec<u8>, Vec<u8>);

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PlannedWrite {
    pub step_id: String,
    pub operation_id: String,
    pub kind: OperationKind,
    pub disposition: Disposition,
    pub path: String,
    pub before_sha256: Option<String>,
    pub after_bytes: Vec<u8>,
    pub backup_path: Option<String>,
    pub staged_path: String,
    pub temporary_path: String,
    pub manifest_commit: bool,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MutationRequest {
    pub command: String,
    pub operation_id: String,
    pub preview_sha256: String,
    pub accepted_preview_sha256: String,
    pub release: PayloadIdentity,
    pub operations: Vec<Operation>,
    pub writes: Vec<PlannedWrite>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct RecoveryAuthorization {
    pub release: PayloadIdentity,
    pub asset_paths: BTreeSet<String>,
    pub asset_sha256: BTreeMap<String, String>,
    pub asset_bytes: BTreeMap<String, Vec<u8>>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum RecoveryMode {
    Resume,
    Rollback,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct RecoveryProbe {
    pub command: String,
    pub operation_id: String,
    pub accepted_preview_sha256: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum MutationResult {
    Committed { manifest_bytes: Vec<u8> },
    RolledBack,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MutationFailure {
    pub error: PortError,
    pub journal_started: bool,
}

impl MutationFailure {
    fn before_journal(error: PortError) -> Self {
        Self {
            error,
            journal_started: false,
        }
    }

    fn after_journal(error: PortError) -> Self {
        Self {
            error,
            journal_started: true,
        }
    }
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
enum JournalState {
    Prepared,
    Applying,
    Committed,
    RolledBack,
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
enum StepState {
    Pending,
    Applied,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct JournalStep {
    step_id: String,
    operation_id: String,
    kind: OperationKind,
    disposition: Disposition,
    path: String,
    before_sha256: Option<String>,
    after_sha256: String,
    backup_path: Option<String>,
    staged_path: String,
    temporary_path: String,
    manifest_commit: bool,
    state: StepState,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct RecoveryJournal {
    schema: String,
    body_sha256: String,
    operation_id: String,
    command: String,
    state: JournalState,
    preview_sha256: String,
    accepted_preview_sha256: String,
    release: PayloadIdentity,
    operations: Vec<Operation>,
    steps: Vec<JournalStep>,
}

impl RecoveryJournal {
    fn from_request(request: &MutationRequest) -> Self {
        Self {
            schema: JOURNAL_SCHEMA.into(),
            body_sha256: String::new(),
            operation_id: request.operation_id.clone(),
            command: request.command.clone(),
            state: JournalState::Prepared,
            preview_sha256: request.preview_sha256.clone(),
            accepted_preview_sha256: request.accepted_preview_sha256.clone(),
            release: request.release.clone(),
            operations: request.operations.clone(),
            steps: request
                .writes
                .iter()
                .map(|write| JournalStep {
                    step_id: write.step_id.clone(),
                    operation_id: write.operation_id.clone(),
                    kind: write.kind.clone(),
                    disposition: write.disposition,
                    path: write.path.clone(),
                    before_sha256: write.before_sha256.clone(),
                    after_sha256: hex_sha256(&write.after_bytes),
                    backup_path: write.backup_path.clone(),
                    staged_path: write.staged_path.clone(),
                    temporary_path: write.temporary_path.clone(),
                    manifest_commit: write.manifest_commit,
                    state: StepState::Pending,
                })
                .collect(),
        }
    }

    fn body_digest(&self) -> Result<String, PortError> {
        let mut body = self.clone();
        body.body_sha256.clear();
        let value = serde_json::to_value(body).map_err(invariant)?;
        digest(&value).map_err(invariant)
    }

    fn encoded(&self) -> Result<Vec<u8>, PortError> {
        let mut journal = self.clone();
        journal.body_sha256 = journal.body_digest()?;
        let value = serde_json::to_value(journal).map_err(invariant)?;
        let mut bytes = canonical(&value).map_err(invariant)?;
        bytes.push(b'\n');
        Ok(bytes)
    }

    fn verify(&self) -> Result<(), PortError> {
        if self.schema != JOURNAL_SCHEMA || self.body_sha256 != self.body_digest()? {
            return Err(invalid("recovery journal schema or body digest mismatch"));
        }
        Ok(())
    }
}

/// Unix descriptor-anchored Phase 3 adapter. The optional kill counter exists
/// only to make every durable boundary mechanically interruptible in tests.
pub struct OsMutationPort {
    #[cfg(unix)]
    root: std::os::fd::OwnedFd,
    #[cfg(unix)]
    root_stat: rustix::fs::Stat,
    #[cfg(unix)]
    kill_after_checkpoint: Option<usize>,
    #[cfg(unix)]
    checkpoints: AtomicUsize,
    #[cfg(all(unix, test))]
    final_swap_after_pin: Option<Vec<u8>>,
    #[cfg(not(unix))]
    _root: PathBuf,
}

impl OsMutationPort {
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
                root,
                root_stat,
                kill_after_checkpoint: None,
                checkpoints: AtomicUsize::new(0),
                #[cfg(test)]
                final_swap_after_pin: None,
            })
        }
        #[cfg(not(unix))]
        {
            Ok(Self { _root: root_path })
        }
    }

    #[doc(hidden)]
    pub fn with_kill_after_checkpoint(
        root: impl Into<PathBuf>,
        checkpoint: usize,
    ) -> Result<Self, PortError> {
        let mut port = Self::new(root)?;
        #[cfg(unix)]
        {
            port.kill_after_checkpoint = Some(checkpoint);
        }
        #[cfg(not(unix))]
        {
            let _ = checkpoint;
        }
        Ok(port)
    }

    #[cfg(all(unix, test))]
    fn with_final_swap_after_pin(
        root: impl Into<PathBuf>,
        bytes: Vec<u8>,
    ) -> Result<Self, PortError> {
        let mut port = Self::new(root)?;
        port.final_swap_after_pin = Some(bytes);
        Ok(port)
    }

    #[cfg(unix)]
    fn checkpoint(&self, label: &str) -> Result<(), PortError> {
        let current = self.checkpoints.fetch_add(1, Ordering::SeqCst) + 1;
        if self.kill_after_checkpoint == Some(current) {
            return Err(PortError::Io {
                path: ".harness/recovery".into(),
                message: format!("injected kill point after {label}"),
            });
        }
        Ok(())
    }

    #[cfg(unix)]
    fn operation_root(operation_id: &str) -> String {
        format!(".harness/recovery/{operation_id}")
    }

    #[cfg(unix)]
    fn journal_path(operation_id: &str) -> String {
        format!("{}/journal.json", Self::operation_root(operation_id))
    }

    #[cfg(unix)]
    fn probe_recovery_unix(&self) -> Result<Vec<RecoveryProbe>, PortError> {
        use rustix::fs::Dir;

        self.validate_root()?;
        let recovery = match self.open_dir(".harness/recovery", false) {
            Ok(recovery) => recovery,
            Err(PortError::Missing(_)) => return Ok(Vec::new()),
            Err(error) => return Err(error),
        };
        let mut operation_ids = Vec::new();
        for entry in Dir::read_from(&recovery).map_err(|error| PortError::Io {
            path: ".harness/recovery".into(),
            message: error.to_string(),
        })? {
            let entry = entry.map_err(|error| PortError::Io {
                path: ".harness/recovery".into(),
                message: error.to_string(),
            })?;
            let name = entry.file_name().to_string_lossy();
            if name == "." || name == ".." {
                continue;
            }
            if is_lower_kebab(&name) {
                operation_ids.push(name.into_owned());
            }
        }
        operation_ids.sort();
        let mut probes = Vec::new();
        for operation_id in operation_ids {
            let journal = match self.load_journal(&operation_id) {
                Ok(journal) => journal,
                // Preparation can be interrupted before the journal's first
                // atomic rename. Exact staged/backup evidence is safely
                // reusable by the deterministic confirmed rerun; it is not an
                // authoritative recovery state until journal.json exists.
                Err(PortError::Missing(_)) => continue,
                Err(error) => return Err(error),
            };
            let authorization = RecoveryAuthorization {
                release: journal.release.clone(),
                asset_paths: journal
                    .steps
                    .iter()
                    .filter(|step| !step.manifest_commit)
                    .map(|step| step.path.clone())
                    .collect(),
                asset_sha256: journal
                    .steps
                    .iter()
                    .filter(|step| !step.manifest_commit && step.kind == OperationKind::Create)
                    .map(|step| (step.path.clone(), step.after_sha256.clone()))
                    .collect(),
                asset_bytes: BTreeMap::new(),
            };
            validate_journal_ownership(&journal, &journal.command, &operation_id, &authorization)?;
            if matches!(
                journal.state,
                JournalState::Prepared | JournalState::Applying
            ) {
                probes.push(RecoveryProbe {
                    command: journal.command,
                    operation_id,
                    accepted_preview_sha256: journal.accepted_preview_sha256,
                });
            }
        }
        self.validate_root()?;
        Ok(probes)
    }

    #[cfg(unix)]
    fn apply_request(
        &self,
        request: &MutationRequest,
        validate_candidate: &mut dyn FnMut(&[u8]) -> Result<(), PortError>,
    ) -> Result<MutationResult, MutationFailure> {
        validate_request(request).map_err(MutationFailure::before_journal)?;
        self.validate_root()
            .map_err(MutationFailure::before_journal)?;
        if self
            .read_optional(&Self::journal_path(&request.operation_id))
            .map_err(MutationFailure::before_journal)?
            .is_some()
        {
            return Err(MutationFailure::after_journal(PortError::Conflict(
                "durable operation journal already exists; use command-owned resume or rollback"
                    .into(),
            )));
        }
        for write in &request.writes {
            self.expect_current(&write.path, write.before_sha256.as_deref())
                .map_err(MutationFailure::before_journal)?;
            if self
                .read_optional(&write.temporary_path)
                .map_err(MutationFailure::before_journal)?
                .is_some()
            {
                return Err(MutationFailure::before_journal(PortError::Conflict(
                    format!(
                        "unowned temporary path already exists: {}",
                        write.temporary_path
                    ),
                )));
            }
        }

        self.ensure_dir(&Self::operation_root(&request.operation_id))
            .and_then(|()| {
                self.ensure_dir(&format!(
                    "{}/backups",
                    Self::operation_root(&request.operation_id)
                ))
            })
            .and_then(|()| {
                self.ensure_dir(&format!(
                    "{}/staged",
                    Self::operation_root(&request.operation_id)
                ))
            })
            .map_err(MutationFailure::before_journal)?;

        for write in &request.writes {
            if let Some(backup_path) = &write.backup_path {
                let before = self
                    .read_required(&write.path)
                    .map_err(MutationFailure::before_journal)?;
                self.write_owned_once(backup_path, &before)
                    .map_err(MutationFailure::before_journal)?;
                self.checkpoint("backup fsync")
                    .map_err(MutationFailure::before_journal)?;
            }
            self.write_owned_once(&write.staged_path, &write.after_bytes)
                .map_err(MutationFailure::before_journal)?;
            self.checkpoint("staged post-image fsync")
                .map_err(MutationFailure::before_journal)?;
        }

        let mut journal = RecoveryJournal::from_request(request);
        self.persist_journal(&journal)
            .map_err(MutationFailure::before_journal)?;
        self.checkpoint("prepared journal fsync")
            .map_err(MutationFailure::after_journal)?;
        journal.state = JournalState::Applying;
        self.persist_journal(&journal)
            .map_err(MutationFailure::after_journal)?;

        self.resume_journal(&mut journal, validate_candidate)
    }

    #[cfg(unix)]
    fn recover_request(
        &self,
        command: &str,
        operation_id: &str,
        mode: RecoveryMode,
        authorization: &RecoveryAuthorization,
        validate_candidate: &mut dyn FnMut(&[u8]) -> Result<(), PortError>,
    ) -> Result<MutationResult, MutationFailure> {
        self.validate_root()
            .map_err(MutationFailure::before_journal)?;
        let mut journal = self
            .load_journal(operation_id)
            .map_err(MutationFailure::before_journal)?;
        validate_journal_ownership(&journal, command, operation_id, authorization)
            .map_err(MutationFailure::after_journal)?;
        self.verify_authenticated_post_images(&journal, authorization)?;
        match mode {
            RecoveryMode::Resume => self.resume_journal(&mut journal, validate_candidate),
            RecoveryMode::Rollback => self.rollback_journal(&mut journal),
        }
    }

    #[cfg(unix)]
    fn resume_journal(
        &self,
        journal: &mut RecoveryJournal,
        validate_candidate: &mut dyn FnMut(&[u8]) -> Result<(), PortError>,
    ) -> Result<MutationResult, MutationFailure> {
        if journal.state == JournalState::RolledBack {
            return Err(MutationFailure::after_journal(PortError::Conflict(
                "rolled-back operation cannot be resumed".into(),
            )));
        }
        let manifest_index = journal
            .steps
            .iter()
            .position(|step| step.manifest_commit)
            .ok_or_else(|| {
                MutationFailure::after_journal(invalid("journal has no manifest-last step"))
            })?;
        if manifest_index + 1 != journal.steps.len() {
            return Err(MutationFailure::after_journal(invalid(
                "manifest is not the last journal step",
            )));
        }

        self.reconcile_step_states(journal)?;
        for index in 0..manifest_index {
            if journal.steps[index].state == StepState::Pending {
                self.apply_step(&journal.steps[index])?;
                journal.steps[index].state = StepState::Applied;
                self.persist_journal(journal)
                    .map_err(MutationFailure::after_journal)?;
                self.checkpoint("applied target step journal fsync")
                    .map_err(MutationFailure::after_journal)?;
            }
        }

        let manifest_bytes = self
            .read_required(&journal.steps[manifest_index].staged_path)
            .map_err(MutationFailure::after_journal)?;
        if hex_sha256(&manifest_bytes) != journal.steps[manifest_index].after_sha256 {
            return Err(MutationFailure::after_journal(invalid(
                "staged manifest digest mismatch",
            )));
        }
        validate_candidate(&manifest_bytes).map_err(MutationFailure::after_journal)?;
        self.checkpoint("candidate structural validation")
            .map_err(MutationFailure::after_journal)?;
        verify_preview(journal).map_err(MutationFailure::after_journal)?;
        self.checkpoint("preview confirmation recheck")
            .map_err(MutationFailure::after_journal)?;

        if journal.steps[manifest_index].state == StepState::Pending {
            self.apply_step(&journal.steps[manifest_index])?;
            journal.steps[manifest_index].state = StepState::Applied;
        }
        self.validate_root()
            .map_err(MutationFailure::after_journal)?;
        journal.state = JournalState::Committed;
        self.persist_journal(journal)
            .map_err(MutationFailure::after_journal)?;
        self.checkpoint("committed journal fsync")
            .map_err(MutationFailure::after_journal)?;
        Ok(MutationResult::Committed { manifest_bytes })
    }

    #[cfg(unix)]
    fn rollback_journal(
        &self,
        journal: &mut RecoveryJournal,
    ) -> Result<MutationResult, MutationFailure> {
        if journal.state == JournalState::RolledBack {
            return Ok(MutationResult::RolledBack);
        }

        // Validate every current image before the first rollback mutation. A
        // target edit therefore wins without a partially attempted rollback.
        let mut applied = Vec::with_capacity(journal.steps.len());
        for step in &journal.steps {
            let current = self
                .read_optional(&step.path)
                .map_err(MutationFailure::after_journal)?;
            let is_after = current
                .as_ref()
                .is_some_and(|bytes| hex_sha256(bytes) == step.after_sha256);
            let is_before = match (&step.before_sha256, &current) {
                (None, None) => true,
                (Some(expected), Some(bytes)) => hex_sha256(bytes) == *expected,
                _ => false,
            };
            if !is_after && !is_before {
                return Err(MutationFailure::after_journal(PortError::Conflict(
                    format!("rollback refuses changed post-image at {}", step.path),
                )));
            }
            applied.push(is_after);
        }

        let manifest_index = journal
            .steps
            .iter()
            .position(|step| step.manifest_commit)
            .ok_or_else(|| {
                MutationFailure::after_journal(invalid("journal has no manifest step"))
            })?;
        if applied[manifest_index] {
            self.remove_exact(
                &journal.steps[manifest_index].path,
                &journal.steps[manifest_index].after_sha256,
            )?;
            self.checkpoint("removed committed manifest before rollback")
                .map_err(MutationFailure::after_journal)?;
        }

        for index in (0..manifest_index).rev() {
            if applied[index] {
                self.restore_step(&journal.steps[index])?;
                self.checkpoint("restored target rollback step")
                    .map_err(MutationFailure::after_journal)?;
            }
        }
        if applied[manifest_index] && journal.steps[manifest_index].before_sha256.is_some() {
            self.restore_step(&journal.steps[manifest_index])?;
        }
        journal.state = JournalState::RolledBack;
        for step in &mut journal.steps {
            step.state = StepState::Pending;
        }
        self.persist_journal(journal)
            .map_err(MutationFailure::after_journal)?;
        Ok(MutationResult::RolledBack)
    }

    #[cfg(unix)]
    fn reconcile_step_states(&self, journal: &mut RecoveryJournal) -> Result<(), MutationFailure> {
        let mut changed = false;
        for step in &mut journal.steps {
            let current = self
                .read_optional(&step.path)
                .map_err(MutationFailure::after_journal)?;
            let is_after = current
                .as_ref()
                .is_some_and(|bytes| hex_sha256(bytes) == step.after_sha256);
            let is_before = match (&step.before_sha256, &current) {
                (None, None) => true,
                (Some(expected), Some(bytes)) => hex_sha256(bytes) == *expected,
                _ => false,
            };
            if is_after {
                if let Some(before) = &step.before_sha256 {
                    if let Some(displaced) = self
                        .read_optional(&step.temporary_path)
                        .map_err(MutationFailure::after_journal)?
                    {
                        if hex_sha256(&displaced) == *before {
                            self.remove_exact(&step.temporary_path, before)?;
                        } else {
                            // A crash may have landed between exchange and the
                            // inode check while an intervening final-component
                            // edit was displaced to the owned temporary name.
                            // Exchange it back; never prefer our candidate over
                            // ambiguous target-owned bytes.
                            self.rename_temporary(
                                &step.temporary_path,
                                &step.path,
                                Some(&step.after_sha256),
                            )
                            .map_err(MutationFailure::after_journal)?;
                            return Err(MutationFailure::after_journal(PortError::Conflict(
                                format!(
                                    "recovery restored ambiguous intervening bytes at {}",
                                    step.path
                                ),
                            )));
                        }
                    }
                }
                if step.state != StepState::Applied {
                    step.state = StepState::Applied;
                    changed = true;
                }
            } else if !is_before {
                return Err(MutationFailure::after_journal(PortError::Conflict(
                    format!("recovery refuses changed image at {}", step.path),
                )));
            }
            self.verify_owned_evidence(step)?;
        }
        if changed {
            self.persist_journal(journal)
                .map_err(MutationFailure::after_journal)?;
        }
        Ok(())
    }

    #[cfg(unix)]
    fn verify_owned_evidence(&self, step: &JournalStep) -> Result<(), MutationFailure> {
        let staged = self
            .read_required(&step.staged_path)
            .map_err(MutationFailure::after_journal)?;
        if hex_sha256(&staged) != step.after_sha256 {
            return Err(MutationFailure::after_journal(invalid(format!(
                "staged post-image digest mismatch for {}",
                step.step_id
            ))));
        }
        if let (Some(before), Some(backup_path)) = (&step.before_sha256, &step.backup_path) {
            let backup = self
                .read_required(backup_path)
                .map_err(MutationFailure::after_journal)?;
            if hex_sha256(&backup) != *before {
                return Err(MutationFailure::after_journal(invalid(format!(
                    "backup digest mismatch for {}",
                    step.step_id
                ))));
            }
        }
        Ok(())
    }

    #[cfg(unix)]
    fn verify_authenticated_post_images(
        &self,
        journal: &RecoveryJournal,
        authorization: &RecoveryAuthorization,
    ) -> Result<(), MutationFailure> {
        for (path, bytes) in &authorization.asset_bytes {
            if authorization.asset_sha256.get(path) != Some(&hex_sha256(bytes)) {
                return Err(MutationFailure::after_journal(invalid(format!(
                    "authenticated asset bytes and digest disagree for {path}"
                ))));
            }
        }
        let manifest_step = journal
            .steps
            .last()
            .expect("journal ownership already established manifest-last");
        let manifest_bytes = self
            .read_required(&manifest_step.staged_path)
            .map_err(MutationFailure::after_journal)?;
        if hex_sha256(&manifest_bytes) != manifest_step.after_sha256 {
            return Err(MutationFailure::after_journal(invalid(
                "staged manifest does not match the authorized plan commitment",
            )));
        }
        let value = parse(&manifest_bytes)
            .map_err(invalid)
            .map_err(MutationFailure::after_journal)?;
        let manifest: Manifest = serde_json::from_value(value)
            .map_err(invariant)
            .map_err(MutationFailure::after_journal)?;

        for step in journal.steps.iter().filter(|step| !step.manifest_commit) {
            self.verify_owned_evidence(step)?;
            let asset = authorization.asset_bytes.get(&step.path).ok_or_else(|| {
                MutationFailure::after_journal(invalid(format!(
                    "no authenticated asset bytes authorize {}",
                    step.path
                )))
            })?;
            match step.kind {
                OperationKind::Create => {
                    if hex_sha256(asset) != step.after_sha256 {
                        return Err(MutationFailure::after_journal(invalid(format!(
                            "{} differs from the authenticated asset post-image",
                            step.path
                        ))));
                    }
                }
                OperationKind::ReplaceManagedBlock => {
                    let marker = manifest
                        .roles
                        .iter()
                        .find(|role| role.path == step.path)
                        .and_then(|role| role.marker.as_deref())
                        .ok_or_else(|| {
                            MutationFailure::after_journal(invalid(format!(
                                "candidate manifest has no marker for {}",
                                step.path
                            )))
                        })?;
                    let backup_path = step.backup_path.as_deref().ok_or_else(|| {
                        MutationFailure::after_journal(invalid(format!(
                            "managed-block recovery has no backup for {}",
                            step.path
                        )))
                    })?;
                    let before = self
                        .read_required(backup_path)
                        .map_err(MutationFailure::after_journal)?;
                    let (mut prefix, _, suffix) = managed_block_parts(&before, marker)
                        .map_err(MutationFailure::after_journal)?;
                    prefix.extend_from_slice(
                        &managed_candidate_interior(asset, marker)
                            .map_err(MutationFailure::after_journal)?,
                    );
                    prefix.extend_from_slice(&suffix);
                    let staged = self
                        .read_required(&step.staged_path)
                        .map_err(MutationFailure::after_journal)?;
                    if staged != prefix || hex_sha256(&prefix) != step.after_sha256 {
                        return Err(MutationFailure::after_journal(invalid(format!(
                            "{} is not the deterministic authenticated managed-block post-image",
                            step.path
                        ))));
                    }
                }
                _ => {
                    return Err(MutationFailure::after_journal(invalid(format!(
                        "unsupported recovery operation kind for {}",
                        step.path
                    ))));
                }
            }
        }
        Ok(())
    }

    #[cfg(unix)]
    fn apply_step(&self, step: &JournalStep) -> Result<(), MutationFailure> {
        self.verify_owned_evidence(step)?;
        self.expect_current(&step.path, step.before_sha256.as_deref())
            .map_err(MutationFailure::after_journal)?;
        let bytes = self
            .read_required(&step.staged_path)
            .map_err(MutationFailure::after_journal)?;
        self.write_temporary(&step.temporary_path, &bytes)
            .map_err(MutationFailure::after_journal)?;
        self.checkpoint("target temporary fsync")
            .map_err(MutationFailure::after_journal)?;
        self.expect_current(&step.path, step.before_sha256.as_deref())
            .map_err(MutationFailure::after_journal)?;
        self.rename_temporary(
            &step.temporary_path,
            &step.path,
            step.before_sha256.as_deref(),
        )
        .map_err(MutationFailure::after_journal)?;
        self.checkpoint(if step.manifest_commit {
            "atomic manifest rename and directory fsync"
        } else {
            "atomic target rename and directory fsync"
        })
        .map_err(MutationFailure::after_journal)?;
        let current = self
            .read_required(&step.path)
            .map_err(MutationFailure::after_journal)?;
        if hex_sha256(&current) != step.after_sha256 {
            return Err(MutationFailure::after_journal(PortError::Changed(
                step.path.clone(),
            )));
        }
        Ok(())
    }

    #[cfg(unix)]
    fn restore_step(&self, step: &JournalStep) -> Result<(), MutationFailure> {
        match (&step.before_sha256, &step.backup_path) {
            (None, None) => self.remove_exact(&step.path, &step.after_sha256),
            (Some(before), Some(backup_path)) => {
                let backup = self
                    .read_required(backup_path)
                    .map_err(MutationFailure::after_journal)?;
                if hex_sha256(&backup) != *before {
                    return Err(MutationFailure::after_journal(invalid(format!(
                        "rollback backup digest mismatch for {}",
                        step.path
                    ))));
                }
                self.write_temporary(&step.temporary_path, &backup)
                    .map_err(MutationFailure::after_journal)?;
                self.expect_current(&step.path, Some(&step.after_sha256))
                    .map_err(MutationFailure::after_journal)?;
                self.rename_temporary(&step.temporary_path, &step.path, Some(&step.after_sha256))
                    .map_err(MutationFailure::after_journal)
            }
            _ => Err(MutationFailure::after_journal(invalid(format!(
                "incomplete rollback ownership for {}",
                step.path
            )))),
        }
    }

    #[cfg(unix)]
    fn remove_exact(&self, path: &str, expected: &str) -> Result<(), MutationFailure> {
        use rustix::fs::{fsync, unlinkat, AtFlags};

        self.expect_current(path, Some(expected))
            .map_err(MutationFailure::after_journal)?;
        let (parent, name) = self
            .open_parent(path, false)
            .map_err(MutationFailure::after_journal)?;
        unlinkat(&parent, name, AtFlags::empty())
            .map_err(|error| MutationFailure::after_journal(map_errno(path, error)))?;
        fsync(&parent).map_err(|error| MutationFailure::after_journal(map_errno(path, error)))
    }

    #[cfg(unix)]
    fn load_journal(&self, operation_id: &str) -> Result<RecoveryJournal, PortError> {
        let path = Self::journal_path(operation_id);
        let bytes = self.read_required(&path)?;
        let value = parse(&bytes).map_err(invalid)?;
        let journal: RecoveryJournal = serde_json::from_value(value).map_err(invariant)?;
        journal.verify()?;
        Ok(journal)
    }

    #[cfg(unix)]
    fn persist_journal(&self, journal: &RecoveryJournal) -> Result<(), PortError> {
        let path = Self::journal_path(&journal.operation_id);
        self.write_internal_atomic(&path, &journal.encoded()?)
    }

    #[cfg(unix)]
    fn read_required(&self, path: &str) -> Result<Vec<u8>, PortError> {
        self.read_optional(path)?
            .ok_or_else(|| PortError::Missing(path.into()))
    }

    #[cfg(unix)]
    fn read_optional(&self, path: &str) -> Result<Option<Vec<u8>>, PortError> {
        use rustix::fs::{fstat, FileType};

        let descriptor = match self.open_file(path) {
            Ok(descriptor) => descriptor,
            Err(PortError::Missing(_)) => return Ok(None),
            Err(error) => return Err(error),
        };
        let stat = fstat(&descriptor).map_err(|error| map_errno(path, error))?;
        if !FileType::from_raw_mode(stat.st_mode).is_file() {
            return Err(PortError::Io {
                path: path.into(),
                message: "path is not a regular file".into(),
            });
        }
        let mut file = File::from(descriptor);
        let mut bytes = Vec::new();
        file.read_to_end(&mut bytes)
            .map_err(|error| PortError::Io {
                path: path.into(),
                message: error.kind().to_string(),
            })?;
        let after = fstat(&file).map_err(|error| map_errno(path, error))?;
        if !same_stat(&stat, &after) || after.st_size != bytes.len() as i64 {
            return Err(PortError::Changed(path.into()));
        }
        Ok(Some(bytes))
    }

    #[cfg(unix)]
    fn expect_current(&self, path: &str, expected: Option<&str>) -> Result<(), PortError> {
        let current = self.read_optional(path)?;
        match (expected, current) {
            (None, None) => Ok(()),
            (Some(expected), Some(bytes)) if hex_sha256(&bytes) == expected => Ok(()),
            (None, Some(_)) => Err(PortError::Conflict(format!(
                "expected absent path appeared: {path}"
            ))),
            (Some(_), None) => Err(PortError::Conflict(format!(
                "expected path disappeared: {path}"
            ))),
            (Some(expected), Some(bytes)) => Err(PortError::Conflict(format!(
                "digest changed at {path}; expected {expected}, actual {}",
                hex_sha256(&bytes)
            ))),
        }
    }

    #[cfg(unix)]
    fn validate_root(&self) -> Result<(), PortError> {
        use rustix::fs::fstat;

        let current = fstat(&self.root).map_err(|error| map_errno(".", error))?;
        if self.root_stat.st_dev != current.st_dev
            || self.root_stat.st_ino != current.st_ino
            || self.root_stat.st_mode != current.st_mode
        {
            return Err(PortError::Changed(".".into()));
        }
        Ok(())
    }

    #[cfg(unix)]
    fn ensure_dir(&self, path: &str) -> Result<(), PortError> {
        let _ = self.open_dir(path, true)?;
        Ok(())
    }

    #[cfg(unix)]
    fn open_dir(&self, path: &str, create: bool) -> Result<std::os::fd::OwnedFd, PortError> {
        use rustix::fs::{fsync, mkdirat, openat, Mode, OFlags};

        if !matches!(path, ".harness" | ".harness/recovery") {
            validate_relative(path, true)?;
        }
        let mut parent: Option<std::os::fd::OwnedFd> = None;
        for component in path.split('/') {
            let opened = openat(
                parent.as_ref().unwrap_or(&self.root),
                component,
                OFlags::RDONLY | OFlags::DIRECTORY | OFlags::CLOEXEC | OFlags::NOFOLLOW,
                Mode::empty(),
            );
            let descriptor = match opened {
                Ok(descriptor) => descriptor,
                Err(error) if create && error == rustix::io::Errno::NOENT => {
                    let parent_fd = parent.as_ref().unwrap_or(&self.root);
                    mkdirat(parent_fd, component, Mode::from_bits_truncate(0o755))
                        .map_err(|error| map_errno(path, error))?;
                    fsync(parent_fd).map_err(|error| map_errno(path, error))?;
                    openat(
                        parent_fd,
                        component,
                        OFlags::RDONLY | OFlags::DIRECTORY | OFlags::CLOEXEC | OFlags::NOFOLLOW,
                        Mode::empty(),
                    )
                    .map_err(|error| map_errno(path, error))?
                }
                Err(error) => return Err(map_errno(path, error)),
            };
            parent = Some(descriptor);
        }
        parent.ok_or_else(|| PortError::UnsafePath(path.into()))
    }

    #[cfg(unix)]
    fn open_parent(
        &self,
        path: &str,
        create: bool,
    ) -> Result<(std::os::fd::OwnedFd, String), PortError> {
        validate_relative(path, true)?;
        let (parent, name) = path.rsplit_once('/').unwrap_or(("", path));
        let descriptor = if parent.is_empty() {
            use rustix::fs::{openat, Mode, OFlags};
            openat(
                &self.root,
                ".",
                OFlags::RDONLY | OFlags::DIRECTORY | OFlags::CLOEXEC | OFlags::NOFOLLOW,
                Mode::empty(),
            )
            .map_err(|error| map_errno(path, error))?
        } else {
            self.open_dir(parent, create)?
        };
        Ok((descriptor, name.into()))
    }

    #[cfg(unix)]
    fn open_file(&self, path: &str) -> Result<std::os::fd::OwnedFd, PortError> {
        use rustix::fs::{openat, Mode, OFlags};

        let (parent, name) = self.open_parent(path, false)?;
        openat(
            &parent,
            name,
            OFlags::RDONLY | OFlags::CLOEXEC | OFlags::NOFOLLOW,
            Mode::empty(),
        )
        .map_err(|error| map_errno(path, error))
    }

    #[cfg(unix)]
    fn write_owned_once(&self, path: &str, bytes: &[u8]) -> Result<(), PortError> {
        if let Some(existing) = self.read_optional(path)? {
            return if existing == bytes {
                Ok(())
            } else {
                Err(PortError::Conflict(format!(
                    "owned recovery evidence differs at {path}"
                )))
            };
        }
        self.write_new(path, bytes, true, 0o600)
    }

    #[cfg(unix)]
    fn write_temporary(&self, path: &str, bytes: &[u8]) -> Result<(), PortError> {
        if let Some(existing) = self.read_optional(path)? {
            if existing == bytes {
                return Ok(());
            }
            return Err(PortError::Conflict(format!(
                "owned temporary digest differs at {path}"
            )));
        }
        self.write_new(path, bytes, true, 0o644)
    }

    #[cfg(unix)]
    fn write_new(
        &self,
        path: &str,
        bytes: &[u8],
        create_parent: bool,
        mode: u16,
    ) -> Result<(), PortError> {
        use rustix::fs::{fsync, openat, Mode, OFlags};

        let (parent, name) = self.open_parent(path, create_parent)?;
        let descriptor = openat(
            &parent,
            name,
            OFlags::WRONLY | OFlags::CREATE | OFlags::EXCL | OFlags::CLOEXEC | OFlags::NOFOLLOW,
            Mode::from_bits_truncate(mode),
        )
        .map_err(|error| map_errno(path, error))?;
        let mut file = File::from(descriptor);
        file.write_all(bytes).map_err(|error| PortError::Io {
            path: path.into(),
            message: error.kind().to_string(),
        })?;
        file.sync_all().map_err(|error| PortError::Io {
            path: path.into(),
            message: error.kind().to_string(),
        })?;
        fsync(&parent).map_err(|error| map_errno(path, error))
    }

    #[cfg(unix)]
    fn write_internal_atomic(&self, path: &str, bytes: &[u8]) -> Result<(), PortError> {
        use rustix::fs::{fsync, openat, renameat, unlinkat, AtFlags, Mode, OFlags};

        let (parent, name) = self.open_parent(path, true)?;
        let temporary = format!(".{name}.tmp");
        if openat(
            &parent,
            &temporary,
            OFlags::RDONLY | OFlags::CLOEXEC | OFlags::NOFOLLOW,
            Mode::empty(),
        )
        .is_ok()
        {
            unlinkat(&parent, &temporary, AtFlags::empty())
                .map_err(|error| map_errno(path, error))?;
        }
        let descriptor = openat(
            &parent,
            &temporary,
            OFlags::WRONLY | OFlags::CREATE | OFlags::EXCL | OFlags::CLOEXEC | OFlags::NOFOLLOW,
            Mode::from_bits_truncate(0o600),
        )
        .map_err(|error| map_errno(path, error))?;
        let mut file = File::from(descriptor);
        file.write_all(bytes).map_err(|error| PortError::Io {
            path: path.into(),
            message: error.kind().to_string(),
        })?;
        file.sync_all().map_err(|error| PortError::Io {
            path: path.into(),
            message: error.kind().to_string(),
        })?;
        renameat(&parent, &temporary, &parent, &name).map_err(|error| map_errno(path, error))?;
        fsync(&parent).map_err(|error| map_errno(path, error))
    }

    #[cfg(unix)]
    fn rename_temporary(
        &self,
        temporary_path: &str,
        destination: &str,
        expected_destination_sha256: Option<&str>,
    ) -> Result<(), PortError> {
        #[cfg(any(target_os = "linux", target_os = "macos"))]
        use rustix::fs::{
            fstat, fsync, openat, renameat_with, unlinkat, AtFlags, FileType, Mode, OFlags,
            RenameFlags,
        };

        let (temporary_parent, temporary_name) = self.open_parent(temporary_path, false)?;
        let (destination_parent, destination_name) = self.open_parent(destination, true)?;
        #[cfg(not(any(target_os = "linux", target_os = "macos")))]
        {
            let _ = (
                temporary_parent,
                temporary_name,
                destination_parent,
                destination_name,
                expected_destination_sha256,
            );
            return Err(PortError::Io {
                path: destination.into(),
                message: "atomic no-replace/exchange is unavailable; Phase 7 platform gate remains closed"
                    .into(),
            });
        }
        #[cfg(any(target_os = "linux", target_os = "macos"))]
        {
            if expected_destination_sha256.is_none() {
                renameat_with(
                    &temporary_parent,
                    &temporary_name,
                    &destination_parent,
                    &destination_name,
                    RenameFlags::NOREPLACE,
                )
                .map_err(|error| map_errno(destination, error))?;
                self.checkpoint("atomic no-replace before directory fsync")?;
                fsync(&destination_parent).map_err(|error| map_errno(destination, error))?;
                fsync(&temporary_parent).map_err(|error| map_errno(temporary_path, error))?;
                return Ok(());
            }

            // Pin both final components before the exchange. The final target
            // descriptor proves which inode was checked; after the exchange,
            // that exact inode must be at the temporary name. A name swap in
            // the check/commit window is therefore detected without clobbering
            // the intervening bytes.
            let mut destination_file = File::from(
                openat(
                    &destination_parent,
                    &destination_name,
                    OFlags::RDONLY | OFlags::CLOEXEC | OFlags::NOFOLLOW,
                    Mode::empty(),
                )
                .map_err(|error| map_errno(destination, error))?,
            );
            let destination_stat =
                fstat(&destination_file).map_err(|error| map_errno(destination, error))?;
            if !FileType::from_raw_mode(destination_stat.st_mode).is_file() {
                return Err(PortError::Conflict(format!(
                    "replacement target is not a regular file: {destination}"
                )));
            }
            let mut destination_bytes = Vec::new();
            destination_file
                .read_to_end(&mut destination_bytes)
                .map_err(|error| PortError::Io {
                    path: destination.into(),
                    message: error.kind().to_string(),
                })?;
            let expected = expected_destination_sha256.expect("replacement branch");
            if hex_sha256(&destination_bytes) != expected {
                return Err(PortError::Conflict(format!(
                    "replacement target changed before atomic exchange: {destination}"
                )));
            }
            let temporary_descriptor = openat(
                &temporary_parent,
                &temporary_name,
                OFlags::RDONLY | OFlags::CLOEXEC | OFlags::NOFOLLOW,
                Mode::empty(),
            )
            .map_err(|error| map_errno(temporary_path, error))?;
            let temporary_stat =
                fstat(&temporary_descriptor).map_err(|error| map_errno(temporary_path, error))?;

            #[cfg(test)]
            if let Some(bytes) = &self.final_swap_after_pin {
                self.write_internal_atomic(destination, bytes)?;
            }

            renameat_with(
                &temporary_parent,
                &temporary_name,
                &destination_parent,
                &destination_name,
                RenameFlags::EXCHANGE,
            )
            .map_err(|error| map_errno(destination, error))?;
            self.checkpoint("atomic exchange before inode verification and directory fsync")?;

            let exchanged_descriptor = openat(
                &temporary_parent,
                &temporary_name,
                OFlags::RDONLY | OFlags::CLOEXEC | OFlags::NOFOLLOW,
                Mode::empty(),
            )
            .map_err(|error| map_errno(temporary_path, error))?;
            let exchanged_stat =
                fstat(&exchanged_descriptor).map_err(|error| map_errno(temporary_path, error))?;
            if exchanged_stat.st_dev != destination_stat.st_dev
                || exchanged_stat.st_ino != destination_stat.st_ino
            {
                // The final target was swapped after it was pinned. The
                // destination still names our exact candidate iff its inode is
                // the one formerly at the temporary path; only then is a
                // compensating exchange safe.
                let now_destination = openat(
                    &destination_parent,
                    &destination_name,
                    OFlags::RDONLY | OFlags::CLOEXEC | OFlags::NOFOLLOW,
                    Mode::empty(),
                )
                .and_then(|descriptor| fstat(&descriptor))
                .map_err(|error| map_errno(destination, error))?;
                if now_destination.st_dev == temporary_stat.st_dev
                    && now_destination.st_ino == temporary_stat.st_ino
                {
                    renameat_with(
                        &temporary_parent,
                        &temporary_name,
                        &destination_parent,
                        &destination_name,
                        RenameFlags::EXCHANGE,
                    )
                    .map_err(|error| map_errno(destination, error))?;
                    fsync(&destination_parent).map_err(|error| map_errno(destination, error))?;
                    fsync(&temporary_parent).map_err(|error| map_errno(temporary_path, error))?;
                }
                return Err(PortError::Conflict(format!(
                    "final target raced atomic exchange; intervening bytes were preserved at {destination}"
                )));
            }

            let mut exchanged_file = File::from(exchanged_descriptor);
            let mut exchanged_bytes = Vec::new();
            exchanged_file
                .read_to_end(&mut exchanged_bytes)
                .map_err(|error| PortError::Io {
                    path: temporary_path.into(),
                    message: error.kind().to_string(),
                })?;
            if hex_sha256(&exchanged_bytes) != expected {
                renameat_with(
                    &temporary_parent,
                    &temporary_name,
                    &destination_parent,
                    &destination_name,
                    RenameFlags::EXCHANGE,
                )
                .map_err(|error| map_errno(destination, error))?;
                fsync(&destination_parent).map_err(|error| map_errno(destination, error))?;
                fsync(&temporary_parent).map_err(|error| map_errno(temporary_path, error))?;
                return Err(PortError::Conflict(format!(
                    "replacement target contents raced atomic exchange: {destination}"
                )));
            }
            unlinkat(&temporary_parent, &temporary_name, AtFlags::empty())
                .map_err(|error| map_errno(temporary_path, error))?;
            fsync(&destination_parent).map_err(|error| map_errno(destination, error))?;
            fsync(&temporary_parent).map_err(|error| map_errno(temporary_path, error))?;
            Ok(())
        }
    }
}

impl MutationPort for OsMutationPort {
    fn probe_recovery(&self) -> Result<Vec<RecoveryProbe>, PortError> {
        #[cfg(unix)]
        {
            self.probe_recovery_unix()
        }
        #[cfg(not(unix))]
        {
            Err(PortError::Io {
                path: ".harness/recovery".into(),
                message: "safe read-only recovery probing is unavailable until Phase 7".into(),
            })
        }
    }

    fn apply(
        &self,
        request: &MutationRequest,
        validate_candidate: &mut dyn FnMut(&[u8]) -> Result<(), PortError>,
    ) -> Result<MutationResult, MutationFailure> {
        #[cfg(unix)]
        {
            self.apply_request(request, validate_candidate)
        }
        #[cfg(not(unix))]
        {
            let _ = (request, validate_candidate);
            Err(MutationFailure::before_journal(PortError::Io {
                path: ".".into(),
                message: "safe descriptor-anchored mutation is unavailable until Phase 7".into(),
            }))
        }
    }

    fn recover(
        &self,
        command: &str,
        operation_id: &str,
        mode: RecoveryMode,
        authorization: &RecoveryAuthorization,
        validate_candidate: &mut dyn FnMut(&[u8]) -> Result<(), PortError>,
    ) -> Result<MutationResult, MutationFailure> {
        #[cfg(unix)]
        {
            self.recover_request(
                command,
                operation_id,
                mode,
                authorization,
                validate_candidate,
            )
        }
        #[cfg(not(unix))]
        {
            let _ = (
                command,
                operation_id,
                mode,
                authorization,
                validate_candidate,
            );
            Err(MutationFailure::before_journal(PortError::Io {
                path: ".".into(),
                message: "safe descriptor-anchored recovery is unavailable until Phase 7".into(),
            }))
        }
    }
}

fn validate_request(request: &MutationRequest) -> Result<(), PortError> {
    if !matches!(request.command.as_str(), "install" | "update" | "scaffold")
        || !is_lower_kebab(&request.operation_id)
        || request.accepted_preview_sha256 != request.preview_sha256
        || request.writes.is_empty()
        || request
            .writes
            .last()
            .is_none_or(|write| !write.manifest_commit)
        || request.writes[..request.writes.len() - 1]
            .iter()
            .any(|write| write.manifest_commit)
    {
        return Err(invalid(
            "mutation request violates the closed Phase 3 contract",
        ));
    }
    let expected_operations = operations_from_writes(&request.operation_id, &request.writes);
    if request.operations != expected_operations {
        return Err(invalid(
            "public operations are not the exact projection of planned writes",
        ));
    }
    let manifest = request
        .writes
        .last()
        .expect("the closed request check requires a manifest step");
    let target_operations = target_operations_from_writes(&request.writes);
    let expected_operation_id = plan_operation_id(
        &request.command,
        &request.release,
        &target_operations,
        &hex_sha256(&manifest.after_bytes),
    )?;
    if request.operation_id != expected_operation_id {
        return Err(invalid(
            "operation identifier does not commit the exact mutation plan",
        ));
    }
    let operations = serde_json::to_value(&request.operations).map_err(invariant)?;
    if digest(&operations).map_err(invariant)? != request.preview_sha256 {
        return Err(invalid("mutation request preview digest mismatch"));
    }
    let mut paths = BTreeSet::new();
    let mut steps = BTreeSet::new();
    let operation_root = format!(".harness/recovery/{}", request.operation_id);
    for write in &request.writes {
        validate_relative(&write.path, true)?;
        validate_relative(&write.staged_path, true)?;
        validate_relative(&write.temporary_path, true)?;
        if let Some(path) = &write.backup_path {
            validate_relative(path, true)?;
        }
        if !paths.insert(write.path.clone())
            || !steps.insert(write.step_id.clone())
            || !is_lower_kebab(&write.step_id)
            || !is_lower_kebab(&write.operation_id)
        {
            return Err(invalid("duplicate mutation path or step identifier"));
        }
        let expected_staged = format!("{operation_root}/staged/{}.after", write.step_id);
        let expected_backup = write
            .before_sha256
            .as_ref()
            .map(|_| format!("{operation_root}/backups/{}.bak", write.step_id));
        let expected_temporary = expected_temporary_path(
            &request.operation_id,
            &write.step_id,
            &write.path,
            write.manifest_commit,
        );
        if write.manifest_commit != (write.path == MANIFEST_PATH)
            || write
                .before_sha256
                .as_ref()
                .is_some_and(|value| !is_sha256(value))
            || write.staged_path != expected_staged
            || write.backup_path != expected_backup
            || write.temporary_path != expected_temporary
        {
            return Err(invalid("mutation write identity is invalid"));
        }
        if write.manifest_commit {
            if write.operation_id != "write-manifest"
                || write.kind != OperationKind::WriteManifest
                || write.disposition != Disposition::ManagedV1
            {
                return Err(invalid(
                    "manifest step is not the exact managed write-manifest operation",
                ));
            }
        } else if !matches!(
            write.kind,
            OperationKind::Create | OperationKind::ReplaceManagedBlock
        ) || (write.kind == OperationKind::ReplaceManagedBlock
            && write.before_sha256.is_none())
        {
            return Err(invalid(
                "non-manifest write kind is outside the implemented Phase 3 boundary",
            ));
        }
    }
    Ok(())
}

fn expected_temporary_path(
    operation_id: &str,
    step_id: &str,
    path: &str,
    manifest_commit: bool,
) -> String {
    if manifest_commit {
        return format!(".harness/recovery/{operation_id}/staged/{step_id}.commit-tmp");
    }
    let name = format!(".repository-harness-tmp-{operation_id}-{step_id}");
    path.rsplit_once('/')
        .map_or(name.clone(), |(parent, _)| format!("{parent}/{name}"))
}

fn operations_from_writes(operation_id: &str, writes: &[PlannedWrite]) -> Vec<Operation> {
    let operation_root = format!(".harness/recovery/{operation_id}");
    let mut operations = vec![Operation {
        operation_id: format!("journal-{operation_id}"),
        kind: OperationKind::WriteRecoveryJournal,
        path: format!("{operation_root}/journal.json"),
        disposition: Disposition::ManagedV1,
        before_sha256: None,
        after_sha256: None,
    }];
    for write in writes {
        if let (Some(before), Some(backup_path)) = (&write.before_sha256, &write.backup_path) {
            operations.push(Operation {
                operation_id: format!("backup-{}", write.step_id),
                kind: OperationKind::Create,
                path: backup_path.clone(),
                disposition: Disposition::ManagedV1,
                before_sha256: None,
                after_sha256: Some(before.clone()),
            });
        }
        operations.push(Operation {
            operation_id: write.operation_id.clone(),
            kind: write.kind.clone(),
            path: write.path.clone(),
            disposition: write.disposition,
            before_sha256: write.before_sha256.clone(),
            after_sha256: Some(hex_sha256(&write.after_bytes)),
        });
    }
    operations
}

fn target_operations_from_writes(writes: &[PlannedWrite]) -> Vec<Operation> {
    writes
        .iter()
        .filter(|write| !write.manifest_commit)
        .map(|write| Operation {
            operation_id: write.operation_id.clone(),
            kind: write.kind.clone(),
            path: write.path.clone(),
            disposition: write.disposition,
            before_sha256: write.before_sha256.clone(),
            after_sha256: Some(hex_sha256(&write.after_bytes)),
        })
        .collect()
}

fn target_operations_from_steps(steps: &[JournalStep]) -> Vec<Operation> {
    steps
        .iter()
        .filter(|step| !step.manifest_commit)
        .map(|step| Operation {
            operation_id: step.operation_id.clone(),
            kind: step.kind.clone(),
            path: step.path.clone(),
            disposition: step.disposition,
            before_sha256: step.before_sha256.clone(),
            after_sha256: Some(step.after_sha256.clone()),
        })
        .collect()
}

fn operations_from_steps(operation_id: &str, steps: &[JournalStep]) -> Vec<Operation> {
    let operation_root = format!(".harness/recovery/{operation_id}");
    let mut operations = vec![Operation {
        operation_id: format!("journal-{operation_id}"),
        kind: OperationKind::WriteRecoveryJournal,
        path: format!("{operation_root}/journal.json"),
        disposition: Disposition::ManagedV1,
        before_sha256: None,
        after_sha256: None,
    }];
    for step in steps {
        if let (Some(before), Some(backup_path)) = (&step.before_sha256, &step.backup_path) {
            operations.push(Operation {
                operation_id: format!("backup-{}", step.step_id),
                kind: OperationKind::Create,
                path: backup_path.clone(),
                disposition: Disposition::ManagedV1,
                before_sha256: None,
                after_sha256: Some(before.clone()),
            });
        }
        operations.push(Operation {
            operation_id: step.operation_id.clone(),
            kind: step.kind.clone(),
            path: step.path.clone(),
            disposition: step.disposition,
            before_sha256: step.before_sha256.clone(),
            after_sha256: Some(step.after_sha256.clone()),
        });
    }
    operations
}

fn plan_operation_id(
    command: &str,
    release: &PayloadIdentity,
    target_operations: &[Operation],
    manifest_sha256: &str,
) -> Result<String, PortError> {
    let seed = serde_json::json!({
        "command": command,
        "release": release,
        "target_operations": target_operations,
        "manifest_sha256": manifest_sha256,
    });
    Ok(format!("{command}-{}", digest(&seed).map_err(invariant)?))
}

fn validate_journal_ownership(
    journal: &RecoveryJournal,
    command: &str,
    operation_id: &str,
    authorization: &RecoveryAuthorization,
) -> Result<(), PortError> {
    journal.verify()?;
    if journal.command != command
        || journal.operation_id != operation_id
        || journal.release != authorization.release
        || !is_lower_kebab(operation_id)
    {
        return Err(invalid(
            "recovery command, operation, or release identity mismatch",
        ));
    }
    let operation_root = OsMutationPort::operation_root(operation_id);
    let mut paths = BTreeSet::new();
    for step in &journal.steps {
        if !is_lower_kebab(&step.step_id) || !is_lower_kebab(&step.operation_id) {
            return Err(invalid("journal step or operation identifier is invalid"));
        }
        validate_relative(&step.path, true)?;
        validate_relative(&step.staged_path, true)?;
        validate_relative(&step.temporary_path, true)?;
        if let Some(path) = &step.backup_path {
            validate_relative(path, true)?;
        }
        let authorized_target =
            step.path == MANIFEST_PATH || authorization.asset_paths.contains(&step.path);
        let expected_staged = format!("{operation_root}/staged/{}.after", step.step_id);
        let expected_backup = step
            .before_sha256
            .as_ref()
            .map(|_| format!("{operation_root}/backups/{}.bak", step.step_id));
        let parent = step.path.rsplit_once('/').map_or("", |(parent, _)| parent);
        let expected_temporary = if step.manifest_commit {
            format!("{operation_root}/staged/{}.commit-tmp", step.step_id)
        } else if parent.is_empty() {
            format!(".repository-harness-tmp-{operation_id}-{}", step.step_id)
        } else {
            format!(
                "{parent}/.repository-harness-tmp-{operation_id}-{}",
                step.step_id
            )
        };
        if !authorized_target
            || step.staged_path != expected_staged
            || step.backup_path != expected_backup
            || step.temporary_path != expected_temporary
            || !paths.insert(step.path.clone())
        {
            return Err(invalid("journal path is not command/release-owned"));
        }
        if step.manifest_commit {
            if step.operation_id != "write-manifest"
                || step.kind != OperationKind::WriteManifest
                || step.disposition != Disposition::ManagedV1
                || step.path != MANIFEST_PATH
            {
                return Err(invalid(
                    "journal manifest step is not the exact managed write-manifest operation",
                ));
            }
        } else if !matches!(
            step.kind,
            OperationKind::Create | OperationKind::ReplaceManagedBlock
        ) || (step.kind == OperationKind::ReplaceManagedBlock
            && step.before_sha256.is_none())
        {
            return Err(invalid(
                "journal target kind is outside the implemented Phase 3 boundary",
            ));
        }
    }
    if journal
        .steps
        .last()
        .is_none_or(|step| !step.manifest_commit)
        || journal
            .steps
            .iter()
            .filter(|step| step.manifest_commit)
            .count()
            != 1
    {
        return Err(invalid("journal does not commit one manifest last"));
    }
    let expected_operations = operations_from_steps(operation_id, &journal.steps);
    if journal.operations != expected_operations {
        return Err(invalid(
            "journal operations are not the exact projection of journal steps",
        ));
    }
    let manifest_sha256 = &journal
        .steps
        .last()
        .expect("the manifest-last check requires a final step")
        .after_sha256;
    let target_operations = target_operations_from_steps(&journal.steps);
    let expected_operation_id = plan_operation_id(
        command,
        &authorization.release,
        &target_operations,
        manifest_sha256,
    )?;
    if operation_id != expected_operation_id {
        return Err(invalid(
            "recovery operation identifier does not authorize the exact post-images",
        ));
    }
    for step in journal.steps.iter().filter(|step| !step.manifest_commit) {
        if step.kind == OperationKind::Create
            && authorization.asset_sha256.get(&step.path) != Some(&step.after_sha256)
        {
            return Err(invalid(format!(
                "{} is not the exact authenticated asset post-image",
                step.path
            )));
        }
    }
    verify_preview(journal)
}

fn verify_preview(journal: &RecoveryJournal) -> Result<(), PortError> {
    let operations = serde_json::to_value(&journal.operations).map_err(invariant)?;
    let actual = digest(&operations).map_err(invariant)?;
    if actual != journal.preview_sha256 || journal.accepted_preview_sha256 != journal.preview_sha256
    {
        return Err(PortError::Conflict(
            "accepted preview digest no longer matches the journal plan".into(),
        ));
    }
    Ok(())
}

fn managed_block_parts(bytes: &[u8], marker: &str) -> Result<ManagedBlockParts, PortError> {
    let text = std::str::from_utf8(bytes)
        .map_err(|_| invalid("managed block is not UTF-8 during recovery"))?;
    let open = format!("<!-- repository-harness:v1:begin:{marker} -->");
    let close = format!("<!-- repository-harness:v1:end:{marker} -->");
    let open_start = text
        .find(&open)
        .ok_or_else(|| invalid("managed block opening marker is missing during recovery"))?;
    let content_start = open_start + open.len();
    let close_start = text[content_start..]
        .find(&close)
        .map(|offset| content_start + offset)
        .ok_or_else(|| invalid("managed block closing marker is missing during recovery"))?;
    if text.matches(&open).count() != 1 || text[content_start..].matches(&close).count() != 1 {
        return Err(invalid(
            "managed block marker pair is not unique during recovery",
        ));
    }
    Ok((
        bytes[..content_start].to_vec(),
        bytes[content_start..close_start].to_vec(),
        bytes[close_start..].to_vec(),
    ))
}

fn managed_candidate_interior(bytes: &[u8], marker: &str) -> Result<Vec<u8>, PortError> {
    let open = format!("<!-- repository-harness:v1:begin:{marker} -->");
    if std::str::from_utf8(bytes).is_ok_and(|text| text.contains(&open)) {
        managed_block_parts(bytes, marker).map(|(_, interior, _)| interior)
    } else {
        Ok(bytes.to_vec())
    }
}

fn invalid(message: impl ToString) -> PortError {
    PortError::ManifestInvalid(message.to_string())
}

fn invariant(message: impl ToString) -> PortError {
    PortError::ManifestInvalid(format!("Phase 3 invariant: {}", message.to_string()))
}

fn is_lower_kebab(value: &str) -> bool {
    !value.is_empty()
        && value
            .bytes()
            .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'-')
        && value.as_bytes()[0].is_ascii_alphanumeric()
        && value.as_bytes()[value.len() - 1].is_ascii_alphanumeric()
}

fn is_sha256(value: &str) -> bool {
    value.len() == 64
        && value
            .bytes()
            .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
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
fn map_errno(path: &str, error: rustix::io::Errno) -> PortError {
    if error == rustix::io::Errno::NOENT || error == rustix::io::Errno::NOTDIR {
        PortError::Missing(path.into())
    } else if error == rustix::io::Errno::LOOP {
        PortError::Link(path.into())
    } else if matches!(
        error,
        rustix::io::Errno::EXIST | rustix::io::Errno::NOTEMPTY
    ) {
        PortError::Conflict(format!("exclusive filesystem operation failed at {path}"))
    } else {
        PortError::Io {
            path: path.into(),
            message: error.to_string(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::domain::{Disposition, OperationKind};
    use crate::ports::MutationPort;

    fn request() -> MutationRequest {
        let asset = b"managed\n".to_vec();
        let release = PayloadIdentity {
            trust_domain: "repository-harness-core".into(),
            role: "core-release".into(),
            sequence: 42,
            index_sha256: "a".repeat(64),
        };
        let mut manifest = serde_json::to_vec(&serde_json::json!({
            "schema": "repository-harness-manifest/v1",
            "repository_mode": "fresh-v1",
            "compatibility": {
                "cli_min": "1.0.0",
                "cli_max": "1.0.0",
                "template_release_min": "1.0.0",
                "template_release_max": "1.999.999"
            },
            "payload": release,
            "roles": []
        }))
        .unwrap();
        manifest.push(b'\n');
        let target_operations = vec![Operation {
            operation_id: "write-001-managed".into(),
            kind: OperationKind::Create,
            path: "managed.md".into(),
            disposition: Disposition::ManagedV1,
            before_sha256: None,
            after_sha256: Some(hex_sha256(&asset)),
        }];
        let operation_id = plan_operation_id(
            "install",
            &release,
            &target_operations,
            &hex_sha256(&manifest),
        )
        .unwrap();
        let write = |step: &str,
                     operation: &str,
                     kind: OperationKind,
                     path: &str,
                     bytes: Vec<u8>,
                     manifest_commit: bool| PlannedWrite {
            step_id: step.into(),
            operation_id: operation.into(),
            kind,
            disposition: Disposition::ManagedV1,
            path: path.into(),
            before_sha256: None,
            after_bytes: bytes,
            backup_path: None,
            staged_path: format!(".harness/recovery/{operation_id}/staged/{step}.after"),
            temporary_path: if manifest_commit {
                format!(".harness/recovery/{operation_id}/staged/{step}.commit-tmp")
            } else if let Some((parent, _)) = path.rsplit_once('/') {
                format!("{parent}/.repository-harness-tmp-{operation_id}-{step}")
            } else {
                format!(".repository-harness-tmp-{operation_id}-{step}")
            },
            manifest_commit,
        };
        let writes = vec![
            write(
                "target-001-managed",
                "write-001-managed",
                OperationKind::Create,
                "managed.md",
                asset,
                false,
            ),
            write(
                "manifest",
                "write-manifest",
                OperationKind::WriteManifest,
                MANIFEST_PATH,
                manifest,
                true,
            ),
        ];
        let operations = operations_from_writes(&operation_id, &writes);
        let preview_sha256 = digest(&serde_json::to_value(&operations).unwrap()).unwrap();
        MutationRequest {
            command: "install".into(),
            operation_id,
            preview_sha256: preview_sha256.clone(),
            accepted_preview_sha256: preview_sha256,
            release,
            operations,
            writes,
        }
    }

    fn authorization(request: &MutationRequest) -> RecoveryAuthorization {
        let bytes = b"managed\n".to_vec();
        RecoveryAuthorization {
            release: request.release.clone(),
            asset_paths: BTreeSet::from(["managed.md".into()]),
            asset_sha256: BTreeMap::from([("managed.md".into(), hex_sha256(&bytes))]),
            asset_bytes: BTreeMap::from([("managed.md".into(), bytes)]),
        }
    }

    fn replacement_request(old_target: &[u8], old_manifest: &[u8]) -> MutationRequest {
        let mut request = request();
        request.command = "update".into();
        request.writes[0].before_sha256 = Some(hex_sha256(old_target));
        request.writes[1].before_sha256 = Some(hex_sha256(old_manifest));
        let target_operations = target_operations_from_writes(&request.writes);
        request.operation_id = plan_operation_id(
            &request.command,
            &request.release,
            &target_operations,
            &hex_sha256(&request.writes[1].after_bytes),
        )
        .unwrap();
        let operation_root = format!(".harness/recovery/{}", request.operation_id);
        for write in &mut request.writes {
            write.backup_path = Some(format!("{operation_root}/backups/{}.bak", write.step_id));
            write.staged_path = format!("{operation_root}/staged/{}.after", write.step_id);
            write.temporary_path = if write.manifest_commit {
                format!("{operation_root}/staged/{}.commit-tmp", write.step_id)
            } else {
                format!(
                    ".repository-harness-tmp-{}-{}",
                    request.operation_id, write.step_id
                )
            };
        }
        request.operations = operations_from_writes(&request.operation_id, &request.writes);
        request.preview_sha256 =
            digest(&serde_json::to_value(&request.operations).unwrap()).unwrap();
        request.accepted_preview_sha256 = request.preview_sha256.clone();
        request
    }

    fn rebind_request(request: &mut MutationRequest) {
        let target_operations = target_operations_from_writes(&request.writes);
        request.operation_id = plan_operation_id(
            &request.command,
            &request.release,
            &target_operations,
            &hex_sha256(&request.writes.last().unwrap().after_bytes),
        )
        .unwrap();
        let operation_root = format!(".harness/recovery/{}", request.operation_id);
        for write in &mut request.writes {
            if write.backup_path.is_some() {
                write.backup_path = Some(format!("{operation_root}/backups/{}.bak", write.step_id));
            }
            write.staged_path = format!("{operation_root}/staged/{}.after", write.step_id);
            write.temporary_path = expected_temporary_path(
                &request.operation_id,
                &write.step_id,
                &write.path,
                write.manifest_commit,
            );
        }
        request.operations = operations_from_writes(&request.operation_id, &request.writes);
        request.preview_sha256 =
            digest(&serde_json::to_value(&request.operations).unwrap()).unwrap();
        request.accepted_preview_sha256 = request.preview_sha256.clone();
    }

    #[cfg(unix)]
    #[test]
    fn manifest_is_committed_last_and_rollback_removes_exact_created_images() {
        let temporary = tempfile::tempdir().unwrap();
        let port = OsMutationPort::new(temporary.path()).unwrap();
        let request = request();
        let result = port
            .apply(&request, &mut |_| Ok(()))
            .expect("apply succeeds");
        assert!(matches!(result, MutationResult::Committed { .. }));
        assert_eq!(
            std::fs::read(temporary.path().join("managed.md")).unwrap(),
            b"managed\n"
        );
        assert!(temporary.path().join(MANIFEST_PATH).is_file());

        let authorization = authorization(&request);
        let result = port
            .recover(
                "install",
                &request.operation_id,
                RecoveryMode::Rollback,
                &authorization,
                &mut |_| Ok(()),
            )
            .unwrap();
        assert_eq!(result, MutationResult::RolledBack);
        assert!(!temporary.path().join("managed.md").exists());
        assert!(!temporary.path().join(MANIFEST_PATH).exists());
    }

    #[cfg(unix)]
    #[test]
    fn target_edit_blocks_rollback_before_any_restoration() {
        let temporary = tempfile::tempdir().unwrap();
        let port = OsMutationPort::new(temporary.path()).unwrap();
        let request = request();
        port.apply(&request, &mut |_| Ok(())).unwrap();
        std::fs::write(temporary.path().join("managed.md"), b"human edit\n").unwrap();
        let manifest_before = std::fs::read(temporary.path().join(MANIFEST_PATH)).unwrap();
        let authorization = authorization(&request);
        let result = port.recover(
            "install",
            &request.operation_id,
            RecoveryMode::Rollback,
            &authorization,
            &mut |_| Ok(()),
        );
        assert!(matches!(
            result,
            Err(MutationFailure {
                error: PortError::Conflict(_),
                journal_started: true
            })
        ));
        assert_eq!(
            std::fs::read(temporary.path().join(MANIFEST_PATH)).unwrap(),
            manifest_before
        );
    }

    #[test]
    fn accepted_preview_cannot_authorize_mismatched_planned_write_bytes() {
        let temporary = tempfile::tempdir().unwrap();
        let port = OsMutationPort::new(temporary.path()).unwrap();
        let mut request = request();
        request.writes[0].after_bytes = b"different staged bytes\n".to_vec();

        let result = port.apply(&request, &mut |_| Ok(()));

        assert!(matches!(
            result,
            Err(MutationFailure {
                error: PortError::ManifestInvalid(_),
                journal_started: false
            })
        ));
        assert!(!temporary.path().join("managed.md").exists());
        assert!(!temporary.path().join(".harness").exists());
    }

    #[cfg(unix)]
    #[test]
    fn unrelated_private_staged_path_is_rejected_before_zero_filesystem_mutation() {
        let temporary = tempfile::tempdir().unwrap();
        let port = OsMutationPort::new(temporary.path()).unwrap();
        let mut request = request();
        request.writes[0].staged_path = "unrelated-safe-path".into();

        let result = port.apply(&request, &mut |_| Ok(()));

        assert!(matches!(
            result,
            Err(MutationFailure {
                error: PortError::ManifestInvalid(_),
                journal_started: false
            })
        ));
        assert!(!temporary.path().join("unrelated-safe-path").exists());
        assert!(!temporary.path().join("managed.md").exists());
        assert!(!temporary.path().join(".harness").exists());
    }

    #[cfg(unix)]
    #[test]
    fn backup_manifest_and_kind_invariants_fail_before_zero_filesystem_mutation() {
        type RequestMutation = fn(&mut MutationRequest);
        let variants: [(&str, RequestMutation); 4] = [
            ("before-without-backup", |request| {
                request.writes[0].before_sha256 = Some("d".repeat(64));
                rebind_request(request);
            }),
            ("manifest-kind", |request| {
                request.writes[1].kind = OperationKind::Create;
                rebind_request(request);
            }),
            ("manifest-disposition", |request| {
                request.writes[1].disposition = Disposition::OptionalV1;
                rebind_request(request);
            }),
            ("unsupported-target-kind", |request| {
                request.writes[0].kind = OperationKind::RemoveManagedFile;
                rebind_request(request);
            }),
        ];
        for (label, mutate) in variants {
            let temporary = tempfile::tempdir().unwrap();
            let port = OsMutationPort::new(temporary.path()).unwrap();
            let mut request = request();
            mutate(&mut request);
            let result = port.apply(&request, &mut |_| Ok(()));
            assert!(
                matches!(
                    result,
                    Err(MutationFailure {
                        error: PortError::ManifestInvalid(_),
                        journal_started: false
                    })
                ),
                "{label}: {result:?}"
            );
            assert!(!temporary.path().join("managed.md").exists(), "{label}");
            assert!(!temporary.path().join(".harness").exists(), "{label}");
        }
    }

    #[cfg(unix)]
    #[test]
    fn recomputed_unkeyed_journal_digest_cannot_change_authorized_manifest_post_image() {
        let temporary = tempfile::tempdir().unwrap();
        let request = request();
        let killed = OsMutationPort::with_kill_after_checkpoint(temporary.path(), 3).unwrap();
        assert!(killed.apply(&request, &mut |_| Ok(())).is_err());
        assert!(!temporary.path().join("managed.md").exists());

        let port = OsMutationPort::new(temporary.path()).unwrap();
        let mut journal = port.load_journal(&request.operation_id).unwrap();
        let manifest = journal.steps.last_mut().unwrap();
        let mut value = parse(&port.read_required(&manifest.staged_path).unwrap()).unwrap();
        value["compatibility"]["cli_max"] = serde_json::Value::String("1.0.1".into());
        let mut altered = canonical(&value).unwrap();
        altered.push(b'\n');
        port.write_internal_atomic(&manifest.staged_path, &altered)
            .unwrap();
        manifest.after_sha256 = hex_sha256(&altered);
        journal
            .operations
            .iter_mut()
            .find(|operation| operation.kind == OperationKind::WriteManifest)
            .unwrap()
            .after_sha256 = Some(manifest.after_sha256.clone());
        journal.preview_sha256 =
            digest(&serde_json::to_value(&journal.operations).unwrap()).unwrap();
        journal.accepted_preview_sha256 = journal.preview_sha256.clone();
        port.persist_journal(&journal).unwrap();
        assert!(port.load_journal(&request.operation_id).is_ok());

        let result = port.recover(
            "install",
            &request.operation_id,
            RecoveryMode::Resume,
            &authorization(&request),
            &mut |_| Ok(()),
        );
        assert!(matches!(
            result,
            Err(MutationFailure {
                error: PortError::ManifestInvalid(_),
                journal_started: true
            })
        ));
        assert!(!temporary.path().join("managed.md").exists());
        assert!(!temporary.path().join(MANIFEST_PATH).exists());
    }

    #[cfg(unix)]
    #[test]
    fn recomputed_journal_body_cannot_tamper_command_path_operation_before_after_or_acceptance() {
        type JournalMutation = fn(&mut RecoveryJournal);
        let attacks: [(&str, JournalMutation); 7] = [
            ("command", |journal| journal.command = "update".into()),
            ("journal-operation-id", |journal| {
                journal.operation_id = "0".repeat(64)
            }),
            ("step-path", |journal| {
                journal.steps[0].path = "unrelated-safe-path".into()
            }),
            ("step-before-digest", |journal| {
                journal.steps[0].before_sha256 = Some("a".repeat(64))
            }),
            ("step-after-digest", |journal| {
                journal.steps[0].after_sha256 = "b".repeat(64)
            }),
            ("public-operation-row", |journal| {
                journal.operations[0].after_sha256 = Some("c".repeat(64))
            }),
            ("accepted-preview", |journal| {
                journal.accepted_preview_sha256 = "d".repeat(64)
            }),
        ];

        for (attack, mutate) in attacks {
            let temporary = tempfile::tempdir().unwrap();
            let request = request();
            let killed = OsMutationPort::with_kill_after_checkpoint(temporary.path(), 3).unwrap();
            assert!(killed.apply(&request, &mut |_| Ok(())).is_err());
            let port = OsMutationPort::new(temporary.path()).unwrap();
            let mut journal = port.load_journal(&request.operation_id).unwrap();
            mutate(&mut journal);
            // Persist the tampered bytes at the *owned* journal path.  Using
            // persist_journal here would derive a new path from a mutated
            // operation_id and leave the authoritative journal untouched,
            // making the attack appear to succeed for the wrong reason.
            let encoded = journal.encoded().unwrap();
            port.write_internal_atomic(
                &OsMutationPort::journal_path(&request.operation_id),
                &encoded,
            )
            .unwrap();
            let surviving_recovery_artifact = port
                .read_required(&OsMutationPort::journal_path(&request.operation_id))
                .unwrap();

            let result = port.recover(
                "install",
                &request.operation_id,
                RecoveryMode::Resume,
                &authorization(&request),
                &mut |_| Ok(()),
            );

            assert!(
                matches!(
                    result,
                    Err(MutationFailure {
                        error: PortError::ManifestInvalid(_) | PortError::Conflict(_),
                        journal_started: true
                    })
                ),
                "tamper attack {attack}: {result:?}"
            );
            assert!(!temporary.path().join("managed.md").exists(), "{attack}");
            assert!(!temporary.path().join(MANIFEST_PATH).exists(), "{attack}");
            assert_eq!(
                port.read_required(&OsMutationPort::journal_path(&request.operation_id))
                    .unwrap(),
                surviving_recovery_artifact,
                "tamper attack {attack}: evidence remains byte-for-byte intact"
            );
        }
    }

    #[cfg(unix)]
    #[test]
    fn nested_operation_unknown_field_is_rejected_even_with_recomputed_body_digest() {
        let temporary = tempfile::tempdir().unwrap();
        let request = request();
        let killed = OsMutationPort::with_kill_after_checkpoint(temporary.path(), 3).unwrap();
        assert!(killed.apply(&request, &mut |_| Ok(())).is_err());
        let port = OsMutationPort::new(temporary.path()).unwrap();
        let journal_path = OsMutationPort::journal_path(&request.operation_id);
        let mut raw = parse(&port.read_required(&journal_path).unwrap()).unwrap();
        raw["operations"][1]["undeclared_nested_member"] = serde_json::json!(true);
        raw["body_sha256"] = serde_json::Value::String(String::new());
        let body_sha256 = digest(&raw).unwrap();
        raw["body_sha256"] = serde_json::Value::String(body_sha256);
        let mut encoded = canonical(&raw).unwrap();
        encoded.push(b'\n');
        port.write_internal_atomic(&journal_path, &encoded).unwrap();

        assert!(matches!(
            port.load_journal(&request.operation_id),
            Err(PortError::ManifestInvalid(_))
        ));
        assert!(!temporary.path().join("managed.md").exists());
        assert!(!temporary.path().join(MANIFEST_PATH).exists());
    }

    #[cfg(unix)]
    #[test]
    fn rollback_does_not_restore_old_manifest_when_manifest_step_was_never_applied() {
        let temporary = tempfile::tempdir().unwrap();
        let old_target = b"old managed\n".to_vec();
        let mut old_manifest = request().writes[1].after_bytes.clone();
        let needle = b"\"sequence\":42";
        let start = old_manifest
            .windows(needle.len())
            .position(|window| window == needle)
            .unwrap();
        old_manifest[start..start + needle.len()].copy_from_slice(b"\"sequence\":41");
        std::fs::create_dir_all(temporary.path().join(".harness")).unwrap();
        std::fs::write(temporary.path().join("managed.md"), &old_target).unwrap();
        std::fs::write(temporary.path().join(MANIFEST_PATH), &old_manifest).unwrap();
        let request = replacement_request(&old_target, &old_manifest);
        let killed = OsMutationPort::with_kill_after_checkpoint(temporary.path(), 9).unwrap();
        assert!(killed.apply(&request, &mut |_| Ok(())).is_err());
        assert_eq!(
            std::fs::read(temporary.path().join("managed.md")).unwrap(),
            b"managed\n"
        );
        assert_eq!(
            std::fs::read(temporary.path().join(MANIFEST_PATH)).unwrap(),
            old_manifest
        );

        let port = OsMutationPort::new(temporary.path()).unwrap();
        let result = port
            .recover(
                "update",
                &request.operation_id,
                RecoveryMode::Rollback,
                &authorization(&request),
                &mut |_| Ok(()),
            )
            .unwrap();
        assert_eq!(result, MutationResult::RolledBack);
        assert_eq!(
            std::fs::read(temporary.path().join("managed.md")).unwrap(),
            old_target
        );
        assert_eq!(
            std::fs::read(temporary.path().join(MANIFEST_PATH)).unwrap(),
            old_manifest
        );
    }

    #[cfg(all(unix, any(target_os = "linux", target_os = "macos")))]
    #[test]
    fn final_component_swap_is_reversed_without_clobbering_intervening_bytes() {
        let temporary = tempfile::tempdir().unwrap();
        std::fs::write(temporary.path().join("managed.md"), b"old managed\n").unwrap();
        let port = OsMutationPort::with_final_swap_after_pin(
            temporary.path(),
            b"intervening human edit\n".to_vec(),
        )
        .unwrap();
        port.write_temporary(".candidate", b"authenticated candidate\n")
            .unwrap();

        let result = port.rename_temporary(
            ".candidate",
            "managed.md",
            Some(&hex_sha256(b"old managed\n")),
        );

        assert!(matches!(result, Err(PortError::Conflict(_))));
        assert_eq!(
            std::fs::read(temporary.path().join("managed.md")).unwrap(),
            b"intervening human edit\n"
        );
    }
}
