//! Explicit ports separating the pure V1 application from host I/O.

use std::collections::BTreeMap;

use thiserror::Error;

use crate::domain::Manifest;
use crate::recovery::{
    MutationFailure, MutationRequest, MutationResult, RecoveryAuthorization, RecoveryMode,
    RecoveryProbe,
};

#[derive(Clone, Debug, Error, PartialEq, Eq)]
pub enum PortError {
    #[error("path is missing: {0}")]
    Missing(String),
    #[error("path is unsafe: {0}")]
    UnsafePath(String),
    #[error("path traverses a link: {0}")]
    Link(String),
    #[error("path changed during inspection: {0}")]
    Changed(String),
    #[error("filesystem conflict: {0}")]
    Conflict(String),
    #[error("I/O failure at {path}: {message}")]
    Io { path: String, message: String },
    #[error("release material is unavailable: {0}")]
    ReleaseUnavailable(String),
    #[error("release material is invalid: {0}")]
    ReleaseInvalid(String),
    #[error("manifest is invalid: {0}")]
    ManifestInvalid(String),
}

pub trait FileSystemPort {
    fn read_declared(&self, path: &str) -> Result<Vec<u8>, PortError>;
    fn exists_declared(&self, path: &str) -> Result<bool, PortError>;
    fn validate_snapshot(&self) -> Result<(), PortError>;

    /// Structural compatibility observation only. Implementations may inspect
    /// path identities, but this boundary never opens SQLite, parses V0
    /// changesets, or depends on the conversion bridge.
    fn observe_compatibility(&self) -> Result<CompatibilityObservation, PortError> {
        Ok(CompatibilityObservation::default())
    }
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct CompatibilityObservation {
    pub observed: bool,
    pub legacy_artifact_present: bool,
    pub conversion_journal_present: bool,
    pub conversion_archive_present: bool,
    pub conversion_evidence_authenticated: bool,
}

pub trait ManifestPort {
    fn load(&self, filesystem: &dyn FileSystemPort) -> Result<Option<Manifest>, PortError>;
    fn parse_bytes(&self, bytes: &[u8]) -> Result<Manifest, PortError>;
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PinnedRootKey {
    pub key_id: String,
    pub public_key: [u8; 32],
    pub test_fixture: bool,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct TrustedRootState {
    pub trust_domain: String,
    pub sequence: u64,
    pub bundle_sha256: String,
    pub threshold: u8,
    pub keys: Vec<PinnedRootKey>,
    pub revoked_key_ids: Vec<String>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum TrustPolicy {
    Production,
    TestFixtures,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct RollbackMaterial {
    pub authorization: Vec<u8>,
    pub signatures: Vec<u8>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum ReleaseFreshness {
    FirstInstallExactDigest(String),
    FirstInstallMinimumSequence(u64),
    Existing {
        sequence: u64,
        digest: String,
        rollback: Option<RollbackMaterial>,
    },
}

/// Independently provisioned trust, ledger policy, and monotonic state. This
/// must not come from the release-material transport that supplies adjacent
/// bundle and ledger bytes.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ReleaseTrustInput {
    pub trusted_root: TrustedRootState,
    pub trust_policy: TrustPolicy,
    pub freshness: ReleaseFreshness,
    pub path_ledger_sha256: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ReleaseMaterial {
    pub index: Vec<u8>,
    pub signatures: Vec<u8>,
    pub trust_bundle: Vec<u8>,
    pub trust_bundle_signatures: Vec<u8>,
    pub path_ledger: Vec<u8>,
    pub source_files: BTreeMap<String, Vec<u8>>,
}

pub trait ReleasePort {
    fn load(&self) -> Result<ReleaseMaterial, PortError>;
}

pub trait TrustPort {
    fn load(&self) -> Result<ReleaseTrustInput, PortError>;
}

/// Explicit Phase 3 write boundary. The application calls this only after the
/// Phase 2 trust verifier has returned an authenticated release.
pub trait MutationPort {
    /// Read-only discovery of structurally valid, incomplete tool-local
    /// journals. This method must never create, repair, or rewrite evidence.
    fn probe_recovery(&self) -> Result<Vec<RecoveryProbe>, PortError>;

    fn apply(
        &self,
        request: &MutationRequest,
        validate_candidate: &mut dyn FnMut(&[u8]) -> Result<(), PortError>,
    ) -> Result<MutationResult, MutationFailure>;

    fn recover(
        &self,
        command: &str,
        operation_id: &str,
        mode: RecoveryMode,
        authorization: &RecoveryAuthorization,
        validate_candidate: &mut dyn FnMut(&[u8]) -> Result<(), PortError>,
    ) -> Result<MutationResult, MutationFailure>;
}
