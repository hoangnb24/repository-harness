#![cfg(unix)]

use std::cell::Cell;
use std::collections::BTreeMap;
use std::os::unix::fs::MetadataExt;
use std::path::Path;

use harness_core::application::HarnessCore;
use harness_core::domain::{Command, Envelope, Mutation, MutatorOptions, Notice, ScaffoldOptions};
use harness_core::infrastructure::{JsonManifestPort, OsFileSystem};
use harness_core::ports::{
    PinnedRootKey, PortError, ReleaseFreshness, ReleaseMaterial, ReleasePort, ReleaseTrustInput,
    TrustPolicy, TrustPort, TrustedRootState,
};
use harness_core::recovery::OsMutationPort;
use sha2::{Digest, Sha256};

const INDEX: &[u8] =
    include_bytes!("../../../tests/fixtures/v1-phase1/positive/core-payload-index.json");
const SIGNATURES: &[u8] =
    include_bytes!("../../../tests/fixtures/v1-phase1/positive/core-payload-index.signatures.json");
const TRUST: &[u8] =
    include_bytes!("../../../tests/fixtures/v1-phase1/positive/core-trust-bundle.json");
const TRUST_SIGNATURES: &[u8] =
    include_bytes!("../../../tests/fixtures/v1-phase1/positive/core-trust-bundle.signatures.json");
const BOOTSTRAP_ANCHORS: &[u8] =
    include_bytes!("../../../tests/fixtures/v1-phase1/positive/test-bootstrap-anchors.json");
const LEDGER: &[u8] = include_bytes!("../../../release/contracts/v1/path-dispositions.json");
const DECISION: &[u8] = include_bytes!("../../../docs/templates/decision.md");
const STORY: &[u8] = include_bytes!("../../../docs/templates/story.md");

#[derive(Clone)]
struct SignedFixtureRelease;

impl ReleasePort for SignedFixtureRelease {
    fn load(&self) -> Result<ReleaseMaterial, PortError> {
        Ok(signed_release_material())
    }
}

impl TrustPort for SignedFixtureRelease {
    fn load(&self) -> Result<ReleaseTrustInput, PortError> {
        Ok(signed_release_trust())
    }
}

struct FailSecondReleaseAuthentication {
    release_loads: Cell<usize>,
}

impl FailSecondReleaseAuthentication {
    fn new() -> Self {
        Self {
            release_loads: Cell::new(0),
        }
    }
}

impl ReleasePort for FailSecondReleaseAuthentication {
    fn load(&self) -> Result<ReleaseMaterial, PortError> {
        let load = self.release_loads.get() + 1;
        self.release_loads.set(load);
        if load == 2 {
            return Err(PortError::ReleaseInvalid(
                "attack: authenticated release changed at commit boundary".into(),
            ));
        }
        Ok(signed_release_material())
    }
}

impl TrustPort for FailSecondReleaseAuthentication {
    fn load(&self) -> Result<ReleaseTrustInput, PortError> {
        Ok(signed_release_trust())
    }
}

fn signed_release_material() -> ReleaseMaterial {
    ReleaseMaterial {
        index: INDEX.to_vec(),
        signatures: SIGNATURES.to_vec(),
        trust_bundle: TRUST.to_vec(),
        trust_bundle_signatures: TRUST_SIGNATURES.to_vec(),
        path_ledger: LEDGER.to_vec(),
        source_files: BTreeMap::from([
            ("docs/templates/decision.md".into(), DECISION.to_vec()),
            ("docs/templates/story.md".into(), STORY.to_vec()),
        ]),
    }
}

fn signed_release_trust() -> ReleaseTrustInput {
    let anchors: serde_json::Value = serde_json::from_slice(BOOTSTRAP_ANCHORS).unwrap();
    let root = &anchors["core"];
    ReleaseTrustInput {
        trusted_root: TrustedRootState {
            trust_domain: root["trust_domain"].as_str().unwrap().into(),
            sequence: 1,
            bundle_sha256: root["exact_bundle_digest"].as_str().unwrap().into(),
            threshold: root["root_threshold"].as_u64().unwrap() as u8,
            keys: root["root_keys"]
                .as_array()
                .unwrap()
                .iter()
                .map(|key| PinnedRootKey {
                    key_id: key["key_id"].as_str().unwrap().into(),
                    public_key: decode_base64_32(key["public_key_base64"].as_str().unwrap()),
                    test_fixture: true,
                })
                .collect(),
            revoked_key_ids: Vec::new(),
        },
        trust_policy: TrustPolicy::TestFixtures,
        path_ledger_sha256: "e26476d03baf7b44a99fa3c6c9aab0dd5de107be6c3ed1f2c0c318591b919f5e"
            .into(),
        freshness: ReleaseFreshness::Existing {
            sequence: 42,
            digest: "dc70df55c0fbb3fcf548aa12cb13bcca0110e94a3b90300dfcc9522fd8de7bf7".into(),
            rollback: None,
        },
    }
}

fn decode_base64_32(value: &str) -> [u8; 32] {
    fn digit(byte: u8) -> u8 {
        match byte {
            b'A'..=b'Z' => byte - b'A',
            b'a'..=b'z' => byte - b'a' + 26,
            b'0'..=b'9' => byte - b'0' + 52,
            b'+' => 62,
            b'/' => 63,
            _ => 0,
        }
    }
    let mut output = Vec::new();
    for chunk in value.as_bytes().chunks_exact(4) {
        let bits = (u32::from(digit(chunk[0])) << 18)
            | (u32::from(digit(chunk[1])) << 12)
            | (u32::from(if chunk[2] == b'=' { 0 } else { digit(chunk[2]) }) << 6)
            | u32::from(if chunk[3] == b'=' { 0 } else { digit(chunk[3]) });
        output.push((bits >> 16) as u8);
        if chunk[2] != b'=' {
            output.push((bits >> 8) as u8);
        }
        if chunk[3] != b'=' {
            output.push(bits as u8);
        }
    }
    output.try_into().unwrap()
}

