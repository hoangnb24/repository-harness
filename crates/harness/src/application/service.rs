use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;

use crate::application::{
    CoreDistributionPort, InstallationStatePort, PortError, ThreeWayMergePort,
};
use crate::domain::{
    BaselineFile, ConflictReason, CoreDistribution, DoctorCheck, DoctorReport, FileChangeKind,
    FileStatus, FrozenWorkspaceFile, InstallReport, InstallationCondition, InstallationState,
    MergeOutcome, PlannedFileChange, ResolutionConflict, StatusReport, UpdateConflict,
    UpdateReport, UpdateResolutionSession, WorkspaceMutation,
};

pub struct CoreApplication<D, S, M> {
    distribution: D,
    state: S,
    merger: M,
}

impl<D, S, M> CoreApplication<D, S, M>
where
    D: CoreDistributionPort,
    S: InstallationStatePort,
    M: ThreeWayMergePort,
{
    pub fn new(distribution: D, state: S, merger: M) -> Self {
        Self {
            distribution,
            state,
            merger,
        }
    }

    pub fn install(&self, root: &Path, dry_run: bool) -> Result<InstallReport, ApplicationError> {
        let distribution = self.load_distribution()?;
        let recovered = if dry_run {
            false
        } else {
            self.state.recover_interrupted(root)?
        };
        if self.state.load(root)?.is_some() {
            return Err(ApplicationError::AlreadyInstalled);
        }

        let mut changes = Vec::new();
        let mut mutations = Vec::new();
        for file in &distribution.files {
            self.state.validate_managed_path(root, &file.path)?;
            match self.state.read_workspace_file(root, &file.path)? {
                Some(_) => changes.push(PlannedFileChange {
                    path: file.path.clone(),
                    kind: FileChangeKind::Adopt,
                }),
                None => {
                    changes.push(PlannedFileChange {
                        path: file.path.clone(),
                        kind: FileChangeKind::Create,
                    });
                    mutations.push(WorkspaceMutation::Write {
                        path: file.path.clone(),
                        content: file.content.clone(),
                    });
                }
            }
        }

        let state = state_from_distribution(&distribution);
        let receipt = if dry_run {
            None
        } else {
            Some(self.state.apply(root, &state, &mutations)?)
        };
        Ok(InstallReport {
            version: distribution.version,
            dry_run,
            applied: !dry_run,
            changes,
            backup_path: receipt.and_then(|value| value.backup_path),
            recovered_interrupted_transaction: recovered,
        })
    }

    pub fn update(&self, root: &Path, dry_run: bool) -> Result<UpdateReport, ApplicationError> {
        let distribution = self.load_distribution()?;
        let recovered = if dry_run {
            false
        } else {
            self.state.recover_interrupted(root)?
        };
        let installed = self
            .state
            .load(root)?
            .ok_or(ApplicationError::NotInstalled)?;
        installed.validate()?;
        ensure_forward_version(&installed.core_version, &distribution.version)?;

        let plan = self.plan_update(root, &distribution, &installed, &BTreeMap::new())?;
        if !dry_run {
            // A normal update means "re-plan from the installed version to the
            // latest candidate". Only --continue remains pinned to an existing
            // resolution session.
            self.state.clear_resolution(root)?;
            if !plan.conflicts.is_empty() && plan.conflicts.len() == plan.resolution_conflicts.len()
            {
                self.state.stage_resolution(
                    root,
                    &UpdateResolutionSession {
                        from_version: installed.core_version.clone(),
                        to_version: distribution.version.clone(),
                        conflicts: plan.resolution_conflicts.clone(),
                        frozen_files: plan.frozen_files.clone(),
                    },
                )?;
            }
        }

        let mut report = self.finish_update(
            root,
            distribution,
            installed,
            plan,
            FinishUpdate {
                dry_run,
                recovered,
                expected: None,
            },
        )?;
        if dry_run {
            // A normal dry-run previews a fresh latest-version plan but does
            // not claim that this preview replaced the retained session.
            report.resolution_staged = false;
        }
        Ok(report)
    }

    pub fn continue_update(
        &self,
        root: &Path,
        dry_run: bool,
    ) -> Result<UpdateReport, ApplicationError> {
        let distribution = self.load_distribution()?;
        let recovered = if dry_run {
            false
        } else {
            self.state.recover_interrupted(root)?
        };
        let installed = self
            .state
            .load(root)?
            .ok_or(ApplicationError::NotInstalled)?;
        installed.validate()?;
        ensure_forward_version(&installed.core_version, &distribution.version)?;
        let session = self
            .state
            .load_resolution(root)?
            .ok_or(ApplicationError::NoResolutionPending)?;
        if session.from_version != installed.core_version
            || session.to_version != distribution.version
        {
            return Err(ApplicationError::ResolutionVersionMismatch {
                installed: installed.core_version,
                candidate: distribution.version,
                session_from: session.from_version,
                session_to: session.to_version,
            });
        }
        let upstream = distribution
            .files
            .iter()
            .map(|file| (file.path.clone(), file))
            .collect::<BTreeMap<_, _>>();
        let baselines = installed
            .files
            .iter()
            .map(|file| (file.path.clone(), file))
            .collect::<BTreeMap<_, _>>();
        let expected_paths = upstream
            .keys()
            .chain(baselines.keys())
            .cloned()
            .collect::<BTreeSet<_>>();
        let frozen_paths = session
            .frozen_files
            .iter()
            .map(|file| file.path.clone())
            .collect::<BTreeSet<_>>();
        if frozen_paths.len() != session.frozen_files.len() || frozen_paths != expected_paths {
            return Err(ApplicationError::ResolutionPlanMismatch);
        }
        for frozen in &session.frozen_files {
            let current = self.state.read_workspace_file(root, &frozen.path)?;
            if current != frozen.content {
                return Err(ApplicationError::ResolutionDrift(frozen.path.clone()));
            }
        }
        let mut resolutions = BTreeMap::new();
        for conflict in &session.conflicts {
            let current = self
                .state
                .read_workspace_file(root, &conflict.path)?
                .ok_or_else(|| ApplicationError::ResolutionDrift(conflict.path.clone()))?;
            let base_matches = baselines
                .get(&conflict.path)
                .is_some_and(|base| base.content == conflict.base);
            let incoming_matches = upstream
                .get(&conflict.path)
                .is_some_and(|incoming| incoming.content == conflict.incoming);
            if current != conflict.local || !base_matches || !incoming_matches {
                return Err(ApplicationError::ResolutionDrift(conflict.path.clone()));
            }
            if contains_conflict_markers(&conflict.resolved) {
                return Err(ApplicationError::UnresolvedMarkers(conflict.path.clone()));
            }
            resolutions.insert(conflict.path.clone(), conflict.resolved.clone());
        }
        let plan = self.plan_update(root, &distribution, &installed, &resolutions)?;
        let report = self.finish_update(
            root,
            distribution,
            installed,
            plan,
            FinishUpdate {
                dry_run,
                recovered,
                expected: Some(&session.frozen_files),
            },
        )?;
        if report.applied {
            self.state.clear_resolution(root)?;
        }
        Ok(report)
    }

    pub fn abort_update(&self, root: &Path) -> Result<bool, ApplicationError> {
        self.state.clear_resolution(root).map_err(Into::into)
    }

    fn plan_update(
        &self,
        root: &Path,
        distribution: &CoreDistribution,
        installed: &InstallationState,
        resolutions: &BTreeMap<crate::domain::RelativePath, Vec<u8>>,
    ) -> Result<UpdatePlan, ApplicationError> {
        let mut changes = Vec::new();
        let mut conflicts = Vec::new();
        let mut resolution_conflicts = Vec::new();
        let mut mutations = Vec::new();
        let mut frozen_files = Vec::new();
        let upstream = distribution
            .files
            .iter()
            .map(|file| (file.path.clone(), file))
            .collect::<BTreeMap<_, _>>();
        let baselines = installed
            .files
            .iter()
            .map(|file| (file.path.clone(), file))
            .collect::<BTreeMap<_, _>>();
        let paths = upstream
            .keys()
            .chain(baselines.keys())
            .cloned()
            .collect::<BTreeSet<_>>();

        for path in paths {
            if let Err(error) = self.state.validate_managed_path(root, &path) {
                conflicts.push(UpdateConflict {
                    path: path.clone(),
                    reason: ConflictReason::UnsafePath,
                    detail: error.to_string(),
                });
                continue;
            }
            let local = self.state.read_workspace_file(root, &path)?;
            frozen_files.push(FrozenWorkspaceFile {
                path: path.clone(),
                content: local.clone(),
            });
            match (baselines.get(&path), upstream.get(&path), local) {
                (Some(base), Some(next), Some(local)) => {
                    if let Some(resolved) = resolutions.get(&path) {
                        let kind = if resolved == &local {
                            FileChangeKind::Preserve
                        } else {
                            mutations.push(WorkspaceMutation::Write {
                                path: path.clone(),
                                content: resolved.clone(),
                            });
                            FileChangeKind::Update
                        };
                        changes.push(PlannedFileChange { path, kind });
                        continue;
                    }
                    match self.merge_contents(&base.content, &local, &next.content)? {
                        MergeOutcome::Clean(content) => {
                            let kind = if content == local {
                                FileChangeKind::Preserve
                            } else {
                                mutations.push(WorkspaceMutation::Write {
                                    path: path.clone(),
                                    content,
                                });
                                FileChangeKind::Update
                            };
                            changes.push(PlannedFileChange { path, kind });
                        }
                        MergeOutcome::Conflict { content, detail } => {
                            resolution_conflicts.push(ResolutionConflict {
                                path: path.clone(),
                                base: base.content.clone(),
                                local,
                                incoming: next.content.clone(),
                                resolved: content,
                            });
                            conflicts.push(UpdateConflict {
                                path,
                                reason: ConflictReason::OverlappingChanges,
                                detail,
                            });
                        }
                    }
                }
                (Some(_), Some(_), None) => conflicts.push(UpdateConflict {
                    path,
                    reason: ConflictReason::MissingManagedFile,
                    detail: "managed file is missing from the consumer workspace".to_owned(),
                }),
                (None, Some(next), None) => {
                    changes.push(PlannedFileChange {
                        path: path.clone(),
                        kind: FileChangeKind::Create,
                    });
                    mutations.push(WorkspaceMutation::Write {
                        path,
                        content: next.content.clone(),
                    });
                }
                (None, Some(_), Some(_)) => conflicts.push(UpdateConflict {
                    path,
                    reason: ConflictReason::ExistingUnmanagedPath,
                    detail: "new upstream managed path already exists locally".to_owned(),
                }),
                (Some(base), None, Some(local)) if local == base.content => {
                    changes.push(PlannedFileChange {
                        path: path.clone(),
                        kind: FileChangeKind::Delete,
                    });
                    mutations.push(WorkspaceMutation::Delete { path });
                }
                (Some(_), None, Some(_)) => conflicts.push(UpdateConflict {
                    path,
                    reason: ConflictReason::ModifiedRemovedFile,
                    detail: "upstream removed a file that contains consumer changes".to_owned(),
                }),
                (Some(_), None, None) => changes.push(PlannedFileChange {
                    path,
                    kind: FileChangeKind::Preserve,
                }),
                (None, None, _) => unreachable!("path union cannot contain an absent path"),
            }
        }

        Ok(UpdatePlan {
            changes,
            conflicts,
            resolution_conflicts,
            mutations,
            frozen_files,
        })
    }

    fn finish_update(
        &self,
        root: &Path,
        distribution: CoreDistribution,
        installed: InstallationState,
        plan: UpdatePlan,
        options: FinishUpdate<'_>,
    ) -> Result<UpdateReport, ApplicationError> {
        let mut backup_path = None;
        let applied = plan.conflicts.is_empty() && !options.dry_run;
        if applied {
            let next_state = state_from_distribution(&distribution);
            let receipt = if let Some(expected) = options.expected {
                self.state
                    .apply_if_unchanged(root, &next_state, &plan.mutations, expected)?
            } else {
                self.state.apply(root, &next_state, &plan.mutations)?
            };
            backup_path = receipt.backup_path;
        }

        Ok(UpdateReport {
            from_version: installed.core_version,
            to_version: distribution.version,
            dry_run: options.dry_run,
            applied,
            changes: plan.changes,
            conflicts: plan.conflicts,
            resolution_staged: !applied && self.state.resolution_pending(root)?,
            backup_path,
            recovered_interrupted_transaction: options.recovered,
        })
    }

    pub fn status(&self, root: &Path) -> Result<StatusReport, ApplicationError> {
        let distribution = self.load_distribution()?;
        let Some(installed) = self.state.load(root)? else {
            return Ok(StatusReport {
                condition: InstallationCondition::NotInstalled,
                installed_version: None,
                target_version: distribution.version,
                files: Vec::new(),
            });
        };
        installed.validate()?;
        let mut files = Vec::new();
        for base in &installed.files {
            let local = self.state.read_workspace_file(root, &base.path)?;
            files.push(FileStatus {
                path: base.path.clone(),
                modified: local
                    .as_ref()
                    .is_some_and(|content| content != &base.content),
                missing: local.is_none(),
            });
        }
        let installed_version = semver::Version::parse(&installed.core_version)
            .map_err(|_| ApplicationError::InvalidCoreVersion(installed.core_version.clone()))?;
        let target_version = semver::Version::parse(&distribution.version)
            .map_err(|_| ApplicationError::InvalidCoreVersion(distribution.version.clone()))?;
        Ok(StatusReport {
            condition: if installed_version == target_version {
                InstallationCondition::Current
            } else if installed_version < target_version {
                InstallationCondition::UpdateAvailable
            } else {
                InstallationCondition::ExecutableOutdated
            },
            installed_version: Some(installed.core_version),
            target_version: distribution.version,
            files,
        })
    }

    pub fn doctor(&self, root: &Path) -> Result<DoctorReport, ApplicationError> {
        let mut checks = Vec::new();
        let pending = self.state.transaction_pending(root)?;
        checks.push(DoctorCheck {
            name: "transaction".to_owned(),
            passed: !pending,
            detail: if pending {
                "an interrupted transaction requires recovery by install or update".to_owned()
            } else {
                "no interrupted transaction".to_owned()
            },
        });
        let resolution_pending = self.state.resolution_pending(root)?;
        checks.push(DoctorCheck {
            name: "update_resolution".to_owned(),
            passed: !resolution_pending,
            detail: if resolution_pending {
                "an update conflict awaits human-directed resolution, continuation, or abort"
                    .to_owned()
            } else {
                "no staged update conflict".to_owned()
            },
        });
        checks.push(DoctorCheck {
            name: "three_way_merge".to_owned(),
            passed: self.merger.available()?,
            detail: "Git merge-file is required for overlapping update analysis".to_owned(),
        });
        match self.state.load(root) {
            Ok(Some(installed)) => {
                checks.push(DoctorCheck {
                    name: "provenance".to_owned(),
                    passed: installed.validate().is_ok(),
                    detail: format!("installed core {}", installed.core_version),
                });
                for baseline in installed.files {
                    let safety = self.state.validate_managed_path(root, &baseline.path);
                    checks.push(DoctorCheck {
                        name: format!("path:{}", baseline.path),
                        passed: safety.is_ok(),
                        detail: safety
                            .map(|_| "managed path is safe".to_owned())
                            .unwrap_or_else(|error| error.to_string()),
                    });
                }
            }
            Ok(None) => checks.push(DoctorCheck {
                name: "provenance".to_owned(),
                passed: false,
                detail: "core is not installed".to_owned(),
            }),
            Err(error) => checks.push(DoctorCheck {
                name: "provenance".to_owned(),
                passed: false,
                detail: error.to_string(),
            }),
        }
        Ok(DoctorReport {
            healthy: checks.iter().all(|check| check.passed),
            checks,
        })
    }

    fn load_distribution(&self) -> Result<CoreDistribution, ApplicationError> {
        let distribution = self.distribution.current()?;
        distribution.validate()?;
        Ok(distribution)
    }

    fn merge_contents(
        &self,
        base: &[u8],
        local: &[u8],
        upstream: &[u8],
    ) -> Result<MergeOutcome, ApplicationError> {
        if local == base {
            return Ok(MergeOutcome::Clean(upstream.to_vec()));
        }
        if upstream == base || local == upstream {
            return Ok(MergeOutcome::Clean(local.to_vec()));
        }
        self.merger.merge(base, local, upstream).map_err(Into::into)
    }
}

