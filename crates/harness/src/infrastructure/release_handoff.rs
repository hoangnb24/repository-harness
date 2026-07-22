use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

use semver::Version;
use sha2::{Digest, Sha256};

use crate::application::{CandidateExit, CandidateRequest, PortError, UpdateCandidatePort};

const RELEASE_TAG_URL: &str =
    "https://raw.githubusercontent.com/hoangnb24/repository-harness/main/scripts/harness-release-tag";
const RELEASE_DOWNLOAD_ROOT: &str =
    "https://github.com/hoangnb24/repository-harness/releases/download";

pub struct LatestReleaseCandidates {
    test_release_root: Option<String>,
    replace_executable: bool,
}

pub struct VerifiedCandidate {
    _temp: tempfile::TempDir,
    path: PathBuf,
    release_version: String,
}

impl Default for LatestReleaseCandidates {
    fn default() -> Self {
        let test_release_root = cfg!(debug_assertions)
            .then(|| env::var("HARNESS_TEST_RELEASE_ROOT").ok())
            .flatten();
        let replace_executable =
            !(cfg!(debug_assertions) && env::var_os("HARNESS_TEST_SKIP_SELF_REPLACE").is_some());
        Self {
            test_release_root,
            replace_executable,
        }
    }
}

impl UpdateCandidatePort for LatestReleaseCandidates {
    type Candidate = VerifiedCandidate;

    fn latest(&self) -> Result<Self::Candidate, PortError> {
        let temp = tempfile::NamedTempFile::new().map_err(io_error)?;
        fetch_url(&self.pointer_url(), temp.path())?;
        let content = fs::read_to_string(temp.path()).map_err(io_error)?;
        let tag = content
            .lines()
            .map(str::trim)
            .find(|line| !line.is_empty() && !line.starts_with('#'))
            .ok_or_else(|| PortError::new("Harness core release pointer is empty"))?;
        let version = parse_release_tag(tag)?;
        self.download_version(&version)
    }

    fn exact(&self, version: &str) -> Result<Self::Candidate, PortError> {
        Version::parse(version)
            .map_err(|error| PortError::new(format!("invalid core version {version}: {error}")))?;
        self.download_version(version)
    }

    fn staged(&self, root: &Path, version: &str) -> Result<Self::Candidate, PortError> {
        Version::parse(version).map_err(|error| {
            PortError::new(format!("invalid staged version {version}: {error}"))
        })?;
        let staged = require_regular_repository_file(
            root,
            &[".harness-core", "update-candidate", candidate_filename()],
            "staged update candidate",
        )?;
        let temp = tempfile::tempdir().map_err(io_error)?;
        let path = temp.path().join(candidate_filename());
        fs::copy(staged, &path).map_err(io_error)?;
        let expected = self.fetch_expected_checksum(version, temp.path())?;
        verify_candidate(&path, &expected)?;
        make_executable(&path)?;
        Ok(VerifiedCandidate {
            _temp: temp,
            path,
            release_version: version.to_owned(),
        })
    }

