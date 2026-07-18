use std::cell::Cell;
use std::collections::{BTreeMap, BTreeSet};

use harness_core::application::HarnessCore;
use harness_core::domain::{
    Command, MutatorOptions, Outcome, Readiness, RepositoryMode, ScaffoldOptions,
};
use harness_core::infrastructure::JsonManifestPort;
use harness_core::path::validate_relative;
use harness_core::ports::{
    CompatibilityObservation, FileSystemPort, ManifestPort, PinnedRootKey, PortError,
    ReleaseFreshness, ReleaseMaterial, ReleasePort, ReleaseTrustInput, RollbackMaterial,
    TrustPolicy, TrustPort, TrustedRootState,
};
use harness_core::trust::{verify_release, VerifiedRelease};
use sha2::{Digest, Sha256};

const INDEX: &[u8] =
    include_bytes!("../../../tests/fixtures/v1-phase2/current-core-payload-index.json");
const SIGNATURES: &[u8] =
    include_bytes!("../../../tests/fixtures/v1-phase2/current-core-payload-index.signatures.json");
const PHASE1_INDEX: &[u8] =
    include_bytes!("../../../tests/fixtures/v1-phase1/positive/core-payload-index.json");
const PHASE1_SIGNATURES: &[u8] =
    include_bytes!("../../../tests/fixtures/v1-phase1/positive/core-payload-index.signatures.json");
const TRUST: &[u8] =
    include_bytes!("../../../tests/fixtures/v1-phase1/positive/core-trust-bundle.json");
const TRUST_SIGNATURES: &[u8] =
    include_bytes!("../../../tests/fixtures/v1-phase1/positive/core-trust-bundle.signatures.json");
const BOOTSTRAP_ANCHORS: &[u8] =
    include_bytes!("../../../tests/fixtures/v1-phase1/positive/test-bootstrap-anchors.json");
const BRIDGE_INDEX: &[u8] =
    include_bytes!("../../../tests/fixtures/v1-phase1/positive/bridge-payload-index.json");
const BRIDGE_SIGNATURES: &[u8] = include_bytes!(
    "../../../tests/fixtures/v1-phase1/positive/bridge-payload-index.signatures.json"
);
const BRIDGE_TRUST: &[u8] =
    include_bytes!("../../../tests/fixtures/v1-phase1/positive/bridge-trust-bundle.json");
const BRIDGE_TRUST_SIGNATURES: &[u8] = include_bytes!(
    "../../../tests/fixtures/v1-phase1/positive/bridge-trust-bundle.signatures.json"
);
const REVOCATION_TRUST: &[u8] =
    include_bytes!("../../../tests/fixtures/v1-phase1/positive/revocation-trust-bundle.json");
const REVOCATION_TRUST_SIGNATURES: &[u8] = include_bytes!(
    "../../../tests/fixtures/v1-phase1/positive/revocation-trust-bundle.signatures.json"
);
const ROTATION_TRUST: &[u8] =
    include_bytes!("../../../tests/fixtures/v1-phase1/positive/root-rotation-trust-bundle.json");
const ROTATION_TRUST_SIGNATURES: &[u8] = include_bytes!(
    "../../../tests/fixtures/v1-phase1/positive/root-rotation-trust-bundle.signatures.json"
);
const FREEZE_INDEX: &[u8] =
    include_bytes!("../../../tests/fixtures/v1-phase1/negative/freeze-payload-index.json");
const FREEZE_SIGNATURES: &[u8] = include_bytes!(
    "../../../tests/fixtures/v1-phase1/negative/freeze-payload-index.signatures.json"
);
const AUTHORIZED_ROLLBACK: &[u8] =
    include_bytes!("../../../tests/fixtures/v1-phase1/positive/authorized-rollback.json");
const AUTHORIZED_ROLLBACK_SIGNATURES: &[u8] = include_bytes!(
    "../../../tests/fixtures/v1-phase1/positive/authorized-rollback.signatures.json"
);
const WRONG_ROOT_ROLLBACK: &[u8] = include_bytes!(
    "../../../tests/fixtures/v1-phase1/negative/wrong-root-bundle-sequence-rollback.json"
);
const WRONG_ROOT_ROLLBACK_SIGNATURES: &[u8] = include_bytes!(
    "../../../tests/fixtures/v1-phase1/negative/wrong-root-bundle-sequence-rollback.signatures.json"
);
const POST_REVOCATION_INDEX: &[u8] =
    include_bytes!("../../../tests/fixtures/v1-phase1/positive/post-revocation-payload-index.json");
const POST_REVOCATION_SIGNATURES: &[u8] = include_bytes!(
    "../../../tests/fixtures/v1-phase1/positive/post-revocation-payload-index.signatures.json"
);
const LEDGER: &[u8] = include_bytes!("../../../release/contracts/v1/path-dispositions.json");
const DECISION: &[u8] = include_bytes!("../../../docs/templates/decision.md");
const STORY: &[u8] = include_bytes!("../../../docs/templates/story.md");
const PHASE1_STORY: &[u8] =
    include_bytes!("../../../tests/fixtures/v1-phase2/historical-phase1-story.md");

#[derive(Clone, Default)]
struct MemoryFileSystem {
    files: BTreeMap<String, Vec<u8>>,
    reads: Cell<usize>,
    compatibility: CompatibilityObservation,
}

impl MemoryFileSystem {
    fn with(mut self, path: &str, bytes: impl Into<Vec<u8>>) -> Self {
        self.files.insert(path.into(), bytes.into());
        self
    }

    fn with_compatibility(mut self, compatibility: CompatibilityObservation) -> Self {
        self.compatibility = compatibility;
        self
    }
}

impl FileSystemPort for MemoryFileSystem {
    fn read_declared(&self, path: &str) -> Result<Vec<u8>, PortError> {
        validate_relative(path, true)?;
        self.reads.set(self.reads.get() + 1);
        self.files
            .get(path)
            .cloned()
            .ok_or_else(|| PortError::Missing(path.into()))
    }

    fn exists_declared(&self, path: &str) -> Result<bool, PortError> {
        validate_relative(path, true)?;
        Ok(self.files.contains_key(path))
    }

    fn validate_snapshot(&self) -> Result<(), PortError> {
        Ok(())
    }

    fn observe_compatibility(&self) -> Result<CompatibilityObservation, PortError> {
        Ok(self.compatibility)
    }
}

