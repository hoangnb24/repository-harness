use std::collections::BTreeSet;
use std::fmt::{Display, Formatter};

#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct RelativePath(String);

impl RelativePath {
    pub fn parse(value: impl Into<String>) -> Result<Self, DomainError> {
        let value = value.into();
        let invalid = value.is_empty()
            || value.starts_with('/')
            || value.ends_with('/')
            || value.contains('\\')
            || value.contains('\0')
            || value.contains(':')
            || value
                .split('/')
                .any(|component| component.is_empty() || component == "." || component == "..");
        if invalid {
            return Err(DomainError::InvalidRelativePath(value));
        }
        Ok(Self(value))
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl Display for RelativePath {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        self.0.fmt(formatter)
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ContentHash(String);

impl ContentHash {
    pub fn parse(value: impl Into<String>) -> Result<Self, DomainError> {
        let value = value.into();
        if value.len() != 64
            || !value
                .bytes()
                .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
        {
            return Err(DomainError::InvalidContentHash(value));
        }
        Ok(Self(value))
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DistributionFile {
    pub path: RelativePath,
    pub content: Vec<u8>,
    pub hash: ContentHash,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CoreDistribution {
    pub version: String,
    pub files: Vec<DistributionFile>,
}

impl CoreDistribution {
    pub fn validate(&self) -> Result<(), DomainError> {
        if self.version.trim().is_empty() {
            return Err(DomainError::EmptyVersion);
        }
        let mut paths = BTreeSet::new();
        for file in &self.files {
            if !paths.insert(file.path.clone()) {
                return Err(DomainError::DuplicatePath(file.path.clone()));
            }
        }
        Ok(())
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct BaselineFile {
    pub path: RelativePath,
    pub content: Vec<u8>,
    pub hash: ContentHash,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct InstallationState {
    pub schema_version: u32,
    pub core_version: String,
    pub files: Vec<BaselineFile>,
}

impl InstallationState {
    pub const SCHEMA_VERSION: u32 = 1;

    pub fn baseline(&self, path: &RelativePath) -> Option<&BaselineFile> {
        self.files.iter().find(|file| &file.path == path)
    }

    pub fn validate(&self) -> Result<(), DomainError> {
        if self.schema_version != Self::SCHEMA_VERSION {
            return Err(DomainError::UnsupportedSchema(self.schema_version));
        }
        let mut paths = BTreeSet::new();
        for file in &self.files {
            if !paths.insert(file.path.clone()) {
                return Err(DomainError::DuplicatePath(file.path.clone()));
            }
        }
        Ok(())
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum WorkspaceMutation {
    Write {
        path: RelativePath,
        content: Vec<u8>,
    },
    Delete {
        path: RelativePath,
    },
}

impl WorkspaceMutation {
    pub fn path(&self) -> &RelativePath {
        match self {
            Self::Write { path, .. } | Self::Delete { path } => path,
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum FileChangeKind {
    Create,
    Update,
    Delete,
    Preserve,
    Adopt,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PlannedFileChange {
    pub path: RelativePath,
    pub kind: FileChangeKind,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ConflictReason {
    OverlappingChanges,
    MissingManagedFile,
    ExistingUnmanagedPath,
    ModifiedRemovedFile,
    UnsafePath,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct UpdateConflict {
    pub path: RelativePath,
    pub reason: ConflictReason,
    pub detail: String,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ResolutionConflict {
    pub path: RelativePath,
    pub base: Vec<u8>,
    pub local: Vec<u8>,
    pub incoming: Vec<u8>,
    pub resolved: Vec<u8>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct FrozenWorkspaceFile {
    pub path: RelativePath,
    pub content: Option<Vec<u8>>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct UpdateResolutionSession {
    pub from_version: String,
    pub to_version: String,
    pub conflicts: Vec<ResolutionConflict>,
    pub frozen_files: Vec<FrozenWorkspaceFile>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct InstallReport {
    pub version: String,
    pub dry_run: bool,
    pub applied: bool,
    pub changes: Vec<PlannedFileChange>,
    pub backup_path: Option<String>,
    pub recovered_interrupted_transaction: bool,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct UpdateReport {
    pub from_version: String,
    pub to_version: String,
    pub dry_run: bool,
    pub applied: bool,
    pub changes: Vec<PlannedFileChange>,
    pub conflicts: Vec<UpdateConflict>,
    pub resolution_staged: bool,
    pub backup_path: Option<String>,
    pub recovered_interrupted_transaction: bool,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum InstallationCondition {
    NotInstalled,
    Current,
    UpdateAvailable,
    ExecutableOutdated,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct FileStatus {
    pub path: RelativePath,
    pub modified: bool,
    pub missing: bool,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct StatusReport {
    pub condition: InstallationCondition,
    pub installed_version: Option<String>,
    pub target_version: String,
    pub files: Vec<FileStatus>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DoctorCheck {
    pub name: String,
    pub passed: bool,
    pub detail: String,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DoctorReport {
    pub healthy: bool,
    pub checks: Vec<DoctorCheck>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum MergeOutcome {
    Clean(Vec<u8>),
    Conflict { content: Vec<u8>, detail: String },
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ApplyReceipt {
    pub backup_path: Option<String>,
}

#[derive(Debug)]
pub enum DomainError {
    InvalidRelativePath(String),
    InvalidContentHash(String),
    EmptyVersion,
    DuplicatePath(RelativePath),
    UnsupportedSchema(u32),
}

impl Display for DomainError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::InvalidRelativePath(value) => write!(formatter, "invalid relative path: {value}"),
            Self::InvalidContentHash(value) => {
                write!(formatter, "invalid SHA-256 content hash: {value}")
            }
            Self::EmptyVersion => {
                formatter.write_str("core distribution version must not be empty")
            }
            Self::DuplicatePath(path) => write!(formatter, "duplicate managed path: {path}"),
            Self::UnsupportedSchema(version) => {
                write!(
                    formatter,
                    "unsupported installation-state schema: {version}"
                )
            }
        }
    }
}

impl std::error::Error for DomainError {}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn relative_paths_reject_escape_and_platform_ambiguous_forms() {
        for invalid in ["", "/root", "../x", "x/../y", "x\\y", "C:/x", "x/"] {
            assert!(RelativePath::parse(invalid).is_err(), "accepted {invalid}");
        }
        assert_eq!(
            RelativePath::parse("docs/WORKFLOW.md").unwrap().as_str(),
            "docs/WORKFLOW.md"
        );
    }

    #[test]
    fn installation_state_requires_unique_paths_and_current_schema() {
        let path = RelativePath::parse("AGENTS.md").unwrap();
        let hash = ContentHash::parse("a".repeat(64)).unwrap();
        let baseline = BaselineFile {
            path,
            content: b"base".to_vec(),
            hash,
        };
        let duplicate = InstallationState {
            schema_version: InstallationState::SCHEMA_VERSION,
            core_version: "1.0.0".to_owned(),
            files: vec![baseline.clone(), baseline],
        };
        assert!(matches!(
            duplicate.validate(),
            Err(DomainError::DuplicatePath(_))
        ));
    }
}