    fn release_version<'a>(&self, candidate: &'a Self::Candidate) -> &'a str {
        &candidate.release_version
    }

    fn reported_version(&self, candidate: &Self::Candidate) -> Result<String, PortError> {
        read_candidate_version(&candidate.path)
    }

    fn execute(
        &self,
        candidate: &Self::Candidate,
        request: &CandidateRequest<'_>,
    ) -> Result<CandidateExit, PortError> {
        let mut command = Command::new(&candidate.path);
        command
            .arg("update")
            .arg("--candidate")
            .arg("--directory")
            .arg(request.root);
        if request.dry_run {
            command.arg("--dry-run");
        }
        if request.continue_update {
            command.arg("--continue");
        }
        if request.json {
            command.arg("--json");
        }
        let output = command.output().map_err(|error| {
            PortError::new(format!(
                "could not execute verified update candidate: {error}"
            ))
        })?;
        Ok(CandidateExit {
            code: output.status.code().unwrap_or(1),
            stdout: output.stdout,
            stderr: output.stderr,
        })
    }

    fn persist(&self, root: &Path, candidate: &Self::Candidate) -> Result<(), PortError> {
        let target_root = persisted_root(root);
        reject_existing_repository_symlinks(
            root,
            &[".harness-core", "update-candidate"],
            ".harness-core/update-candidate",
        )?;
        fs::create_dir_all(&target_root).map_err(io_error)?;
        require_repository_directories(
            root,
            &[".harness-core", "update-candidate"],
            ".harness-core/update-candidate",
        )?;
        let target = persisted_candidate(root);
        reject_existing_repository_symlinks(
            root,
            &[".harness-core", "update-candidate", candidate_filename()],
            "staged update candidate",
        )?;
        if target.exists() {
            require_regular_repository_file(
                root,
                &[".harness-core", "update-candidate", candidate_filename()],
                "staged update candidate",
            )?;
        }
        fs::copy(&candidate.path, &target).map_err(io_error)?;
        make_executable(&target)
    }

    fn clear_persisted(&self, root: &Path) -> Result<(), PortError> {
        let target_root = persisted_root(root);
        match fs::symlink_metadata(&target_root) {
            Ok(_) => {
                require_repository_directories(
                    root,
                    &[".harness-core", "update-candidate"],
                    ".harness-core/update-candidate",
                )?;
                fs::remove_dir_all(target_root).map_err(io_error)?;
            }
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => {}
            Err(error) => return Err(io_error(error)),
        }
        Ok(())
    }

    fn validate_replacement_target(&self, root: &Path) -> Result<(), PortError> {
        if !self.replace_executable {
            return Ok(());
        }
        let expected_path = require_regular_repository_file(
            root,
            &["scripts", "bin", candidate_filename()],
            "installed repository executable",
        )?;
        let expected = expected_path.canonicalize().map_err(io_error)?;
        let current = env::current_exe()
            .and_then(|path| path.canonicalize())
            .map_err(io_error)?;
        if current != expected {
            return Err(PortError::new(format!(
                "refusing to update {} while running {}; invoke the repository-local executable",
                expected.display(),
                current.display()
            )));
        }
        Ok(())
    }

    fn replace(&self, candidate: &Self::Candidate) -> Result<(), PortError> {
        if !self.replace_executable {
            return Ok(());
        }
        self_replace::self_replace(&candidate.path).map_err(|error| {
            PortError::new(format!("could not replace installed executable: {error}"))
        })
    }
}

impl LatestReleaseCandidates {
    fn pointer_url(&self) -> String {
        self.test_release_root
            .as_ref()
            .map(|root| format!("{}/harness-release-tag", root.trim_end_matches('/')))
            .unwrap_or_else(|| RELEASE_TAG_URL.to_owned())
    }

    fn download_version(&self, version: &str) -> Result<VerifiedCandidate, PortError> {
        let temp = tempfile::tempdir().map_err(io_error)?;
        let path = temp.path().join(candidate_filename());
        let artifact = candidate_artifact()?;
        let base_url = self.release_base_url(version);
        fetch(&base_url, artifact, &path)?;
        let expected = self.fetch_expected_checksum(version, temp.path())?;
        verify_candidate(&path, &expected)?;
        make_executable(&path)?;
        Ok(VerifiedCandidate {
            _temp: temp,
            path,
            release_version: version.to_owned(),
        })
    }

    fn fetch_expected_checksum(&self, version: &str, temp: &Path) -> Result<String, PortError> {
        let artifact = candidate_artifact()?;
        let checksum = temp.join(format!("{artifact}.sha256"));
        fetch(
            &self.release_base_url(version),
            &format!("{artifact}.sha256"),
            &checksum,
        )?;
        read_expected_checksum(&checksum)
    }

    fn release_base_url(&self, version: &str) -> String {
        let tag = format!("harness-v{version}");
        self.test_release_root
            .as_ref()
            .map(|root| format!("{}/{tag}", root.trim_end_matches('/')))
            .unwrap_or_else(|| format!("{RELEASE_DOWNLOAD_ROOT}/{tag}"))
    }

    #[cfg(test)]
    fn for_test(root: &Path) -> Self {
        Self {
            test_release_root: Some(format!("file://{}", root.display())),
            replace_executable: false,
        }
    }
}

