//! Pure command application around injected filesystem, manifest, and release ports.

use std::collections::BTreeSet;

use semver::Version;

use crate::domain::{
    Activation, Command, Envelope, Manifest, ManifestRepositoryMode, Mutation, Notice, Operation,
    OperationKind, Outcome, Ownership, Readiness, ReleaseOutput, RepositoryMode, ScaffoldOptions,
    UpdatePolicy, CORE_VERSION,
};
use crate::markdown::parse_commonmark;
use crate::path::{validate_exact_destination, validate_relative};
use crate::ports::{FileSystemPort, ManifestPort, PortError, ReleasePort, TrustPort};
use crate::strict_json::{digest, hex_sha256};
use crate::trust::{verify_release, VerifiedAsset, VerifiedRelease};

pub fn version_envelope() -> Envelope {
    let mut envelope = Envelope::new("version");
    envelope.notices.push(Notice {
        code: "core-version".into(),
        path: None,
        message: format!(
            "Repository Harness V1 core {CORE_VERSION}; manifest v1; template releases 1.0.0 through 1.x"
        ),
    });
    envelope.normalize();
    envelope
}

pub fn io_failure_envelope(command: &str, path: &str, message: &str) -> Envelope {
    let mut envelope = Envelope::new(command);
    apply_port_error(
        &mut envelope,
        PortError::Io {
            path: path.into(),
            message: message.into(),
        },
    );
    envelope.normalize();
    envelope
}

pub struct HarnessCore<'a> {
    filesystem: &'a dyn FileSystemPort,
    manifests: &'a dyn ManifestPort,
    releases: &'a dyn ReleasePort,
    trust: &'a dyn TrustPort,
}

impl<'a> HarnessCore<'a> {
    pub fn new(
        filesystem: &'a dyn FileSystemPort,
        manifests: &'a dyn ManifestPort,
        releases: &'a dyn ReleasePort,
        trust: &'a dyn TrustPort,
    ) -> Self {
        Self {
            filesystem,
            manifests,
            releases,
            trust,
        }
    }

    pub fn execute(&self, command: &Command) -> Envelope {
        let mut envelope = match command {
            Command::Version { .. } => version_envelope(),
            Command::Status { .. } => self.inspect(false),
            Command::Audit { .. } => self.inspect(true),
            Command::Install(options) => self.plan_mutation("install", options, None),
            Command::Update(options) => self.plan_mutation("update", options, None),
            Command::Scaffold(options) => {
                self.plan_mutation("scaffold", &options.mutation, Some(options))
            }
        };
        if !matches!(command, Command::Version { .. }) && matches!(envelope.exit_code, 0 | 2) {
            if let Err(error) = self.filesystem.validate_snapshot() {
                apply_port_error(&mut envelope, error);
            }
        }
        envelope.normalize();
        envelope
    }

    fn inspect(&self, audit: bool) -> Envelope {
        let command = if audit { "audit" } else { "status" };
        let mut envelope = Envelope::new(command);
        let manifest = match self.manifests.load(self.filesystem) {
            Ok(Some(manifest)) => manifest,
            Ok(None) => {
                envelope.notices.push(Notice {
                    code: "manifest-absent".into(),
                    path: Some(".harness/manifest.json".into()),
                    message:
                        "No declared V1 manifest is present; no V0 state was opened or inferred"
                            .into(),
                });
                if audit {
                    envelope.outcome = Outcome::Invalid;
                    envelope.exit_code = 3;
                    envelope.details.readiness = Readiness::Invalid;
                    envelope.details.violations.push("manifest-absent".into());
                }
                return envelope;
            }
            Err(error) => {
                apply_port_error(&mut envelope, error);
                return envelope;
            }
        };
        envelope.repository_mode = output_mode(manifest.repository_mode);
        envelope.release = ReleaseOutput::from(manifest.payload.clone());
        let audit_result = match self.audit_manifest(&manifest) {
            Ok(result) => result,
            Err(error) => {
                apply_port_error(&mut envelope, error);
                return envelope;
            }
        };
        if audit_result.violations.is_empty() {
            if audit_result.unresolved {
                envelope.outcome = Outcome::Unresolved;
                envelope.details.readiness = Readiness::Unresolved;
                envelope.exit_code = if audit { 2 } else { 0 };
            } else {
                envelope.outcome = Outcome::Ready;
                envelope.details.readiness = Readiness::Ready;
            }
        } else {
            envelope.repository_mode = RepositoryMode::MixedInvalid;
            envelope.outcome = Outcome::Invalid;
            envelope.details.readiness = Readiness::Invalid;
            envelope.details.violations = audit_result.violations;
            envelope.exit_code = 3;
        }
        envelope.notices.extend(audit_result.notices);
        envelope
    }