fn execute(root: &Path, command: Command, kill_after: Option<usize>) -> Envelope {
    let filesystem = OsFileSystem::new(root).unwrap();
    let mutations = match kill_after {
        Some(checkpoint) => OsMutationPort::with_kill_after_checkpoint(root, checkpoint).unwrap(),
        None => OsMutationPort::new(root).unwrap(),
    };
    let release = SignedFixtureRelease;
    HarnessCore::with_mutations(
        &filesystem,
        &JsonManifestPort,
        &release,
        &release,
        &mutations,
    )
    .execute(&command)
}

fn execute_with_release(
    root: &Path,
    command: Command,
    release: &dyn ReleasePort,
    trust: &dyn TrustPort,
) -> Envelope {
    let filesystem = OsFileSystem::new(root).unwrap();
    let mutations = OsMutationPort::new(root).unwrap();
    HarnessCore::with_mutations(&filesystem, &JsonManifestPort, release, trust, &mutations)
        .execute(&command)
}

fn preview(root: &Path, command: fn(MutatorOptions) -> Command) -> (String, String, Envelope) {
    let envelope = execute(
        root,
        command(MutatorOptions {
            preview: true,
            ..MutatorOptions::default()
        }),
        None,
    );
    assert!(matches!(envelope.exit_code, 0 | 2), "{envelope:?}");
    let preview = notice(&envelope.notices, "preview-sha256").message.clone();
    let operation = notice(&envelope.notices, "operation-id").message.clone();
    (preview, operation, envelope)
}

fn confirm(digest: String) -> MutatorOptions {
    MutatorOptions {
        non_interactive: true,
        accept_preview_sha256: Some(digest),
        ..MutatorOptions::default()
    }
}

fn notice<'a>(notices: &'a [Notice], code: &str) -> &'a Notice {
    notices
        .iter()
        .find(|notice| notice.code == code)
        .unwrap_or_else(|| panic!("missing notice {code}: {notices:?}"))
}

fn sha256(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

fn tree_snapshot(root: &Path) -> BTreeMap<String, Vec<u8>> {
    fn visit(root: &Path, current: &Path, output: &mut BTreeMap<String, Vec<u8>>) {
        let mut entries: Vec<_> = std::fs::read_dir(current)
            .unwrap()
            .map(|entry| entry.unwrap().path())
            .collect();
        entries.sort();
        for path in entries {
            if path.is_dir() {
                visit(root, &path, output);
            } else {
                output.insert(
                    path.strip_prefix(root)
                        .unwrap()
                        .to_string_lossy()
                        .into_owned(),
                    std::fs::read(path).unwrap(),
                );
            }
        }
    }
    let mut output = BTreeMap::new();
    visit(root, root, &mut output);
    output
}

fn prepare_managed_block_update(root: &Path) -> Vec<u8> {
    let digest = preview(root, Command::Install).0;
    assert!(matches!(
        execute(root, Command::Install(confirm(digest)), None).exit_code,
        0 | 2
    ));
    let prefix = b"human prefix\n<!-- repository-harness:v1:begin:decision -->";
    let old_interior = b"\nold managed interior\n";
    let suffix = b"<!-- repository-harness:v1:end:decision -->\nhuman suffix\n";
    let block = [
        prefix.as_slice(),
        old_interior.as_slice(),
        suffix.as_slice(),
    ]
    .concat();
    std::fs::write(root.join("docs/templates/decision.md"), &block).unwrap();
    let manifest_path = root.join(".harness/manifest.json");
    let mut manifest: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest_path).unwrap()).unwrap();
    let role = manifest["roles"]
        .as_array_mut()
        .unwrap()
        .iter_mut()
        .find(|role| role["path"] == "docs/templates/decision.md")
        .unwrap();
    role["ownership"] = serde_json::json!("managed-block");
    role["marker"] = serde_json::json!("decision");
    role["update_policy"] = serde_json::json!("three-way-review");
    role["base_sha256"] = serde_json::json!(sha256(old_interior));
    role["current_sha256"] = serde_json::json!(sha256(&block));
    std::fs::write(&manifest_path, serde_json::to_vec(&manifest).unwrap()).unwrap();
    [prefix.as_slice(), DECISION, suffix.as_slice()].concat()
}

