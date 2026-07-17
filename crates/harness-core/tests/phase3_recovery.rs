#![cfg(unix)]

use std::cell::Cell;
use std::collections::BTreeMap;
use std::ffi::OsString;
use std::os::unix::fs::{MetadataExt, PermissionsExt};
use std::path::Path;

use harness_core::application::HarnessCore;
use harness_core::domain::{
    Command, Envelope, ManifestRepositoryMode, Mutation, MutatorOptions, Notice, ScaffoldOptions,
};
use harness_core::infrastructure::{JsonManifestPort, OsFileSystem, UnavailableReleasePort};
use harness_core::interface::{parse, Parsed};
use harness_core::ports::{
    ManifestPort, PinnedRootKey, PortError, ReleaseFreshness, ReleaseMaterial, ReleasePort,
    ReleaseTrustInput, TrustPolicy, TrustPort, TrustedRootState,
};
use harness_core::recovery::OsMutationPort;
use hmac::{Hmac, Mac};
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
        path_ledger_sha256: "c8c5b7f4ec8a1e71fac3c2a7d8e3c36cbd39768eeb54603e17d95687bc68a625"
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

fn has_actionable_recovery_notice(envelope: &Envelope) -> bool {
    envelope.notices.iter().any(|notice| {
        matches!(
            notice.code.as_str(),
            "recovery-required" | "exact-rerun-recovery-required"
        )
    })
}

