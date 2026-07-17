use std::path::{Path, PathBuf};

use hmac::{Hmac, Mac};
use serde::{Deserialize, Serialize};
use sha2::Sha256;

use crate::secure_fs::{RootIdentity, SecureRoot};
use crate::{BridgeError, Result};

pub const JOURNAL_SCHEMA: &str = "repository-harness-v0-conversion-journal/v1";
const AUTH_KEY_PATH: &str = ".harness/recovery/v0-conversion/journal-auth.key";

#[derive(Clone, Copy, Debug, Serialize, Deserialize, PartialEq, Eq, PartialOrd, Ord)]
#[serde(rename_all = "kebab-case")]
pub enum JournalState {
    Discovered,
    Inspected,
    Exported,
    Archived,
    Prepared,
    Applying,
    Committed,
    Completed,
    RollingBack,
    RolledBack,
    RecoveryRequired,
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Journal {
    pub schema: String,
    pub authentication: String,
    pub root: RootIdentity,
    pub conversion_id: String,
    pub operation_id: String,
    pub state: JournalState,
    pub source_schema: u32,
    pub source_sha256: String,
    pub capture_members_sha256: String,
    pub export_sha256: Option<String>,
    pub standalone_backup_sha256: String,
    pub archive_sha256: Option<String>,
    pub archive_manifest_sha256: Option<String>,
    pub archive_staging_path: Option<String>,
    pub archive_path: Option<String>,
    pub confidentiality_mode: Option<String>,
    pub recipient_fingerprints: Vec<String>,
    pub plaintext_risk_acknowledged: Option<bool>,
    pub preview_sha256: String,
    pub manifest_before_sha256: Option<String>,
    pub manifest_after_sha256: Option<String>,
    pub receipt_sha256: Option<String>,
    pub rolled_back: bool,
}

impl Journal {
    pub fn new(
        root: RootIdentity,
        conversion_id: String,
        source_schema: u32,
        source_sha256: String,
        capture_members_sha256: String,
        standalone_backup_sha256: String,
        preview_sha256: String,
    ) -> Self {
        Self {
            schema: JOURNAL_SCHEMA.into(),
            authentication: String::new(),
            root,
            operation_id: format!("v0-conversion:{conversion_id}"),
            conversion_id,
            state: JournalState::Discovered,
            source_schema,
            source_sha256,
            capture_members_sha256,
            export_sha256: None,
            standalone_backup_sha256,
            archive_sha256: None,
            archive_manifest_sha256: None,
            archive_staging_path: None,
            archive_path: None,
            confidentiality_mode: None,
            recipient_fingerprints: Vec::new(),
            plaintext_risk_acknowledged: None,
            preview_sha256,
            manifest_before_sha256: None,
            manifest_after_sha256: None,
            receipt_sha256: None,
            rolled_back: false,
        }
    }

    fn authenticated_bytes(&self) -> Result<Vec<u8>> {
        let mut body = self.clone();
        body.authentication.clear();
        Ok(serde_json::to_vec(&body)?)
    }

