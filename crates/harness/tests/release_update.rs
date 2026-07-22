use std::fs;
use std::process::Command;

use harness::application::InstallationStatePort;
use harness::domain::{
    BaselineFile, ContentHash, InstallationState, RelativePath, WorkspaceMutation,
};
use harness::infrastructure::FileSystemInstallationState;
use sha2::{Digest, Sha256};

#[test]
fn latest_release_handoff_retains_candidate_across_agent_resolved_conflict() {
    let release = tempfile::tempdir().unwrap();
    let workspace = tempfile::tempdir().unwrap();
    let binary = env!("CARGO_BIN_EXE_harness");
    let artifact = platform_artifact();
    let version = env!("CARGO_PKG_VERSION");
    let tag_root = release.path().join(format!("harness-v{version}"));
    fs::create_dir_all(&tag_root).unwrap();
    fs::write(
        release.path().join("harness-release-tag"),
        format!("harness-v{version}\n"),
    )
    .unwrap();
    let release_binary = tag_root.join(artifact);
    fs::copy(binary, &release_binary).unwrap();
    let digest = format!("{:x}", Sha256::digest(fs::read(&release_binary).unwrap()));
    fs::write(
        tag_root.join(format!("{artifact}.sha256")),
        format!("{digest}  {artifact}\n"),
    )
    .unwrap();

    let path = RelativePath::parse("AGENTS.md").unwrap();
    let base = b"base authority\n";
    let state = InstallationState {
        schema_version: InstallationState::SCHEMA_VERSION,
        core_version: "0.1.3".to_owned(),
        files: vec![BaselineFile {
            path: path.clone(),
            content: base.to_vec(),
            hash: ContentHash::parse(format!("{:x}", Sha256::digest(base))).unwrap(),
        }],
    };
    FileSystemInstallationState
        .apply(
            workspace.path(),
            &state,
            &[WorkspaceMutation::Write {
                path: path.clone(),
                content: b"local authority\n".to_vec(),
            }],
        )
        .unwrap();

    let stopped = run_update(binary, release.path(), workspace.path(), &["--json"]);
    assert_eq!(stopped.status.code(), Some(2));
    let stopped_json: serde_json::Value = serde_json::from_slice(&stopped.stdout).unwrap();
    assert_eq!(stopped_json["resolution_staged"], true);
    assert_eq!(
        fs::read(workspace.path().join("AGENTS.md")).unwrap(),
        b"local authority\n"
    );
    assert!(workspace
        .path()
        .join(".harness-core/update-candidate")
        .join(if cfg!(windows) {
            "harness.exe"
        } else {
            "harness"
        })
        .is_file());

    fs::write(
        workspace
            .path()
            .join(".harness-core/update/resolved/AGENTS.md"),
        b"human-approved combined authority\n",
    )
    .unwrap();
    let retained_candidate = workspace
        .path()
        .join(".harness-core/update-candidate")
        .join(if cfg!(windows) {
            "harness.exe"
        } else {
            "harness"
        });
    fs::write(&retained_candidate, b"tampered candidate").unwrap();
    let tampered = run_update(
        binary,
        release.path(),
        workspace.path(),
        &["--continue", "--json"],
    );
    assert!(!tampered.status.success());
    assert!(String::from_utf8_lossy(&tampered.stderr).contains("checksum mismatch"));
    assert_eq!(
        fs::read(workspace.path().join("AGENTS.md")).unwrap(),
        b"local authority\n"
    );
    fs::copy(&release_binary, &retained_candidate).unwrap();
    let continued = run_update(
        binary,
        release.path(),
        workspace.path(),
        &["--continue", "--json"],
    );
    assert!(
        continued.status.success(),
        "{}",
        String::from_utf8_lossy(&continued.stderr)
    );
    let continued_json: serde_json::Value = serde_json::from_slice(&continued.stdout).unwrap();
    assert_eq!(continued_json["applied"], true);
    assert_eq!(continued_json["resolution_staged"], false);
    assert_eq!(
        fs::read(workspace.path().join("AGENTS.md")).unwrap(),
        b"human-approved combined authority\n"
    );
    assert!(!workspace.path().join(".harness-core/update").exists());
}

