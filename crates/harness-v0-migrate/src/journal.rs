use std::fs::{File, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

use crate::Result;

pub const JOURNAL_SCHEMA: &str = "repository-harness-v0-conversion-journal/v1";

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
    RecoveryRequired,
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct Journal {
    pub schema: String,
    pub conversion_id: String,
    pub state: JournalState,
    pub source_sha256: String,
    pub export_sha256: Option<String>,
    pub standalone_backup_sha256: Option<String>,
    pub archive_sha256: Option<String>,
    pub archive_path: Option<String>,
    pub confidentiality_mode: Option<String>,
    pub recipient_fingerprints: Vec<String>,
    pub plaintext_risk_acknowledged: Option<bool>,
    pub preview_sha256: String,
    pub manifest_before_sha256: Option<String>,
    pub manifest_after_sha256: Option<String>,
    pub rolled_back: bool,
}

impl Journal {
    pub fn new(conversion_id: String, source_sha256: String, preview_sha256: String) -> Self {
        Self {
            schema: JOURNAL_SCHEMA.into(),
            conversion_id,
            state: JournalState::Discovered,
            source_sha256,
            export_sha256: None,
            standalone_backup_sha256: None,
            archive_sha256: None,
            archive_path: None,
            confidentiality_mode: None,
            recipient_fingerprints: Vec::new(),
            plaintext_risk_acknowledged: None,
            preview_sha256,
            manifest_before_sha256: None,
            manifest_after_sha256: None,
            rolled_back: false,
        }
    }
}

pub fn path(root: &Path, conversion_id: &str) -> PathBuf {
    root.join(".harness/recovery/v0-conversion")
        .join(conversion_id)
        .join("journal.json")
}

pub fn load(root: &Path, conversion_id: &str) -> Result<Journal> {
    Ok(serde_json::from_slice(&std::fs::read(path(
        root,
        conversion_id,
    ))?)?)
}

pub fn save(root: &Path, journal: &Journal) -> Result<()> {
    let directory = path(root, &journal.conversion_id)
        .parent()
        .expect("journal path has parent")
        .to_path_buf();
    ensure_directory(root, ".harness")?;
    ensure_directory(root, ".harness/recovery")?;
    ensure_directory(root, ".harness/recovery/v0-conversion")?;
    if !directory.exists() {
        std::fs::create_dir(&directory)?;
    }
    let mut bytes = serde_json::to_vec(journal)?;
    bytes.push(b'\n');
    let temporary = directory.join("journal.json.tmp");
    let mut file = OpenOptions::new()
        .write(true)
        .create(true)
        .truncate(true)
        .open(&temporary)?;
    file.write_all(&bytes)?;
    file.sync_all()?;
    std::fs::rename(&temporary, path(root, &journal.conversion_id))?;
    File::open(&directory)?.sync_all()?;
    Ok(())
}

fn ensure_directory(root: &Path, relative: &str) -> Result<()> {
    let path = root.join(relative);
    if path.exists() {
        let metadata = std::fs::symlink_metadata(&path)?;
        if !metadata.is_dir() || metadata.file_type().is_symlink() {
            return Err(crate::BridgeError::Conflict(format!(
                "journal path is not a no-follow directory: {relative}"
            )));
        }
    } else {
        std::fs::create_dir(&path)?;
    }
    Ok(())
}