    fn audit_manifest(&self, manifest: &Manifest) -> Result<AuditResult, PortError> {
        let mut result = AuditResult::default();
        validate_manifest_header(manifest, &mut result.violations);
        let mut role_ids = BTreeSet::new();
        let mut marker_ids = BTreeSet::new();
        let mut paths = BTreeSet::new();
        for role in &manifest.roles {
            if !role_ids.insert(role.role.clone()) {
                result
                    .violations
                    .push(format!("duplicate-role:{}", role.role));
            }
            let collision = match validate_relative(&role.path, false) {
                Ok(collision) => collision,
                Err(_) => {
                    result.violations.push(format!("unsafe-path:{}", role.path));
                    continue;
                }
            };
            if !paths.insert(collision) {
                result
                    .violations
                    .push(format!("path-collision:{}", role.path));
            }
            validate_role_contract(role, &mut marker_ids, &mut result.violations);
            if role.activation == Activation::Disabled && !role.required {
                continue;
            }
            let bytes = match self.filesystem.read_declared(&role.path) {
                Ok(bytes) => bytes,
                Err(
                    error @ (PortError::Missing(_) | PortError::UnsafePath(_) | PortError::Link(_)),
                ) => {
                    result
                        .violations
                        .push(format!("declared-file:{}:{error}", role.path));
                    continue;
                }
                Err(error) => return Err(error),
            };
            if !is_sha256(&role.current_sha256) || hex_sha256(&bytes) != role.current_sha256 {
                result
                    .violations
                    .push(format!("digest-mismatch:{}", role.path));
            }
            let text = match std::str::from_utf8(&bytes) {
                Ok(text) => text,
                Err(_) => {
                    result
                        .violations
                        .push(format!("declared-text-not-utf8:{}", role.path));
                    continue;
                }
            };
            validate_markers(role, text, &mut result.violations);
            if role.ownership != Ownership::TargetOwned {
                validate_links(self.filesystem, &role.path, text, &mut result.violations)?;
            }
            if role.activation == Activation::Unresolved {
                result.unresolved = true;
                result.notices.push(Notice {
                    code: "role-unresolved".into(),
                    path: Some(role.path.clone()),
                    message: format!("Role {} retains declared completion markers", role.role),
                });
            }
        }
        Ok(result)
    }