#[test]
fn signed_install_requires_exact_confirmation_commits_manifest_last_and_is_idempotent() {
    let temporary = tempfile::tempdir().unwrap();
    let (digest, operation, first_preview) = preview(temporary.path(), Command::Install);
    let second_preview = preview(temporary.path(), Command::Install).2;
    assert_eq!(
        first_preview.details.operations,
        second_preview.details.operations
    );
    assert_eq!(
        notice(&first_preview.notices, "preview-sha256"),
        notice(&second_preview.notices, "preview-sha256")
    );
    assert!(!temporary.path().join(".harness").exists());

    let absent_confirmation = execute(
        temporary.path(),
        Command::Install(MutatorOptions::default()),
        None,
    );
    assert_eq!(absent_confirmation.exit_code, 4);
    assert!(!temporary.path().join(".harness").exists());
    let wrong_confirmation = execute(
        temporary.path(),
        Command::Install(confirm("0".repeat(64))),
        None,
    );
    assert_eq!(wrong_confirmation.exit_code, 4);
    assert!(!temporary.path().join(".harness").exists());

    let committed = execute(temporary.path(), Command::Install(confirm(digest)), None);
    assert!(matches!(committed.exit_code, 0 | 2), "{committed:?}");
    assert_eq!(committed.mutation, Mutation::Committed);
    assert_eq!(
        std::fs::read(temporary.path().join("docs/templates/decision.md")).unwrap(),
        DECISION
    );
    assert_eq!(
        std::fs::read(temporary.path().join("docs/templates/story.md")).unwrap(),
        STORY
    );
    assert!(temporary.path().join(".harness/manifest.json").is_file());
    assert!(temporary
        .path()
        .join(format!(".harness/recovery/{operation}/journal.json"))
        .is_file());

    let rerun = execute(
        temporary.path(),
        Command::Install(MutatorOptions::default()),
        None,
    );
    assert!(matches!(rerun.exit_code, 0 | 2), "{rerun:?}");
    assert_eq!(rerun.mutation, Mutation::None);
    assert_eq!(notice(&rerun.notices, "idempotent-noop").path, None);
}

#[test]
fn commit_and_resume_reauthenticate_release_identity_before_manifest_or_success() {
    let initial = tempfile::tempdir().unwrap();
    let (digest, operation, _) = preview(initial.path(), Command::Install);
    let changing_release = FailSecondReleaseAuthentication::new();
    let refused = execute_with_release(
        initial.path(),
        Command::Install(confirm(digest)),
        &changing_release,
        &changing_release,
    );
    assert_eq!(refused.exit_code, 4, "commit-boundary attack: {refused:?}");
    assert_eq!(refused.mutation, Mutation::RecoveryRequired);
    assert_eq!(
        std::fs::read(initial.path().join("docs/templates/decision.md")).unwrap(),
        DECISION,
        "authenticated target post-image survives"
    );
    assert_eq!(
        std::fs::read(initial.path().join("docs/templates/story.md")).unwrap(),
        STORY,
        "authenticated target post-image survives"
    );
    assert!(!initial.path().join(".harness/manifest.json").exists());
    assert!(initial
        .path()
        .join(format!(".harness/recovery/{operation}/journal.json"))
        .is_file());

    let resumed = tempfile::tempdir().unwrap();
    let (digest, operation, _) = preview(resumed.path(), Command::Install);
    let killed = execute(resumed.path(), Command::Install(confirm(digest)), Some(14));
    assert_eq!(
        killed.exit_code, 4,
        "kill after preview recheck: {killed:?}"
    );
    assert_eq!(killed.mutation, Mutation::RecoveryRequired);
    let before_resume = tree_snapshot(resumed.path());
    let changing_release = FailSecondReleaseAuthentication::new();
    let refused_resume = execute_with_release(
        resumed.path(),
        Command::Install(MutatorOptions {
            resume: Some(operation.clone()),
            ..MutatorOptions::default()
        }),
        &changing_release,
        &changing_release,
    );
    assert_eq!(
        refused_resume.exit_code, 4,
        "resume re-authentication attack: {refused_resume:?}"
    );
    assert_eq!(refused_resume.mutation, Mutation::RecoveryRequired);
    assert_eq!(tree_snapshot(resumed.path()), before_resume);
    assert!(!resumed.path().join(".harness/manifest.json").exists());
    assert!(resumed
        .path()
        .join(format!(".harness/recovery/{operation}/journal.json"))
        .is_file());
}

#[test]
fn scaffold_is_exact_and_update_preserves_target_owned_bytes() {
    let temporary = tempfile::tempdir().unwrap();
    let options = ScaffoldOptions {
        template: Some("decision-template".into()),
        destination: Some("docs/templates/decision.md".into()),
        mutation: MutatorOptions {
            preview: true,
            ..MutatorOptions::default()
        },
    };
    let scaffold_preview = execute(temporary.path(), Command::Scaffold(options), None);
    let digest = notice(&scaffold_preview.notices, "preview-sha256")
        .message
        .clone();
    let committed = execute(
        temporary.path(),
        Command::Scaffold(ScaffoldOptions {
            template: Some("decision-template".into()),
            destination: Some("docs/templates/decision.md".into()),
            mutation: confirm(digest),
        }),
        None,
    );
    assert!(matches!(committed.exit_code, 0 | 2), "{committed:?}");

    let repeated = execute(
        temporary.path(),
        Command::Scaffold(ScaffoldOptions {
            template: Some("decision-template".into()),
            destination: Some("docs/templates/decision.md".into()),
            mutation: MutatorOptions::default(),
        }),
        None,
    );
    assert!(matches!(repeated.exit_code, 0 | 2), "{repeated:?}");
    assert_eq!(repeated.mutation, Mutation::None);
    assert_eq!(notice(&repeated.notices, "idempotent-noop").path, None);

    let human = b"# Human-owned decision template\n";
    std::fs::write(temporary.path().join("docs/templates/decision.md"), human).unwrap();
    let manifest_path = temporary.path().join(".harness/manifest.json");
    let mut manifest: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest_path).unwrap()).unwrap();
    manifest["roles"][0]["current_sha256"] = serde_json::json!(sha256(human));
    std::fs::write(&manifest_path, serde_json::to_vec(&manifest).unwrap()).unwrap();

    let (digest, _, update_preview) = preview(temporary.path(), Command::Update);
    assert!(update_preview
        .notices
        .iter()
        .any(|notice| notice.code == "target-owned-preserved"));
    let updated = execute(temporary.path(), Command::Update(confirm(digest)), None);
    assert!(matches!(updated.exit_code, 0 | 2), "{updated:?}");
    assert_eq!(
        std::fs::read(temporary.path().join("docs/templates/decision.md")).unwrap(),
        human
    );
    assert_eq!(
        std::fs::read(temporary.path().join("docs/templates/story.md")).unwrap(),
        STORY
    );
}