    fn validate_shape(&self) -> Result<()> {
        if self.schema != JOURNAL_SCHEMA
            || self.operation_id != format!("v0-conversion:{}", self.conversion_id)
            || self.conversion_id.is_empty()
            || self.source_schema == 0
            || !is_digest(&self.source_sha256)
            || !is_digest(&self.capture_members_sha256)
            || !is_digest(&self.standalone_backup_sha256)
            || !is_digest(&self.preview_sha256)
            || !self.export_sha256.as_deref().is_none_or(is_digest)
            || !self.archive_sha256.as_deref().is_none_or(is_digest)
            || !self
                .archive_manifest_sha256
                .as_deref()
                .is_none_or(is_digest)
            || self.archive_staging_path.as_deref().is_some_and(|path| {
                !path.starts_with(".harness/recovery/v0-conversion/")
                    || path.contains("..")
                    || path.contains('\\')
            })
            || !self.manifest_before_sha256.as_deref().is_none_or(is_digest)
            || !self.manifest_after_sha256.as_deref().is_none_or(is_digest)
            || !self.receipt_sha256.as_deref().is_none_or(is_digest)
        {
            return Err(BridgeError::Invalid(
                "conversion journal is outside its closed schema".into(),
            ));
        }
        if self.state >= JournalState::Exported && self.export_sha256.is_none() {
            return Err(BridgeError::Invalid(
                "exported journal state lacks its immutable export witness".into(),
            ));
        }
        if matches!(
            self.state,
            JournalState::Archived
                | JournalState::Prepared
                | JournalState::Applying
                | JournalState::Committed
                | JournalState::Completed
                | JournalState::RollingBack
                | JournalState::RolledBack
        ) && (self.archive_sha256.is_none()
            || self.archive_manifest_sha256.is_none()
            || self.archive_path.is_none())
        {
            return Err(BridgeError::Invalid(
                "archived journal state lacks archive witnesses".into(),
            ));
        }
        if matches!(
            self.state,
            JournalState::Prepared
                | JournalState::Applying
                | JournalState::Committed
                | JournalState::Completed
                | JournalState::RollingBack
                | JournalState::RolledBack
        ) && (self.manifest_after_sha256.is_none() || self.receipt_sha256.is_none())
        {
            return Err(BridgeError::Invalid(
                "prepared journal state lacks target and receipt witnesses".into(),
            ));
        }
        if self.state == JournalState::RolledBack && !self.rolled_back {
            return Err(BridgeError::Invalid(
                "rolled-back journal lacks its terminal witness".into(),
            ));
        }
        Ok(())
    }
}

pub fn path(root: &Path, conversion_id: &str) -> PathBuf {
    root.join(relative_path(conversion_id))
}

pub fn relative_path(conversion_id: &str) -> String {
    format!(".harness/recovery/v0-conversion/{conversion_id}/journal.json")
}

pub fn load(root: &Path, conversion_id: &str) -> Result<Journal> {
    let root = SecureRoot::open(root)?;
    load_pinned(&root, conversion_id)
}

pub(crate) fn load_pinned(root: &SecureRoot, conversion_id: &str) -> Result<Journal> {
    root.validate_root()?;
    let bytes = root.read(&relative_path(conversion_id))?;
    let journal: Journal = serde_json::from_slice(&bytes).map_err(|error| {
        BridgeError::Invalid(format!("conversion journal is malformed: {error}"))
    })?;
    verify(root, &journal)?;
    if journal.conversion_id != conversion_id {
        return Err(BridgeError::Conflict(
            "journal path and authenticated conversion identity differ".into(),
        ));
    }
    Ok(journal)
}

pub fn save(root: &Path, journal: &Journal) -> Result<()> {
    let root = SecureRoot::open(root)?;
    save_pinned(&root, journal)
}

#[cfg(unix)]
pub(crate) fn save_pinned(root: &SecureRoot, journal: &Journal) -> Result<()> {
    root.validate_root()?;
    if journal.root != root.identity() {
        return Err(BridgeError::Conflict(
            "journal repository-root identity differs from the pinned root".into(),
        ));
    }
    journal.validate_shape()?;
    root.open_dir(".harness", true, false)?;
    let conversion_root_preexisting = root
        .open_dir(".harness/recovery/v0-conversion", false, true)
        .is_ok();
    let journal_relative = relative_path(&journal.conversion_id);
    if !root.exists(&journal_relative)? && conversion_root_preexisting {
        return Err(BridgeError::Conflict(
            "pre-existing recovery custody cannot become bridge-owned authority".into(),
        ));
    }
    root.open_dir(".harness/recovery", true, true)?;
    root.open_dir(".harness/recovery/v0-conversion", true, true)?;
    let journal_directory = format!(".harness/recovery/v0-conversion/{}", journal.conversion_id);
    match root.open_dir(&journal_directory, false, true) {
        Ok(_) => {}
        Err(BridgeError::Errno(error)) if error == rustix::io::Errno::NOENT => {
            root.create_dir_exact(&journal_directory)?;
        }
        Err(error) => return Err(error),
    }
    let relative = relative_path(&journal.conversion_id);
    let journal_exists = root.exists(&relative)?;
    let key = load_key(root, !journal_exists)?;
    if journal_exists {
        let old = load_pinned(root, &journal.conversion_id)?;
        validate_transition(&old, journal)?;
    } else if journal.state != JournalState::Discovered {
        return Err(BridgeError::Conflict(
            "a new journal must begin at discovered".into(),
        ));
    }
    let mut encoded = journal.clone();
    encoded.authentication = authenticate(&key, &encoded.authenticated_bytes()?)?;
    let mut bytes = serde_json::to_vec(&encoded)?;
    bytes.push(b'\n');
    root.write_atomic_owned(&relative, &bytes)?;
    root.validate_root()?;
    Ok(())
}

#[cfg(not(unix))]
pub(crate) fn save_pinned(_root: &SecureRoot, _journal: &Journal) -> Result<()> {
    Err(BridgeError::Unsupported(
        "descriptor-relative journal custody is unavailable until Phase 7".into(),
    ))
}

pub(crate) fn verify(root: &SecureRoot, journal: &Journal) -> Result<()> {
    journal.validate_shape()?;
    if journal.root != root.identity() {
        return Err(BridgeError::Conflict(
            "copied journal does not belong to this repository root".into(),
        ));
    }
    let key = load_key(root, false)?;
    let expected = authenticate(&key, &journal.authenticated_bytes()?)?;
    if !constant_time_eq(expected.as_bytes(), journal.authentication.as_bytes()) {
        return Err(BridgeError::Conflict(
            "journal authentication or ownership verification failed".into(),
        ));
    }
    Ok(())
}

fn load_key(root: &SecureRoot, create: bool) -> Result<Vec<u8>> {
    match root.read_optional(AUTH_KEY_PATH)? {
        Some(_) if !create => root.read_private_regular(AUTH_KEY_PATH, 32),
        Some(_) => Err(BridgeError::Conflict(
            "pre-existing journal authentication key cannot be adopted".into(),
        )),
        None if create => {
            let mut key = vec![0_u8; 32];
            getrandom::getrandom(&mut key).map_err(|error| {
                BridgeError::Io(std::io::Error::other(format!(
                    "journal authentication randomness failed: {error}"
                )))
            })?;
            root.write_new(AUTH_KEY_PATH, &key)?;
            root.read_private_regular(AUTH_KEY_PATH, 32)
        }
        None => Err(BridgeError::Conflict(
            "journal authentication key is absent; no mutation is authorized".into(),
        )),
    }
}

fn authenticate(key: &[u8], bytes: &[u8]) -> Result<String> {
    let mut mac = Hmac::<Sha256>::new_from_slice(key)
        .map_err(|_| BridgeError::Invalid("invalid journal authentication key".into()))?;
    mac.update(bytes);
    Ok(format!("{:x}", mac.finalize().into_bytes()))
}

fn constant_time_eq(left: &[u8], right: &[u8]) -> bool {
    if left.len() != right.len() {
        return false;
    }
    left.iter()
        .zip(right)
        .fold(0_u8, |difference, (left, right)| {
            difference | (left ^ right)
        })
        == 0
}

fn validate_transition(old: &Journal, new: &Journal) -> Result<()> {
    let immutable = old.schema == new.schema
        && old.root == new.root
        && old.conversion_id == new.conversion_id
        && old.operation_id == new.operation_id
        && old.source_schema == new.source_schema
        && old.source_sha256 == new.source_sha256
        && old.capture_members_sha256 == new.capture_members_sha256
        && old.standalone_backup_sha256 == new.standalone_backup_sha256
        && old.preview_sha256 == new.preview_sha256
        && option_is_immutable(&old.export_sha256, &new.export_sha256)
        && option_is_immutable(&old.archive_sha256, &new.archive_sha256)
        && option_is_immutable(&old.archive_manifest_sha256, &new.archive_manifest_sha256)
        && option_is_immutable(&old.archive_staging_path, &new.archive_staging_path)
        && option_is_immutable(&old.archive_path, &new.archive_path)
        && option_is_immutable(&old.confidentiality_mode, &new.confidentiality_mode)
        && option_is_immutable(&old.manifest_before_sha256, &new.manifest_before_sha256)
        && option_is_immutable(&old.manifest_after_sha256, &new.manifest_after_sha256)
        && option_is_immutable(&old.receipt_sha256, &new.receipt_sha256)
        && (old.recipient_fingerprints.is_empty()
            || old.recipient_fingerprints == new.recipient_fingerprints)
        && (old.plaintext_risk_acknowledged.is_none()
            || old.plaintext_risk_acknowledged == new.plaintext_risk_acknowledged);
    let state_is_valid = new.state == old.state
        || new.state == JournalState::RecoveryRequired
        || matches!(
            (old.state, new.state),
            (JournalState::Discovered, JournalState::Inspected)
                | (JournalState::Inspected, JournalState::Exported)
                | (JournalState::Exported, JournalState::Archived)
                | (JournalState::Archived, JournalState::Prepared)
                | (JournalState::Prepared, JournalState::Applying)
                | (JournalState::Applying, JournalState::Committed)
                | (JournalState::Committed, JournalState::Completed)
                | (JournalState::Completed, JournalState::RollingBack)
                | (JournalState::Committed, JournalState::RollingBack)
                | (JournalState::Applying, JournalState::RollingBack)
                | (JournalState::Prepared, JournalState::RollingBack)
                | (JournalState::RollingBack, JournalState::RolledBack)
        );
    if !immutable || !state_is_valid || (old.rolled_back && !new.rolled_back) {
        return Err(BridgeError::Conflict(
            "journal transition changed immutable evidence or moved non-monotonically".into(),
        ));
    }
    Ok(())
}

fn option_is_immutable<T: PartialEq>(old: &Option<T>, new: &Option<T>) -> bool {
    old.as_ref().is_none_or(|old| new.as_ref() == Some(old))
}

fn is_digest(value: &str) -> bool {
    value.len() == 64
        && value
            .as_bytes()
            .iter()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(byte))
}