struct UpdatePlan {
    changes: Vec<PlannedFileChange>,
    conflicts: Vec<UpdateConflict>,
    resolution_conflicts: Vec<ResolutionConflict>,
    mutations: Vec<WorkspaceMutation>,
    frozen_files: Vec<FrozenWorkspaceFile>,
}

struct FinishUpdate<'a> {
    dry_run: bool,
    recovered: bool,
    expected: Option<&'a [FrozenWorkspaceFile]>,
}

fn ensure_forward_version(installed: &str, candidate: &str) -> Result<(), ApplicationError> {
    let installed_version = semver::Version::parse(installed)
        .map_err(|_| ApplicationError::InvalidCoreVersion(installed.to_owned()))?;
    let candidate_version = semver::Version::parse(candidate)
        .map_err(|_| ApplicationError::InvalidCoreVersion(candidate.to_owned()))?;
    if candidate_version < installed_version {
        return Err(ApplicationError::CoreDowngrade {
            installed: installed.to_owned(),
            candidate: candidate.to_owned(),
        });
    }
    Ok(())
}

fn contains_conflict_markers(content: &[u8]) -> bool {
    content.split(|byte| *byte == b'\n').any(|line| {
        line.starts_with(b"<<<<<<< ")
            || line.starts_with(b"||||||| ")
            || line == b"======="
            || line.starts_with(b">>>>>>> ")
    })
}