    fn plan_mutation(
        &self,
        command: &str,
        options: &crate::domain::MutatorOptions,
        scaffold: Option<&ScaffoldOptions>,
    ) -> Envelope {
        let mut envelope = Envelope::new(command);
        if options.resume.is_some() || options.rollback.is_some() {
            conflict(
                &mut envelope,
                "phase3-recovery-unavailable",
                "Atomic backup/journal resume and rollback belong to Phase 3",
            );
            return envelope;
        }
        let existing = match self.manifests.load(self.filesystem) {
            Ok(existing) => existing,
            Err(error) => {
                apply_port_error(&mut envelope, error);
                return envelope;
            }
        };
        if command == "update" && existing.is_none() {
            conflict(
                &mut envelope,
                "update-manifest-absent",
                "Update requires an existing declared V1 manifest",
            );
            return envelope;
        }
        if let Some(manifest) = &existing {
            envelope.repository_mode = output_mode(manifest.repository_mode);
            envelope.release = ReleaseOutput::from(manifest.payload.clone());
            let audit = match self.audit_manifest(manifest) {
                Ok(audit) => audit,
                Err(error) => {
                    apply_port_error(&mut envelope, error);
                    return envelope;
                }
            };
            if !audit.violations.is_empty() {
                envelope.details.violations = audit.violations;
                envelope.notices = audit.notices;
                invalidate(
                    &mut envelope,
                    "existing-manifest-fails-structural-audit".into(),
                );
                return envelope;
            }
            if audit.unresolved {
                envelope.details.readiness = Readiness::Unresolved;
            }
            envelope.notices.extend(audit.notices);
        }
        let release = match self.releases.load().and_then(|material| {
            self.trust
                .load()
                .and_then(|trust| verify_release(material, trust))
        }) {
            Ok(release) => release,
            Err(error) => {
                apply_port_error(&mut envelope, error);
                return envelope;
            }
        };
        if let Some(manifest) = &existing {
            if let Err(violation) = validate_payload_transition(manifest, &release) {
                invalidate(&mut envelope, violation);
                return envelope;
            }
        }
        envelope.release = ReleaseOutput::from(release.identity().clone());
        let operations = match command {
            "install" => self.plan_install(&release, &mut envelope),
            "update" => self.plan_install(&release, &mut envelope),
            "scaffold" => {
                self.plan_scaffold(&release, scaffold.expect("scaffold options"), &mut envelope)
            }
            _ => unreachable!("closed command dispatch"),
        };
        let Some(operations) = operations else {
            return envelope;
        };
        let operations_value = serde_json::to_value(&operations).expect("operations serialize");
        let preview_sha256 =
            digest(&operations_value).expect("operations are canonical JSON values");
        envelope.details.operations = Some(operations);
        envelope.notices.push(Notice {
            code: "preview-sha256".into(),
            path: None,
            message: preview_sha256.clone(),
        });
        envelope.notices.push(Notice {
            code: "phase3-mutation-deferred".into(),
            path: None,
            message: "Plan is inspectable, but Phase 2 never writes target or manifest bytes"
                .into(),
        });
        if options
            .accept_preview_sha256
            .as_ref()
            .is_some_and(|accepted| accepted != &preview_sha256)
        {
            conflict(
                &mut envelope,
                "preview-digest-conflict",
                "Accepted preview digest differs from current deterministic plan",
            );
            return envelope;
        }
        if options.preview {
            envelope.outcome = Outcome::Success;
            envelope.exit_code = 0;
            envelope.mutation = Mutation::Preview;
        } else {
            conflict(
                &mut envelope,
                "phase3-mutation-unavailable",
                "Mutation execution is intentionally unavailable until Phase 3 atomic recovery",
            );
        }
        envelope
    }

    fn plan_install(
        &self,
        release: &VerifiedRelease,
        envelope: &mut Envelope,
    ) -> Option<Vec<Operation>> {
        let mut operations = Vec::new();
        for asset in release.assets() {
            match self.plan_create(asset) {
                Ok(Some(operation)) => operations.push(operation),
                Ok(None) => {}
                Err(error) => {
                    apply_port_error(envelope, error);
                    return None;
                }
            }
        }
        Some(operations)
    }

    fn plan_scaffold(
        &self,
        release: &VerifiedRelease,
        options: &ScaffoldOptions,
        envelope: &mut Envelope,
    ) -> Option<Vec<Operation>> {
        let (Some(template), Some(destination)) = (&options.template, &options.destination) else {
            invalidate(
                envelope,
                "scaffold requires --template and --destination".into(),
            );
            return None;
        };
        if validate_exact_destination(destination).is_err() {
            invalidate(
                envelope,
                format!("unsafe scaffold destination: {destination}"),
            );
            return None;
        }
        let Some(asset) = release.assets().iter().find(|asset| {
            asset.id == *template || asset.template.as_deref() == Some(template.as_str())
        }) else {
            invalidate(
                envelope,
                format!("template is not authenticated/indexed: {template}"),
            );
            return None;
        };
        if asset.destination != *destination {
            invalidate(
                envelope,
                "scaffold destination differs from the signed exact destination".into(),
            );
            return None;
        }
        match self.plan_create(asset) {
            Ok(Some(operation)) => Some(vec![operation]),
            Ok(None) => {
                conflict(
                    envelope,
                    "scaffold-path-exists",
                    "Scaffold never overwrites a pre-existing destination",
                );
                None
            }
            Err(error) => {
                apply_port_error(envelope, error);
                None
            }
        }
    }