#[test]
fn scaffold_kill_resume_is_one_destination_scoped_and_repeated_resume_is_idempotent() {
    let temporary = tempfile::tempdir().unwrap();
    std::fs::write(
        temporary.path().join("human-sentinel.txt"),
        b"target-owned\n",
    )
    .unwrap();
    let preview_options = ScaffoldOptions {
        template: Some("decision-template".into()),
        destination: Some("docs/templates/decision.md".into()),
        mutation: MutatorOptions {
            preview: true,
            ..MutatorOptions::default()
        },
    };
    let planned = execute(temporary.path(), Command::Scaffold(preview_options), None);
    let digest = notice(&planned.notices, "preview-sha256").message.clone();
    let operation = notice(&planned.notices, "operation-id").message.clone();
    let interrupted = execute(
        temporary.path(),
        Command::Scaffold(ScaffoldOptions {
            template: Some("decision-template".into()),
            destination: Some("docs/templates/decision.md".into()),
            mutation: confirm(digest),
        }),
        Some(7),
    );
    assert_eq!(
        interrupted.exit_code, 4,
        "scaffold target-journal kill: {interrupted:?}"
    );
    assert_eq!(interrupted.mutation, Mutation::RecoveryRequired);
    assert_eq!(
        std::fs::read(temporary.path().join("docs/templates/decision.md")).unwrap(),
        DECISION
    );
    assert!(!temporary.path().join("docs/templates/story.md").exists());
    assert!(!temporary.path().join(".harness/manifest.json").exists());
    assert_eq!(
        std::fs::read(temporary.path().join("human-sentinel.txt")).unwrap(),
        b"target-owned\n"
    );
    assert!(temporary
        .path()
        .join(format!(".harness/recovery/{operation}/journal.json"))
        .is_file());

    let recovery_command = || {
        Command::Scaffold(ScaffoldOptions {
            template: Some("decision-template".into()),
            destination: Some("docs/templates/decision.md".into()),
            mutation: MutatorOptions {
                resume: Some(operation.clone()),
                ..MutatorOptions::default()
            },
        })
    };
    let recovered = execute(temporary.path(), recovery_command(), None);
    assert!(matches!(recovered.exit_code, 0 | 2), "{recovered:?}");
    let manifest: serde_json::Value = serde_json::from_slice(
        &std::fs::read(temporary.path().join(".harness/manifest.json")).unwrap(),
    )
    .unwrap();
    assert_eq!(manifest["roles"].as_array().unwrap().len(), 1);
    assert_eq!(manifest["roles"][0]["path"], "docs/templates/decision.md");
    assert!(!temporary.path().join("docs/templates/story.md").exists());
    assert_eq!(
        std::fs::read(temporary.path().join("human-sentinel.txt")).unwrap(),
        b"target-owned\n"
    );
    let committed_snapshot = tree_snapshot(temporary.path());
    let repeated = execute(temporary.path(), recovery_command(), None);
    assert!(matches!(repeated.exit_code, 0 | 2), "{repeated:?}");
    assert_eq!(tree_snapshot(temporary.path()), committed_snapshot);
}

#[test]
fn identical_preexisting_asset_commits_brownfield_mode_and_target_ownership() {
    let temporary = tempfile::tempdir().unwrap();
    std::fs::create_dir_all(temporary.path().join("docs/templates")).unwrap();
    std::fs::write(
        temporary.path().join("docs/templates/decision.md"),
        DECISION,
    )
    .unwrap();
    let digest = preview(temporary.path(), Command::Install).0;
    let committed = execute(temporary.path(), Command::Install(confirm(digest)), None);
    assert!(matches!(committed.exit_code, 0 | 2), "{committed:?}");
    let manifest: serde_json::Value = serde_json::from_slice(
        &std::fs::read(temporary.path().join(".harness/manifest.json")).unwrap(),
    )
    .unwrap();
    assert_eq!(manifest["repository_mode"], "brownfield-v1");
    let role = manifest["roles"]
        .as_array()
        .unwrap()
        .iter()
        .find(|role| role["path"] == "docs/templates/decision.md")
        .unwrap();
    assert_eq!(role["origin"], "brownfield-mapped");
    assert_eq!(role["ownership"], "target-owned");
    assert_eq!(role["update_policy"], "never-auto-patch");
}

