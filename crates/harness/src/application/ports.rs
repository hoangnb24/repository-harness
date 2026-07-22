use std::path::Path;

use crate::domain::{
    ApplyReceipt, CoreDistribution, FrozenWorkspaceFile, InstallationState, MergeOutcome,
    RelativePath, UpdateResolutionSession, WorkspaceMutation,
};

#[derive(Debug, thiserror::Error)]
#[error("{message}")]
pub struct PortError {
    pub message: String,
}

impl PortError {
    pub fn new(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
        }
    }
}

pub trait CoreDistributionPort {
    fn current(&self) -> Result<CoreDistribution, PortError>;
}

pub trait InstallationStatePort {
    fn recover_interrupted(&self, root: &Path) -> Result<bool, PortError>;
    fn transaction_pending(&self, root: &Path) -> Result<bool, PortError>;
    fn load(&self, root: &Path) -> Result<Option<InstallationState>, PortError>;
    fn read_workspace_file(
        &self,
        root: &Path,
        path: &RelativePath,
    ) -> Result<Option<Vec<u8>>, PortError>;
    fn validate_managed_path(&self, root: &Path, path: &RelativePath) -> Result<(), PortError>;
    fn apply(
        &self,
        root: &Path,
        state: &InstallationState,
        mutations: &[WorkspaceMutation],
    ) -> Result<ApplyReceipt, PortError>;
    fn apply_if_unchanged(
        &self,
        root: &Path,
        state: &InstallationState,
        mutations: &[WorkspaceMutation],
        expected: &[FrozenWorkspaceFile],
    ) -> Result<ApplyReceipt, PortError>;
    fn resolution_pending(&self, root: &Path) -> Result<bool, PortError>;
    fn stage_resolution(
        &self,
        root: &Path,
        session: &UpdateResolutionSession,
    ) -> Result<(), PortError>;
    fn load_resolution(&self, root: &Path) -> Result<Option<UpdateResolutionSession>, PortError>;
    fn clear_resolution(&self, root: &Path) -> Result<bool, PortError>;
}

#[derive(Debug)]
pub struct CandidateExit {
    pub code: i32,
    pub stdout: Vec<u8>,
    pub stderr: Vec<u8>,
}

pub struct CandidateRequest<'a> {
    pub root: &'a Path,
    pub dry_run: bool,
    pub continue_update: bool,
    pub json: bool,
}

pub trait UpdateCandidatePort {
    type Candidate;

    fn latest(&self) -> Result<Self::Candidate, PortError>;
    fn exact(&self, version: &str) -> Result<Self::Candidate, PortError>;
    fn staged(&self, root: &Path, version: &str) -> Result<Self::Candidate, PortError>;
    fn release_version<'a>(&self, candidate: &'a Self::Candidate) -> &'a str;
    fn reported_version(&self, candidate: &Self::Candidate) -> Result<String, PortError>;
    fn execute(
        &self,
        candidate: &Self::Candidate,
        request: &CandidateRequest<'_>,
    ) -> Result<CandidateExit, PortError>;
    fn persist(&self, root: &Path, candidate: &Self::Candidate) -> Result<(), PortError>;
    fn clear_persisted(&self, root: &Path) -> Result<(), PortError>;
    fn validate_replacement_target(&self, root: &Path) -> Result<(), PortError>;
    fn replace(&self, candidate: &Self::Candidate) -> Result<(), PortError>;
}

pub trait ThreeWayMergePort {
    fn available(&self) -> Result<bool, PortError>;
    fn merge(&self, base: &[u8], local: &[u8], upstream: &[u8]) -> Result<MergeOutcome, PortError>;
}