    fn plan_create(&self, asset: &VerifiedAsset) -> Result<Option<Operation>, PortError> {
        match self.filesystem.exists_declared(&asset.destination) {
            Ok(false) => Ok(Some(Operation {
                operation_id: format!("create-{}", asset.id),
                kind: OperationKind::Create,
                path: asset.destination.clone(),
                disposition: asset.disposition,
                before_sha256: None,
                after_sha256: Some(asset.sha256.clone()),
            })),
            Ok(true) => {
                let bytes = self.filesystem.read_declared(&asset.destination)?;
                if hex_sha256(&bytes) == asset.sha256 {
                    Ok(None)
                } else {
                    Err(PortError::Conflict(format!(
                        "{} exists with bytes outside the authenticated release",
                        asset.destination
                    )))
                }
            }
            Err(error) => Err(error),
        }
    }
}

#[derive(Default)]
struct AuditResult {
    unresolved: bool,
    violations: Vec<String>,
    notices: Vec<Notice>,
}

fn validate_manifest_header(manifest: &Manifest, violations: &mut Vec<String>) {
    let versions = [
        ("cli-min", Version::parse(&manifest.compatibility.cli_min)),
        ("cli-max", Version::parse(&manifest.compatibility.cli_max)),
        (
            "template-min",
            Version::parse(&manifest.compatibility.template_release_min),
        ),
        (
            "template-max",
            Version::parse(&manifest.compatibility.template_release_max),
        ),
    ];
    for (name, parsed) in &versions {
        if parsed.is_err() {
            violations.push(format!("invalid-semver:{name}"));
        }
    }
    if let (Ok(cli_min), Ok(cli_max)) = (&versions[0].1, &versions[1].1) {
        let current = Version::parse(CORE_VERSION).expect("crate version is semver");
        if cli_min > cli_max || &current < cli_min || &current > cli_max {
            violations.push("unsupported-cli-range".into());
        }
    }
    if let (Ok(template_min), Ok(template_max)) = (&versions[2].1, &versions[3].1) {
        if template_min > template_max {
            violations.push("reversed-template-range".into());
        }
    }
    if manifest.payload.trust_domain != "repository-harness-core"
        || manifest.payload.role != "core-release"
        || manifest.payload.sequence == 0
        || !is_sha256(&manifest.payload.index_sha256)
    {
        violations.push("invalid-payload-identity".into());
    }
    if manifest.roles.is_empty() {
        violations.push("manifest-has-no-roles".into());
    }
    match manifest.repository_mode {
        ManifestRepositoryMode::ConvertedV1WithArchive if manifest.conversion_receipt.is_none() => {
            violations.push("converted-mode-missing-receipt".into());
        }
        ManifestRepositoryMode::FreshV1 | ManifestRepositoryMode::BrownfieldV1
            if manifest.conversion_receipt.is_some() =>
        {
            violations.push("nonconverted-mode-has-receipt".into());
        }
        _ => {}
    }
    if let Some(receipt) = &manifest.conversion_receipt {
        let expected = format!(".harness/legacy/v0-conversion/{}/", receipt.conversion_id);
        if receipt.schema != "repository-harness-conversion-receipt/v1"
            || !receipt.archive_path.starts_with(&expected)
            || validate_relative(&receipt.archive_path, true).is_err()
            || !is_sha256(&receipt.export_sha256)
            || !is_sha256(&receipt.standalone_backup_sha256)
            || !is_sha256(&receipt.archive_sha256)
        {
            violations.push("invalid-conversion-receipt".into());
        }
        match receipt.confidentiality_mode.as_str() {
            "encrypted-age-x25519"
                if receipt.recipient_fingerprints.is_empty()
                    || receipt.plaintext_risk_acknowledged.is_some() =>
            {
                violations.push("invalid-encrypted-receipt".into());
            }
            "plaintext-explicit-override"
                if !receipt.recipient_fingerprints.is_empty()
                    || receipt.plaintext_risk_acknowledged != Some(true) =>
            {
                violations.push("invalid-plaintext-receipt".into());
            }
            "encrypted-age-x25519" | "plaintext-explicit-override" => {}
            _ => violations.push("invalid-confidentiality-mode".into()),
        }
    }
}