fn parse_release_tag(tag: &str) -> Result<String, PortError> {
    let version = tag
        .strip_prefix("harness-v")
        .ok_or_else(|| PortError::new(format!("invalid Harness core release tag: {tag}")))?;
    Version::parse(version)
        .map_err(|error| PortError::new(format!("invalid release tag {tag}: {error}")))?;
    Ok(version.to_owned())
}

fn read_candidate_version(path: &Path) -> Result<String, PortError> {
    let output = Command::new(path)
        .arg("--version")
        .output()
        .map_err(|error| PortError::new(format!("could not query candidate version: {error}")))?;
    if !output.status.success() {
        return Err(PortError::new("candidate did not report its version"));
    }
    let text = String::from_utf8_lossy(&output.stdout);
    text.split_whitespace()
        .last()
        .map(str::to_owned)
        .ok_or_else(|| PortError::new("candidate version output is empty"))
}

fn fetch(base_url: &str, asset: &str, destination: &Path) -> Result<(), PortError> {
    let url = format!("{}/{asset}", base_url.trim_end_matches('/'));
    fetch_url(&url, destination)
}

fn fetch_url(url: &str, destination: &Path) -> Result<(), PortError> {
    if let Some(path) = url.strip_prefix("file://") {
        fs::copy(path, destination).map_err(io_error)?;
        return Ok(());
    }
    let output = Command::new("curl")
        .args([
            "-fsSL",
            "--connect-timeout",
            "15",
            "--max-time",
            "120",
            url,
            "-o",
        ])
        .arg(destination)
        .output()
        .map_err(|error| PortError::new(format!("could not run curl: {error}")))?;
    if !output.status.success() {
        return Err(PortError::new(format!(
            "could not download {url}: {}",
            String::from_utf8_lossy(&output.stderr).trim()
        )));
    }
    Ok(())
}

fn read_expected_checksum(path: &Path) -> Result<String, PortError> {
    let content = fs::read_to_string(path).map_err(io_error)?;
    let expected = content
        .split_whitespace()
        .next()
        .ok_or_else(|| PortError::new("candidate checksum file is empty"))?;
    if expected.len() != 64 || !expected.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        return Err(PortError::new("candidate checksum is not a SHA-256 digest"));
    }
    Ok(expected.to_ascii_lowercase())
}

fn verify_candidate(path: &Path, expected: &str) -> Result<(), PortError> {
    let bytes = fs::read(path).map_err(io_error)?;
    let actual = format!("{:x}", Sha256::digest(bytes));
    if actual != expected {
        return Err(PortError::new(format!(
            "candidate checksum mismatch: expected {expected}, got {actual}"
        )));
    }
    Ok(())
}

fn candidate_artifact() -> Result<&'static str, PortError> {
    match (env::consts::OS, env::consts::ARCH) {
        ("macos", "aarch64") => Ok("harness-macos-arm64"),
        ("macos", "x86_64") => Ok("harness-macos-x64"),
        ("linux", "aarch64") => Ok("harness-linux-arm64"),
        ("linux", "x86_64") => Ok("harness-linux-x64"),
        ("windows", "x86_64") => Ok("harness-windows-x64.exe"),
        (os, arch) => Err(PortError::new(format!(
            "unsupported Harness update platform: {os}/{arch}"
        ))),
    }
}

fn candidate_filename() -> &'static str {
    if cfg!(windows) {
        "harness.exe"
    } else {
        "harness"
    }
}

fn persisted_root(root: &Path) -> PathBuf {
    root.join(".harness-core/update-candidate")
}

fn persisted_candidate(root: &Path) -> PathBuf {
    persisted_root(root).join(candidate_filename())
}

fn reject_existing_repository_symlinks(
    root: &Path,
    components: &[&str],
    label: &str,
) -> Result<(), PortError> {
    let mut current = root.to_path_buf();
    for component in components {
        current.push(component);
        match fs::symlink_metadata(&current) {
            Ok(metadata) if metadata.file_type().is_symlink() => {
                return Err(PortError::new(format!("refusing symlink for {label}")));
            }
            Ok(_) => {}
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => break,
            Err(error) => return Err(io_error(error)),
        }
    }
    Ok(())
}

