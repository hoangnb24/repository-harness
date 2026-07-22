use std::fs;

use harness::application::{
    CoreApplication, CoreDistributionPort, InstallationStatePort, PortError,
};
use harness::domain::{
    ContentHash, CoreDistribution, DistributionFile, InstallationCondition, RelativePath,
};
use harness::infrastructure::{FileSystemInstallationState, GitThreeWayMerge};
use sha2::{Digest, Sha256};

#[derive(Clone)]
struct DistributionFixture(CoreDistribution);

impl CoreDistributionPort for DistributionFixture {
    fn current(&self) -> Result<CoreDistribution, PortError> {
        Ok(self.0.clone())
    }
}

#[test]
fn update_merges_non_overlapping_changes_and_stops_on_policy_overlap() {
    let root = tempfile::tempdir().unwrap();
    let path = root.path().join("docs/WORKFLOW.md");
    let version_one = application("1.0.0", b"one\ntwo\nthree\n");
    version_one.install(root.path(), false).unwrap();

    fs::write(&path, b"ONE\ntwo\nthree\n").unwrap();
    let version_two = application("2.0.0", b"one\ntwo\nTHREE\n");
    let preview = version_two.update(root.path(), true).unwrap();
    assert!(!preview.applied);
    assert!(preview.conflicts.is_empty());
    assert_eq!(fs::read(&path).unwrap(), b"ONE\ntwo\nthree\n");

    let applied = version_two.update(root.path(), false).unwrap();
    assert!(applied.applied);
    assert!(applied.conflicts.is_empty());
    assert_eq!(fs::read(&path).unwrap(), b"ONE\ntwo\nTHREE\n");
    assert!(root
        .path()
        .join(applied.backup_path.unwrap())
        .join("files/docs/WORKFLOW.md")
        .is_file());

    let manifest_before = fs::read(root.path().join(".harness-core/manifest.json")).unwrap();
    let base_before = fs::read(root.path().join(".harness-core/base/docs/WORKFLOW.md")).unwrap();
    let local_before = fs::read(&path).unwrap();
    let version_three = application("3.0.0", b"UPSTREAM\ntwo\nTHREE\n");
    let conflict = version_three.update(root.path(), false).unwrap();
    assert!(!conflict.applied);
    assert_eq!(conflict.conflicts.len(), 1);
    assert_eq!(fs::read(&path).unwrap(), local_before);
    assert_eq!(
        fs::read(root.path().join(".harness-core/manifest.json")).unwrap(),
        manifest_before
    );
    assert_eq!(
        fs::read(root.path().join(".harness-core/base/docs/WORKFLOW.md")).unwrap(),
        base_before
    );
}

#[test]
fn update_handles_one_sided_add_remove_and_missing_file_rules_atomically() {
    let root = tempfile::tempdir().unwrap();
    let version_one = application_with_files(
        "1.0.0",
        &[
            ("docs/local.md", b"base local\n"),
            ("docs/upstream.md", b"base upstream\n"),
            ("docs/removed.md", b"remove me\n"),
        ],
    );
    version_one.install(root.path(), false).unwrap();
    fs::write(root.path().join("docs/local.md"), b"consumer local\n").unwrap();

    let version_two = application_with_files(
        "2.0.0",
        &[
            ("docs/local.md", b"base local\n"),
            ("docs/upstream.md", b"upstream changed\n"),
            ("docs/added.md", b"new upstream\n"),
        ],
    );
    let report = version_two.update(root.path(), false).unwrap();
    assert!(report.applied);
    assert_eq!(
        fs::read(root.path().join("docs/local.md")).unwrap(),
        b"consumer local\n"
    );
    assert_eq!(
        fs::read(root.path().join("docs/upstream.md")).unwrap(),
        b"upstream changed\n"
    );
    assert_eq!(
        fs::read(root.path().join("docs/added.md")).unwrap(),
        b"new upstream\n"
    );
    assert!(!root.path().join("docs/removed.md").exists());

    fs::remove_file(root.path().join("docs/upstream.md")).unwrap();
    let before = fs::read(root.path().join("docs/local.md")).unwrap();
    let version_three = application_with_files(
        "3.0.0",
        &[
            ("docs/local.md", b"would change\n"),
            ("docs/upstream.md", b"upstream changed again\n"),
            ("docs/added.md", b"new upstream\n"),
        ],
    );
    let conflict = version_three.update(root.path(), false).unwrap();
    assert!(!conflict.applied);
    assert!(conflict
        .conflicts
        .iter()
        .any(|value| value.path.as_str() == "docs/upstream.md"));
    assert_eq!(fs::read(root.path().join("docs/local.md")).unwrap(), before);
}