fn state_from_distribution(distribution: &CoreDistribution) -> InstallationState {
    InstallationState {
        schema_version: InstallationState::SCHEMA_VERSION,
        core_version: distribution.version.clone(),
        files: distribution
            .files
            .iter()
            .map(|file| BaselineFile {
                path: file.path.clone(),
                content: file.content.clone(),
                hash: file.hash.clone(),
            })
            .collect(),
    }
}

#[derive(Debug, thiserror::Error)]
pub enum ApplicationError {
    #[error("core is already installed; run `harness update`")]
    AlreadyInstalled,
    #[error("core is not installed; run `harness install`")]
    NotInstalled,
    #[error("no update resolution is pending")]
    NoResolutionPending,
    #[error("update resolution no longer matches installed/candidate versions (installed={installed}, candidate={candidate}, session={session_from}->{session_to}); abort and restart the update")]
    ResolutionVersionMismatch {
        installed: String,
        candidate: String,
        session_from: String,
        session_to: String,
    },
    #[error("staged update plan no longer matches the installed/candidate managed paths; abort and restart the update")]
    ResolutionPlanMismatch,
    #[error("workspace or staged inputs changed after conflict detection for {0}; abort and restart the update")]
    ResolutionDrift(crate::domain::RelativePath),
    #[error("resolution still contains conflict markers for {0}")]
    UnresolvedMarkers(crate::domain::RelativePath),
    #[error("invalid Harness core version: {0}")]
    InvalidCoreVersion(String),
    #[error("refusing to downgrade installed core {installed} to candidate {candidate}")]
    CoreDowngrade {
        installed: String,
        candidate: String,
    },
    #[error(transparent)]
    Port(#[from] PortError),
    #[error(transparent)]
    Domain(#[from] crate::domain::DomainError),
}

#[cfg(test)]
mod tests {
    use std::cell::RefCell;
    use std::collections::BTreeMap;
    use std::path::Path;

    use super::*;
    use crate::application::{CoreDistributionPort, InstallationStatePort, ThreeWayMergePort};
    use crate::domain::{ApplyReceipt, ContentHash, DistributionFile, RelativePath};

    #[derive(Clone)]
    struct DistributionFixture(CoreDistribution);

    impl CoreDistributionPort for DistributionFixture {
        fn current(&self) -> Result<CoreDistribution, PortError> {
            Ok(self.0.clone())
        }
    }

    #[derive(Default)]
    struct StateFixture {
        installation: RefCell<Option<InstallationState>>,
        files: RefCell<BTreeMap<RelativePath, Vec<u8>>>,
        resolution: RefCell<Option<UpdateResolutionSession>>,
    }

    impl InstallationStatePort for StateFixture {
        fn recover_interrupted(&self, _root: &Path) -> Result<bool, PortError> {
            Ok(false)
        }
        fn transaction_pending(&self, _root: &Path) -> Result<bool, PortError> {
            Ok(false)
        }
        fn load(&self, _root: &Path) -> Result<Option<InstallationState>, PortError> {
            Ok(self.installation.borrow().clone())
        }
        fn read_workspace_file(
            &self,
            _root: &Path,
            path: &RelativePath,
        ) -> Result<Option<Vec<u8>>, PortError> {
            Ok(self.files.borrow().get(path).cloned())
        }
        fn validate_managed_path(
            &self,
            _root: &Path,
            _path: &RelativePath,
        ) -> Result<(), PortError> {
            Ok(())
        }
        fn apply(
            &self,
            _root: &Path,
            state: &InstallationState,
            mutations: &[WorkspaceMutation],
        ) -> Result<ApplyReceipt, PortError> {
            let mut files = self.files.borrow_mut();
            for mutation in mutations {
                match mutation {
                    WorkspaceMutation::Write { path, content } => {
                        files.insert(path.clone(), content.clone());
                    }
                    WorkspaceMutation::Delete { path } => {
                        files.remove(path);
                    }
                }
            }
            *self.installation.borrow_mut() = Some(state.clone());
            Ok(ApplyReceipt { backup_path: None })
        }
        fn apply_if_unchanged(
            &self,
            root: &Path,
            state: &InstallationState,
            mutations: &[WorkspaceMutation],
            expected: &[FrozenWorkspaceFile],
        ) -> Result<ApplyReceipt, PortError> {
            for frozen in expected {
                if self.files.borrow().get(&frozen.path).cloned() != frozen.content {
                    return Err(PortError::new(format!(
                        "workspace changed after conflict detection for {}",
                        frozen.path
                    )));
                }
            }
            self.apply(root, state, mutations)
        }
        fn resolution_pending(&self, _root: &Path) -> Result<bool, PortError> {
            Ok(self.resolution.borrow().is_some())
        }
        fn stage_resolution(
            &self,
            _root: &Path,
            session: &UpdateResolutionSession,
        ) -> Result<(), PortError> {
            *self.resolution.borrow_mut() = Some(session.clone());
            Ok(())
        }
        fn load_resolution(
            &self,
            _root: &Path,
        ) -> Result<Option<UpdateResolutionSession>, PortError> {
            Ok(self.resolution.borrow().clone())
        }
        fn clear_resolution(&self, _root: &Path) -> Result<bool, PortError> {
            Ok(self.resolution.borrow_mut().take().is_some())
        }
    }

    struct MergeFixture;
    impl ThreeWayMergePort for MergeFixture {
        fn available(&self) -> Result<bool, PortError> {
            Ok(true)
        }
        fn merge(
            &self,
            _base: &[u8],
            _local: &[u8],
            _upstream: &[u8],
        ) -> Result<MergeOutcome, PortError> {
            Ok(MergeOutcome::Conflict {
                content: b"<<<<<<< local\nlocal\n=======\nincoming\n>>>>>>> upstream\n".to_vec(),
                detail: "overlap".to_owned(),
            })
        }
    }

    fn distribution(version: &str, content: &[u8]) -> CoreDistribution {
        CoreDistribution {
            version: version.to_owned(),
            files: vec![DistributionFile {
                path: RelativePath::parse("AGENTS.md").unwrap(),
                content: content.to_vec(),
                hash: ContentHash::parse("a".repeat(64)).unwrap(),
            }],
        }
    }

    #[test]
    fn install_adopts_existing_files_without_overwriting_them() {
        let state = StateFixture::default();
        state.files.borrow_mut().insert(
            RelativePath::parse("AGENTS.md").unwrap(),
            b"consumer".to_vec(),
        );
        let app = CoreApplication::new(
            DistributionFixture(distribution("1.0.0", b"upstream")),
            state,
            MergeFixture,
        );
        let report = app.install(Path::new("."), false).unwrap();
        assert_eq!(report.changes[0].kind, FileChangeKind::Adopt);
        assert!(report.applied);
    }

    #[test]
    fn update_stops_when_local_and_upstream_changes_overlap() {
        let state = StateFixture::default();
        let path = RelativePath::parse("AGENTS.md").unwrap();
        state
            .files
            .borrow_mut()
            .insert(path.clone(), b"local".to_vec());
        *state.installation.borrow_mut() =
            Some(state_from_distribution(&distribution("1.0.0", b"base")));
        let app = CoreApplication::new(
            DistributionFixture(distribution("2.0.0", b"upstream")),
            state,
            MergeFixture,
        );
        let report = app.update(Path::new("."), false).unwrap();
        assert!(!report.applied);
        assert_eq!(report.conflicts.len(), 1);
    }
}