#[test]
fn release_pointer_version_must_match_candidate_reported_version() {
    let release = tempfile::tempdir().unwrap();
    let workspace = tempfile::tempdir().unwrap();
    let binary = env!("CARGO_BIN_EXE_harness");
    let artifact = platform_artifact();
    let candidate_version = next_patch_version();
    let tag_root = release.path().join(format!("harness-v{candidate_version}"));
    fs::create_dir_all(&tag_root).unwrap();
    fs::write(
        release.path().join("harness-release-tag"),
        format!("harness-v{candidate_version}\n"),
    )
    .unwrap();
    let release_binary = tag_root.join(artifact);
    fs::copy(binary, &release_binary).unwrap();
    let digest = format!("{:x}", Sha256::digest(fs::read(&release_binary).unwrap()));
    fs::write(
        tag_root.join(format!("{artifact}.sha256")),
        format!("{digest}  {artifact}\n"),
    )
    .unwrap();

    let path = RelativePath::parse("AGENTS.md").unwrap();
    let base = b"base authority\n";
    FileSystemInstallationState
        .apply(
            workspace.path(),
            &InstallationState {
                schema_version: InstallationState::SCHEMA_VERSION,
                core_version: "0.1.3".to_owned(),
                files: vec![BaselineFile {
                    path: path.clone(),
                    content: base.to_vec(),
                    hash: ContentHash::parse(format!("{:x}", Sha256::digest(base))).unwrap(),
                }],
            },
            &[WorkspaceMutation::Write {
                path,
                content: base.to_vec(),
            }],
        )
        .unwrap();

    let output = run_update(binary, release.path(), workspace.path(), &[]);
    assert!(!output.status.success());
    assert!(String::from_utf8_lossy(&output.stderr).contains("release identity mismatch"));
    assert_eq!(
        FileSystemInstallationState
            .load(workspace.path())
            .unwrap()
            .unwrap()
            .core_version,
        "0.1.3"
    );
}

