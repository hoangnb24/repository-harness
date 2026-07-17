//! Pure V1 domain values. This module has no filesystem or process APIs.

use serde::{Deserialize, Serialize};

pub const OUTPUT_SCHEMA: &str = "repository-harness-output/v1";
pub const MANIFEST_SCHEMA: &str = "repository-harness-manifest/v1";
pub const CORE_VERSION: &str = env!("CARGO_PKG_VERSION");
pub const UNBOUND_RELEASE_SHA256: &str =
    "8d55b3997149d0b961ed34e71d2dc8cba69b38ee02ce45eb087802ae1162d7d0";

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Command {
    Install(MutatorOptions),
    Update(MutatorOptions),
    Audit { json: bool },
    Scaffold(ScaffoldOptions),
    Status { json: bool },
    Version { json: bool },
}

impl Command {
    pub fn name(&self) -> &'static str {
        match self {
            Self::Install(_) => "install",
            Self::Update(_) => "update",
            Self::Audit { .. } => "audit",
            Self::Scaffold(_) => "scaffold",
            Self::Status { .. } => "status",
            Self::Version { .. } => "version",
        }
    }

    pub fn json(&self) -> bool {
        matches!(
            self,
            Self::Audit { json: true } | Self::Status { json: true } | Self::Version { json: true }
        )
    }
}

#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct MutatorOptions {
    pub preview: bool,
    pub non_interactive: bool,
    pub accept_preview_sha256: Option<String>,
    pub resume: Option<String>,
    pub rollback: Option<String>,
}

#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct ScaffoldOptions {
    pub template: Option<String>,
    pub destination: Option<String>,
    pub mutation: MutatorOptions,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Manifest {
    pub schema: String,
    pub repository_mode: ManifestRepositoryMode,
    pub compatibility: Compatibility,
    pub payload: PayloadIdentity,
    pub roles: Vec<Role>,
    pub conversion_receipt: Option<ConversionReceipt>,
}

#[derive(Clone, Copy, Debug, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum ManifestRepositoryMode {
    FreshV1,
    BrownfieldV1,
    ConvertedV1WithArchive,
}

impl ManifestRepositoryMode {
    pub fn output_name(self) -> &'static str {
        match self {
            Self::FreshV1 => "fresh-v1",
            Self::BrownfieldV1 => "brownfield-v1",
            Self::ConvertedV1WithArchive => "converted-v1-with-archive",
        }
    }
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Compatibility {
    pub cli_min: String,
    pub cli_max: String,
    pub template_release_min: String,
    pub template_release_max: String,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct PayloadIdentity {
    pub trust_domain: String,
    pub role: String,
    pub sequence: u64,
    pub index_sha256: String,
}

impl PayloadIdentity {
    pub fn unbound() -> Self {
        Self {
            trust_domain: "repository-harness-core".into(),
            role: "core-release".into(),
            sequence: 1,
            index_sha256: UNBOUND_RELEASE_SHA256.into(),
        }
    }
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Role {
    pub role: String,
    pub asset: String,
    pub activation: Activation,
    pub ownership: Ownership,
    pub origin: Origin,
    pub required: bool,
    pub path: String,
    pub template: Option<String>,
    pub template_release: Option<String>,
    pub base_sha256: Option<String>,
    pub current_sha256: String,
    pub marker: Option<String>,
    pub update_policy: UpdatePolicy,
    pub unresolved_markers: Vec<String>,
}

#[derive(Clone, Copy, Debug, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum Activation {
    Active,
    Unresolved,
    Disabled,
}

#[derive(Clone, Copy, Debug, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum Ownership {
    ManagedFile,
    ManagedBlock,
    TargetOwned,
}

#[derive(Clone, Copy, Debug, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum Origin {
    Created,
    V0Adopted,
    BrownfieldMapped,
}