fn sha256(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

fn write_archive_fixture(root: &Path) -> String {
    write_bridge_compatible_custody(root);
    let directory = root.join(".harness-v0-archive/archive-test");
    std::fs::create_dir_all(&directory).unwrap();
    let payload = b"opaque encrypted archive fixture";
    std::fs::write(directory.join("archive.age"), payload).unwrap();
    let manifest = serde_json::json!({
        "schema": "repository-harness-v0-archive-manifest/v1",
        "archive_id": "archive-test",
        "bridge_release": "1.0.0",
        "source_schema": 13,
        "source_sha256": sha256(b"source"),
        "capture_members_sha256": sha256(b"capture members"),
        "export_sha256": sha256(b"neutral export"),
        "standalone_backup_sha256": sha256(b"standalone"),
        "confidentiality_mode": "encrypted-age-x25519",
        "recipient_fingerprints": ["age1fixture"],
        "payload_path": "archive.age",
        "payload_sha256": sha256(payload),
        "payload_bytes": payload.len(),
        "members": [
            {"path":"raw/harness.db","sha256":sha256(b"db"),"bytes":2,"capture":"pre-copy-post-equal"},
            {"path":"standalone/standalone.db","sha256":sha256(b"standalone"),"bytes":10,"capture":"private-staged-wal-recovery-online-backup"},
            {"path":"export/export.json","sha256":sha256(b"neutral export"),"bytes":14,"capture":"neutral-read-only-export"}
        ],
        "custody": "repository-owner-indefinite-write-once"
    });
    let mut bytes = serde_json::to_vec(&manifest).unwrap();
    bytes.push(b'\n');
    std::fs::write(directory.join("archive-manifest.json"), bytes).unwrap();
    ".harness-v0-archive/archive-test/archive-manifest.json".into()
}

fn write_bridge_compatible_custody(root: &Path) {
    let custody = root.join(".harness-v0-archive");
    std::fs::create_dir_all(&custody).unwrap();
    std::fs::set_permissions(&custody, std::fs::Permissions::from_mode(0o700)).unwrap();
    let key = [0x42_u8; 32];
    let key_path = custody.join("custody.key");
    std::fs::write(&key_path, key).unwrap();
    std::fs::set_permissions(&key_path, std::fs::Permissions::from_mode(0o600)).unwrap();
    let metadata = std::fs::metadata(root).unwrap();
    let message = format!(
        "repository-harness-v0-archive-custody/v1\0.harness-v0-archive\0{}\0{}",
        metadata.dev(),
        metadata.ino()
    );
    let mut mac = Hmac::<Sha256>::new_from_slice(&key).unwrap();
    mac.update(message.as_bytes());
    let marker = serde_json::json!({
        "schema": "repository-harness-v0-archive-custody/v1",
        "path": ".harness-v0-archive",
        "root": {"device": metadata.dev().to_string(), "inode": metadata.ino().to_string()},
        "key_sha256": sha256(&key),
        "authentication": format!("{:x}", mac.finalize().into_bytes())
    });
    let marker_path = custody.join("custody.json");
    let mut marker_bytes = serde_json::to_vec(&marker).unwrap();
    marker_bytes.push(b'\n');
    std::fs::write(&marker_path, marker_bytes).unwrap();
    std::fs::set_permissions(&marker_path, std::fs::Permissions::from_mode(0o600)).unwrap();
}

fn canonical_json_digest(value: &serde_json::Value) -> String {
    fn render(value: &serde_json::Value, output: &mut String) {
        match value {
            serde_json::Value::Null => output.push_str("null"),
            serde_json::Value::Bool(true) => output.push_str("true"),
            serde_json::Value::Bool(false) => output.push_str("false"),
            serde_json::Value::Number(number) => output.push_str(&number.to_string()),
            serde_json::Value::String(string) => {
                output.push_str(&serde_json::to_string(string).unwrap());
            }
            serde_json::Value::Array(values) => {
                output.push('[');
                for (index, child) in values.iter().enumerate() {
                    if index > 0 {
                        output.push(',');
                    }
                    render(child, output);
                }
                output.push(']');
            }
            serde_json::Value::Object(values) => {
                output.push('{');
                let mut ordered: Vec<_> = values.iter().collect();
                ordered.sort_by_key(|(key, _)| key.encode_utf16().collect::<Vec<_>>());
                for (index, (key, child)) in ordered.into_iter().enumerate() {
                    if index > 0 {
                        output.push(',');
                    }
                    output.push_str(&serde_json::to_string(key).unwrap());
                    output.push(':');
                    render(child, output);
                }
                output.push('}');
            }
        }
    }

    let mut canonical = String::new();
    render(value, &mut canonical);
    sha256(canonical.as_bytes())
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

fn copy_tree(source: &Path, destination: &Path) {
    fn visit(source_root: &Path, current: &Path, destination_root: &Path) {
        let mut entries: Vec<_> = std::fs::read_dir(current)
            .unwrap()
            .map(|entry| entry.unwrap().path())
            .collect();
        entries.sort();
        for path in entries {
            let relative = path.strip_prefix(source_root).unwrap();
            let target = destination_root.join(relative);
            if path.is_dir() {
                std::fs::create_dir_all(&target).unwrap();
                visit(source_root, &path, destination_root);
            } else {
                if let Some(parent) = target.parent() {
                    std::fs::create_dir_all(parent).unwrap();
                }
                std::fs::copy(&path, &target).unwrap();
            }
        }
    }

    visit(source, source, destination);
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

fn prepare_two_managed_file_update(root: &Path) -> (Vec<u8>, Vec<u8>, Vec<u8>, String, String) {
    let digest = preview(root, Command::Install).0;
    assert!(matches!(
        execute(root, Command::Install(confirm(digest)), None).exit_code,
        0 | 2
    ));
    let old_decision = b"# Old managed decision\n".to_vec();
    let old_story = b"# Old managed story\n".to_vec();
    std::fs::write(root.join("docs/templates/decision.md"), &old_decision).unwrap();
    std::fs::write(root.join("docs/templates/story.md"), &old_story).unwrap();
    let manifest_path = root.join(".harness/manifest.json");
    let mut manifest: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest_path).unwrap()).unwrap();
    for (path, bytes) in [
        ("docs/templates/decision.md", old_decision.as_slice()),
        ("docs/templates/story.md", old_story.as_slice()),
    ] {
        let role = manifest["roles"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|role| role["path"] == path)
            .unwrap();
        role["base_sha256"] = serde_json::json!(sha256(bytes));
        role["current_sha256"] = serde_json::json!(sha256(bytes));
    }
    let old_manifest = serde_json::to_vec(&manifest).unwrap();
    std::fs::write(&manifest_path, &old_manifest).unwrap();
    let (digest, operation, _) = preview(root, Command::Update);
    (old_decision, old_story, old_manifest, digest, operation)
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
fn fresh_install_recovery_commits_exact_v0_archive_receipt_without_reading_sqlite() {
    let temporary = tempfile::tempdir().unwrap();
    std::fs::write(temporary.path().join("harness.db"), b"opaque V0 bytes").unwrap();
    let archive_manifest = write_archive_fixture(temporary.path());
    let previewed = execute(
        temporary.path(),
        Command::Install(MutatorOptions {
            preview: true,
            v0_archive_manifest: Some(archive_manifest.clone()),
            ..MutatorOptions::default()
        }),
        None,
    );
    assert!(matches!(previewed.exit_code, 0 | 2), "{previewed:?}");
    let digest = notice(&previewed.notices, "preview-sha256").message.clone();
    let operation = notice(&previewed.notices, "operation-id").message.clone();
    let interrupted = execute(
        temporary.path(),
        Command::Install(MutatorOptions {
            non_interactive: true,
            accept_preview_sha256: Some(digest),
            v0_archive_manifest: Some(archive_manifest.clone()),
            ..MutatorOptions::default()
        }),
        Some(14),
    );
    assert!(matches!(interrupted.exit_code, 4 | 74), "{interrupted:?}");
    assert!(!temporary.path().join(".harness/manifest.json").exists());

    let resumed = execute(
        temporary.path(),
        Command::Install(MutatorOptions {
            resume: Some(operation),
            ..MutatorOptions::default()
        }),
        None,
    );
    assert!(matches!(resumed.exit_code, 0 | 2), "{resumed:?}");
    let manifest: serde_json::Value = serde_json::from_slice(
        &std::fs::read(temporary.path().join(".harness/manifest.json")).unwrap(),
    )
    .unwrap();
    assert_eq!(manifest["repository_mode"], "fresh-v1");
    assert_eq!(
        manifest["v0_archive_receipt"]["archive_manifest_path"],
        archive_manifest
    );
    assert_eq!(
        manifest["v0_archive_receipt"]["export_sha256"],
        sha256(b"neutral export")
    );
    assert!(!temporary.path().join("harness-v1.db").exists());

    std::fs::write(
        temporary
            .path()
            .join(".harness-v0-archive/archive-test/archive.age"),
        b"tampered",
    )
    .unwrap();
    let invalid = execute(temporary.path(), Command::Status { json: true }, None);
    assert_eq!(invalid.exit_code, 3);
    assert!(invalid
        .details
        .violations
        .contains(&"v0-archive-receipt-invalid".into()));
}

#[test]
fn fake_or_missing_custody_cannot_become_a_v1_archive_receipt() {
    use std::os::unix::fs::symlink;

    for case in [
        "missing-marker",
        "malformed-marker",
        "symlinked-marker",
        "wrong-directory-mode",
        "wrong-key-mode",
        "wrong-key-length",
        "wrong-root",
        "wrong-hmac",
    ] {
        let temporary = tempfile::tempdir().unwrap();
        std::fs::write(temporary.path().join("harness.db"), b"opaque V0 bytes").unwrap();
        let archive_manifest = write_archive_fixture(temporary.path());
        let custody = temporary.path().join(".harness-v0-archive");
        let marker_path = custody.join("custody.json");
        let key_path = custody.join("custody.key");
        match case {
            "missing-marker" => std::fs::remove_file(&marker_path).unwrap(),
            "malformed-marker" => std::fs::write(&marker_path, b"{not-json").unwrap(),
            "symlinked-marker" => {
                let outside = temporary.path().join("foreign-custody.json");
                std::fs::rename(&marker_path, &outside).unwrap();
                symlink(&outside, &marker_path).unwrap();
            }
            "wrong-directory-mode" => {
                std::fs::set_permissions(&custody, std::fs::Permissions::from_mode(0o755)).unwrap();
            }
            "wrong-key-mode" => {
                std::fs::set_permissions(&key_path, std::fs::Permissions::from_mode(0o644))
                    .unwrap();
            }
            "wrong-key-length" => std::fs::write(&key_path, [0x42_u8; 31]).unwrap(),
            "wrong-root" | "wrong-hmac" => {
                let mut marker: serde_json::Value =
                    serde_json::from_slice(&std::fs::read(&marker_path).unwrap()).unwrap();
                if case == "wrong-root" {
                    marker["root"]["inode"] = serde_json::json!("0");
                } else {
                    marker["authentication"] = serde_json::json!("0".repeat(64));
                }
                std::fs::write(&marker_path, serde_json::to_vec(&marker).unwrap()).unwrap();
            }
            _ => unreachable!(),
        }
        let rejected = execute(
            temporary.path(),
            Command::Install(MutatorOptions {
                preview: true,
                v0_archive_manifest: Some(archive_manifest),
                ..MutatorOptions::default()
            }),
            None,
        );
        assert!(
            matches!(rejected.exit_code, 3 | 4 | 74),
            "case {case}: {rejected:?}"
        );
        assert!(
            !temporary.path().join(".harness/manifest.json").exists(),
            "case {case} created a V1 receipt"
        );
    }
}

#[test]
fn archive_member_capture_and_bridge_release_are_closed_contracts() {
    for field in ["capture", "bridge-release"] {
        let temporary = tempfile::tempdir().unwrap();
        std::fs::write(temporary.path().join("harness.db"), b"opaque V0 bytes").unwrap();
        let archive_manifest = write_archive_fixture(temporary.path());
        let manifest_path = temporary.path().join(&archive_manifest);
        let mut manifest: serde_json::Value =
            serde_json::from_slice(&std::fs::read(&manifest_path).unwrap()).unwrap();
        if field == "capture" {
            manifest["members"][0]["capture"] = serde_json::json!("self-authored-copy");
        } else {
            manifest["bridge_release"] = serde_json::json!("1.0.1");
        }
        std::fs::write(&manifest_path, serde_json::to_vec(&manifest).unwrap()).unwrap();
        let rejected = execute(
            temporary.path(),
            Command::Install(MutatorOptions {
                preview: true,
                v0_archive_manifest: Some(archive_manifest),
                ..MutatorOptions::default()
            }),
            None,
        );
        assert_eq!(rejected.exit_code, 3, "field {field}: {rejected:?}");
        assert!(!temporary.path().join(".harness/manifest.json").exists());
    }
}

#[test]
fn preview_sha256_matches_the_exact_emitted_operations_array() {
    let temporary = tempfile::tempdir().unwrap();
    let (_, _, preview) = preview(temporary.path(), Command::Install);
    let operations = preview
        .details
        .operations
        .clone()
        .expect("preview exposes public operations");
    let recomputed = canonical_json_digest(&serde_json::to_value(&operations).unwrap());
    assert_eq!(
        recomputed,
        notice(&preview.notices, "preview-sha256").message
    );
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

    let before_status = tree_snapshot(temporary.path());
    let status = execute(temporary.path(), Command::Status { json: true }, None);
    assert_eq!(status.exit_code, 3, "{status:?}");
    assert_eq!(status.mutation, Mutation::RecoveryRequired);
    assert_eq!(tree_snapshot(temporary.path()), before_status);
    let recovery_notice = notice(&status.notices, "recovery-required");
    assert!(recovery_notice.message.contains(&format!(
        "scaffold --template decision-template --destination docs/templates/decision.md --resume {operation}"
    )));
    assert!(recovery_notice.message.contains(&format!(
        "scaffold --template decision-template --destination docs/templates/decision.md --rollback {operation}"
    )));

    let before_wrong_scope = tree_snapshot(temporary.path());
    let wrong_scope = execute(
        temporary.path(),
        Command::Scaffold(ScaffoldOptions {
            template: Some("story-template".into()),
            destination: Some("docs/templates/story.md".into()),
            mutation: MutatorOptions {
                resume: Some(operation.clone()),
                ..MutatorOptions::default()
            },
        }),
        None,
    );
    assert_eq!(wrong_scope.exit_code, 4, "{wrong_scope:?}");
    assert_eq!(wrong_scope.mutation, Mutation::RecoveryRequired);
    assert_eq!(tree_snapshot(temporary.path()), before_wrong_scope);

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
    let parsed = parse([
        OsString::from("scaffold"),
        OsString::from("--template"),
        OsString::from("decision-template"),
        OsString::from("--destination"),
        OsString::from("docs/templates/decision.md"),
        OsString::from("--resume"),
        OsString::from(&operation),
    ])
    .expect("emitted scaffold recovery syntax is accepted by the frozen parser");
    let Parsed::Command(parsed_command) = parsed else {
        panic!("recovery syntax unexpectedly parsed as help");
    };
    assert_eq!(parsed_command, recovery_command());
    let recovered = execute(temporary.path(), parsed_command, None);
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
    let manifest_bytes = std::fs::read(temporary.path().join(".harness/manifest.json")).unwrap();
    let manifest: serde_json::Value = serde_json::from_slice(&manifest_bytes).unwrap();
    assert_eq!(manifest["repository_mode"], "brownfield-v1");
    let parsed = JsonManifestPort
        .parse_bytes(&manifest_bytes)
        .expect("core-generated brownfield manifest must satisfy the runtime contract");
    assert_eq!(parsed.repository_mode, ManifestRepositoryMode::BrownfieldV1);
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
fn damaged_applying_update_evidence_is_non_actionable_and_preserves_the_tree() {
    for (label, damage_backup) in [
        ("corrupted-staged-target", false),
        ("missing-required-backup", true),
    ] {
        let temporary = tempfile::tempdir().unwrap();
        let (_, _, _, digest, operation) = prepare_two_managed_file_update(temporary.path());
        let interrupted = execute(temporary.path(), Command::Update(confirm(digest)), Some(8));
        assert_eq!(interrupted.exit_code, 4, "{label}: {interrupted:?}");
        assert_eq!(interrupted.mutation, Mutation::RecoveryRequired, "{label}");

        let journal_path = temporary
            .path()
            .join(format!(".harness/recovery/{operation}/journal.json"));
        let journal: serde_json::Value =
            serde_json::from_slice(&std::fs::read(&journal_path).unwrap()).unwrap();
        assert_eq!(journal["state"], "applying", "{label}");
        let decision_step = journal["steps"]
            .as_array()
            .unwrap()
            .iter()
            .find(|step| step["path"] == "docs/templates/decision.md")
            .unwrap();
        if damage_backup {
            let backup_path = decision_step["backup_path"].as_str().unwrap();
            std::fs::remove_file(temporary.path().join(backup_path)).unwrap();
        } else {
            let staged_path = decision_step["staged_path"].as_str().unwrap();
            std::fs::write(
                temporary.path().join(staged_path),
                b"corrupted staged evidence\n",
            )
            .unwrap();
        }
        let before = tree_snapshot(temporary.path());

        let status = execute(temporary.path(), Command::Status { json: true }, None);
        assert_eq!(status.exit_code, 3, "{label}: {status:?}");
        assert_eq!(status.mutation, Mutation::None, "{label}");
        assert!(
            !has_actionable_recovery_notice(&status),
            "{label}: {status:?}"
        );
        assert_eq!(tree_snapshot(temporary.path()), before, "{label}");

        let ordinary = execute(
            temporary.path(),
            Command::Update(MutatorOptions::default()),
            None,
        );
        assert_eq!(ordinary.exit_code, 3, "{label}: {ordinary:?}");
        assert_eq!(ordinary.mutation, Mutation::None, "{label}");
        assert!(
            !has_actionable_recovery_notice(&ordinary),
            "{label}: {ordinary:?}"
        );
        assert_eq!(tree_snapshot(temporary.path()), before, "{label}");

        let explicit = execute(
            temporary.path(),
            Command::Update(MutatorOptions {
                resume: Some(operation.clone()),
                ..MutatorOptions::default()
            }),
            None,
        );
        assert_eq!(explicit.exit_code, 4, "{label}: {explicit:?}");
        assert_eq!(tree_snapshot(temporary.path()), before, "{label}");
    }
}

#[test]
fn fabricated_fresh_pending_journal_is_not_reported_or_resumed_against_preexisting_authenticated_bytes(
) {
    let source = tempfile::tempdir().unwrap();
    let (digest, operation, _) = preview(source.path(), Command::Install);
    let interrupted = execute(source.path(), Command::Install(confirm(digest)), Some(4));
    assert_eq!(interrupted.mutation, Mutation::RecoveryRequired);

    let target = tempfile::tempdir().unwrap();
    std::fs::create_dir_all(target.path().join("docs/templates")).unwrap();
    std::fs::write(target.path().join("docs/templates/decision.md"), DECISION).unwrap();
    copy_tree(
        &source.path().join(format!(".harness/recovery/{operation}")),
        &target.path().join(format!(".harness/recovery/{operation}")),
    );
    let before = tree_snapshot(target.path());

    let status = execute(target.path(), Command::Status { json: true }, None);
    assert_eq!(status.exit_code, 0, "{status:?}");
    assert_eq!(status.mutation, Mutation::None);
    assert!(
        status
            .notices
            .iter()
            .all(|notice| notice.code != "recovery-required"),
        "{status:?}"
    );
    assert!(
        status
            .notices
            .iter()
            .all(|notice| !notice.message.contains(&operation)),
        "{status:?}"
    );
    assert_eq!(tree_snapshot(target.path()), before);

    let refused = execute(
        target.path(),
        Command::Install(MutatorOptions {
            resume: Some(operation),
            ..MutatorOptions::default()
        }),
        None,
    );
    assert_eq!(refused.exit_code, 4, "{refused:?}");
    assert_eq!(refused.mutation, Mutation::None);
    assert_eq!(
        std::fs::read(target.path().join("docs/templates/decision.md")).unwrap(),
        DECISION
    );
    assert!(!target.path().join(".harness/manifest.json").exists());
}

#[test]
fn fabricated_fresh_pending_journal_cannot_rollback_delete_preexisting_authenticated_bytes() {
    let source = tempfile::tempdir().unwrap();
    let (digest, operation, _) = preview(source.path(), Command::Install);
    let interrupted = execute(source.path(), Command::Install(confirm(digest)), Some(4));
    assert_eq!(interrupted.mutation, Mutation::RecoveryRequired);

    let target = tempfile::tempdir().unwrap();
    std::fs::create_dir_all(target.path().join("docs/templates")).unwrap();
    std::fs::write(target.path().join("docs/templates/decision.md"), DECISION).unwrap();
    copy_tree(
        &source.path().join(format!(".harness/recovery/{operation}")),
        &target.path().join(format!(".harness/recovery/{operation}")),
    );
    let before = tree_snapshot(target.path());

    let refused = execute(
        target.path(),
        Command::Install(MutatorOptions {
            rollback: Some(operation.clone()),
            ..MutatorOptions::default()
        }),
        None,
    );
    assert_eq!(refused.exit_code, 4, "{refused:?}");
    assert_eq!(refused.mutation, Mutation::None);
    assert_eq!(
        std::fs::read(target.path().join("docs/templates/decision.md")).unwrap(),
        DECISION
    );
    assert!(!target.path().join(".harness/manifest.json").exists());
    assert_eq!(tree_snapshot(target.path()), before);
}

#[test]
fn copied_interrupted_update_journal_is_not_actionable_in_another_repository_root() {
    let source = tempfile::tempdir().unwrap();
    let (_, _, _, digest, operation) = prepare_two_managed_file_update(source.path());
    let interrupted = execute(source.path(), Command::Update(confirm(digest)), Some(7));
    assert_eq!(interrupted.exit_code, 4, "{interrupted:?}");
    assert_eq!(interrupted.mutation, Mutation::RecoveryRequired);
    assert!(source
        .path()
        .join(format!(".harness/recovery/{operation}/journal.json"))
        .is_file());

    let target = tempfile::tempdir().unwrap();
    prepare_two_managed_file_update(target.path());
    copy_tree(
        &source.path().join(format!(".harness/recovery/{operation}")),
        &target.path().join(format!(".harness/recovery/{operation}")),
    );
    let before = tree_snapshot(target.path());

    let status = execute(target.path(), Command::Status { json: true }, None);
    assert_eq!(status.exit_code, 0, "{status:?}");
    assert_eq!(status.mutation, Mutation::None);
    assert!(
        status
            .notices
            .iter()
            .all(|notice| notice.code != "recovery-required"),
        "{status:?}"
    );
    assert!(
        status
            .notices
            .iter()
            .all(|notice| !notice.message.contains(&operation)),
        "{status:?}"
    );
    assert_eq!(tree_snapshot(target.path()), before);

    let refused = execute(
        target.path(),
        Command::Update(MutatorOptions {
            resume: Some(operation),
            ..MutatorOptions::default()
        }),
        None,
    );
    assert_eq!(refused.exit_code, 4, "{refused:?}");
    assert_eq!(refused.mutation, Mutation::None);
    assert_eq!(tree_snapshot(target.path()), before);
}

#[test]
fn copied_committed_update_journal_cannot_drive_rollback_in_another_repository_root() {
    let source = tempfile::tempdir().unwrap();
    let (_, _, _, digest, operation) = prepare_two_managed_file_update(source.path());
    let committed = execute(source.path(), Command::Update(confirm(digest)), None);
    assert!(matches!(committed.exit_code, 0 | 2), "{committed:?}");

    let target = tempfile::tempdir().unwrap();
    prepare_two_managed_file_update(target.path());
    std::fs::write(target.path().join("docs/templates/decision.md"), DECISION).unwrap();
    std::fs::write(target.path().join("docs/templates/story.md"), STORY).unwrap();
    std::fs::create_dir_all(target.path().join(".harness")).unwrap();
    std::fs::copy(
        source.path().join(".harness/manifest.json"),
        target.path().join(".harness/manifest.json"),
    )
    .unwrap();
    copy_tree(
        &source.path().join(format!(".harness/recovery/{operation}")),
        &target.path().join(format!(".harness/recovery/{operation}")),
    );
    let before = tree_snapshot(target.path());

    let refused = execute(
        target.path(),
        Command::Update(MutatorOptions {
            rollback: Some(operation),
            ..MutatorOptions::default()
        }),
        None,
    );
    assert_eq!(refused.exit_code, 4, "{refused:?}");
    assert_eq!(refused.mutation, Mutation::None);
    assert_eq!(tree_snapshot(target.path()), before);
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
fn every_committed_update_rollback_checkpoint_resumes_in_reverse_with_old_manifest_last() {
    for checkpoint in 1..=13 {
        let temporary = tempfile::tempdir().unwrap();
        let (old_decision, old_story, old_manifest, digest, operation) =
            prepare_two_managed_file_update(temporary.path());
        let committed = execute(temporary.path(), Command::Update(confirm(digest)), None);
        assert!(matches!(committed.exit_code, 0 | 2), "{committed:?}");
        assert_eq!(
            std::fs::read(temporary.path().join("docs/templates/decision.md")).unwrap(),
            DECISION
        );
        assert_eq!(
            std::fs::read(temporary.path().join("docs/templates/story.md")).unwrap(),
            STORY
        );

        let interrupted = execute(
            temporary.path(),
            Command::Update(MutatorOptions {
                rollback: Some(operation.clone()),
                ..MutatorOptions::default()
            }),
            Some(checkpoint),
        );
        assert_eq!(
            interrupted.exit_code, 4,
            "checkpoint {checkpoint}: {interrupted:?}"
        );
        assert_eq!(interrupted.mutation, Mutation::RecoveryRequired);
        if checkpoint == 2 {
            assert!(
                !temporary.path().join(".harness/manifest.json").exists(),
                "the explicit rolling-back intent makes the new-manifest removal gap resumable"
            );
        }
        if checkpoint == 6 {
            assert_eq!(
                std::fs::read(temporary.path().join("docs/templates/story.md")).unwrap(),
                old_story,
                "the lexically later target is restored first"
            );
            assert_eq!(
                std::fs::read(temporary.path().join("docs/templates/decision.md")).unwrap(),
                DECISION,
                "the earlier target remains at its post-image until reverse restoration reaches it"
            );
            assert!(!temporary.path().join(".harness/manifest.json").exists());
        }

        let recovered = execute(
            temporary.path(),
            Command::Update(MutatorOptions {
                rollback: Some(operation.clone()),
                ..MutatorOptions::default()
            }),
            None,
        );
        assert_eq!(
            recovered.exit_code, 0,
            "checkpoint {checkpoint}: {recovered:?}"
        );
        assert_eq!(recovered.mutation, Mutation::RolledBack);
        assert_eq!(
            std::fs::read(temporary.path().join("docs/templates/decision.md")).unwrap(),
            old_decision,
            "checkpoint {checkpoint}"
        );
        assert_eq!(
            std::fs::read(temporary.path().join("docs/templates/story.md")).unwrap(),
            old_story,
            "checkpoint {checkpoint}"
        );
        assert_eq!(
            std::fs::read(temporary.path().join(".harness/manifest.json")).unwrap(),
            old_manifest,
            "checkpoint {checkpoint}: old manifest is restored only after both targets"
        );

        let repeated = execute(
            temporary.path(),
            Command::Update(MutatorOptions {
                rollback: Some(operation),
                ..MutatorOptions::default()
            }),
            None,
        );
        assert_eq!(
            repeated.exit_code, 0,
            "checkpoint {checkpoint}: {repeated:?}"
        );
        assert_eq!(repeated.mutation, Mutation::RolledBack);
    }

    let temporary = tempfile::tempdir().unwrap();
    let (_, _, _, digest, operation) = prepare_two_managed_file_update(temporary.path());
    assert!(matches!(
        execute(temporary.path(), Command::Update(confirm(digest)), None).exit_code,
        0 | 2
    ));
    let no_fourteenth_checkpoint = execute(
        temporary.path(),
        Command::Update(MutatorOptions {
            rollback: Some(operation),
            ..MutatorOptions::default()
        }),
        Some(14),
    );
    assert_eq!(
        no_fourteenth_checkpoint.exit_code, 0,
        "{no_fourteenth_checkpoint:?}"
    );
    assert_eq!(no_fourteenth_checkpoint.mutation, Mutation::RolledBack);
}

#[test]
fn human_edit_during_committed_update_rollback_is_preserved_before_old_manifest_restore() {
    let temporary = tempfile::tempdir().unwrap();
    let (_, _, _, digest, operation) = prepare_two_managed_file_update(temporary.path());
    assert!(matches!(
        execute(temporary.path(), Command::Update(confirm(digest)), None).exit_code,
        0 | 2
    ));
    let interrupted = execute(
        temporary.path(),
        Command::Update(MutatorOptions {
            rollback: Some(operation.clone()),
            ..MutatorOptions::default()
        }),
        Some(2),
    );
    assert_eq!(interrupted.mutation, Mutation::RecoveryRequired);
    assert!(!temporary.path().join(".harness/manifest.json").exists());
    let human = b"# Human edit during rollback\n";
    std::fs::write(temporary.path().join("docs/templates/story.md"), human).unwrap();

    let refused = execute(
        temporary.path(),
        Command::Update(MutatorOptions {
            rollback: Some(operation),
            ..MutatorOptions::default()
        }),
        None,
    );
    assert_eq!(refused.exit_code, 4, "{refused:?}");
    assert_eq!(refused.mutation, Mutation::RecoveryRequired);
    assert_eq!(
        std::fs::read(temporary.path().join("docs/templates/story.md")).unwrap(),
        human
    );
    assert!(!temporary.path().join(".harness/manifest.json").exists());
}

#[test]
fn rollback_deliberately_requires_live_release_authorization_before_using_local_evidence() {
    let temporary = tempfile::tempdir().unwrap();
    let (old_decision, old_story, old_manifest, digest, operation) =
        prepare_two_managed_file_update(temporary.path());
    assert!(matches!(
        execute(temporary.path(), Command::Update(confirm(digest)), None).exit_code,
        0 | 2
    ));
    let committed_snapshot = tree_snapshot(temporary.path());
    let trust = SignedFixtureRelease;
    let refused = execute_with_release(
        temporary.path(),
        Command::Update(MutatorOptions {
            rollback: Some(operation.clone()),
            ..MutatorOptions::default()
        }),
        &UnavailableReleasePort,
        &trust,
    );
    // Rollback remains deliberately bound to a live authenticated release;
    // when that authority is unavailable, recovery stops before local
    // evidence is consulted and reports the normal mutation conflict.
    assert_eq!(refused.exit_code, 4, "{refused:?}");
    assert_eq!(refused.mutation, Mutation::None);
    assert_eq!(tree_snapshot(temporary.path()), committed_snapshot);

    let authorized = execute(
        temporary.path(),
        Command::Update(MutatorOptions {
            rollback: Some(operation),
            ..MutatorOptions::default()
        }),
        None,
    );
    assert_eq!(authorized.exit_code, 0, "{authorized:?}");
    assert_eq!(authorized.mutation, Mutation::RolledBack);
    assert_eq!(
        std::fs::read(temporary.path().join("docs/templates/decision.md")).unwrap(),
        old_decision
    );
    assert_eq!(
        std::fs::read(temporary.path().join("docs/templates/story.md")).unwrap(),
        old_story
    );
    assert_eq!(
        std::fs::read(temporary.path().join(".harness/manifest.json")).unwrap(),
        old_manifest
    );
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