fn validate_role_contract(
    role: &crate::domain::Role,
    marker_ids: &mut BTreeSet<String>,
    violations: &mut Vec<String>,
) {
    if role.required && role.activation == Activation::Disabled {
        violations.push(format!("required-role-disabled:{}", role.role));
    }
    if role.ownership == Ownership::TargetOwned
        && role.update_policy != UpdatePolicy::NeverAutoPatch
    {
        violations.push(format!("target-owned-auto-patch:{}", role.role));
    }
    if role.ownership == Ownership::ManagedBlock {
        match &role.marker {
            Some(marker) if is_lower_kebab(marker) && marker_ids.insert(marker.clone()) => {}
            _ => violations.push(format!("invalid-managed-marker:{}", role.role)),
        }
    } else if role.marker.is_some() {
        violations.push(format!("unexpected-managed-marker:{}", role.role));
    }
    if role.activation == Activation::Unresolved {
        let mut markers = BTreeSet::new();
        if role.unresolved_markers.is_empty()
            || role.unresolved_markers.iter().any(|marker| {
                !valid_unresolved_marker(&role.role, marker) || !markers.insert(marker.as_str())
            })
        {
            violations.push(format!("invalid-unresolved-markers:{}", role.role));
        }
    } else if !role.unresolved_markers.is_empty() {
        violations.push(format!("unexpected-unresolved-markers:{}", role.role));
    }
    if !is_sha256(&role.current_sha256)
        || role
            .base_sha256
            .as_ref()
            .is_some_and(|digest| !is_sha256(digest))
    {
        violations.push(format!("invalid-role-digest:{}", role.role));
    }
}

fn valid_unresolved_marker(role: &str, token: &str) -> bool {
    let Some(inner) = token
        .strip_prefix("REPOSITORY-HARNESS-UNRESOLVED(")
        .and_then(|value| value.strip_suffix(')'))
    else {
        return false;
    };
    let Some((declared_role, marker_id)) = inner.split_once(':') else {
        return false;
    };
    declared_role == role && is_lower_kebab(marker_id)
}

fn validate_markers(role: &crate::domain::Role, text: &str, violations: &mut Vec<String>) {
    if let Some(marker) = &role.marker {
        let open = format!("<!-- repository-harness:v1:begin:{marker} -->");
        let close = format!("<!-- repository-harness:v1:end:{marker} -->");
        let opens: Vec<usize> = text.match_indices(&open).map(|(index, _)| index).collect();
        let closes: Vec<usize> = text.match_indices(&close).map(|(index, _)| index).collect();
        if opens.len() != 1 || closes.len() != 1 || opens[0] >= closes[0] {
            violations.push(format!("managed-marker-pair:{}", role.path));
        }
        let total_openings = text.matches("<!-- repository-harness:v1:begin:").count();
        let total_closings = text.matches("<!-- repository-harness:v1:end:").count();
        if total_openings != 1 || total_closings != 1 {
            violations.push(format!("nested-or-extra-managed-marker:{}", role.path));
        }
    } else if text.contains("<!-- repository-harness:v1:begin:")
        || text.contains("<!-- repository-harness:v1:end:")
    {
        violations.push(format!("unexpected-managed-marker:{}", role.path));
    }
    let declared: BTreeSet<&str> = role.unresolved_markers.iter().map(String::as_str).collect();
    for marker in &declared {
        if text.matches(marker).count() != 1 {
            violations.push(format!("unresolved-marker-count:{}:{marker}", role.path));
        }
    }
    for token in unresolved_tokens(text) {
        if !declared.contains(token.as_str()) {
            violations.push(format!(
                "undeclared-unresolved-marker:{}:{token}",
                role.path
            ));
        }
    }
}

fn unresolved_tokens(text: &str) -> Vec<String> {
    let prefix = "REPOSITORY-HARNESS-UNRESOLVED(";
    let mut result = Vec::new();
    let mut remaining = text;
    while let Some(start) = remaining.find(prefix) {
        let candidate = &remaining[start..];
        if let Some(end) = candidate.find(')') {
            result.push(candidate[..=end].to_string());
            remaining = &candidate[end + 1..];
        } else {
            result.push(candidate.to_string());
            break;
        }
    }
    result
}