#[test]
fn overlapping_update_stages_agent_resolution_and_continues_atomically() {
    let root = tempfile::tempdir().unwrap();
    let path = root.path().join("docs/WORKFLOW.md");
    let version_one = application("1.0.0", b"rule: base\n");
    version_one.install(root.path(), false).unwrap();
    fs::write(&path, b"rule: local policy\n").unwrap();

    let version_two = application("2.0.0", b"rule: upstream policy\n");
    let stopped = version_two.update(root.path(), false).unwrap();
    assert!(!stopped.applied);
    assert!(stopped.resolution_staged);
    assert_eq!(fs::read(&path).unwrap(), b"rule: local policy\n");

    let resolution = root
        .path()
        .join(".harness-core/update/resolved/docs/WORKFLOW.md");
    let staged = fs::read_to_string(&resolution).unwrap();
    assert!(staged.contains("<<<<<<< LOCAL"));
    assert!(staged.contains("||||||| BASE"));
    assert!(staged.contains(">>>>>>> UPSTREAM"));

    let unresolved = version_two.continue_update(root.path(), false).unwrap_err();
    assert!(unresolved.to_string().contains("conflict markers"));
    fs::write(&resolution, b"rule: accepted combined policy\n").unwrap();

    let preview = version_two.continue_update(root.path(), true).unwrap();
    assert!(!preview.applied);
    assert_eq!(fs::read(&path).unwrap(), b"rule: local policy\n");

    let applied = version_two.continue_update(root.path(), false).unwrap();
    assert!(applied.applied);
    assert_eq!(
        fs::read(&path).unwrap(),
        b"rule: accepted combined policy\n"
    );
    assert!(!root.path().join(".harness-core/update").exists());
    assert_eq!(
        FileSystemInstallationState
            .load(root.path())
            .unwrap()
            .unwrap()
            .core_version,
        "2.0.0"
    );
    assert_eq!(
        application("1.0.0", b"older\n")
            .status(root.path())
            .unwrap()
            .condition,
        InstallationCondition::ExecutableOutdated
    );
}

#[test]
fn normal_update_replaces_a_pending_plan_with_the_newer_candidate() {
    let root = tempfile::tempdir().unwrap();
    let path = root.path().join("docs/WORKFLOW.md");
    application("0.1.4", b"rule: base\n")
        .install(root.path(), false)
        .unwrap();
    fs::write(&path, b"rule: local policy\n").unwrap();

    let version_018 = application("0.1.8", b"rule: 0.1.8 policy\n");
    let first = version_018.update(root.path(), false).unwrap();
    assert!(first.resolution_staged);
    fs::write(
        root.path()
            .join(".harness-core/update/resolved/docs/WORKFLOW.md"),
        b"resolution prepared for 0.1.8\n",
    )
    .unwrap();

    let version_020 = application("0.2.0", b"rule: 0.2.0 policy\n");
    let preview = version_020.update(root.path(), true).unwrap();
    assert!(!preview.resolution_staged);
    let retained_session = FileSystemInstallationState
        .load_resolution(root.path())
        .unwrap()
        .unwrap();
    assert_eq!(retained_session.to_version, "0.1.8");
    assert_eq!(
        fs::read(
            root.path()
                .join(".harness-core/update/resolved/docs/WORKFLOW.md")
        )
        .unwrap(),
        b"resolution prepared for 0.1.8\n"
    );

    let restarted = version_020.update(root.path(), false).unwrap();
    assert!(restarted.resolution_staged);
    let session = FileSystemInstallationState
        .load_resolution(root.path())
        .unwrap()
        .unwrap();
    assert_eq!(session.from_version, "0.1.4");
    assert_eq!(session.to_version, "0.2.0");
    let fresh_resolution = fs::read_to_string(
        root.path()
            .join(".harness-core/update/resolved/docs/WORKFLOW.md"),
    )
    .unwrap();
    assert!(fresh_resolution.contains("0.2.0 policy"));
    assert!(!fresh_resolution.contains("resolution prepared for 0.1.8"));
    assert_eq!(fs::read(&path).unwrap(), b"rule: local policy\n");
}

