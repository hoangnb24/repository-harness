//! Pure command application around injected filesystem, manifest, and release ports.

use std::collections::BTreeSet;

use semver::Version;

use crate::domain::{
    Activation, Command, Compatibility, Disposition, Envelope, Manifest, ManifestRepositoryMode,
    Mutation, Notice, Operation, OperationKind, Origin, Outcome, Ownership, PayloadIdentity,
    Readiness, ReleaseOutput, RepositoryMode, Role, ScaffoldOptions, UpdatePolicy, CORE_VERSION,
};
use crate::markdown::parse_commonmark;
use crate::path::{validate_exact_destination, validate_relative};
use crate::ports::{FileSystemPort, ManifestPort, MutationPort, PortError, ReleasePort, TrustPort};
use crate::recovery::{
    MutationFailure, MutationRequest, MutationResult, PlannedWrite, RecoveryAsset,
    RecoveryAuthorization, RecoveryMode, RecoveryProbe, RecoveryScope,
};
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
    mutations: Option<&'a dyn MutationPort>,
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
            mutations: None,
        }
    }

    pub fn with_mutations(
        filesystem: &'a dyn FileSystemPort,
        manifests: &'a dyn ManifestPort,
        releases: &'a dyn ReleasePort,
        trust: &'a dyn TrustPort,
        mutations: &'a dyn MutationPort,
    ) -> Self {
        Self {
            filesystem,
            manifests,
            releases,
            trust,
            mutations: Some(mutations),
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
        let mutation_validated_its_anchored_root = self.mutations.is_some()
            && matches!(
                envelope.mutation,
                Mutation::Committed | Mutation::RolledBack
            );
        if !matches!(command, Command::Version { .. })
            && matches!(envelope.exit_code, 0 | 2)
            && !mutation_validated_its_anchored_root
        {
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
                if !audit {
                    if let Some(mutations) = self.mutations {
                        match mutations.probe_recovery() {
                            Ok(probes) if !probes.is_empty() => {
                                return recovery_required_envelope(envelope, probes, None);
                            }
                            Ok(_) => {}
                            Err(error) => {
                                apply_port_error(&mut envelope, error);
                                return envelope;
                            }
                        }
                    }
                }
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
        envelope.details.readiness = if manifest
            .roles
            .iter()
            .any(|role| role.activation == Activation::Unresolved)
        {
            Readiness::Unresolved
        } else {
            Readiness::Ready
        };
        if !audit {
            if let Some(mutations) = self.mutations {
                match mutations.probe_recovery() {
                    Ok(probes) if !probes.is_empty() => {
                        return recovery_required_envelope(envelope, probes, None);
                    }
                    Ok(_) => {}
                    Err(error) => {
                        apply_port_error(&mut envelope, error);
                        return envelope;
                    }
                }
            }
        }
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
            if self.mutations.is_some() {
                return self.recover_mutation(command, options, scaffold);
            }
            conflict(
                &mut envelope,
                "phase3-recovery-unavailable",
                "Atomic backup/journal resume and rollback belong to Phase 3",
            );
            return envelope;
        }
        if let Some(mutations) = self.mutations {
            match mutations.probe_recovery() {
                Ok(probes) if !probes.is_empty() => {
                    let exact = options.accept_preview_sha256.as_deref();
                    return recovery_required_envelope(envelope, probes, exact);
                }
                Ok(_) => {}
                Err(error) => {
                    apply_port_error(&mut envelope, error);
                    return envelope;
                }
            }
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
                let violation = if violation == "payload-transition-release-sequence-regressed" {
                    format!("{violation}; resolve with explicit rollback or supported resume")
                } else {
                    violation
                };
                invalidate(&mut envelope, violation);
                return envelope;
            }
        }
        envelope.release = ReleaseOutput::from(release.identity().clone());
        if self.mutations.is_some() {
            return self.execute_phase3_plan(
                command,
                options,
                scaffold,
                existing.as_ref(),
                &release,
                envelope,
            );
        }
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

    fn recover_mutation(
        &self,
        command: &str,
        options: &crate::domain::MutatorOptions,
        scaffold: Option<&ScaffoldOptions>,
    ) -> Envelope {
        let mut envelope = Envelope::new(command);
        let (operation_id, mode) = match (&options.resume, &options.rollback) {
            (Some(operation_id), None) => (operation_id.as_str(), RecoveryMode::Resume),
            (None, Some(operation_id)) => (operation_id.as_str(), RecoveryMode::Rollback),
            _ => {
                invalidate(&mut envelope, "invalid recovery option state".into());
                return envelope;
            }
        };
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
        envelope.release = ReleaseOutput::from(release.identity().clone());
        let scope = match recovery_scope(command, scaffold) {
            Ok(scope) => scope,
            Err(error) => {
                apply_port_error(&mut envelope, error);
                return envelope;
            }
        };
        let assets = match recovery_assets(&release, &scope) {
            Ok(assets) => assets,
            Err(error) => {
                apply_port_error(&mut envelope, error);
                return envelope;
            }
        };
        let authorization = RecoveryAuthorization {
            release: release.identity().clone(),
            release_version: release.release().into(),
            scope,
            assets,
        };
        let mutations = self
            .mutations
            .expect("recovery dispatch requires the injected mutation port");
        let expected_release = authorization.release.clone();
        let mut validate = |bytes: &[u8]| {
            self.validate_authenticated_candidate(bytes, &expected_release)
                .map(|_| ())
        };
        match mutations.recover(command, operation_id, mode, &authorization, &mut validate) {
            Ok(MutationResult::Committed { manifest_bytes }) => {
                match self.validate_candidate_bytes(&manifest_bytes) {
                    Ok((manifest, audit)) => {
                        finish_committed(&mut envelope, &manifest, audit, Mutation::Committed)
                    }
                    Err(error) => apply_port_error(&mut envelope, error),
                }
            }
            Ok(MutationResult::RolledBack) => self.finish_rollback(&mut envelope),
            Err(failure) => apply_mutation_failure(
                &mut envelope,
                failure,
                Some(RecoveryProbe {
                    command: command.into(),
                    scope: authorization.scope.clone(),
                    operation_id: operation_id.into(),
                    accepted_preview_sha256: String::new(),
                }),
            ),
        }
        envelope
    }

    fn execute_phase3_plan(
        &self,
        command: &str,
        options: &crate::domain::MutatorOptions,
        scaffold: Option<&ScaffoldOptions>,
        existing: Option<&Manifest>,
        release: &VerifiedRelease,
        mut envelope: Envelope,
    ) -> Envelope {
        let candidate =
            match self.build_candidate(command, scaffold, existing, release, &mut envelope) {
                Ok(Some(candidate)) => candidate,
                Ok(None) => return envelope,
                Err(error) => {
                    apply_port_error(&mut envelope, error);
                    return envelope;
                }
            };
        if candidate.writes.is_empty() && existing == Some(&candidate.manifest) {
            envelope.notices.push(Notice {
                code: "idempotent-noop".into(),
                path: None,
                message: "Authenticated release and all declared bytes are already committed"
                    .into(),
            });
            finish_semantic_state(&mut envelope, &candidate.manifest, Mutation::None);
            return envelope;
        }
        let scope = match recovery_scope(command, scaffold) {
            Ok(scope) => scope,
            Err(error) => {
                apply_port_error(&mut envelope, error);
                return envelope;
            }
        };
        let mut request =
            match self.build_mutation_request(command, scope, release, existing, candidate) {
                Ok(request) => request,
                Err(error) => {
                    apply_port_error(&mut envelope, error);
                    return envelope;
                }
            };
        envelope.details.operations = Some(request.operations.clone());
        envelope.notices.push(Notice {
            code: "operation-id".into(),
            path: Some(format!(
                ".harness/recovery/{}/journal.json",
                request.operation_id
            )),
            message: request.operation_id.clone(),
        });
        envelope.notices.push(Notice {
            code: "preview-sha256".into(),
            path: None,
            message: request.preview_sha256.clone(),
        });
        if options
            .accept_preview_sha256
            .as_ref()
            .is_some_and(|accepted| accepted != &request.preview_sha256)
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
            return envelope;
        }
        let Some(accepted) = &options.accept_preview_sha256 else {
            conflict(
                &mut envelope,
                "confirmation-required",
                "Rerun with --non-interactive and the exact preview SHA-256",
            );
            return envelope;
        };
        if !options.non_interactive {
            conflict(
                &mut envelope,
                "confirmation-required",
                "Exact preview acceptance is valid only with --non-interactive",
            );
            return envelope;
        }
        request.accepted_preview_sha256 = accepted.clone();
        let mutations = self
            .mutations
            .expect("Phase 3 planning requires the injected mutation port");
        let expected_release = request.release.clone();
        let mut validate = |bytes: &[u8]| {
            self.validate_authenticated_candidate(bytes, &expected_release)
                .map(|_| ())
        };
        match mutations.apply(&request, &mut validate) {
            Ok(MutationResult::Committed { manifest_bytes }) => {
                match self.validate_candidate_bytes(&manifest_bytes) {
                    Ok((manifest, audit)) => {
                        finish_committed(&mut envelope, &manifest, audit, Mutation::Committed)
                    }
                    Err(error) => apply_port_error(&mut envelope, error),
                }
            }
            Ok(MutationResult::RolledBack) => {
                invalidate(
                    &mut envelope,
                    "apply returned an impossible rollback result".into(),
                );
            }
            Err(failure) => apply_mutation_failure(
                &mut envelope,
                failure,
                Some(RecoveryProbe {
                    command: command.into(),
                    scope: request.scope.clone(),
                    operation_id: request.operation_id.clone(),
                    accepted_preview_sha256: request.accepted_preview_sha256.clone(),
                }),
            ),
        }
        envelope
    }

    fn build_candidate(
        &self,
        command: &str,
        scaffold: Option<&ScaffoldOptions>,
        existing: Option<&Manifest>,
        release: &VerifiedRelease,
        envelope: &mut Envelope,
    ) -> Result<Option<CandidateMutation>, PortError> {
        if command == "scaffold" {
            return self.build_scaffold_candidate(
                scaffold.expect("scaffold options are present"),
                existing,
                release,
                envelope,
            );
        }
        let no_prior_manifest = existing.is_none();
        let mut manifest = existing.cloned().unwrap_or_else(|| Manifest {
            schema: crate::domain::MANIFEST_SCHEMA.into(),
            repository_mode: ManifestRepositoryMode::FreshV1,
            compatibility: Compatibility {
                cli_min: CORE_VERSION.into(),
                cli_max: CORE_VERSION.into(),
                template_release_min: release.release().into(),
                template_release_max: "1.999.999".into(),
            },
            payload: release.identity().clone(),
            roles: Vec::new(),
            conversion_receipt: None,
        });
        manifest.payload = release.identity().clone();
        let mut writes = Vec::new();
        let mut assets: Vec<&VerifiedAsset> = release.assets().iter().collect();
        assets.sort_by(|left, right| left.destination.cmp(&right.destination));
        for asset in assets {
            if let Some(index) = manifest
                .roles
                .iter()
                .position(|role| role.asset == asset.id)
            {
                let role = &mut manifest.roles[index];
                if role.ownership == Ownership::TargetOwned
                    || role.update_policy == UpdatePolicy::NeverAutoPatch
                {
                    envelope.notices.push(Notice {
                        code: "target-owned-preserved".into(),
                        path: Some(role.path.clone()),
                        message: format!(
                            "Candidate {} is available but never-auto-patch preserves target bytes",
                            asset.id
                        ),
                    });
                    continue;
                }
                if role.path != asset.destination {
                    conflict(
                        envelope,
                        "managed-destination-conflict",
                        &format!(
                            "Managed role {} is mapped to {}, not authenticated destination {}",
                            role.role, role.path, asset.destination
                        ),
                    );
                    return Ok(None);
                }
                let current = self.filesystem.read_declared(&role.path)?;
                let current_sha256 = hex_sha256(&current);
                if role.ownership == Ownership::ManagedBlock {
                    let marker = role.marker.as_deref().ok_or_else(|| {
                        PortError::ManifestInvalid(format!(
                            "managed block {} has no marker",
                            role.role
                        ))
                    })?;
                    let (prefix, interior, suffix) = managed_block_parts(&current, marker)?;
                    let candidate_interior = managed_candidate_interior(&asset.bytes, marker)?;
                    let candidate_sha256 = hex_sha256(&candidate_interior);
                    if interior == candidate_interior {
                        role.base_sha256 = Some(candidate_sha256);
                        role.template_release = Some(release.release().into());
                        continue;
                    }
                    let base = role.base_sha256.as_deref().unwrap_or("");
                    let interior_sha256 = hex_sha256(&interior);
                    if base != interior_sha256 {
                        three_way_conflict(
                            envelope,
                            &role.path,
                            base,
                            &interior_sha256,
                            &candidate_sha256,
                        );
                        return Ok(None);
                    }
                    let mut after = prefix;
                    after.extend_from_slice(&candidate_interior);
                    after.extend_from_slice(&suffix);
                    role.base_sha256 = Some(candidate_sha256);
                    role.current_sha256 = hex_sha256(&after);
                    role.template_release = Some(release.release().into());
                    role.activation =
                        activation_for(&role.role, &after, &mut role.unresolved_markers);
                    writes.push(TargetWriteDraft {
                        label: asset.id.clone(),
                        path: role.path.clone(),
                        before_sha256: Some(current_sha256),
                        after_bytes: after,
                        kind: OperationKind::ReplaceManagedBlock,
                        disposition: asset.disposition,
                    });
                } else {
                    if current == asset.bytes {
                        role.base_sha256 = Some(asset.sha256.clone());
                        role.current_sha256 = asset.sha256.clone();
                        role.template_release = Some(release.release().into());
                        continue;
                    }
                    let base = role.base_sha256.as_deref().unwrap_or("");
                    if base != current_sha256 {
                        three_way_conflict(
                            envelope,
                            &role.path,
                            base,
                            &current_sha256,
                            &asset.sha256,
                        );
                        return Ok(None);
                    }
                    role.base_sha256 = Some(asset.sha256.clone());
                    role.current_sha256 = asset.sha256.clone();
                    role.template_release = Some(release.release().into());
                    role.activation =
                        activation_for(&role.role, &asset.bytes, &mut role.unresolved_markers);
                    writes.push(TargetWriteDraft {
                        label: asset.id.clone(),
                        path: role.path.clone(),
                        before_sha256: Some(current_sha256),
                        after_bytes: asset.bytes.clone(),
                        kind: OperationKind::Create,
                        disposition: asset.disposition,
                    });
                }
            } else {
                let exists = self.filesystem.exists_declared(&asset.destination)?;
                if exists {
                    let bytes = self.filesystem.read_declared(&asset.destination)?;
                    if bytes != asset.bytes {
                        return Err(PortError::Conflict(format!(
                            "{} exists with bytes outside the authenticated release",
                            asset.destination
                        )));
                    }
                    let mut role =
                        role_from_asset(asset, release.release(), Origin::BrownfieldMapped);
                    role.ownership = Ownership::TargetOwned;
                    role.update_policy = UpdatePolicy::NeverAutoPatch;
                    if no_prior_manifest {
                        manifest.repository_mode = ManifestRepositoryMode::BrownfieldV1;
                    }
                    manifest.roles.push(role);
                    envelope.notices.push(Notice {
                        code: "brownfield-identical-mapped".into(),
                        path: Some(asset.destination.clone()),
                        message: "Existing identical bytes were conservatively mapped target-owned"
                            .into(),
                    });
                } else {
                    manifest
                        .roles
                        .push(role_from_asset(asset, release.release(), Origin::Created));
                    writes.push(TargetWriteDraft {
                        label: asset.id.clone(),
                        path: asset.destination.clone(),
                        before_sha256: None,
                        after_bytes: asset.bytes.clone(),
                        kind: OperationKind::Create,
                        disposition: asset.disposition,
                    });
                }
            }
        }
        manifest.roles.sort_by(|left, right| {
            (&left.path, &left.role, &left.asset).cmp(&(&right.path, &right.role, &right.asset))
        });
        Ok(Some(CandidateMutation { manifest, writes }))
    }

    fn build_scaffold_candidate(
        &self,
        options: &ScaffoldOptions,
        existing: Option<&Manifest>,
        release: &VerifiedRelease,
        envelope: &mut Envelope,
    ) -> Result<Option<CandidateMutation>, PortError> {
        let template = options
            .template
            .as_deref()
            .expect("parser requires template");
        let destination = options
            .destination
            .as_deref()
            .expect("parser requires destination");
        validate_exact_destination(destination)?;
        let Some(asset) = release
            .assets()
            .iter()
            .find(|asset| asset.id == template || asset.template.as_deref() == Some(template))
        else {
            invalidate(
                envelope,
                format!("template is not authenticated/indexed: {template}"),
            );
            return Ok(None);
        };
        if asset.destination != destination {
            invalidate(
                envelope,
                "scaffold destination differs from the signed exact destination".into(),
            );
            return Ok(None);
        }
        if self.filesystem.exists_declared(destination)? {
            if let Some(existing) = existing {
                let exact_committed_role = existing.roles.iter().any(|role| {
                    role.asset == asset.id
                        && role.path == destination
                        && role.ownership == Ownership::TargetOwned
                        && role.update_policy == UpdatePolicy::NeverAutoPatch
                });
                let current = self.filesystem.read_declared(destination)?;
                if exact_committed_role
                    && current == asset.bytes
                    && existing.payload == *release.identity()
                {
                    return Ok(Some(CandidateMutation {
                        manifest: existing.clone(),
                        writes: Vec::new(),
                    }));
                }
            }
            conflict(
                envelope,
                "scaffold-path-exists",
                "Scaffold never overwrites a pre-existing destination",
            );
            return Ok(None);
        }
        let mut manifest = existing.cloned().unwrap_or_else(|| Manifest {
            schema: crate::domain::MANIFEST_SCHEMA.into(),
            repository_mode: ManifestRepositoryMode::FreshV1,
            compatibility: Compatibility {
                cli_min: CORE_VERSION.into(),
                cli_max: CORE_VERSION.into(),
                template_release_min: release.release().into(),
                template_release_max: "1.999.999".into(),
            },
            payload: release.identity().clone(),
            roles: Vec::new(),
            conversion_receipt: None,
        });
        manifest.payload = release.identity().clone();
        let mut role = role_from_asset(asset, release.release(), Origin::Created);
        role.ownership = Ownership::TargetOwned;
        role.update_policy = UpdatePolicy::NeverAutoPatch;
        role.required = false;
        manifest.roles.push(role);
        manifest
            .roles
            .sort_by(|left, right| left.path.cmp(&right.path));
        Ok(Some(CandidateMutation {
            manifest,
            writes: vec![TargetWriteDraft {
                label: asset.id.clone(),
                path: destination.into(),
                before_sha256: None,
                after_bytes: asset.bytes.clone(),
                kind: OperationKind::Create,
                disposition: asset.disposition,
            }],
        }))
    }

    fn build_mutation_request(
        &self,
        command: &str,
        scope: RecoveryScope,
        release: &VerifiedRelease,
        existing: Option<&Manifest>,
        mut candidate: CandidateMutation,
    ) -> Result<MutationRequest, PortError> {
        let mut manifest_bytes = serde_json::to_vec(&candidate.manifest)
            .map_err(|error| PortError::ManifestInvalid(error.to_string()))?;
        manifest_bytes.push(b'\n');
        self.manifests.parse_bytes(&manifest_bytes)?;
        candidate
            .writes
            .sort_by(|left, right| left.path.cmp(&right.path));
        let target_operations: Vec<Operation> = candidate
            .writes
            .iter()
            .enumerate()
            .map(|(index, write)| Operation {
                operation_id: format!("write-{:03}-{}", index + 1, sanitize_id(&write.label)),
                kind: write.kind.clone(),
                path: write.path.clone(),
                disposition: write.disposition,
                before_sha256: write.before_sha256.clone(),
                after_sha256: Some(hex_sha256(&write.after_bytes)),
            })
            .collect();
        let seed = serde_json::json!({
            "command": command,
            "scope": scope,
            "release": release.identity(),
            "target_operations": target_operations,
            "manifest_sha256": hex_sha256(&manifest_bytes),
        });
        let operation_seed = digest(&seed).map_err(PortError::ManifestInvalid)?;
        // Recovery receives this identifier from the authenticated caller, not
        // from the journal. Keep the complete plan digest so it is also an
        // immutable authorization commitment for every exact post-image.
        let operation_id = format!("{command}-{operation_seed}");
        let operation_root = format!(".harness/recovery/{operation_id}");
        let mut operations = vec![Operation {
            operation_id: format!("journal-{operation_id}"),
            kind: OperationKind::WriteRecoveryJournal,
            path: format!("{operation_root}/journal.json"),
            disposition: Disposition::ManagedV1,
            before_sha256: None,
            after_sha256: None,
        }];
        let mut writes = Vec::new();
        for (index, (draft, operation)) in candidate
            .writes
            .into_iter()
            .zip(target_operations)
            .enumerate()
        {
            let step_id = format!("target-{:03}-{}", index + 1, sanitize_id(&draft.label));
            let backup_path = draft
                .before_sha256
                .as_ref()
                .map(|_| format!("{operation_root}/backups/{step_id}.bak"));
            let create_witness_path =
                create_witness_path(&operation_id, &step_id, draft.before_sha256.as_deref());
            if let (Some(before), Some(path)) = (&draft.before_sha256, &backup_path) {
                operations.push(Operation {
                    operation_id: format!("backup-{step_id}"),
                    kind: OperationKind::Create,
                    path: path.clone(),
                    disposition: Disposition::ManagedV1,
                    before_sha256: None,
                    after_sha256: Some(before.clone()),
                });
            }
            if let Some(path) = &create_witness_path {
                operations.push(Operation {
                    operation_id: format!("witness-{step_id}"),
                    kind: OperationKind::Create,
                    path: path.clone(),
                    disposition: Disposition::ManagedV1,
                    before_sha256: None,
                    after_sha256: operation.after_sha256.clone(),
                });
            }
            operations.push(operation);
            writes.push(PlannedWrite {
                step_id: step_id.clone(),
                operation_id: operations
                    .last()
                    .expect("target operation was just appended")
                    .operation_id
                    .clone(),
                kind: operations
                    .last()
                    .expect("target operation was just appended")
                    .kind
                    .clone(),
                disposition: operations
                    .last()
                    .expect("target operation was just appended")
                    .disposition,
                path: draft.path.clone(),
                before_sha256: draft.before_sha256,
                after_bytes: draft.after_bytes,
                backup_path,
                staged_path: format!("{operation_root}/staged/{step_id}.after"),
                temporary_path: temporary_path(&draft.path, &operation_id, &step_id),
                create_witness_path,
                manifest_commit: false,
            });
        }
        let manifest_before = if existing.is_some() {
            Some(self.filesystem.read_declared(".harness/manifest.json")?)
        } else {
            None
        };
        let manifest_before_sha256 = manifest_before.as_ref().map(|bytes| hex_sha256(bytes));
        let manifest_step = "manifest";
        let manifest_backup = manifest_before_sha256
            .as_ref()
            .map(|_| format!("{operation_root}/backups/{manifest_step}.bak"));
        if let (Some(before), Some(path)) = (&manifest_before_sha256, &manifest_backup) {
            operations.push(Operation {
                operation_id: "backup-manifest".into(),
                kind: OperationKind::Create,
                path: path.clone(),
                disposition: Disposition::ManagedV1,
                before_sha256: None,
                after_sha256: Some(before.clone()),
            });
        }
        if let Some(path) = create_witness_path(
            &operation_id,
            manifest_step,
            manifest_before_sha256.as_deref(),
        ) {
            operations.push(Operation {
                operation_id: format!("witness-{manifest_step}"),
                kind: OperationKind::Create,
                path,
                disposition: Disposition::ManagedV1,
                before_sha256: None,
                after_sha256: Some(hex_sha256(&manifest_bytes)),
            });
        }
        operations.push(Operation {
            operation_id: "write-manifest".into(),
            kind: OperationKind::WriteManifest,
            path: ".harness/manifest.json".into(),
            disposition: Disposition::ManagedV1,
            before_sha256: manifest_before_sha256.clone(),
            after_sha256: Some(hex_sha256(&manifest_bytes)),
        });
        writes.push(PlannedWrite {
            step_id: manifest_step.into(),
            operation_id: "write-manifest".into(),
            kind: OperationKind::WriteManifest,
            disposition: Disposition::ManagedV1,
            path: ".harness/manifest.json".into(),
            before_sha256: manifest_before_sha256.clone(),
            after_bytes: manifest_bytes,
            backup_path: manifest_backup,
            staged_path: format!("{operation_root}/staged/{manifest_step}.after"),
            temporary_path: temporary_path(".harness/manifest.json", &operation_id, manifest_step),
            create_witness_path: create_witness_path(
                &operation_id,
                manifest_step,
                manifest_before_sha256.as_deref(),
            ),
            manifest_commit: true,
        });
        let operations_value = serde_json::to_value(&operations)
            .map_err(|error| PortError::ManifestInvalid(error.to_string()))?;
        let preview_sha256 = digest(&operations_value).map_err(PortError::ManifestInvalid)?;
        Ok(MutationRequest {
            command: command.into(),
            scope,
            operation_id,
            preview_sha256: preview_sha256.clone(),
            accepted_preview_sha256: preview_sha256,
            release: release.identity().clone(),
            operations,
            writes,
        })
    }

    fn validate_candidate_bytes(&self, bytes: &[u8]) -> Result<(Manifest, AuditResult), PortError> {
        let manifest = self.manifests.parse_bytes(bytes)?;
        let audit = self.audit_manifest(&manifest)?;
        if !audit.violations.is_empty() {
            return Err(PortError::ManifestInvalid(format!(
                "candidate structural audit failed: {}",
                audit.violations.join(",")
            )));
        }
        Ok((manifest, audit))
    }

    fn validate_authenticated_candidate(
        &self,
        bytes: &[u8],
        expected_release: &PayloadIdentity,
    ) -> Result<(Manifest, AuditResult), PortError> {
        let release = self
            .releases
            .load()
            .and_then(|material| {
                self.trust
                    .load()
                    .and_then(|trust| verify_release(material, trust))
            })
            .map_err(|error| {
                PortError::Conflict(format!(
                    "authenticated release could not be revalidated before manifest commit: {error}"
                ))
            })?;
        if release.identity() != expected_release {
            return Err(PortError::Conflict(
                "authenticated payload identity changed before manifest commit".into(),
            ));
        }
        let (manifest, audit) = self.validate_candidate_bytes(bytes)?;
        if &manifest.payload != expected_release {
            return Err(PortError::ManifestInvalid(
                "candidate manifest payload differs from the authenticated operation identity"
                    .into(),
            ));
        }
        Ok((manifest, audit))
    }

    fn finish_rollback(&self, envelope: &mut Envelope) {
        envelope.mutation = Mutation::RolledBack;
        match self.manifests.load(self.filesystem) {
            Ok(Some(manifest)) => match self.audit_manifest(&manifest) {
                Ok(audit) if audit.violations.is_empty() => {
                    finish_committed(envelope, &manifest, audit, Mutation::RolledBack)
                }
                Ok(audit) => {
                    envelope.details.violations = audit.violations;
                    invalidate(envelope, "rollback-restored-invalid-manifest".into());
                    envelope.mutation = Mutation::RecoveryRequired;
                }
                Err(error) => apply_port_error(envelope, error),
            },
            Ok(None) => {
                envelope.outcome = Outcome::Success;
                envelope.exit_code = 0;
                envelope.repository_mode = RepositoryMode::Absent;
                envelope.details.readiness = Readiness::NotApplicable;
                envelope.mutation = Mutation::RolledBack;
            }
            Err(error) => apply_port_error(envelope, error),
        }
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

struct CandidateMutation {
    manifest: Manifest,
    writes: Vec<TargetWriteDraft>,
}

fn recovery_scope(
    command: &str,
    scaffold: Option<&ScaffoldOptions>,
) -> Result<RecoveryScope, PortError> {
    match command {
        "install" | "update" => Ok(RecoveryScope::ReleaseAssets),
        "scaffold" => {
            let options = scaffold.ok_or_else(|| {
                PortError::ManifestInvalid("scaffold recovery scope is unavailable".into())
            })?;
            let template = options.template.clone().ok_or_else(|| {
                PortError::ManifestInvalid("scaffold recovery template is unavailable".into())
            })?;
            let destination = options.destination.clone().ok_or_else(|| {
                PortError::ManifestInvalid("scaffold recovery destination is unavailable".into())
            })?;
            validate_exact_destination(&destination)?;
            Ok(RecoveryScope::Scaffold {
                template,
                destination,
            })
        }
        _ => Err(PortError::ManifestInvalid(
            "recovery command is outside the closed Phase 3 contract".into(),
        )),
    }
}

fn recovery_assets(
    release: &VerifiedRelease,
    scope: &RecoveryScope,
) -> Result<std::collections::BTreeMap<String, RecoveryAsset>, PortError> {
    let selected: Vec<&VerifiedAsset> = match scope {
        RecoveryScope::ReleaseAssets => release.assets().iter().collect(),
        RecoveryScope::Scaffold {
            template,
            destination,
        } => {
            let asset = release
                .assets()
                .iter()
                .find(|asset| {
                    (asset.id == *template || asset.template.as_deref() == Some(template.as_str()))
                        && asset.destination == *destination
                })
                .ok_or_else(|| {
                    PortError::ManifestInvalid(
                        "scaffold recovery template/destination is not authenticated".into(),
                    )
                })?;
            vec![asset]
        }
    };
    Ok(selected
        .into_iter()
        .map(|asset| {
            (
                asset.destination.clone(),
                RecoveryAsset {
                    id: asset.id.clone(),
                    role: asset.role.clone(),
                    template: asset.template.clone(),
                    destination: asset.destination.clone(),
                    disposition: asset.disposition,
                    sha256: asset.sha256.clone(),
                    bytes: asset.bytes.clone(),
                },
            )
        })
        .collect())
}

struct TargetWriteDraft {
    label: String,
    path: String,
    before_sha256: Option<String>,
    after_bytes: Vec<u8>,
    kind: OperationKind,
    disposition: Disposition,
}

type ManagedBlockParts = (Vec<u8>, Vec<u8>, Vec<u8>);

fn role_from_asset(asset: &VerifiedAsset, release: &str, origin: Origin) -> Role {
    let role_id = asset
        .role
        .clone()
        .unwrap_or_else(|| asset.id.replace('-', "_"));
    let mut unresolved_markers = Vec::new();
    let activation = activation_for(&role_id, &asset.bytes, &mut unresolved_markers);
    Role {
        role: role_id,
        asset: asset.id.clone(),
        activation,
        ownership: Ownership::ManagedFile,
        origin,
        required: asset.disposition == Disposition::ManagedV1,
        path: asset.destination.clone(),
        template: asset.template.clone().or_else(|| Some(asset.id.clone())),
        template_release: Some(release.into()),
        base_sha256: Some(asset.sha256.clone()),
        current_sha256: asset.sha256.clone(),
        marker: None,
        update_policy: UpdatePolicy::ReplaceIfBase,
        unresolved_markers,
    }
}

fn activation_for(role: &str, bytes: &[u8], markers: &mut Vec<String>) -> Activation {
    markers.clear();
    if let Ok(text) = std::str::from_utf8(bytes) {
        markers.extend(
            unresolved_tokens(text)
                .into_iter()
                .filter(|token| valid_unresolved_marker(role, token)),
        );
        markers.sort();
        markers.dedup();
    }
    if markers.is_empty() {
        Activation::Active
    } else {
        Activation::Unresolved
    }
}

fn managed_block_parts(bytes: &[u8], marker: &str) -> Result<ManagedBlockParts, PortError> {
    let text = std::str::from_utf8(bytes)
        .map_err(|_| PortError::ManifestInvalid("managed block is not UTF-8".into()))?;
    let open = format!("<!-- repository-harness:v1:begin:{marker} -->");
    let close = format!("<!-- repository-harness:v1:end:{marker} -->");
    let open_start = text.find(&open).ok_or_else(|| {
        PortError::ManifestInvalid("managed block opening marker is missing".into())
    })?;
    let content_start = open_start + open.len();
    let close_start = text[content_start..]
        .find(&close)
        .map(|offset| content_start + offset)
        .ok_or_else(|| {
            PortError::ManifestInvalid("managed block closing marker is missing".into())
        })?;
    if text[content_start..].matches(&close).count() != 1 || text.matches(&open).count() != 1 {
        return Err(PortError::ManifestInvalid(
            "managed block marker pair is not unique".into(),
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

fn three_way_conflict(
    envelope: &mut Envelope,
    path: &str,
    base: &str,
    current: &str,
    candidate: &str,
) {
    envelope.notices.extend([
        Notice {
            code: "three-way-base-sha256".into(),
            path: Some(path.into()),
            message: base.into(),
        },
        Notice {
            code: "three-way-current-sha256".into(),
            path: Some(path.into()),
            message: current.into(),
        },
        Notice {
            code: "three-way-candidate-sha256".into(),
            path: Some(path.into()),
            message: candidate.into(),
        },
    ]);
    conflict(
        envelope,
        "three-way-review-required",
        "Recorded base differs from current managed bytes; no automatic patch was attempted",
    );
}

fn sanitize_id(value: &str) -> String {
    let value = value
        .bytes()
        .map(|byte| {
            if byte.is_ascii_lowercase() || byte.is_ascii_digit() {
                char::from(byte)
            } else {
                '-'
            }
        })
        .collect::<String>();
    value.trim_matches('-').to_string()
}

fn temporary_path(path: &str, operation_id: &str, step_id: &str) -> String {
    if path == ".harness/manifest.json" {
        return format!(".harness/recovery/{operation_id}/staged/{step_id}.commit-tmp");
    }
    let name = format!(".repository-harness-tmp-{operation_id}-{step_id}");
    path.rsplit_once('/')
        .map_or(name.clone(), |(parent, _)| format!("{parent}/{name}"))
}

fn create_witness_path(
    operation_id: &str,
    step_id: &str,
    before_sha256: Option<&str>,
) -> Option<String> {
    before_sha256
        .is_none()
        .then(|| format!(".harness/recovery/{operation_id}/creates/{step_id}.link"))
}

fn finish_semantic_state(envelope: &mut Envelope, manifest: &Manifest, mutation: Mutation) {
    envelope.repository_mode = output_mode(manifest.repository_mode);
    envelope.release = ReleaseOutput::from(manifest.payload.clone());
    envelope.mutation = mutation;
    if manifest
        .roles
        .iter()
        .any(|role| role.activation == Activation::Unresolved)
    {
        envelope.outcome = Outcome::Unresolved;
        envelope.exit_code = 2;
        envelope.details.readiness = Readiness::Unresolved;
    } else {
        envelope.outcome = Outcome::Ready;
        envelope.exit_code = 0;
        envelope.details.readiness = Readiness::Ready;
    }
}

fn finish_committed(
    envelope: &mut Envelope,
    manifest: &Manifest,
    audit: AuditResult,
    mutation: Mutation,
) {
    finish_semantic_state(envelope, manifest, mutation);
    envelope.notices.extend(audit.notices);
}

fn apply_mutation_failure(
    envelope: &mut Envelope,
    failure: MutationFailure,
    probe: Option<RecoveryProbe>,
) {
    apply_port_error(envelope, failure.error);
    if failure.journal_started {
        // A durable journal makes this a recoverable mutation conflict even
        // when the underlying I/O failure would normally map to 74.
        envelope.exit_code = 4;
        envelope.outcome = Outcome::Conflict;
        envelope.mutation = Mutation::RecoveryRequired;
        envelope.notices.push(Notice {
            code: "recovery-required".into(),
            path: None,
            message: probe.as_ref().map_or_else(
                || {
                    "A durable operation journal exists; use command-owned resume or rollback"
                        .into()
                },
                recovery_instructions,
            ),
        });
    }
}

fn recovery_required_envelope(
    mut envelope: Envelope,
    probes: Vec<crate::recovery::RecoveryProbe>,
    accepted_preview: Option<&str>,
) -> Envelope {
    let command = envelope.command.clone();
    let status = command == "status";
    envelope.outcome = if status {
        Outcome::Invalid
    } else {
        Outcome::Conflict
    };
    envelope.exit_code = if status { 3 } else { 4 };
    envelope.mutation = Mutation::RecoveryRequired;
    for probe in probes {
        let exact_rerun = probe.command == command
            && accepted_preview == Some(probe.accepted_preview_sha256.as_str());
        envelope.notices.push(Notice {
            code: if exact_rerun {
                "exact-rerun-recovery-required".into()
            } else {
                "recovery-required".into()
            },
            path: Some(format!(
                ".harness/recovery/{}/journal.json",
                probe.operation_id
            )),
            message: format!(
                "Incomplete {} operation {}; {}",
                probe.command,
                probe.operation_id,
                recovery_instructions(&probe)
            ),
        });
    }
    envelope
}

fn recovery_instructions(probe: &RecoveryProbe) -> String {
    let mut prefix = vec![shell_argument(&probe.command)];
    if let RecoveryScope::Scaffold {
        template,
        destination,
    } = &probe.scope
    {
        prefix.extend([
            "--template".into(),
            shell_argument(template),
            "--destination".into(),
            shell_argument(destination),
        ]);
    }
    let prefix = prefix.join(" ");
    format!(
        "resume with `{prefix} --resume {operation}` or roll back with `{prefix} --rollback {operation}`",
        operation = shell_argument(&probe.operation_id)
    )
}

fn shell_argument(value: &str) -> String {
    if !value.is_empty()
        && value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'-' | b'_' | b'.' | b'/'))
    {
        return value.into();
    }
    format!("'{}'", value.replace('\'', "'\"'\"'"))
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