fn validate_links(
    filesystem: &dyn FileSystemPort,
    containing_path: &str,
    text: &str,
    violations: &mut Vec<String>,
) -> Result<(), PortError> {
    let document = parse_commonmark(text);
    for raw in document.links.iter() {
        if let Some(raw_anchor) = raw.strip_prefix('#') {
            let anchor = match percent_decode(raw_anchor) {
                Ok(anchor) => anchor,
                Err(()) => {
                    violations.push(format!("invalid-link-encoding:{containing_path}:{raw}"));
                    continue;
                }
            };
            if anchor.is_empty() || !document.anchors.contains(&anchor) {
                violations.push(format!("missing-anchor:{containing_path}:{anchor}"));
            }
            continue;
        }
        if has_uri_scheme(raw) || raw.starts_with("//") {
            continue;
        }
        let (raw_target, raw_anchor) = raw.split_once('#').unwrap_or((raw, ""));
        let target = match percent_decode(raw_target) {
            Ok(target) => target,
            Err(()) => {
                violations.push(format!("invalid-link-encoding:{containing_path}:{raw}"));
                continue;
            }
        };
        let anchor = match percent_decode(raw_anchor) {
            Ok(anchor) => anchor,
            Err(()) => {
                violations.push(format!("invalid-link-encoding:{containing_path}:{raw}"));
                continue;
            }
        };
        let resolved = match resolve_relative(containing_path, &target) {
            Some(path) if validate_relative(&path, false).is_ok() => path,
            _ => {
                violations.push(format!("unsafe-link:{containing_path}:{raw}"));
                continue;
            }
        };
        let bytes = match filesystem.read_declared(&resolved) {
            Ok(bytes) => bytes,
            Err(PortError::Missing(_) | PortError::UnsafePath(_) | PortError::Link(_)) => {
                violations.push(format!("missing-link:{containing_path}:{resolved}"));
                continue;
            }
            Err(error) => return Err(error),
        };
        if !anchor.is_empty() {
            let Ok(target_text) = std::str::from_utf8(&bytes) else {
                violations.push(format!("invalid-link-anchor:{resolved}:{anchor}"));
                continue;
            };
            if !parse_commonmark(target_text).anchors.contains(&anchor) {
                violations.push(format!("missing-anchor:{resolved}:{anchor}"));
            }
        }
    }
    Ok(())
}

fn has_uri_scheme(value: &str) -> bool {
    let Some((scheme, _)) = value.split_once(':') else {
        return false;
    };
    if scheme.len() == 1 {
        return false;
    }
    scheme
        .as_bytes()
        .first()
        .is_some_and(u8::is_ascii_alphabetic)
        && scheme
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'+' | b'-' | b'.'))
}

fn percent_decode(value: &str) -> Result<String, ()> {
    let bytes = value.as_bytes();
    let mut output = Vec::with_capacity(bytes.len());
    let mut index = 0;
    while index < bytes.len() {
        if bytes[index] == b'%' {
            if index + 2 >= bytes.len() {
                return Err(());
            }
            let high = hex(bytes[index + 1]).ok_or(())?;
            let low = hex(bytes[index + 2]).ok_or(())?;
            output.push((high << 4) | low);
            index += 3;
        } else {
            output.push(bytes[index]);
            index += 1;
        }
    }
    String::from_utf8(output).map_err(|_| ())
}

fn hex(byte: u8) -> Option<u8> {
    match byte {
        b'0'..=b'9' => Some(byte - b'0'),
        b'a'..=b'f' => Some(byte - b'a' + 10),
        b'A'..=b'F' => Some(byte - b'A' + 10),
        _ => None,
    }
}

fn resolve_relative(containing_path: &str, target: &str) -> Option<String> {
    let mut components: Vec<&str> = containing_path.split('/').collect();
    components.pop();
    for component in target.split('/') {
        match component {
            "" | "." => {}
            ".." => {
                components.pop()?;
            }
            value => components.push(value),
        }
    }
    Some(components.join("/"))
}