#[test]
fn resolution_rejects_workspace_drift_and_can_be_aborted_without_file_changes() {
    let root = tempfile::tempdir().unwrap();
    let path = root.path().join("docs/WORKFLOW.md");
    application("1.0.0", b"base\n")
        .install(root.path(), false)
        .unwrap();
    fs::write(&path, b"local\n").unwrap();
    let candidate = application("2.0.0", b"incoming\n");
    candidate.update(root.path(), false).unwrap();
    fs::write(&path, b"changed after staging\n").unwrap();

    let error = candidate.continue_update(root.path(), false).unwrap_err();
    assert!(error
        .to_string()
        .contains("changed after conflict detection"));
    assert!(candidate.abort_update(root.path()).unwrap());
    assert_eq!(fs::read(&path).unwrap(), b"changed after staging\n");
    assert!(!root.path().join(".harness-core/update").exists());
}

#[test]
fn resolution_rejects_drift_in_a_file_that_was_clean_when_staged() {
    let root = tempfile::tempdir().unwrap();
    let version_one = application_with_files(
        "1.0.0",
        &[
            ("docs/conflict.md", b"base conflict\n"),
            ("docs/clean.md", b"base clean\n"),
        ],
    );
    version_one.install(root.path(), false).unwrap();
    fs::write(root.path().join("docs/conflict.md"), b"local conflict\n").unwrap();

    let version_two = application_with_files(
        "2.0.0",
        &[
            ("docs/conflict.md", b"incoming conflict\n"),
            ("docs/clean.md", b"incoming clean\n"),
        ],
    );
    let stopped = version_two.update(root.path(), false).unwrap();
    assert!(stopped.resolution_staged);
    fs::write(
        root.path()
            .join(".harness-core/update/resolved/docs/conflict.md"),
        b"human-approved conflict\n",
    )
    .unwrap();
    fs::write(root.path().join("docs/clean.md"), b"changed after review\n").unwrap();

    let error = version_two.continue_update(root.path(), false).unwrap_err();
    assert!(error.to_string().contains("docs/clean.md"));
    assert_eq!(
        fs::read(root.path().join("docs/clean.md")).unwrap(),
        b"changed after review\n"
    );
    assert!(root
        .path()
        .join(".harness-core/update/session.json")
        .is_file());
}

#[test]
fn candidate_mode_cannot_downgrade_installed_core_state() {
    let root = tempfile::tempdir().unwrap();
    application("2.0.0", b"newer\n")
        .install(root.path(), false)
        .unwrap();

    let error = application("1.0.0", b"older\n")
        .update(root.path(), false)
        .unwrap_err();

    assert!(error.to_string().contains("refusing to downgrade"));
    assert_eq!(
        FileSystemInstallationState
            .load(root.path())
            .unwrap()
            .unwrap()
            .core_version,
        "2.0.0"
    );
}

#[test]
fn existing_state_gitignore_is_augmented_without_losing_custom_rules() {
    let root = tempfile::tempdir().unwrap();
    fs::create_dir_all(root.path().join(".harness-core")).unwrap();
    fs::write(
        root.path().join(".harness-core/.gitignore"),
        "/custom-local-state/\n",
    )
    .unwrap();

    application("1.0.0", b"base\n")
        .install(root.path(), false)
        .unwrap();

    let ignore = fs::read_to_string(root.path().join(".harness-core/.gitignore")).unwrap();
    assert!(ignore.contains("/custom-local-state/"));
    assert!(ignore.contains("/update/"));
    assert!(ignore.contains("/update-candidate/"));
}

fn application(
    version: &str,
    content: &[u8],
) -> CoreApplication<DistributionFixture, FileSystemInstallationState, GitThreeWayMerge> {
    application_with_files(version, &[("docs/WORKFLOW.md", content)])
}

fn application_with_files(
    version: &str,
    files: &[(&str, &[u8])],
) -> CoreApplication<DistributionFixture, FileSystemInstallationState, GitThreeWayMerge> {
    CoreApplication::new(
        DistributionFixture(CoreDistribution {
            version: version.to_owned(),
            files: files
                .iter()
                .map(|(path, content)| DistributionFile {
                    path: RelativePath::parse(*path).unwrap(),
                    content: content.to_vec(),
                    hash: ContentHash::parse(format!("{:x}", Sha256::digest(content))).unwrap(),
                })
                .collect(),
        }),
        FileSystemInstallationState,
        GitThreeWayMerge,
    )
}