fn require_repository_directories(
    root: &Path,
    components: &[&str],
    label: &str,
) -> Result<PathBuf, PortError> {
    let mut current = root.to_path_buf();
    for component in components {
        current.push(component);
        let metadata = fs::symlink_metadata(&current).map_err(io_error)?;
        if metadata.file_type().is_symlink() || !metadata.is_dir() {
            return Err(PortError::new(format!(
                "{label} must use repository directories without symlinks"
            )));
        }
    }
    Ok(current)
}

fn require_regular_repository_file(
    root: &Path,
    components: &[&str],
    label: &str,
) -> Result<PathBuf, PortError> {
    let (file, directories) = components
        .split_last()
        .ok_or_else(|| PortError::new(format!("missing path for {label}")))?;
    let parent = require_repository_directories(root, directories, label)?;
    let path = parent.join(file);
    let metadata = fs::symlink_metadata(&path).map_err(|error| {
        PortError::new(format!(
            "{label} is unavailable at {}: {error}",
            path.display()
        ))
    })?;
    if metadata.file_type().is_symlink() || !metadata.is_file() {
        return Err(PortError::new(format!(
            "{label} must be a regular file without symlinks"
        )));
    }
    Ok(path)
}

#[cfg(unix)]
fn make_executable(path: &Path) -> Result<(), PortError> {
    use std::os::unix::fs::PermissionsExt;
    let mut permissions = fs::metadata(path).map_err(io_error)?.permissions();
    permissions.set_mode(0o755);
    fs::set_permissions(path, permissions).map_err(io_error)
}

#[cfg(not(unix))]
fn make_executable(_path: &Path) -> Result<(), PortError> {
    Ok(())
}

fn io_error(error: std::io::Error) -> PortError {
    PortError::new(error.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_a_candidate_that_does_not_match_its_release_checksum() {
        let release = tempfile::tempdir().unwrap();
        let version = env!("CARGO_PKG_VERSION");
        let tag_root = release.path().join(format!("harness-v{version}"));
        fs::create_dir_all(&tag_root).unwrap();
        fs::write(
            release.path().join("harness-release-tag"),
            format!("harness-v{version}\n"),
        )
        .unwrap();
        let artifact = candidate_artifact().unwrap();
        fs::write(tag_root.join(artifact), b"candidate").unwrap();
        fs::write(
            tag_root.join(format!("{artifact}.sha256")),
            format!("{}\n", "0".repeat(64)),
        )
        .unwrap();
        let candidates = LatestReleaseCandidates::for_test(release.path());
        let error = candidates.latest().err().unwrap();
        assert!(error.to_string().contains("checksum mismatch"));
    }

    #[cfg(unix)]
    #[test]
    fn repository_executable_must_not_be_a_symlink() {
        use std::os::unix::fs::symlink;

        let root = tempfile::tempdir().unwrap();
        let outside = tempfile::NamedTempFile::new().unwrap();
        fs::create_dir_all(root.path().join("scripts/bin")).unwrap();
        symlink(outside.path(), root.path().join("scripts/bin/harness")).unwrap();

        let error = require_regular_repository_file(
            root.path(),
            &["scripts", "bin", "harness"],
            "installed repository executable",
        )
        .unwrap_err();
        assert!(error.to_string().contains("regular file without symlinks"));
    }

    #[cfg(unix)]
    #[test]
    fn retained_candidate_write_does_not_follow_a_symlink() {
        use std::os::unix::fs::symlink;

        let root = tempfile::tempdir().unwrap();
        let candidate_root = tempfile::tempdir().unwrap();
        let candidate_path = candidate_root.path().join("candidate");
        fs::write(&candidate_path, b"verified candidate").unwrap();
        let outside = tempfile::NamedTempFile::new().unwrap();
        fs::write(outside.path(), b"outside binary").unwrap();
        fs::create_dir_all(root.path().join(".harness-core/update-candidate")).unwrap();
        symlink(
            outside.path(),
            root.path().join(".harness-core/update-candidate/harness"),
        )
        .unwrap();
        let candidate = VerifiedCandidate {
            _temp: candidate_root,
            path: candidate_path,
            release_version: env!("CARGO_PKG_VERSION").to_owned(),
        };

        let error = LatestReleaseCandidates::default()
            .persist(root.path(), &candidate)
            .unwrap_err();
        assert!(error.to_string().contains("refusing symlink"));
        assert_eq!(fs::read(outside.path()).unwrap(), b"outside binary");
    }
}