#[test]
fn converted_mode_and_receipt_survive_mapping_a_new_identical_authenticated_asset() {
    let temporary = tempfile::tempdir().unwrap();
    let digest = preview(temporary.path(), Command::Install).0;
    assert!(matches!(
        execute(temporary.path(), Command::Install(confirm(digest)), None).exit_code,
        0 | 2
    ));
    let manifest_path = temporary.path().join(".harness/manifest.json");
    let mut manifest: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest_path).unwrap()).unwrap();
    manifest["roles"]
        .as_array_mut()
        .unwrap()
        .retain(|role| role["path"] != "docs/templates/story.md");
    manifest["repository_mode"] = serde_json::json!("converted-v1-with-archive");
    let receipt = serde_json::json!({
        "schema": "repository-harness-conversion-receipt/v1",
        "conversion_id": "retained-conversion",
        "bridge_release": "1.0.0-test.1",
        "archive_path": ".harness/legacy/v0-conversion/retained-conversion/conversion.age",
        "export_sha256": "a".repeat(64),
        "standalone_backup_sha256": "b".repeat(64),
        "archive_sha256": "c".repeat(64),
        "confidentiality_mode": "encrypted-age-x25519",
        "recipient_fingerprints": ["age1retainedowner"]
    });
    manifest["conversion_receipt"] = receipt.clone();
    std::fs::write(&manifest_path, serde_json::to_vec(&manifest).unwrap()).unwrap();

    let digest = preview(temporary.path(), Command::Update).0;
    let updated = execute(temporary.path(), Command::Update(confirm(digest)), None);
    assert!(matches!(updated.exit_code, 0 | 2), "{updated:?}");
    let committed: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest_path).unwrap()).unwrap();
    assert_eq!(committed["repository_mode"], "converted-v1-with-archive");
    assert_eq!(committed["conversion_receipt"], receipt);
    let story = committed["roles"]
        .as_array()
        .unwrap()
        .iter()
        .find(|role| role["path"] == "docs/templates/story.md")
        .unwrap();
    assert_eq!(story["origin"], "brownfield-mapped");
    assert_eq!(story["ownership"], "target-owned");
    assert_eq!(story["update_policy"], "never-auto-patch");
}

#[test]
fn status_and_exact_rerun_report_recovery_without_replay_and_audit_is_read_only() {
    let temporary = tempfile::tempdir().unwrap();
    let (digest, operation, _) = preview(temporary.path(), Command::Install);
    let interrupted = execute(
        temporary.path(),
        Command::Install(confirm(digest.clone())),
        Some(8),
    );
    assert_eq!(interrupted.mutation, Mutation::RecoveryRequired);
    assert!(temporary
        .path()
        .join("docs/templates/decision.md")
        .is_file());
    assert!(!temporary.path().join(".harness/manifest.json").exists());
    let before = tree_snapshot(temporary.path());

    let status = execute(temporary.path(), Command::Status { json: true }, None);
    assert_eq!(status.exit_code, 3, "{status:?}");
    assert!([0, 3, 64, 70, 74].contains(&status.exit_code));
    assert_eq!(status.mutation, Mutation::RecoveryRequired);
    assert!(notice(&status.notices, "recovery-required")
        .message
        .contains(&operation));
    assert_eq!(tree_snapshot(temporary.path()), before);

    let audit = execute(temporary.path(), Command::Audit { json: true }, None);
    assert_eq!(audit.exit_code, 3);
    assert_eq!(audit.mutation, Mutation::None);
    assert_eq!(tree_snapshot(temporary.path()), before);

    let rerun = execute(temporary.path(), Command::Install(confirm(digest)), None);
    assert_eq!(rerun.exit_code, 4, "{rerun:?}");
    assert_eq!(rerun.mutation, Mutation::RecoveryRequired);
    assert!(rerun
        .notices
        .iter()
        .any(|notice| notice.code == "exact-rerun-recovery-required"));
    assert_eq!(tree_snapshot(temporary.path()), before);
}

#[test]
fn recovery_status_preserves_authoritative_manifest_mode_and_declared_readiness() {
    let temporary = tempfile::tempdir().unwrap();
    let digest = preview(temporary.path(), Command::Install).0;
    assert!(matches!(
        execute(temporary.path(), Command::Install(confirm(digest)), None).exit_code,
        0 | 2
    ));

    let prefix = b"human prefix\n<!-- repository-harness:v1:begin:decision -->";
    let old_interior = b"\nold managed interior\n";
    let suffix = b"<!-- repository-harness:v1:end:decision -->\nhuman suffix\n";
    let block = [
        prefix.as_slice(),
        old_interior.as_slice(),
        suffix.as_slice(),
    ]
    .concat();
    std::fs::write(temporary.path().join("docs/templates/decision.md"), &block).unwrap();
    let manifest_path = temporary.path().join(".harness/manifest.json");
    let mut manifest: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest_path).unwrap()).unwrap();
    let role = manifest["roles"]
        .as_array_mut()
        .unwrap()
        .iter_mut()
        .find(|role| role["path"] == "docs/templates/decision.md")
        .unwrap();
    role["ownership"] = serde_json::json!("managed-block");
    role["marker"] = serde_json::json!("decision");
    role["update_policy"] = serde_json::json!("three-way-review");
    role["base_sha256"] = serde_json::json!(sha256(old_interior));
    role["current_sha256"] = serde_json::json!(sha256(&block));
    std::fs::write(&manifest_path, serde_json::to_vec(&manifest).unwrap()).unwrap();
    let before = execute(temporary.path(), Command::Status { json: true }, None);
    assert_eq!(before.exit_code, 0);

    let (digest, _, _) = preview(temporary.path(), Command::Update);
    let interrupted = execute(temporary.path(), Command::Update(confirm(digest)), Some(9));
    assert_eq!(interrupted.mutation, Mutation::RecoveryRequired);
    let snapshot = tree_snapshot(temporary.path());
    let status = execute(temporary.path(), Command::Status { json: true }, None);
    assert_eq!(status.exit_code, 3);
    assert_eq!(status.mutation, Mutation::RecoveryRequired);
    assert_eq!(status.repository_mode, before.repository_mode);
    assert_eq!(status.details.readiness, before.details.readiness);
    assert_eq!(tree_snapshot(temporary.path()), snapshot);
}