#[derive(Clone, Copy, Debug, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum UpdatePolicy {
    ReplaceIfBase,
    ThreeWayReview,
    NeverAutoPatch,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct ConversionReceipt {
    pub schema: String,
    pub conversion_id: String,
    pub bridge_release: String,
    pub archive_path: String,
    pub export_sha256: String,
    pub standalone_backup_sha256: String,
    pub archive_sha256: String,
    pub confidentiality_mode: String,
    pub recipient_fingerprints: Vec<String>,
    pub plaintext_risk_acknowledged: Option<bool>,
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
pub struct Envelope {
    pub schema: &'static str,
    pub command: String,
    pub outcome: Outcome,
    pub exit_code: u8,
    pub mutation: Mutation,
    pub repository_mode: RepositoryMode,
    pub release: ReleaseOutput,
    pub notices: Vec<Notice>,
    pub details: Details,
}

impl Envelope {
    pub fn new(command: impl Into<String>) -> Self {
        Self {
            schema: OUTPUT_SCHEMA,
            command: command.into(),
            outcome: Outcome::Success,
            exit_code: 0,
            mutation: Mutation::None,
            repository_mode: RepositoryMode::Absent,
            release: ReleaseOutput::from(PayloadIdentity::unbound()),
            notices: Vec::new(),
            details: Details {
                readiness: Readiness::NotApplicable,
                violations: Vec::new(),
                operations: None,
            },
        }
    }

    pub fn normalize(&mut self) {
        self.command = sanitize_human_text(&self.command);
        self.release.role = sanitize_human_text(&self.release.role);
        for notice in &mut self.notices {
            notice.code = sanitize_human_text(&notice.code);
            notice.path = notice.path.as_deref().map(sanitize_human_text);
            notice.message = sanitize_human_text(&notice.message);
        }
        for violation in &mut self.details.violations {
            *violation = sanitize_human_text(violation);
        }
        if let Some(operations) = &mut self.details.operations {
            for operation in operations.iter_mut() {
                operation.operation_id = sanitize_human_text(&operation.operation_id);
                operation.path = sanitize_human_text(&operation.path);
            }
        }
        self.notices.sort_by(|left, right| {
            (&left.code, &left.path, &left.message).cmp(&(&right.code, &right.path, &right.message))
        });
        self.details.violations.sort();
        self.details.violations.dedup();
        if let Some(operations) = &mut self.details.operations {
            operations.sort_by(|left, right| {
                (&left.path, &left.operation_id).cmp(&(&right.path, &right.operation_id))
            });
        }
    }
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum Outcome {
    Ready,
    Unresolved,
    Invalid,
    Conflict,
    Unsupported,
    Success,
}

impl Outcome {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Ready => "ready",
            Self::Unresolved => "unresolved",
            Self::Invalid => "invalid",
            Self::Conflict => "conflict",
            Self::Unsupported => "unsupported",
            Self::Success => "success",
        }
    }
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum Mutation {
    None,
    Preview,
    Committed,
    RecoveryRequired,
    RolledBack,
}

impl Mutation {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::None => "none",
            Self::Preview => "preview",
            Self::Committed => "committed",
            Self::RecoveryRequired => "recovery-required",
            Self::RolledBack => "rolled-back",
        }
    }
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum RepositoryMode {
    Absent,
    FreshV1,
    BrownfieldV1,
    V0Legacy,
    ConversionInProgress,
    ConvertedV1WithArchive,
    MixedInvalid,
}

impl RepositoryMode {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Absent => "absent",
            Self::FreshV1 => "fresh-v1",
            Self::BrownfieldV1 => "brownfield-v1",
            Self::V0Legacy => "v0-legacy",
            Self::ConversionInProgress => "conversion-in-progress",
            Self::ConvertedV1WithArchive => "converted-v1-with-archive",
            Self::MixedInvalid => "mixed-invalid",
        }
    }
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
pub struct ReleaseOutput {
    pub role: String,
    pub sequence: u64,
    pub index_sha256: String,
}

impl From<PayloadIdentity> for ReleaseOutput {
    fn from(value: PayloadIdentity) -> Self {
        Self {
            role: value.role,
            sequence: value.sequence,
            index_sha256: value.index_sha256,
        }
    }
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
pub struct Notice {
    pub code: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub path: Option<String>,
    pub message: String,
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
pub struct Details {
    pub readiness: Readiness,
    pub violations: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub operations: Option<Vec<Operation>>,
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum Readiness {
    Ready,
    Unresolved,
    Invalid,
    NotApplicable,
}

impl Readiness {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Ready => "ready",
            Self::Unresolved => "unresolved",
            Self::Invalid => "invalid",
            Self::NotApplicable => "not-applicable",
        }
    }
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
pub struct Operation {
    pub operation_id: String,
    pub kind: OperationKind,
    pub path: String,
    pub disposition: Disposition,
    pub before_sha256: Option<String>,
    pub after_sha256: Option<String>,
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum OperationKind {
    Create,
    ReplaceManagedBlock,
    RemoveManagedFile,
    WriteManifest,
    WriteRecoveryJournal,
    RestoreJournalPostImage,
}

impl OperationKind {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Create => "create",
            Self::ReplaceManagedBlock => "replace-managed-block",
            Self::RemoveManagedFile => "remove-managed-file",
            Self::WriteManifest => "write-manifest",
            Self::WriteRecoveryJournal => "write-recovery-journal",
            Self::RestoreJournalPostImage => "restore-journal-post-image",
        }
    }
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum Disposition {
    ManagedV1,
    OptionalV1,
    TargetOwnedDestination,
}

impl Disposition {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::ManagedV1 => "managed-v1",
            Self::OptionalV1 => "optional-v1",
            Self::TargetOwnedDestination => "target-owned-destination",
        }
    }
}

fn sanitize_human_text(value: &str) -> String {
    let mut output = String::with_capacity(value.len());
    for character in value.chars() {
        if character.is_control() {
            output.push_str(&format!("\\u{{{:x}}}", u32::from(character)));
        } else {
            output.push(character);
        }
    }
    output
}