#[cfg(unix)]
#[test]
fn update_refuses_to_replace_an_executable_outside_the_selected_repository() {
    use std::os::unix::fs::PermissionsExt;

    let release = tempfile::tempdir().unwrap();
    let workspace = tempfile::tempdir().unwrap();
    let artifact = platform_artifact();
    let candidate_version = next_patch_version();
    let tag_root = release.path().join(format!("harness-v{candidate_version}"));
    fs::create_dir_all(&tag_root).unwrap();
    fs::write(
        release.path().join("harness-release-tag"),
        format!("harness-v{candidate_version}\n"),
    )
    .unwrap();
    let release_binary = tag_root.join(artifact);
    fs::write(
        &release_binary,
        format!(
            "#!/bin/sh\nif [ \"$1\" = \"--version\" ]; then echo 'harness {candidate_version}'; exit 0; fi\nexit 99\n"
        ),
    )
    .unwrap();
    fs::set_permissions(&release_binary, fs::Permissions::from_mode(0o755)).unwrap();
    let digest = format!("{:x}", Sha256::digest(fs::read(&release_binary).unwrap()));
    fs::write(
        tag_root.join(format!("{artifact}.sha256")),
        format!("{digest}  {artifact}\n"),
    )
    .unwrap();

    let path = RelativePath::parse("AGENTS.md").unwrap();
    let base = b"base authority\n";
    FileSystemInstallationState
        .apply(
            workspace.path(),
            &InstallationState {
                schema_version: InstallationState::SCHEMA_VERSION,
                core_version: "0.1.3".to_owned(),
                files: vec![BaselineFile {
                    path: path.clone(),
                    content: base.to_vec(),
                    hash: ContentHash::parse(format!("{:x}", Sha256::digest(base))).unwrap(),
                }],
            },
            &[WorkspaceMutation::Write {
                path,
                content: base.to_vec(),
            }],
        )
        .unwrap();
    fs::create_dir_all(workspace.path().join("scripts/bin")).unwrap();
    fs::copy(
        env!("CARGO_BIN_EXE_harness"),
        workspace.path().join("scripts/bin/harness"),
    )
    .unwrap();

    let output = Command::new(env!("CARGO_BIN_EXE_harness"))
        .args(["update", "--directory"])
        .arg(workspace.path())
        .env(
            "HARNESS_TEST_RELEASE_ROOT",
            format!("file://{}", release.path().display()),
        )
        .output()
        .unwrap();
    assert!(!output.status.success());
    assert!(
        String::from_utf8_lossy(&output.stderr).contains("invoke the repository-local executable"),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert_eq!(fs::read(workspace.path().join("AGENTS.md")).unwrap(), base);
}

#[cfg(unix)]
#[test]
fn update_recovers_an_outdated_executable_before_starting_another_core_update() {
    use std::os::unix::fs::PermissionsExt;

    let release = tempfile::tempdir().unwrap();
    let workspace = tempfile::tempdir().unwrap();
    let artifact = platform_artifact();
    let candidate_version = next_patch_version();
    let tag_root = release.path().join(format!("harness-v{candidate_version}"));
    fs::create_dir_all(&tag_root).unwrap();
    fs::write(
        release.path().join("harness-release-tag"),
        format!("harness-v{candidate_version}\n"),
    )
    .unwrap();
    let release_binary = tag_root.join(artifact);
    fs::write(
        &release_binary,
        format!(
            "#!/bin/sh\nif [ \"$1\" = \"--version\" ]; then echo 'harness {candidate_version}'; exit 0; fi\nexit 99\n"
        ),
    )
    .unwrap();
    fs::set_permissions(&release_binary, fs::Permissions::from_mode(0o755)).unwrap();
    let digest = format!("{:x}", Sha256::digest(fs::read(&release_binary).unwrap()));
    fs::write(
        tag_root.join(format!("{artifact}.sha256")),
        format!("{digest}  {artifact}\n"),
    )
    .unwrap();

    let path = RelativePath::parse("AGENTS.md").unwrap();
    let base = b"already updated\n";
    FileSystemInstallationState
        .apply(
            workspace.path(),
            &InstallationState {
                schema_version: InstallationState::SCHEMA_VERSION,
                core_version: candidate_version.to_string(),
                files: vec![BaselineFile {
                    path: path.clone(),
                    content: base.to_vec(),
                    hash: ContentHash::parse(format!("{:x}", Sha256::digest(base))).unwrap(),
                }],
            },
            &[WorkspaceMutation::Write {
                path,
                content: base.to_vec(),
            }],
        )
        .unwrap();
    let retained = workspace
        .path()
        .join(".harness-core/update-candidate/harness");
    fs::create_dir_all(retained.parent().unwrap()).unwrap();
    fs::copy(&release_binary, &retained).unwrap();

    let preview = run_update(
        env!("CARGO_BIN_EXE_harness"),
        release.path(),
        workspace.path(),
        &["--dry-run", "--json"],
    );
    assert!(preview.status.success());
    let preview_json: serde_json::Value = serde_json::from_slice(&preview.stdout).unwrap();
    assert_eq!(preview_json["operation"], "executable_recovery");
    assert_eq!(preview_json["dry_run"], true);
    assert_eq!(preview_json["applied"], false);
    assert!(workspace
        .path()
        .join(".harness-core/update-candidate")
        .exists());

    let output = run_update(
        env!("CARGO_BIN_EXE_harness"),
        release.path(),
        workspace.path(),
        &[],
    );
    assert!(output.status.success());
    assert!(String::from_utf8_lossy(&output.stdout).contains("Recovered Harness executable"));
    assert_eq!(fs::read(workspace.path().join("AGENTS.md")).unwrap(), base);
    assert!(!workspace
        .path()
        .join(".harness-core/update-candidate")
        .exists());
}

#[cfg(unix)]
#[test]
fn clean_update_replaces_the_selected_repository_executable() {
    use std::os::unix::fs::PermissionsExt;

    let release = tempfile::tempdir().unwrap();
    let workspace = tempfile::tempdir().unwrap();
    let artifact = platform_artifact();
    let candidate_version = next_patch_version();
    let tag_root = release.path().join(format!("harness-v{candidate_version}"));
    fs::create_dir_all(&tag_root).unwrap();
    fs::write(
        release.path().join("harness-release-tag"),
        format!("harness-v{candidate_version}\n"),
    )
    .unwrap();
    let release_binary = tag_root.join(artifact);
    fs::write(
        &release_binary,
        format!(
            "#!/bin/sh\nif [ \"$1\" = \"--version\" ]; then echo 'harness {candidate_version}'; fi\nexit 0\n"
        ),
    )
    .unwrap();
    fs::set_permissions(&release_binary, fs::Permissions::from_mode(0o755)).unwrap();
    let digest = format!("{:x}", Sha256::digest(fs::read(&release_binary).unwrap()));
    fs::write(
        tag_root.join(format!("{artifact}.sha256")),
        format!("{digest}  {artifact}\n"),
    )
    .unwrap();

    let path = RelativePath::parse("AGENTS.md").unwrap();
    let base = b"installed authority\n";
    FileSystemInstallationState
        .apply(
            workspace.path(),
            &InstallationState {
                schema_version: InstallationState::SCHEMA_VERSION,
                core_version: "0.1.3".to_owned(),
                files: vec![BaselineFile {
                    path: path.clone(),
                    content: base.to_vec(),
                    hash: ContentHash::parse(format!("{:x}", Sha256::digest(base))).unwrap(),
                }],
            },
            &[WorkspaceMutation::Write {
                path,
                content: base.to_vec(),
            }],
        )
        .unwrap();
    let installed_binary = workspace.path().join("scripts/bin/harness");
    fs::create_dir_all(installed_binary.parent().unwrap()).unwrap();
    fs::copy(env!("CARGO_BIN_EXE_harness"), &installed_binary).unwrap();

    let output = Command::new(&installed_binary)
        .args(["update", "--directory"])
        .arg(workspace.path())
        .env(
            "HARNESS_TEST_RELEASE_ROOT",
            format!("file://{}", release.path().display()),
        )
        .output()
        .unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let version = Command::new(&installed_binary)
        .arg("--version")
        .output()
        .unwrap();
    assert_eq!(
        String::from_utf8_lossy(&version.stdout).trim(),
        format!("harness {candidate_version}")
    );
    assert!(!workspace
        .path()
        .join(".harness-core/update-candidate")
        .exists());
}

fn run_update(
    binary: &str,
    release: &std::path::Path,
    workspace: &std::path::Path,
    additional: &[&str],
) -> std::process::Output {
    Command::new(binary)
        .arg("update")
        .arg("--directory")
        .arg(workspace)
        .args(additional)
        .env(
            "HARNESS_TEST_RELEASE_ROOT",
            format!("file://{}", release.display()),
        )
        .env("HARNESS_TEST_SKIP_SELF_REPLACE", "1")
        .output()
        .unwrap()
}

fn platform_artifact() -> &'static str {
    match (std::env::consts::OS, std::env::consts::ARCH) {
        ("macos", "aarch64") => "harness-macos-arm64",
        ("macos", "x86_64") => "harness-macos-x64",
        ("linux", "aarch64") => "harness-linux-arm64",
        ("linux", "x86_64") => "harness-linux-x64",
        ("windows", "x86_64") => "harness-windows-x64.exe",
        (os, arch) => panic!("unsupported test platform: {os}/{arch}"),
    }
}

fn next_patch_version() -> semver::Version {
    let current = semver::Version::parse(env!("CARGO_PKG_VERSION")).unwrap();
    semver::Version::new(current.major, current.minor, current.patch + 1)
}