#[test]
fn managed_file_drift_returns_exact_three_way_review_without_writing() {
    let temporary = tempfile::tempdir().unwrap();
    let digest = preview(temporary.path(), Command::Install).0;
    let installed = execute(temporary.path(), Command::Install(confirm(digest)), None);
    assert!(matches!(installed.exit_code, 0 | 2));

    let human = b"# Human edit to managed file\n";
    let decision_path = temporary.path().join("docs/templates/decision.md");
    std::fs::write(&decision_path, human).unwrap();
    let manifest_path = temporary.path().join(".harness/manifest.json");
    let mut manifest: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest_path).unwrap()).unwrap();
    let role = manifest["roles"]
        .as_array_mut()
        .unwrap()
        .iter_mut()
        .find(|role| role["path"] == "docs/templates/decision.md")
        .unwrap();
    role["current_sha256"] = serde_json::json!(sha256(human));
    let before_manifest = serde_json::to_vec(&manifest).unwrap();
    std::fs::write(&manifest_path, &before_manifest).unwrap();
    let before_tree = tree_snapshot(temporary.path());

    let result = execute(
        temporary.path(),
        Command::Update(MutatorOptions {
            preview: true,
            ..MutatorOptions::default()
        }),
        None,
    );
    assert_eq!(result.exit_code, 4);
    for code in [
        "three-way-base-sha256",
        "three-way-current-sha256",
        "three-way-candidate-sha256",
    ] {
        assert_eq!(
            notice(&result.notices, code).path.as_deref(),
            Some("docs/templates/decision.md")
        );
    }
    assert_eq!(std::fs::read(decision_path).unwrap(), human);
    assert_eq!(std::fs::read(manifest_path).unwrap(), before_manifest);
    assert_eq!(
        tree_snapshot(temporary.path()),
        before_tree,
        "replace-if-base drift creates no journal or private recovery bytes"
    );
}

#[test]
fn replace_if_base_equal_base_writes_authenticated_image_after_durable_backup() {
    let temporary = tempfile::tempdir().unwrap();
    let digest = preview(temporary.path(), Command::Install).0;
    assert!(matches!(
        execute(temporary.path(), Command::Install(confirm(digest)), None).exit_code,
        0 | 2
    ));

    let old = b"previous authenticated managed-file base\n";
    let decision_path = temporary.path().join("docs/templates/decision.md");
    std::fs::write(&decision_path, old).unwrap();
    let manifest_path = temporary.path().join(".harness/manifest.json");
    let mut manifest: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest_path).unwrap()).unwrap();
    let role = manifest["roles"]
        .as_array_mut()
        .unwrap()
        .iter_mut()
        .find(|role| role["path"] == "docs/templates/decision.md")
        .unwrap();
    role["base_sha256"] = serde_json::json!(sha256(old));
    role["current_sha256"] = serde_json::json!(sha256(old));
    std::fs::write(&manifest_path, serde_json::to_vec(&manifest).unwrap()).unwrap();

    let (digest, operation, _) = preview(temporary.path(), Command::Update);
    let updated = execute(temporary.path(), Command::Update(confirm(digest)), None);
    assert!(matches!(updated.exit_code, 0 | 2), "{updated:?}");
    assert_eq!(std::fs::read(&decision_path).unwrap(), DECISION);
    let journal: serde_json::Value = serde_json::from_slice(
        &std::fs::read(
            temporary
                .path()
                .join(format!(".harness/recovery/{operation}/journal.json")),
        )
        .unwrap(),
    )
    .unwrap();
    let step = journal["steps"]
        .as_array()
        .unwrap()
        .iter()
        .find(|step| step["path"] == "docs/templates/decision.md")
        .unwrap();
    let backup_path = step["backup_path"].as_str().unwrap();
    assert_eq!(
        std::fs::read(temporary.path().join(backup_path)).unwrap(),
        old,
        "before-image backup survives the destructive replacement"
    );
}

#[test]
fn managed_block_update_replaces_only_authenticated_interior() {
    let temporary = tempfile::tempdir().unwrap();
    let digest = preview(temporary.path(), Command::Install).0;
    assert!(matches!(
        execute(temporary.path(), Command::Install(confirm(digest)), None).exit_code,
        0 | 2
    ));

    let prefix = b"human prefix\n<!-- repository-harness:v1:begin:decision -->";
    let old_interior = b"\nold managed interior\n";
    let suffix = b"<!-- repository-harness:v1:end:decision -->\nhuman suffix\n";
    let block = [
        prefix.as_slice(),
        old_interior.as_slice(),
        suffix.as_slice(),
    ]
    .concat();
    let decision_path = temporary.path().join("docs/templates/decision.md");
    std::fs::write(&decision_path, &block).unwrap();
    let manifest_path = temporary.path().join(".harness/manifest.json");
    let mut manifest: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest_path).unwrap()).unwrap();
    let role = manifest["roles"]
        .as_array_mut()
        .unwrap()
        .iter_mut()
        .find(|role| role["path"] == "docs/templates/decision.md")
        .unwrap();
    role["ownership"] = serde_json::json!("managed-block");
    role["marker"] = serde_json::json!("decision");
    role["update_policy"] = serde_json::json!("three-way-review");
    role["base_sha256"] = serde_json::json!(sha256(old_interior));
    role["current_sha256"] = serde_json::json!(sha256(&block));
    std::fs::write(&manifest_path, serde_json::to_vec(&manifest).unwrap()).unwrap();

    let digest = preview(temporary.path(), Command::Update).0;
    let updated = execute(temporary.path(), Command::Update(confirm(digest)), None);
    assert!(matches!(updated.exit_code, 0 | 2), "{updated:?}");
    let expected = [prefix.as_slice(), DECISION, suffix.as_slice()].concat();
    assert_eq!(std::fs::read(decision_path).unwrap(), expected);
}