fn validate_payload_transition(
    manifest: &Manifest,
    release: &VerifiedRelease,
) -> Result<(), String> {
    let current = &manifest.payload;
    let candidate = release.identity();
    if candidate.sequence < current.sequence {
        return Err("payload-transition-release-sequence-regressed".into());
    }
    if candidate.sequence == current.sequence && candidate.index_sha256 != current.index_sha256 {
        return Err("payload-transition-equal-sequence-digest-mismatch".into());
    }
    let candidate_release =
        Version::parse(release.release()).map_err(|_| "payload-transition-invalid-release")?;
    let minimum = Version::parse(&manifest.compatibility.template_release_min)
        .map_err(|_| "payload-transition-invalid-template-minimum")?;
    let maximum = Version::parse(&manifest.compatibility.template_release_max)
        .map_err(|_| "payload-transition-invalid-template-maximum")?;
    if candidate_release < minimum || candidate_release > maximum {
        return Err("payload-transition-template-release-outside-manifest-range".into());
    }
    Ok(())
}

fn output_mode(mode: ManifestRepositoryMode) -> RepositoryMode {
    match mode {
        ManifestRepositoryMode::FreshV1 => RepositoryMode::FreshV1,
        ManifestRepositoryMode::BrownfieldV1 => RepositoryMode::BrownfieldV1,
        ManifestRepositoryMode::ConvertedV1WithArchive => RepositoryMode::ConvertedV1WithArchive,
    }
}

fn conflict(envelope: &mut Envelope, code: &str, message: &str) {
    envelope.outcome = Outcome::Conflict;
    envelope.exit_code = 4;
    envelope.mutation = Mutation::None;
    envelope.notices.push(Notice {
        code: code.into(),
        path: None,
        message: message.into(),
    });
}

fn invalidate(envelope: &mut Envelope, violation: String) {
    envelope.outcome = Outcome::Invalid;
    envelope.exit_code = 3;
    envelope.repository_mode = RepositoryMode::MixedInvalid;
    envelope.details.readiness = Readiness::Invalid;
    envelope.details.violations.push(violation);
}

fn apply_port_error(envelope: &mut Envelope, error: PortError) {
    match error {
        PortError::Io { path, message } => {
            envelope.outcome = Outcome::Unsupported;
            envelope.exit_code = 74;
            envelope.mutation = Mutation::None;
            envelope.notices.push(Notice {
                code: "io-failure".into(),
                path: Some(path),
                message,
            });
        }
        PortError::Changed(path) if matches!(envelope.command.as_str(), "audit" | "status") => {
            envelope.outcome = Outcome::Unsupported;
            envelope.exit_code = 74;
            envelope.mutation = Mutation::None;
            envelope.notices.push(Notice {
                code: "filesystem-snapshot-changed".into(),
                path: Some(path),
                message: "Pinned filesystem identity changed during read-only inspection".into(),
            });
        }
        PortError::Changed(path) => conflict(
            envelope,
            "filesystem-snapshot-changed",
            &format!("Pinned filesystem identity changed at {path}"),
        ),
        PortError::Conflict(message) => conflict(envelope, "destination-conflict", &message),
        PortError::ReleaseUnavailable(message) => {
            conflict(envelope, "authenticated-release-unavailable", &message)
        }
        PortError::Missing(message)
        | PortError::UnsafePath(message)
        | PortError::Link(message)
        | PortError::ReleaseInvalid(message)
        | PortError::ManifestInvalid(message) => invalidate(envelope, message),
    }
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn relative_link_resolution_cannot_escape_repository() {
        assert_eq!(
            resolve_relative("docs/maps/index.md", "../README.md"),
            Some("docs/README.md".into())
        );
        assert_eq!(resolve_relative("docs/index.md", "../../outside"), None);
    }

    #[test]
    fn anchors_use_deterministic_duplicate_suffixes() {
        let anchors = parse_commonmark("# Hello World\n## Hello World\n").anchors;
        assert!(anchors.contains("hello-world"));
        assert!(anchors.contains("hello-world-1"));
    }

    #[test]
    fn preview_digest_depends_only_on_closed_operations() {
        let operations = vec![Operation {
            operation_id: "create-decision-template".into(),
            kind: OperationKind::Create,
            path: "docs/templates/decision.md".into(),
            disposition: crate::domain::Disposition::ManagedV1,
            before_sha256: None,
            after_sha256: Some("a".repeat(64)),
        }];
        let value = serde_json::to_value(&operations).unwrap();
        assert_eq!(digest(&value).unwrap(), digest(&value).unwrap());
    }
}