#[derive(Clone)]
struct MemoryRelease {
    material: ReleaseMaterial,
    trust: ReleaseTrustInput,
}

impl MemoryRelease {
    fn core() -> Self {
        Self {
            material: core_material(),
            trust: core_trust(),
        }
    }
}

impl ReleasePort for MemoryRelease {
    fn load(&self) -> Result<ReleaseMaterial, PortError> {
        Ok(self.material.clone())
    }
}

impl TrustPort for MemoryRelease {
    fn load(&self) -> Result<ReleaseTrustInput, PortError> {
        Ok(self.trust.clone())
    }
}

fn core_material() -> ReleaseMaterial {
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

fn phase1_core_material() -> ReleaseMaterial {
    let mut material = core_material();
    material.index = PHASE1_INDEX.to_vec();
    material.signatures = PHASE1_SIGNATURES.to_vec();
    material
        .source_files
        .insert("docs/templates/story.md".into(), PHASE1_STORY.to_vec());
    material
}

fn core_trust() -> ReleaseTrustInput {
    ReleaseTrustInput {
        trusted_root: fixture_root("core"),
        trust_policy: TrustPolicy::TestFixtures,
        path_ledger_sha256: "b701a5c74ba3c65cd6a1f3e06b52c00823f0db315b72bb1d3ba78587903e53b0"
            .into(),
        freshness: ReleaseFreshness::Existing {
            sequence: 44,
            digest: "0e2f88897e5c18ce8b1515a0c6de2f6bcfac97994fac3320965afd51ef1ddcdb".into(),
            rollback: None,
        },
    }
}

fn verify(material: ReleaseMaterial) -> Result<VerifiedRelease, PortError> {
    verify_release(material, core_trust())
}

fn verify_with(
    material: ReleaseMaterial,
    trust: ReleaseTrustInput,
) -> Result<VerifiedRelease, PortError> {
    verify_release(material, trust)
}

fn fixture_root(surface: &str) -> TrustedRootState {
    let anchors: serde_json::Value = serde_json::from_slice(BOOTSTRAP_ANCHORS).unwrap();
    let value = &anchors[surface];
    TrustedRootState {
        trust_domain: value["trust_domain"].as_str().unwrap().into(),
        sequence: 1,
        bundle_sha256: value["exact_bundle_digest"].as_str().unwrap().into(),
        threshold: value["root_threshold"].as_u64().unwrap() as u8,
        keys: value["root_keys"]
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

fn manifest(path: &str, bytes: &[u8], activation: &str, unresolved: &[&str]) -> Vec<u8> {
    let digest = format!("{:x}", Sha256::digest(bytes));
    serde_json::to_vec(&serde_json::json!({
        "schema": "repository-harness-manifest/v1",
        "repository_mode": "fresh-v1",
        "compatibility": {
            "cli_min": "1.0.0",
            "cli_max": "1.0.0",
            "template_release_min": "1.0.0-test.1",
            "template_release_max": "1.0.0"
        },
        "payload": {
            "trust_domain": "repository-harness-core",
            "role": "core-release",
            "sequence": 44,
            "index_sha256": "0e2f88897e5c18ce8b1515a0c6de2f6bcfac97994fac3320965afd51ef1ddcdb"
        },
        "roles": [{
            "role": "decision_template",
            "asset": "decision-template",
            "activation": activation,
            "ownership": "managed-file",
            "origin": "created",
            "required": true,
            "path": path,
            "template": "decision-template",
            "template_release": "1.0.0",
            "base_sha256": digest,
            "current_sha256": digest,
            "update_policy": "replace-if-base",
            "unresolved_markers": unresolved
        }]
    }))
    .unwrap()
}

#[test]
fn strict_release_verifier_accepts_only_signed_indexed_core_assets() {
    let verified = verify(core_material()).unwrap();
    assert_eq!(verified.identity().role, "core-release");
    assert_eq!(verified.identity().sequence, 44);
    assert_eq!(verified.assets().len(), 2);

    let mut unindexed = core_material();
    unindexed
        .source_files
        .insert("harness.db".into(), b"forbidden".to_vec());
    assert!(verify(unindexed)
        .unwrap_err()
        .to_string()
        .contains("unindexed"));

    let mut forbidden_ledger = core_material();
    let mut ledger: serde_json::Value = serde_json::from_slice(LEDGER).unwrap();
    for entry in ledger["entries"].as_array_mut().unwrap() {
        if entry["path"] == "docs/templates/decision.md" {
            entry["disposition"] = "forbidden-v0-operational".into();
        }
    }
    forbidden_ledger.path_ledger = serde_json::to_vec(&ledger).unwrap();
    assert!(verify(forbidden_ledger).is_err());
}

#[test]
fn strict_release_verifier_rejects_bridge_domain_and_rollback() {
    let bridge_material = ReleaseMaterial {
        index: BRIDGE_INDEX.to_vec(),
        signatures: BRIDGE_SIGNATURES.to_vec(),
        trust_bundle: BRIDGE_TRUST.to_vec(),
        trust_bundle_signatures: BRIDGE_TRUST_SIGNATURES.to_vec(),
        path_ledger: LEDGER.to_vec(),
        source_files: BTreeMap::new(),
    };
    let bridge_trust = ReleaseTrustInput {
        trusted_root: fixture_root("bridge"),
        trust_policy: TrustPolicy::TestFixtures,
        path_ledger_sha256: "b701a5c74ba3c65cd6a1f3e06b52c00823f0db315b72bb1d3ba78587903e53b0"
            .into(),
        freshness: ReleaseFreshness::FirstInstallMinimumSequence(7),
    };
    assert!(verify_with(bridge_material, bridge_trust).is_err());

    let mut rollback_trust = core_trust();
    rollback_trust.freshness = ReleaseFreshness::Existing {
        sequence: 45,
        digest: "a".repeat(64),
        rollback: None,
    };
    assert!(verify_with(core_material(), rollback_trust)
        .unwrap_err()
        .to_string()
        .contains("lacks root rollback authorization"));
}

#[test]
fn path_ledger_requires_an_independent_canonical_digest_pin() {
    let mut rewritten = core_material();
    let mut ledger: serde_json::Value = serde_json::from_slice(LEDGER).unwrap();
    ledger["entries"][0]["reason"] = serde_json::json!("attacker-rewritten-policy");
    rewritten.path_ledger = serde_json::to_vec(&ledger).unwrap();
    assert!(verify(rewritten)
        .unwrap_err()
        .to_string()
        .contains("independently pinned canonical digest"));

    let mut wrong_pin = core_trust();
    wrong_pin.path_ledger_sha256 = "0".repeat(64);
    assert!(verify_with(core_material(), wrong_pin).is_err());
}

#[test]
fn detached_signature_envelopes_require_canonical_jcs_bytes() {
    let mut release_envelope = core_material();
    let value: serde_json::Value = serde_json::from_slice(SIGNATURES).unwrap();
    release_envelope.signatures = serde_json::to_vec_pretty(&value).unwrap();
    assert!(verify(release_envelope)
        .unwrap_err()
        .to_string()
        .contains("not canonical JCS"));

    let mut bundle_envelope = core_material();
    let value: serde_json::Value = serde_json::from_slice(TRUST_SIGNATURES).unwrap();
    bundle_envelope.trust_bundle_signatures = serde_json::to_vec_pretty(&value).unwrap();
    assert!(verify(bundle_envelope)
        .unwrap_err()
        .to_string()
        .contains("not canonical JCS"));
}

#[test]
fn trust_bundle_requires_independent_anchor_and_detached_envelope() {
    let mut missing_envelope = core_material();
    missing_envelope.trust_bundle_signatures.clear();
    assert!(verify(missing_envelope).is_err());

    let mut wrong_pin = core_trust();
    wrong_pin.trusted_root.bundle_sha256 = "0".repeat(64);
    assert!(verify_with(core_material(), wrong_pin)
        .unwrap_err()
        .to_string()
        .contains("equal trust bundle sequence"));

    let mut self_issued = core_material();
    self_issued.trust_bundle = ROTATION_TRUST.to_vec();
    let mut pinned_trust = core_trust();
    pinned_trust.trusted_root = active_revocation_root();
    let mut envelope: serde_json::Value =
        serde_json::from_slice(ROTATION_TRUST_SIGNATURES).unwrap();
    let old_ids: BTreeMap<String, ()> = pinned_trust
        .trusted_root
        .keys
        .iter()
        .map(|key| (key.key_id.clone(), ()))
        .collect();
    envelope["signatures"]
        .as_array_mut()
        .unwrap()
        .retain(|signature| !old_ids.contains_key(signature["key_id"].as_str().unwrap()));
    self_issued.trust_bundle_signatures = serde_json::to_vec(&envelope).unwrap();
    assert!(verify_with(self_issued, pinned_trust)
        .unwrap_err()
        .to_string()
        .contains("threshold"));
}

#[test]
fn trust_lifecycle_rejects_stale_revoked_and_incomplete_rotation_states() {
    let mut stale_trust = core_trust();
    stale_trust.trusted_root = active_revocation_root();
    assert!(verify_with(core_material(), stale_trust)
        .unwrap_err()
        .to_string()
        .contains("below the active root"));

    let mut revoked_release = core_material();
    revoked_release.trust_bundle = REVOCATION_TRUST.to_vec();
    revoked_release.trust_bundle_signatures = REVOCATION_TRUST_SIGNATURES.to_vec();
    assert!(verify(revoked_release)
        .unwrap_err()
        .to_string()
        .contains("threshold"));

    let mut authenticated_revocation = phase1_core_material();
    authenticated_revocation.index = POST_REVOCATION_INDEX.to_vec();
    authenticated_revocation.signatures = POST_REVOCATION_SIGNATURES.to_vec();
    authenticated_revocation.trust_bundle = REVOCATION_TRUST.to_vec();
    authenticated_revocation.trust_bundle_signatures = REVOCATION_TRUST_SIGNATURES.to_vec();
    let mut authenticated_revocation_trust = core_trust();
    authenticated_revocation_trust.freshness = ReleaseFreshness::FirstInstallMinimumSequence(43);
    assert_eq!(
        verify_with(authenticated_revocation, authenticated_revocation_trust)
            .unwrap()
            .active_root_bundle()
            .0,
        2
    );

    let rotation_envelope: serde_json::Value =
        serde_json::from_slice(ROTATION_TRUST_SIGNATURES).unwrap();
    let active = active_revocation_root();
    for keep_old in [true, false] {
        let mut material = core_material();
        material.trust_bundle = ROTATION_TRUST.to_vec();
        let mut rotation_trust = core_trust();
        rotation_trust.trusted_root = active.clone();
        let old_ids: BTreeSet<&str> = active.keys.iter().map(|key| key.key_id.as_str()).collect();
        let mut envelope = rotation_envelope.clone();
        envelope["signatures"]
            .as_array_mut()
            .unwrap()
            .retain(|signature| {
                old_ids.contains(signature["key_id"].as_str().unwrap()) == keep_old
            });
        material.trust_bundle_signatures = serde_json::to_vec(&envelope).unwrap();
        assert!(verify_with(material, rotation_trust).is_err());
    }

    let mut valid_rotation = phase1_core_material();
    valid_rotation.index = POST_REVOCATION_INDEX.to_vec();
    valid_rotation.signatures = POST_REVOCATION_SIGNATURES.to_vec();
    valid_rotation.trust_bundle = ROTATION_TRUST.to_vec();
    valid_rotation.trust_bundle_signatures = ROTATION_TRUST_SIGNATURES.to_vec();
    let mut valid_rotation_trust = core_trust();
    valid_rotation_trust.trusted_root = active_revocation_root();
    valid_rotation_trust.freshness = ReleaseFreshness::FirstInstallMinimumSequence(43);
    let verified = verify_with(valid_rotation, valid_rotation_trust).unwrap();
    assert_eq!(verified.active_root_bundle().0, 3);

    let mut idempotent_rotation = phase1_core_material();
    idempotent_rotation.index = POST_REVOCATION_INDEX.to_vec();
    idempotent_rotation.signatures = POST_REVOCATION_SIGNATURES.to_vec();
    idempotent_rotation.trust_bundle = ROTATION_TRUST.to_vec();
    idempotent_rotation.trust_bundle_signatures = ROTATION_TRUST_SIGNATURES.to_vec();
    let mut idempotent_rotation_trust = core_trust();
    idempotent_rotation_trust.trusted_root = active_rotation_root();
    idempotent_rotation_trust.freshness = ReleaseFreshness::FirstInstallMinimumSequence(43);
    assert_eq!(
        verify_with(idempotent_rotation, idempotent_rotation_trust)
            .unwrap()
            .active_root_bundle()
            .0,
        3
    );
}

#[test]
fn rollback_requires_exact_active_root_authorization_and_retains_high_water() {
    let mut unauthorized = phase1_core_material();
    unauthorized.index = FREEZE_INDEX.to_vec();
    unauthorized.signatures = FREEZE_SIGNATURES.to_vec();
    assert!(verify(unauthorized).is_err());

    let mut authorized = phase1_core_material();
    authorized.index = FREEZE_INDEX.to_vec();
    authorized.signatures = FREEZE_SIGNATURES.to_vec();
    let mut authorized_trust = core_trust();
    authorized_trust.freshness = ReleaseFreshness::Existing {
        sequence: 42,
        digest: "dc70df55c0fbb3fcf548aa12cb13bcca0110e94a3b90300dfcc9522fd8de7bf7".into(),
        rollback: Some(RollbackMaterial {
            authorization: AUTHORIZED_ROLLBACK.to_vec(),
            signatures: AUTHORIZED_ROLLBACK_SIGNATURES.to_vec(),
        }),
    };
    let verified = verify_with(authorized, authorized_trust).unwrap();
    assert_eq!(verified.identity().sequence, 41);
    assert_eq!(verified.retained_release_high_water().0, 42);

    let mut noncanonical_rollback = phase1_core_material();
    noncanonical_rollback.index = FREEZE_INDEX.to_vec();
    noncanonical_rollback.signatures = FREEZE_SIGNATURES.to_vec();
    let mut noncanonical_trust = core_trust();
    let envelope: serde_json::Value =
        serde_json::from_slice(AUTHORIZED_ROLLBACK_SIGNATURES).unwrap();
    noncanonical_trust.freshness = ReleaseFreshness::Existing {
        sequence: 42,
        digest: "dc70df55c0fbb3fcf548aa12cb13bcca0110e94a3b90300dfcc9522fd8de7bf7".into(),
        rollback: Some(RollbackMaterial {
            authorization: AUTHORIZED_ROLLBACK.to_vec(),
            signatures: serde_json::to_vec_pretty(&envelope).unwrap(),
        }),
    };
    assert!(verify_with(noncanonical_rollback, noncanonical_trust)
        .unwrap_err()
        .to_string()
        .contains("not canonical JCS"));

    let mut wrong_root_sequence = phase1_core_material();
    wrong_root_sequence.index = FREEZE_INDEX.to_vec();
    wrong_root_sequence.signatures = FREEZE_SIGNATURES.to_vec();
    let mut wrong_root_trust = core_trust();
    wrong_root_trust.freshness = ReleaseFreshness::Existing {
        sequence: 42,
        digest: "dc70df55c0fbb3fcf548aa12cb13bcca0110e94a3b90300dfcc9522fd8de7bf7".into(),
        rollback: Some(RollbackMaterial {
            authorization: WRONG_ROOT_ROLLBACK.to_vec(),
            signatures: WRONG_ROOT_ROLLBACK_SIGNATURES.to_vec(),
        }),
    };
    assert!(verify_with(wrong_root_sequence, wrong_root_trust).is_err());
}

#[test]
fn offline_first_install_pin_is_mandatory_and_fixture_trust_is_test_only() {
    let mut exact_trust = core_trust();
    exact_trust.freshness = ReleaseFreshness::FirstInstallExactDigest(
        "0e2f88897e5c18ce8b1515a0c6de2f6bcfac97994fac3320965afd51ef1ddcdb".into(),
    );
    assert!(verify_with(core_material(), exact_trust).is_ok());

    let mut wrong_exact_trust = core_trust();
    wrong_exact_trust.freshness = ReleaseFreshness::FirstInstallExactDigest("0".repeat(64));
    assert!(verify_with(core_material(), wrong_exact_trust).is_err());

    let mut minimum_trust = core_trust();
    minimum_trust.freshness = ReleaseFreshness::FirstInstallMinimumSequence(45);
    assert!(verify_with(core_material(), minimum_trust).is_err());

    let mut production_trust = core_trust();
    production_trust.trust_policy = TrustPolicy::Production;
    assert!(verify_with(core_material(), production_trust)
        .unwrap_err()
        .to_string()
        .contains("production policy rejects test-fixture"));
}

fn active_revocation_root() -> TrustedRootState {
    let mut root = fixture_root("core");
    root.sequence = 2;
    root.bundle_sha256 = "2a48aa4ee218681e2bbbdcc3305ffe9685b01a596c0e1f49f6cffa73bbfa9984".into();
    root.revoked_key_ids = vec![
        "ed25519-sha256:feecf73dfe80f7c662b79bbfa20b22c27933682fa20ce8e3e5fd71575b472da3".into(),
    ];
    root
}

fn active_rotation_root() -> TrustedRootState {
    let bundle: serde_json::Value = serde_json::from_slice(ROTATION_TRUST).unwrap();
    TrustedRootState {
        trust_domain: bundle["trust_domain"].as_str().unwrap().into(),
        sequence: bundle["sequence"].as_u64().unwrap(),
        bundle_sha256: "500671020a6a2bbfa7e037770b19947cf63644c728906302a0a847bca49cc580".into(),
        threshold: bundle["roots"]["threshold"].as_u64().unwrap() as u8,
        keys: bundle["roots"]["keys"]
            .as_array()
            .unwrap()
            .iter()
            .map(|key| PinnedRootKey {
                key_id: key["key_id"].as_str().unwrap().into(),
                public_key: decode_base64_32(key["public_key_base64"].as_str().unwrap()),
                test_fixture: true,
            })
            .collect(),
        revoked_key_ids: bundle["revoked_key_ids"]
            .as_array()
            .unwrap()
            .iter()
            .map(|key| key.as_str().unwrap().into())
            .collect(),
    }
}

#[test]
fn authenticated_install_preview_is_deterministic_and_never_writes() {
    let filesystem = MemoryFileSystem::default();
    let manifests = JsonManifestPort;
    let release = MemoryRelease::core();
    let core = HarnessCore::new(&filesystem, &manifests, &release, &release);
    let command = Command::Install(MutatorOptions {
        preview: true,
        ..MutatorOptions::default()
    });
    let first = core.execute(&command);
    let second = core.execute(&command);
    assert_eq!(first, second);
    assert_eq!(first.exit_code, 0);
    assert_eq!(first.details.operations.as_ref().unwrap().len(), 2);
    assert_eq!(filesystem.files.len(), 0);

    let refused = core.execute(&Command::Install(MutatorOptions::default()));
    assert_eq!(refused.exit_code, 4);
    assert_eq!(filesystem.files.len(), 0);
}

#[test]
fn scaffold_requires_exact_authenticated_destination() {
    let filesystem = MemoryFileSystem::default();
    let manifests = JsonManifestPort;
    let release = MemoryRelease::core();
    let core = HarnessCore::new(&filesystem, &manifests, &release, &release);
    let accepted = core.execute(&Command::Scaffold(ScaffoldOptions {
        template: Some("decision-template".into()),
        destination: Some("docs/templates/decision.md".into()),
        mutation: MutatorOptions {
            preview: true,
            ..MutatorOptions::default()
        },
    }));
    assert_eq!(accepted.exit_code, 0);

    let rejected = core.execute(&Command::Scaffold(ScaffoldOptions {
        template: Some("decision-template".into()),
        destination: Some("docs/elsewhere.md".into()),
        mutation: MutatorOptions {
            preview: true,
            ..MutatorOptions::default()
        },
    }));
    assert_eq!(rejected.exit_code, 3);
    assert!(filesystem.files.is_empty());
}

#[test]
fn audit_is_deterministic_ready_or_unresolved_from_declared_bytes_only() {
    let ready_bytes = b"# Managed\n";
    let ready = MemoryFileSystem::default()
        .with("managed.md", ready_bytes)
        .with(
            ".harness/manifest.json",
            manifest("managed.md", ready_bytes, "active", &[]),
        );
    let release = MemoryRelease::core();
    let core = HarnessCore::new(&ready, &JsonManifestPort, &release, &release);
    let first = core.execute(&Command::Audit { json: true });
    let second = core.execute(&Command::Audit { json: true });
    assert_eq!(first, second);
    assert_eq!(first.exit_code, 0);
    assert_eq!(first.outcome, Outcome::Ready);
    assert_eq!(first.details.readiness, Readiness::Ready);

    let token = "REPOSITORY-HARNESS-UNRESOLVED(decision_template:test-command)";
    let unresolved_bytes = format!("# Managed\n{token}\n");
    let unresolved = MemoryFileSystem::default()
        .with("managed.md", unresolved_bytes.as_bytes())
        .with(
            ".harness/manifest.json",
            manifest(
                "managed.md",
                unresolved_bytes.as_bytes(),
                "unresolved",
                &[token],
            ),
        );
    let release = MemoryRelease::core();
    let core = HarnessCore::new(&unresolved, &JsonManifestPort, &release, &release);
    let result = core.execute(&Command::Audit { json: true });
    assert_eq!(result.exit_code, 2);
    assert_eq!(result.details.readiness, Readiness::Unresolved);
}

#[test]
fn status_classifies_structural_v0_and_mixed_state_without_a_sqlite_or_bridge_dependency() {
    let release = MemoryRelease::core();
    let legacy = MemoryFileSystem::default().with_compatibility(CompatibilityObservation {
        observed: true,
        legacy_artifact_present: true,
        archive_custody_present: false,
    });
    let result = HarnessCore::new(&legacy, &JsonManifestPort, &release, &release)
        .execute(&Command::Status { json: true });
    assert_eq!(result.exit_code, 0);
    assert_eq!(result.repository_mode, RepositoryMode::V0Legacy);

    let bytes = b"# Managed\n";
    let mixed = MemoryFileSystem::default()
        .with("managed.md", bytes)
        .with(
            ".harness/manifest.json",
            manifest("managed.md", bytes, "active", &[]),
        )
        .with_compatibility(CompatibilityObservation {
            observed: true,
            legacy_artifact_present: true,
            archive_custody_present: false,
        });
    let result = HarnessCore::new(&mixed, &JsonManifestPort, &release, &release)
        .execute(&Command::Status { json: true });
    assert_eq!(result.exit_code, 3);
    assert_eq!(result.repository_mode, RepositoryMode::MixedInvalid);
}

#[test]
fn archive_receipt_without_its_exact_manifest_and_payload_is_invalid() {
    let bytes = b"# Managed\n";
    let mut converted: serde_json::Value =
        serde_json::from_slice(&manifest("managed.md", bytes, "active", &[])).unwrap();
    converted["v0_archive_receipt"] = serde_json::json!({
        "schema": "repository-harness-v0-archive-receipt/v1",
        "archive_id": "v0-authentication-test",
        "bridge_release": "1.0.0",
        "archive_manifest_path": ".harness-v0-archive/v0-authentication-test/archive-manifest.json",
        "archive_manifest_sha256": "d".repeat(64),
        "export_sha256": "a".repeat(64),
        "standalone_backup_sha256": "b".repeat(64),
        "payload_sha256": "c".repeat(64),
        "source_sha256": "e".repeat(64),
        "confidentiality_mode": "encrypted-age-x25519",
        "custody_identity_sha256": "f".repeat(64)
    });
    let filesystem = MemoryFileSystem::default()
        .with("managed.md", bytes)
        .with(
            ".harness/manifest.json",
            serde_json::to_vec(&converted).unwrap(),
        )
        .with_compatibility(CompatibilityObservation {
            observed: true,
            legacy_artifact_present: false,
            archive_custody_present: true,
        });
    let release = MemoryRelease::core();
    let result = HarnessCore::new(&filesystem, &JsonManifestPort, &release, &release)
        .execute(&Command::Status { json: true });
    assert_eq!(result.exit_code, 3);
    assert!(result
        .details
        .violations
        .contains(&"v0-archive-receipt-invalid".to_owned()));
}

#[test]
fn manifest_operational_fields_and_digest_drift_are_invalid() {
    let bytes = b"# Managed\n";
    let mut value: serde_json::Value =
        serde_json::from_slice(&manifest("managed.md", bytes, "active", &[])).unwrap();
    value["tasks"] = serde_json::json!([]);
    let forbidden = MemoryFileSystem::default().with("managed.md", bytes).with(
        ".harness/manifest.json",
        serde_json::to_vec(&value).unwrap(),
    );
    let release = MemoryRelease::core();
    let core = HarnessCore::new(&forbidden, &JsonManifestPort, &release, &release);
    assert_eq!(core.execute(&Command::Audit { json: true }).exit_code, 3);

    let drift = MemoryFileSystem::default()
        .with("managed.md", b"changed bytes")
        .with(
            ".harness/manifest.json",
            manifest("managed.md", bytes, "active", &[]),
        );
    let release = MemoryRelease::core();
    let core = HarnessCore::new(&drift, &JsonManifestPort, &release, &release);
    assert_eq!(core.execute(&Command::Audit { json: true }).exit_code, 3);
}

#[test]
fn every_mutator_preview_refuses_corrupt_existing_manifest_state() {
    let bytes = b"# Managed\n";
    let mut corrupt: serde_json::Value =
        serde_json::from_slice(&manifest("managed.md", bytes, "active", &[])).unwrap();
    corrupt["tasks"] = serde_json::json!([]);
    let filesystem = MemoryFileSystem::default().with("managed.md", bytes).with(
        ".harness/manifest.json",
        serde_json::to_vec(&corrupt).unwrap(),
    );
    let release = MemoryRelease::core();
    let core = HarnessCore::new(&filesystem, &JsonManifestPort, &release, &release);
    let commands = [
        Command::Install(MutatorOptions {
            preview: true,
            ..MutatorOptions::default()
        }),
        Command::Update(MutatorOptions {
            preview: true,
            ..MutatorOptions::default()
        }),
        Command::Scaffold(ScaffoldOptions {
            template: Some("decision-template".into()),
            destination: Some("docs/templates/decision.md".into()),
            mutation: MutatorOptions {
                preview: true,
                ..MutatorOptions::default()
            },
        }),
    ];
    for command in commands {
        let result = core.execute(&command);
        assert_eq!(
            result.exit_code,
            3,
            "{} planned around corruption",
            command.name()
        );
        assert!(result.details.operations.is_none());
    }
}

#[test]
fn update_audits_existing_state_and_binds_payload_transition() {
    let unresolved_token = "REPOSITORY-HARNESS-UNRESOLVED(decision_template:test-command)";
    let unresolved = format!("# Managed\n{unresolved_token}\n");
    let valid = MemoryFileSystem::default()
        .with("managed.md", unresolved.as_bytes())
        .with(
            ".harness/manifest.json",
            manifest(
                "managed.md",
                unresolved.as_bytes(),
                "unresolved",
                &[unresolved_token],
            ),
        );
    let release = MemoryRelease::core();
    let core = HarnessCore::new(&valid, &JsonManifestPort, &release, &release);
    let preview = core.execute(&Command::Update(MutatorOptions {
        preview: true,
        ..MutatorOptions::default()
    }));
    assert_eq!(preview.exit_code, 0);
    assert!(preview.details.operations.is_some());
    assert_eq!(preview.details.readiness, Readiness::Unresolved);
    assert!(preview
        .notices
        .iter()
        .any(|notice| notice.code == "role-unresolved"));

    let mut mismatched: serde_json::Value =
        serde_json::from_slice(&manifest("managed.md", b"# Managed\n", "active", &[])).unwrap();
    mismatched["payload"]["index_sha256"] = serde_json::Value::String("0".repeat(64));
    let mismatch_filesystem = MemoryFileSystem::default()
        .with("managed.md", b"# Managed\n")
        .with(
            ".harness/manifest.json",
            serde_json::to_vec(&mismatched).unwrap(),
        );
    let release = MemoryRelease::core();
    let core = HarnessCore::new(&mismatch_filesystem, &JsonManifestPort, &release, &release);
    let rejected = core.execute(&Command::Update(MutatorOptions {
        preview: true,
        ..MutatorOptions::default()
    }));
    assert_eq!(rejected.exit_code, 3);
    assert!(rejected
        .details
        .violations
        .contains(&"payload-transition-equal-sequence-digest-mismatch".into()));
}

#[test]
fn runtime_manifest_validation_matches_closed_schema_constraints() {
    let bytes = b"# Managed\n";
    let base: serde_json::Value =
        serde_json::from_slice(&manifest("managed.md", bytes, "active", &[])).unwrap();
    let mut cases = Vec::new();
    for (pointer, invalid_value) in [
        (
            "/schema",
            serde_json::json!("repository-harness-manifest/v2"),
        ),
        ("/roles/0/role", serde_json::json!("Bad-Role")),
        ("/roles/0/asset", serde_json::json!("_asset")),
        ("/roles/0/base_sha256", serde_json::json!("g".repeat(64))),
        ("/roles/0/current_sha256", serde_json::json!("A".repeat(64))),
        ("/payload/sequence", serde_json::json!(0)),
        (
            "/payload/sequence",
            serde_json::json!(9_007_199_254_740_992_u64),
        ),
        ("/payload/index_sha256", serde_json::json!("1".repeat(63))),
        (
            "/payload/trust_domain",
            serde_json::json!("repository-harness-bridge"),
        ),
        ("/payload/role", serde_json::json!("bridge-release")),
    ] {
        let mut value = base.clone();
        *value.pointer_mut(pointer).unwrap() = invalid_value;
        cases.push(value);
    }
    let mut unknown = base.clone();
    unknown["roles"][0]["unexpected"] = serde_json::json!(true);
    cases.push(unknown);
    let mut unknown_top = base.clone();
    unknown_top["unexpected"] = serde_json::json!(true);
    cases.push(unknown_top);
    for object in ["compatibility", "payload"] {
        let mut unknown_nested = base.clone();
        unknown_nested[object]["unexpected"] = serde_json::json!(true);
        cases.push(unknown_nested);
    }
    let mut bad_marker = base.clone();
    bad_marker["roles"][0]["marker"] = serde_json::json!("bad_marker");
    cases.push(bad_marker);
    for field in ["template", "template_release", "base_sha256", "marker"] {
        let mut null_optional = base.clone();
        null_optional["roles"][0][field] = serde_json::Value::Null;
        cases.push(null_optional);
    }
    let mut null_receipt = base.clone();
    null_receipt["v0_archive_receipt"] = serde_json::Value::Null;
    cases.push(null_receipt);
    let mut archive_base = base.clone();
    archive_base["v0_archive_receipt"] = serde_json::json!({
        "schema": "repository-harness-v0-archive-receipt/v1",
        "archive_id": "archive-1",
        "bridge_release": "1.0.0",
        "archive_manifest_path": ".harness-v0-archive/archive-1/archive-manifest.json",
        "archive_manifest_sha256": "3".repeat(64),
        "export_sha256": "0".repeat(64),
        "standalone_backup_sha256": "1".repeat(64),
        "payload_sha256": "2".repeat(64),
        "source_sha256": "4".repeat(64),
        "confidentiality_mode": "encrypted-age-x25519",
        "custody_identity_sha256": "5".repeat(64)
    });
    for (pointer, invalid_value) in [
        (
            "/v0_archive_receipt/schema",
            serde_json::json!("repository-harness-v0-archive-receipt/v2"),
        ),
        (
            "/v0_archive_receipt/archive_id",
            serde_json::json!("Bad_ID"),
        ),
        (
            "/v0_archive_receipt/archive_manifest_path",
            serde_json::json!(".harness/legacy/archive-manifest.json"),
        ),
        (
            "/v0_archive_receipt/archive_manifest_sha256",
            serde_json::json!("z".repeat(64)),
        ),
        (
            "/v0_archive_receipt/export_sha256",
            serde_json::json!("z".repeat(64)),
        ),
        (
            "/v0_archive_receipt/standalone_backup_sha256",
            serde_json::json!("1".repeat(63)),
        ),
        (
            "/v0_archive_receipt/payload_sha256",
            serde_json::json!("A".repeat(64)),
        ),
        (
            "/v0_archive_receipt/source_sha256",
            serde_json::json!("A".repeat(64)),
        ),
        (
            "/v0_archive_receipt/confidentiality_mode",
            serde_json::json!("unknown"),
        ),
        (
            "/v0_archive_receipt/custody_identity_sha256",
            serde_json::json!("5".repeat(63)),
        ),
    ] {
        let mut archived = archive_base.clone();
        *archived.pointer_mut(pointer).unwrap() = invalid_value;
        cases.push(archived);
    }
    let mut unknown_receipt = archive_base;
    unknown_receipt["v0_archive_receipt"]["unexpected"] = serde_json::json!(true);
    cases.push(unknown_receipt);

    for value in cases {
        let filesystem = MemoryFileSystem::default().with(
            ".harness/manifest.json",
            serde_json::to_vec(&value).unwrap(),
        );
        assert!(JsonManifestPort.load(&filesystem).is_err());
    }

    let mut interoperable_maximum = base;
    interoperable_maximum["payload"]["sequence"] = serde_json::json!(9_007_199_254_740_991_u64);
    let filesystem = MemoryFileSystem::default().with(
        ".harness/manifest.json",
        serde_json::to_vec(&interoperable_maximum).unwrap(),
    );
    assert!(JsonManifestPort.load(&filesystem).is_ok());
}

#[test]
fn commonmark_links_and_anchors_are_structural_without_false_code_links() {
    let main = br#"# Main
[inline](a\(b\).md "Inline title")
[reference][target]
![image](../images/pic.png 'Image title')
[external](urn:ietf:rfc:3986)
[network-path](//example.invalid/spec)
[encoded-hash](a%23b.md)
`[code](missing-code.md)`
[malformed](missing-malformed.md

[target]: ref.md#target-heading "Reference title"
"#;
    let mut value: serde_json::Value =
        serde_json::from_slice(&manifest("docs/main.md", main, "active", &[])).unwrap();
    value["roles"][0]["asset"] = serde_json::json!("main-document");
    let filesystem = MemoryFileSystem::default()
        .with("docs/main.md", main)
        .with("docs/a(b).md", b"# Inline\n")
        .with("docs/a#b.md", b"# Encoded Hash\n")
        .with("docs/ref.md", b"# Target Heading\n")
        .with("images/pic.png", b"image bytes")
        .with(
            ".harness/manifest.json",
            serde_json::to_vec(&value).unwrap(),
        );
    let release = MemoryRelease::core();
    let core = HarnessCore::new(&filesystem, &JsonManifestPort, &release, &release);
    let result = core.execute(&Command::Audit { json: true });
    assert_eq!(result.exit_code, 0, "{:?}", result.details.violations);

    let drive = b"# Main\n[drive](C:/Users/alice/.ssh/id_rsa)\n";
    let mut drive_value: serde_json::Value =
        serde_json::from_slice(&manifest("docs/main.md", drive, "active", &[])).unwrap();
    drive_value["roles"][0]["asset"] = serde_json::json!("main-document");
    let filesystem = MemoryFileSystem::default()
        .with("docs/main.md", drive)
        .with(
            ".harness/manifest.json",
            serde_json::to_vec(&drive_value).unwrap(),
        );
    let core = HarnessCore::new(&filesystem, &JsonManifestPort, &release, &release);
    let result = core.execute(&Command::Audit { json: true });
    assert_eq!(result.exit_code, 3);
    assert!(result
        .details
        .violations
        .contains(&"unsafe-link:docs/main.md:C:/Users/alice/.ssh/id_rsa".into()));
}

#[test]
fn same_document_commonmark_fragments_validate_percent_unicode_and_duplicates() {
    let valid = "# Same Document\n[local](#same-document)\n## Café\n[unicode](#caf%C3%A9)\n## Duplicate\n## Duplicate\n[second](#duplicate-1)\n## Straße\n[street](#stra%C3%9Fe)\n## build--test\n[repeated-hyphen](#build--test)\n## -edge-\n[edge-hyphens](#-edge-)\n";
    let filesystem = MemoryFileSystem::default()
        .with("docs/main.md", valid.as_bytes())
        .with(
            ".harness/manifest.json",
            manifest("docs/main.md", valid.as_bytes(), "active", &[]),
        );
    let release = MemoryRelease::core();
    let core = HarnessCore::new(&filesystem, &JsonManifestPort, &release, &release);
    assert_eq!(core.execute(&Command::Audit { json: true }).exit_code, 0);

    let invalid = "# Same Document\n[missing](#does-not-exist)\n";
    let filesystem = MemoryFileSystem::default()
        .with("docs/main.md", invalid.as_bytes())
        .with(
            ".harness/manifest.json",
            manifest("docs/main.md", invalid.as_bytes(), "active", &[]),
        );
    let core = HarnessCore::new(&filesystem, &JsonManifestPort, &release, &release);
    let result = core.execute(&Command::Audit { json: true });
    assert_eq!(result.exit_code, 3);
    assert!(result
        .details
        .violations
        .contains(&"missing-anchor:docs/main.md:does-not-exist".into()));
}

#[test]
fn target_owned_prose_is_not_link_audited_or_auto_patchable() {
    let contents = b"# Target Owned\n[private prose](missing-target.md)\n";
    let mut value: serde_json::Value =
        serde_json::from_slice(&manifest("README.md", contents, "active", &[])).unwrap();
    value["roles"][0]["ownership"] = serde_json::json!("target-owned");
    value["roles"][0]["update_policy"] = serde_json::json!("never-auto-patch");
    let filesystem = MemoryFileSystem::default()
        .with("README.md", contents)
        .with(
            ".harness/manifest.json",
            serde_json::to_vec(&value).unwrap(),
        );
    let release = MemoryRelease::core();
    let core = HarnessCore::new(&filesystem, &JsonManifestPort, &release, &release);
    assert_eq!(core.execute(&Command::Audit { json: true }).exit_code, 0);
}

#[test]
fn extra_closing_marker_and_control_character_output_injection_are_invalid() {
    let text = b"<!-- repository-harness:v1:begin:agent-map -->\nmanaged\n<!-- repository-harness:v1:end:agent-map -->\n<!-- repository-harness:v1:end:other -->\n";
    let mut value: serde_json::Value =
        serde_json::from_slice(&manifest("managed.md", text, "active", &[])).unwrap();
    value["roles"][0]["ownership"] = serde_json::json!("managed-block");
    value["roles"][0]["marker"] = serde_json::json!("agent-map");
    let filesystem = MemoryFileSystem::default().with("managed.md", text).with(
        ".harness/manifest.json",
        serde_json::to_vec(&value).unwrap(),
    );
    let release = MemoryRelease::core();
    let core = HarnessCore::new(&filesystem, &JsonManifestPort, &release, &release);
    let result = core.execute(&Command::Audit { json: false });
    assert_eq!(result.exit_code, 3);
    assert!(result
        .details
        .violations
        .iter()
        .any(|violation| violation.starts_with("nested-or-extra-managed-marker")));

    let injected_manifest = manifest("evil\ninjected.md", b"x", "active", &[]);
    let injected = MemoryFileSystem::default()
        .with(".harness/manifest.json", injected_manifest)
        .with("evil\ninjected.md", b"x");
    let release = MemoryRelease::core();
    let core = HarnessCore::new(&injected, &JsonManifestPort, &release, &release);
    let envelope = core.execute(&Command::Audit { json: false });
    let human = harness_core::interface::render(&envelope, false).unwrap();
    assert!(!human.contains("evil\ninjected"));
    assert!(human.contains("evil\\u{a}injected"));

    let malformed_token = "REPOSITORY-HARNESS-UNRESOLVED(decision_template:Bad:marker)";
    let malformed_bytes = format!("# Managed\n{malformed_token}\n");
    let malformed = MemoryFileSystem::default()
        .with("managed.md", malformed_bytes.as_bytes())
        .with(
            ".harness/manifest.json",
            manifest(
                "managed.md",
                malformed_bytes.as_bytes(),
                "unresolved",
                &[malformed_token],
            ),
        );
    let release = MemoryRelease::core();
    let core = HarnessCore::new(&malformed, &JsonManifestPort, &release, &release);
    assert_eq!(core.execute(&Command::Audit { json: true }).exit_code, 3);
}

struct IoFileSystem;

impl FileSystemPort for IoFileSystem {
    fn read_declared(&self, path: &str) -> Result<Vec<u8>, PortError> {
        Err(PortError::Io {
            path: path.into(),
            message: "deterministic-read-failure".into(),
        })
    }

    fn exists_declared(&self, path: &str) -> Result<bool, PortError> {
        Err(PortError::Io {
            path: path.into(),
            message: "deterministic-exists-failure".into(),
        })
    }

    fn validate_snapshot(&self) -> Result<(), PortError> {
        Ok(())
    }
}

#[test]
fn io_errors_map_to_exit_74_without_claiming_validated_invalid_state() {
    let release = MemoryRelease::core();
    let core = HarnessCore::new(&IoFileSystem, &JsonManifestPort, &release, &release);
    let result = core.execute(&Command::Audit { json: true });
    assert_eq!(result.exit_code, 74);
    assert_eq!(result.outcome, Outcome::Unsupported);
    assert_eq!(
        result.repository_mode,
        harness_core::domain::RepositoryMode::Absent
    );
    assert!(result.details.violations.is_empty());
    assert_eq!(result.notices[0].code, "io-failure");
}

struct ChangedSnapshotFileSystem(MemoryFileSystem);

impl FileSystemPort for ChangedSnapshotFileSystem {
    fn read_declared(&self, path: &str) -> Result<Vec<u8>, PortError> {
        self.0.read_declared(path)
    }

    fn exists_declared(&self, path: &str) -> Result<bool, PortError> {
        self.0.exists_declared(path)
    }

    fn validate_snapshot(&self) -> Result<(), PortError> {
        Err(PortError::Changed(".".into()))
    }
}

#[test]
fn changed_snapshot_uses_documented_read_only_exit_74() {
    let bytes = b"# Managed\n";
    let filesystem =
        ChangedSnapshotFileSystem(MemoryFileSystem::default().with("managed.md", bytes).with(
            ".harness/manifest.json",
            manifest("managed.md", bytes, "active", &[]),
        ));
    let release = MemoryRelease::core();
    let core = HarnessCore::new(&filesystem, &JsonManifestPort, &release, &release);
    for command in [
        Command::Status { json: true },
        Command::Audit { json: true },
    ] {
        let result = core.execute(&command);
        assert_eq!(result.exit_code, 74);
        assert_eq!(result.outcome, Outcome::Unsupported);
        assert_eq!(result.notices[0].code, "filesystem-snapshot-changed");
    }
}

struct PanicFileSystem;

impl FileSystemPort for PanicFileSystem {
    fn read_declared(&self, _path: &str) -> Result<Vec<u8>, PortError> {
        panic!("version touched repository state")
    }

    fn exists_declared(&self, _path: &str) -> Result<bool, PortError> {
        panic!("version touched repository state")
    }

    fn validate_snapshot(&self) -> Result<(), PortError> {
        panic!("version touched repository state")
    }
}

#[test]
fn version_is_repository_and_release_independent() {
    let release = MemoryRelease::core();
    let core = HarnessCore::new(&PanicFileSystem, &JsonManifestPort, &release, &release);
    let version = core.execute(&Command::Version { json: true });
    assert_eq!(version.exit_code, 0);
    assert_eq!(version.command, "version");
}