#[test]
fn three_way_review_managed_block_drift_refuses_without_journal_or_byte_change() {
    let temporary = tempfile::tempdir().unwrap();
    prepare_managed_block_update(temporary.path());
    let decision_path = temporary.path().join("docs/templates/decision.md");
    let manifest_path = temporary.path().join(".harness/manifest.json");
    let human_block = b"human prefix\n<!-- repository-harness:v1:begin:decision -->\nhuman changed managed interior\n<!-- repository-harness:v1:end:decision -->\nhuman suffix\n";
    std::fs::write(&decision_path, human_block).unwrap();
    let mut manifest: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest_path).unwrap()).unwrap();
    let role = manifest["roles"]
        .as_array_mut()
        .unwrap()
        .iter_mut()
        .find(|role| role["path"] == "docs/templates/decision.md")
        .unwrap();
    role["current_sha256"] = serde_json::json!(sha256(human_block));
    std::fs::write(&manifest_path, serde_json::to_vec(&manifest).unwrap()).unwrap();
    let before = tree_snapshot(temporary.path());

    let result = execute(
        temporary.path(),
        Command::Update(MutatorOptions {
            preview: true,
            ..MutatorOptions::default()
        }),
        None,
    );
    assert_eq!(
        result.exit_code, 4,
        "three-way managed-block drift: {result:?}"
    );
    for code in [
        "three-way-base-sha256",
        "three-way-current-sha256",
        "three-way-candidate-sha256",
    ] {
        assert_eq!(
            notice(&result.notices, code).path.as_deref(),
            Some("docs/templates/decision.md")
        );
    }
    assert_eq!(tree_snapshot(temporary.path()), before);
}

#[test]
fn mixed_invalid_and_payload_downgrade_refuse_before_new_journal_or_mutation() {
    let mixed = tempfile::tempdir().unwrap();
    let digest = preview(mixed.path(), Command::Install).0;
    assert!(matches!(
        execute(mixed.path(), Command::Install(confirm(digest)), None).exit_code,
        0 | 2
    ));
    std::fs::write(
        mixed.path().join("docs/templates/decision.md"),
        b"attack: undeclared drift\n",
    )
    .unwrap();
    let before_mixed = tree_snapshot(mixed.path());
    let refused_mixed = execute(
        mixed.path(),
        Command::Update(MutatorOptions::default()),
        None,
    );
    assert_eq!(
        refused_mixed.exit_code, 3,
        "mixed-invalid attack: {refused_mixed:?}"
    );
    assert_eq!(refused_mixed.mutation, Mutation::None);
    assert_eq!(tree_snapshot(mixed.path()), before_mixed);

    let downgrade = tempfile::tempdir().unwrap();
    let digest = preview(downgrade.path(), Command::Install).0;
    assert!(matches!(
        execute(downgrade.path(), Command::Install(confirm(digest)), None).exit_code,
        0 | 2
    ));
    let manifest_path = downgrade.path().join(".harness/manifest.json");
    let mut manifest: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest_path).unwrap()).unwrap();
    manifest["payload"]["sequence"] = serde_json::json!(43);
    std::fs::write(&manifest_path, serde_json::to_vec(&manifest).unwrap()).unwrap();
    let before_downgrade = tree_snapshot(downgrade.path());
    let refused_downgrade = execute(
        downgrade.path(),
        Command::Update(MutatorOptions::default()),
        None,
    );
    assert_eq!(
        refused_downgrade.exit_code, 3,
        "payload downgrade: {refused_downgrade:?}"
    );
    assert_eq!(refused_downgrade.mutation, Mutation::None);
    assert!(refused_downgrade
        .details
        .violations
        .iter()
        .any(|violation| violation.contains("rollback")));
    assert_eq!(tree_snapshot(downgrade.path()), before_downgrade);
}

#[test]
fn resume_skips_the_already_applied_operation_and_commits_only_incomplete_steps() {
    let temporary = tempfile::tempdir().unwrap();
    let (digest, operation, _) = preview(temporary.path(), Command::Install);
    let interrupted = execute(temporary.path(), Command::Install(confirm(digest)), Some(8));
    assert_eq!(
        interrupted.exit_code, 4,
        "kill after first applied-step journal: {interrupted:?}"
    );
    assert_eq!(interrupted.mutation, Mutation::RecoveryRequired);
    let decision_path = temporary.path().join("docs/templates/decision.md");
    let before_inode = std::fs::metadata(&decision_path).unwrap().ino();
    assert_eq!(std::fs::read(&decision_path).unwrap(), DECISION);
    assert!(!temporary.path().join("docs/templates/story.md").exists());
    assert!(!temporary.path().join(".harness/manifest.json").exists());

    let resumed = execute(
        temporary.path(),
        Command::Install(MutatorOptions {
            resume: Some(operation.clone()),
            ..MutatorOptions::default()
        }),
        None,
    );
    assert!(matches!(resumed.exit_code, 0 | 2), "{resumed:?}");
    assert_eq!(
        std::fs::metadata(&decision_path).unwrap().ino(),
        before_inode
    );
    assert_eq!(std::fs::read(&decision_path).unwrap(), DECISION);
    assert_eq!(
        std::fs::read(temporary.path().join("docs/templates/story.md")).unwrap(),
        STORY
    );
    assert!(temporary.path().join(".harness/manifest.json").is_file());
    assert!(temporary
        .path()
        .join(format!(".harness/recovery/{operation}/journal.json"))
        .is_file());
}

