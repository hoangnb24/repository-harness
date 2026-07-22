use std::path::Path;

use semver::Version;

use crate::application::{CandidateRequest, InstallationStatePort, PortError, UpdateCandidatePort};

pub struct SelfUpdateApplication<C, S> {
    candidates: C,
    state: S,
}

#[derive(Debug)]
pub enum SelfUpdateExit {
    Forwarded {
        code: i32,
        stdout: Vec<u8>,
        stderr: Vec<u8>,
    },
    Recovery(ExecutableRecoveryReport),
}

#[derive(Debug)]
pub struct ExecutableRecoveryReport {
    pub executable_version: String,
    pub core_version: String,
    pub dry_run: bool,
    pub applied: bool,
}

impl<C, S> SelfUpdateApplication<C, S>
where
    C: UpdateCandidatePort,
    S: InstallationStatePort,
{
    pub fn new(candidates: C, state: S) -> Self {
        Self { candidates, state }
    }

    pub fn execute(
        &self,
        root: &Path,
        dry_run: bool,
        continue_update: bool,
        json: bool,
    ) -> Result<SelfUpdateExit, PortError> {
        let installed = self
            .state
            .load(root)?
            .ok_or_else(|| PortError::new("core is not installed; run `harness install`"))?;
        let installed_version = parse_version("installed core", &installed.core_version)?;
        let executable_version = parse_version("installed executable", env!("CARGO_PKG_VERSION"))?;

        if installed_version > executable_version {
            let candidate = self
                .candidates
                .staged(root, &installed.core_version)
                .or_else(|_| self.candidates.exact(&installed.core_version))?;
            self.verify_identity(&candidate, &installed_version)?;
            if !dry_run {
                self.candidates.validate_replacement_target(root)?;
                self.candidates.persist(root, &candidate)?;
                self.candidates.replace(&candidate)?;
                self.candidates.clear_persisted(root)?;
            }
            return Ok(SelfUpdateExit::Recovery(ExecutableRecoveryReport {
                executable_version: executable_version.to_string(),
                core_version: installed_version.to_string(),
                dry_run,
                applied: !dry_run,
            }));
        }

        let candidate = if continue_update {
            let session = self
                .state
                .load_resolution(root)?
                .ok_or_else(|| PortError::new("no update resolution is pending"))?;
            self.candidates.staged(root, &session.to_version)?
        } else {
            self.candidates.latest()?
        };
        let candidate_version = self.verify_identity(&candidate, &installed_version)?;
        if candidate_version < executable_version {
            return Err(PortError::new(format!(
                "release candidate {candidate_version} is older than installed executable {executable_version}"
            )));
        }
        let replaces_executable = candidate_version > executable_version;
        if replaces_executable && !dry_run {
            self.candidates.validate_replacement_target(root)?;
        }
        if !continue_update && !dry_run {
            // Starting a normal update explicitly abandons any pinned plan and
            // retained candidate before handing off to the latest candidate.
            self.state.clear_resolution(root)?;
            self.candidates.clear_persisted(root)?;
        }
        if replaces_executable && !dry_run {
            self.candidates.persist(root, &candidate)?;
        }

        let output = self.candidates.execute(
            &candidate,
            &CandidateRequest {
                root,
                dry_run,
                continue_update,
                json,
            },
        )?;

        if output.code == 2 && !dry_run {
            self.candidates.persist(root, &candidate)?;
        } else if output.code == 0 && !dry_run && replaces_executable {
            self.candidates.replace(&candidate).map_err(|error| {
                PortError::new(format!(
                    "core files updated; executable recovery remains pending: {error}"
                ))
            })?;
            self.candidates.clear_persisted(root)?;
        } else if output.code == 0 && !dry_run {
            self.candidates.clear_persisted(root)?;
        }

        Ok(SelfUpdateExit::Forwarded {
            code: output.code,
            stdout: output.stdout,
            stderr: output.stderr,
        })
    }

    pub fn discard_retained_candidate(&self, root: &Path) -> Result<(), PortError> {
        self.candidates.clear_persisted(root)
    }

    fn verify_identity(
        &self,
        candidate: &C::Candidate,
        installed_version: &Version,
    ) -> Result<Version, PortError> {
        let release_version = parse_version(
            "release pointer",
            self.candidates.release_version(candidate),
        )?;
        let reported = self.candidates.reported_version(candidate)?;
        let candidate_version = parse_version("release candidate", &reported)?;
        if candidate_version != release_version {
            return Err(PortError::new(format!(
                "release identity mismatch: pointer={release_version}, candidate={candidate_version}"
            )));
        }
        if candidate_version < *installed_version {
            return Err(PortError::new(format!(
                "release candidate {candidate_version} would downgrade installed core {installed_version}"
            )));
        }
        Ok(candidate_version)
    }
}

fn parse_version(label: &str, value: &str) -> Result<Version, PortError> {
    Version::parse(value)
        .map_err(|error| PortError::new(format!("invalid {label} version {value}: {error}")))
}