#[test]
fn every_update_backup_exchange_and_manifest_kill_point_resumes_deterministically() {
    for checkpoint in 1..=15 {
        let temporary = tempfile::tempdir().unwrap();
        let expected = prepare_managed_block_update(temporary.path());
        let old_target =
            std::fs::read(temporary.path().join("docs/templates/decision.md")).unwrap();
        let old_manifest = std::fs::read(temporary.path().join(".harness/manifest.json")).unwrap();
        let (digest, operation, _) = preview(temporary.path(), Command::Update);
        let interrupted = execute(
            temporary.path(),
            Command::Update(confirm(digest.clone())),
            Some(checkpoint),
        );
        assert_ne!(interrupted.exit_code, 0, "kill point {checkpoint}");
        assert_ne!(interrupted.exit_code, 2, "kill point {checkpoint}");
        assert!(
            temporary
                .path()
                .join(format!(".harness/recovery/{operation}"))
                .is_dir(),
            "kill point {checkpoint}: durable staged/backup recovery artifact"
        );
        if checkpoint <= 12 {
            assert_eq!(
                std::fs::read(temporary.path().join(".harness/manifest.json")).unwrap(),
                old_manifest,
                "kill point {checkpoint}: old manifest survives until the sole commit"
            );
        }
        if checkpoint == 1 {
            assert_eq!(
                std::fs::read(temporary.path().join("docs/templates/decision.md")).unwrap(),
                old_target,
                "backup-fsync kill precedes every destructive target write"
            );
            let recovery_files = tree_snapshot(temporary.path());
            assert!(recovery_files.iter().any(|(path, bytes)| {
                path.starts_with(&format!(".harness/recovery/{operation}/backups/"))
                    && bytes == &old_target
            }));
        }
        let journal = temporary
            .path()
            .join(format!(".harness/recovery/{operation}/journal.json"));
        let recovered = if journal.exists() {
            execute(
                temporary.path(),
                Command::Update(MutatorOptions {
                    resume: Some(operation),
                    ..MutatorOptions::default()
                }),
                None,
            )
        } else {
            execute(temporary.path(), Command::Update(confirm(digest)), None)
        };
        assert!(
            matches!(recovered.exit_code, 0 | 2),
            "checkpoint {checkpoint}: {recovered:?}"
        );
        assert_eq!(
            std::fs::read(temporary.path().join("docs/templates/decision.md")).unwrap(),
            expected,
            "checkpoint {checkpoint}"
        );
    }
}

#[test]
fn every_install_kill_point_has_a_deterministic_rerun_resume_or_rollback() {
    for checkpoint in 1..=18 {
        let temporary = tempfile::tempdir().unwrap();
        let (digest, operation, _) = preview(temporary.path(), Command::Install);
        let interrupted = execute(
            temporary.path(),
            Command::Install(confirm(digest.clone())),
            Some(checkpoint),
        );
        assert_ne!(interrupted.exit_code, 0, "kill point {checkpoint}");
        assert_ne!(interrupted.exit_code, 2, "kill point {checkpoint}");
        assert!(
            temporary
                .path()
                .join(format!(".harness/recovery/{operation}"))
                .is_dir(),
            "kill point {checkpoint}: staged recovery artifact survives"
        );
        if checkpoint <= 15 {
            assert!(
                !temporary.path().join(".harness/manifest.json").exists(),
                "kill point {checkpoint}: manifest is absent before its sole atomic rename"
            );
        }

        let journal = temporary
            .path()
            .join(format!(".harness/recovery/{operation}/journal.json"));
        let recovered = if journal.exists() {
            execute(
                temporary.path(),
                Command::Install(MutatorOptions {
                    resume: Some(operation.clone()),
                    ..MutatorOptions::default()
                }),
                None,
            )
        } else {
            execute(temporary.path(), Command::Install(confirm(digest)), None)
        };
        assert!(
            matches!(recovered.exit_code, 0 | 2),
            "checkpoint {checkpoint}: {recovered:?}"
        );
        assert!(temporary.path().join(".harness/manifest.json").is_file());

        if journal.exists() {
            let repeated = execute(
                temporary.path(),
                Command::Install(MutatorOptions {
                    resume: Some(operation),
                    ..MutatorOptions::default()
                }),
                None,
            );
            assert!(matches!(repeated.exit_code, 0 | 2));
        }
    }

    let temporary = tempfile::tempdir().unwrap();
    let (digest, operation, _) = preview(temporary.path(), Command::Install);
    let interrupted = execute(temporary.path(), Command::Install(confirm(digest)), Some(8));
    assert_eq!(interrupted.mutation, Mutation::RecoveryRequired);
    let rollback = execute(
        temporary.path(),
        Command::Install(MutatorOptions {
            rollback: Some(operation.clone()),
            ..MutatorOptions::default()
        }),
        None,
    );
    assert_eq!(rollback.exit_code, 0, "{rollback:?}");
    assert_eq!(rollback.mutation, Mutation::RolledBack);
    assert!(!temporary.path().join(".harness/manifest.json").exists());
    assert!(!temporary.path().join("docs/templates/decision.md").exists());
    let repeated = execute(
        temporary.path(),
        Command::Install(MutatorOptions {
            rollback: Some(operation),
            ..MutatorOptions::default()
        }),
        None,
    );
    assert_eq!(repeated.exit_code, 0);
    assert_eq!(repeated.mutation, Mutation::RolledBack);
}
