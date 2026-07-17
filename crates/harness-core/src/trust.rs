//! Strict Phase 1 trust lifecycle and path-ledger verification for core payloads.

use std::collections::{BTreeMap, BTreeSet};

use curve25519_dalek::edwards::CompressedEdwardsY;
use curve25519_dalek::scalar::Scalar;
use ed25519_dalek::{Signature, VerifyingKey};
use semver::Version;
use serde::Deserialize;

use crate::domain::{Disposition, PayloadIdentity};
use crate::path::{validate_exact_destination, validate_relative};
use crate::ports::{
    PinnedRootKey, PortError, ReleaseFreshness, ReleaseMaterial, ReleaseTrustInput,
    RollbackMaterial, TrustPolicy, TrustedRootState,
};
use crate::strict_json::{canonical, digest, hex_sha256, parse, signed_message};

const CORE_DOMAIN: &str = "repository-harness-core";
const CORE_ROOT_ROLE: &str = "core-root";
const CORE_ROTATION_ROLE: &str = "core-root-rotation";
const CORE_RELEASE_ROLE: &str = "core-release";
const CORE_INDEX_SCHEMA: &str = "repository-harness-payload-index/v1";
const CORE_INDEX_SIGNATURE_DOMAIN: &str = "repository-harness-payload-index-v1";
const CORE_BUNDLE_SIGNATURE_DOMAIN: &str = "repository-harness-core-trust-bundle-v1";
const CORE_ROLLBACK_SIGNATURE_DOMAIN: &str = "repository-harness-core-rollback-authorization-v1";
const TEST_BUNDLE_NOTICE: &str = "UNSAFE-TEST-ONLY-NOT-FOR-RELEASE";

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct VerifiedRelease {
    identity: PayloadIdentity,
    release: String,
    assets: Vec<VerifiedAsset>,
    active_root_bundle: (u64, String),
    retained_release_high_water: (u64, String),
}

impl VerifiedRelease {
    pub fn identity(&self) -> &PayloadIdentity {
        &self.identity
    }

    pub fn release(&self) -> &str {
        &self.release
    }

    pub fn assets(&self) -> &[VerifiedAsset] {
        &self.assets
    }

    pub fn active_root_bundle(&self) -> &(u64, String) {
        &self.active_root_bundle
    }

    pub fn retained_release_high_water(&self) -> &(u64, String) {
        &self.retained_release_high_water
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct VerifiedAsset {
    pub id: String,
    pub source: String,
    pub destination: String,
    pub sha256: String,
    pub disposition: Disposition,
    pub role: Option<String>,
    pub template: Option<String>,
    pub bytes: Vec<u8>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct PayloadIndex {
    schema: String,
    trust_domain: String,
    role: String,
    sequence: u64,
    release: String,
    source_commit: String,
    tag: String,
    assets: Vec<PayloadAsset>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct PayloadAsset {
    id: String,
    source: String,
    sha256: String,
    bytes: u64,
    disposition: String,
    destination: String,
    role: Option<String>,
    template: Option<String>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct SignatureEnvelope {
    schema: String,
    trust_domain: String,
    role: String,
    sequence: u64,
    payload_sha256: String,
    signatures: Vec<DetachedSignature>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct DetachedSignature {
    key_id: String,
    algorithm: String,
    signature: String,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct TrustBundle {
    schema: String,
    trust_domain: String,
    sequence: u64,
    previous_bundle_sha256: Option<String>,
    test_fixture_notice: Option<String>,
    roots: KeyRole,
    roles: Vec<NamedKeyRole>,
    revoked_key_ids: Vec<String>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct KeyRole {
    threshold: u8,
    keys: Vec<PublicKey>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct NamedKeyRole {
    name: String,
    threshold: u8,
    keys: Vec<PublicKey>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct PublicKey {
    key_id: String,
    algorithm: String,
    public_key_base64: String,
    test_fixture: Option<bool>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct RollbackAuthorization {
    schema: String,
    trust_domain: String,
    root_bundle_sequence: u64,
    role: String,
    authorized_sequence: u64,
    authorized_digest: String,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct PathLedger {
    schema: String,
    allowed_dispositions: Vec<String>,
    entries: Vec<LedgerEntry>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct LedgerEntry {
    path: String,
    surface: String,
    disposition: String,
    reason: String,
}

struct AuthenticatedBundle {
    sequence: u64,
    digest: String,
    roots: BTreeMap<String, [u8; 32]>,
    release_keys: BTreeMap<String, [u8; 32]>,
    revoked: BTreeSet<String>,
}

pub fn verify_release(
    material: ReleaseMaterial,
    trust: ReleaseTrustInput,
) -> Result<VerifiedRelease, PortError> {
    let index_value = parse(&material.index).map_err(invalid)?;
    let index_envelope_value = parse_canonical_envelope(&material.signatures)?;
    let bundle_value = parse(&material.trust_bundle).map_err(invalid)?;
    let bundle_envelope_value = parse_canonical_envelope(&material.trust_bundle_signatures)?;
    let ledger_value = parse(&material.path_ledger).map_err(invalid)?;
    reject_schema_nulls(&index_value, &bundle_value)?;
    let index: PayloadIndex = serde_json::from_value(index_value.clone()).map_err(invalid)?;
    let index_envelope: SignatureEnvelope =
        serde_json::from_value(index_envelope_value).map_err(invalid)?;
    let bundle: TrustBundle = serde_json::from_value(bundle_value.clone()).map_err(invalid)?;
    let bundle_envelope: SignatureEnvelope =
        serde_json::from_value(bundle_envelope_value).map_err(invalid)?;
    let ledger_digest = digest(&ledger_value).map_err(invalid)?;
    let ledger: PathLedger = serde_json::from_value(ledger_value).map_err(invalid)?;
    if !is_sha256(&trust.path_ledger_sha256) || ledger_digest != trust.path_ledger_sha256 {
        return Err(invalid(
            "Phase 1 path ledger does not match the independently pinned canonical digest",
        ));
    }

    validate_index_identity(&index)?;
    let authenticated_bundle = authenticate_bundle(
        &bundle,
        &bundle_value,
        &bundle_envelope,
        &trust.trusted_root,
        trust.trust_policy,
    )?;
    verify_envelope(
        &index_value,
        &index_envelope,
        CORE_INDEX_SIGNATURE_DOMAIN,
        CORE_RELEASE_ROLE,
        index.sequence,
        &authenticated_bundle.release_keys,
        2,
        &authenticated_bundle.revoked,
    )?;
    let index_sha256 = digest(&index_value).map_err(invalid)?;
    let retained_release_high_water = authorize_release_freshness(
        &trust.freshness,
        &index,
        &index_sha256,
        &authenticated_bundle,
    )?;
    validate_ledger_header(&ledger)?;

    let indexed_sources: BTreeSet<&str> = index
        .assets
        .iter()
        .map(|asset| asset.source.as_str())
        .collect();
    let supplied_sources: BTreeSet<&str> =
        material.source_files.keys().map(String::as_str).collect();
    if indexed_sources.len() != index.assets.len() || indexed_sources != supplied_sources {
        return Err(invalid(
            "release source set contains a duplicate, missing, or unindexed path",
        ));
    }

    let mut ids = BTreeSet::new();
    let mut source_collisions = BTreeSet::new();
    let mut destinations = BTreeSet::new();
    let mut assets = Vec::new();
    for asset in index.assets {
        if !is_lower_kebab(&asset.id) || !ids.insert(asset.id.clone()) {
            return Err(invalid("payload asset id is invalid or duplicated"));
        }
        if !is_sha256(&asset.sha256)
            || asset
                .role
                .as_deref()
                .is_some_and(|role| !is_lower_snake(role))
            || asset
                .template
                .as_deref()
                .is_some_and(|template| !is_lower_kebab(template))
        {
            return Err(invalid(
                "payload asset fields are outside the closed identifier rules",
            ));
        }
        let source_collision = validate_relative(&asset.source, false)?;
        if !source_collisions.insert(source_collision) {
            return Err(invalid("payload source path collision"));
        }
        let destination_collision = validate_exact_destination(&asset.destination)?;
        if !destinations.insert(destination_collision) {
            return Err(invalid("payload destination collision"));
        }
        let disposition = match asset.disposition.as_str() {
            "managed-v1" => Disposition::ManagedV1,
            "optional-v1" => Disposition::OptionalV1,
            _ => return Err(invalid("core payload contains a non-core disposition")),
        };
        let matches: Vec<&LedgerEntry> = ledger
            .entries
            .iter()
            .filter(|entry| entry.path == asset.source)
            .collect();
        if matches.len() != 1 || matches[0].disposition != asset.disposition {
            return Err(invalid(
                "payload path is missing or disagrees with the Phase 1 ledger",
            ));
        }
        if matches[0].surface.trim().is_empty() || matches[0].reason.trim().is_empty() {
            return Err(invalid("payload ledger entry is incomplete"));
        }
        let bytes = material
            .source_files
            .get(&asset.source)
            .expect("source set equality established")
            .clone();
        if bytes.len() as u64 != asset.bytes || hex_sha256(&bytes) != asset.sha256 {
            return Err(invalid(
                "payload source digest or byte length differs from its index",
            ));
        }
        assets.push(VerifiedAsset {
            id: asset.id,
            source: asset.source,
            destination: asset.destination,
            sha256: asset.sha256,
            disposition,
            role: asset.role,
            template: asset.template,
            bytes,
        });
    }
    assets
        .sort_by(|left, right| (&left.destination, &left.id).cmp(&(&right.destination, &right.id)));
    Ok(VerifiedRelease {
        identity: PayloadIdentity {
            trust_domain: CORE_DOMAIN.into(),
            role: CORE_RELEASE_ROLE.into(),
            sequence: index.sequence,
            index_sha256,
        },
        release: index.release,
        assets,
        active_root_bundle: (authenticated_bundle.sequence, authenticated_bundle.digest),
        retained_release_high_water,
    })
}

fn reject_schema_nulls(
    index: &serde_json::Value,
    bundle: &serde_json::Value,
) -> Result<(), PortError> {
    if let Some(assets) = index.get("assets").and_then(serde_json::Value::as_array) {
        for (position, asset) in assets.iter().enumerate() {
            for field in ["role", "template"] {
                if asset.get(field).is_some_and(serde_json::Value::is_null) {
                    return Err(invalid(format!(
                        "payload assets[{position}].{field} must be a string when present"
                    )));
                }
            }
        }
    }
    for field in ["previous_bundle_sha256", "test_fixture_notice"] {
        if bundle.get(field).is_some_and(serde_json::Value::is_null) {
            return Err(invalid(format!(
                "trust bundle {field} must be a string when present"
            )));
        }
    }
    let root_keys = bundle
        .get("roots")
        .and_then(|roots| roots.get("keys"))
        .and_then(serde_json::Value::as_array)
        .into_iter()
        .flatten();
    let role_keys = bundle
        .get("roles")
        .and_then(serde_json::Value::as_array)
        .into_iter()
        .flatten()
        .filter_map(|role| role.get("keys").and_then(serde_json::Value::as_array))
        .flatten();
    for key in root_keys.chain(role_keys) {
        if key
            .get("test_fixture")
            .is_some_and(serde_json::Value::is_null)
        {
            return Err(invalid(
                "trust bundle key test_fixture must be boolean when present",
            ));
        }
    }
    Ok(())
}

fn authenticate_bundle(
    bundle: &TrustBundle,
    bundle_value: &serde_json::Value,
    envelope: &SignatureEnvelope,
    trusted: &TrustedRootState,
    policy: TrustPolicy,
) -> Result<AuthenticatedBundle, PortError> {
    validate_trusted_root(trusted, policy)?;
    if bundle.schema != "repository-harness-trust-bundle/v1"
        || bundle.trust_domain != CORE_DOMAIN
        || bundle.sequence == 0
        || bundle.roots.threshold != 2
        || bundle.roots.keys.len() != 3
        || bundle.roles.len() != 1
        || bundle
            .previous_bundle_sha256
            .as_ref()
            .is_some_and(|value| !is_sha256(value))
    {
        return Err(invalid("trust bundle identity or shape is invalid"));
    }
    match policy {
        TrustPolicy::Production => {
            if bundle.test_fixture_notice.is_some() {
                return Err(invalid(
                    "production policy rejects test-fixture trust bundles",
                ));
            }
        }
        TrustPolicy::TestFixtures => {
            if bundle.test_fixture_notice.as_deref() != Some(TEST_BUNDLE_NOTICE) {
                return Err(invalid(
                    "test-fixture trust policy requires the unsafe bundle notice",
                ));
            }
        }
    }
    let role = &bundle.roles[0];
    if role.name != CORE_RELEASE_ROLE || role.threshold != 2 || role.keys.len() != 3 {
        return Err(invalid("core release role is not exactly 2-of-3"));
    }
    let roots = decode_keys(&bundle.roots.keys, policy)?;
    let release_keys = decode_keys(&role.keys, policy)?;
    if roots.keys().any(|key| release_keys.contains_key(key)) {
        return Err(invalid("root and core release keys overlap"));
    }
    let revoked: BTreeSet<String> = bundle.revoked_key_ids.iter().cloned().collect();
    if revoked.len() != bundle.revoked_key_ids.len() || revoked.iter().any(|key| !is_key_id(key)) {
        return Err(invalid("trust bundle revocation list is invalid"));
    }
    let digest = digest(bundle_value).map_err(invalid)?;
    if bundle.sequence < trusted.sequence {
        return Err(invalid(
            "trust bundle sequence is below the active root state",
        ));
    }
    if bundle.sequence == trusted.sequence && digest != trusted.bundle_sha256 {
        return Err(invalid(
            "equal trust bundle sequence has a different canonical digest",
        ));
    }
    if bundle.sequence > trusted.sequence
        && bundle.previous_bundle_sha256.as_deref() != Some(&trusted.bundle_sha256)
    {
        return Err(invalid(
            "new trust bundle does not chain the active bundle digest",
        ));
    }

    let trusted_revoked: BTreeSet<String> = trusted.revoked_key_ids.iter().cloned().collect();
    let trusted_keys = pinned_key_map(&trusted.keys)?;
    if bundle.sequence == trusted.sequence {
        if trusted_keys != roots {
            return Err(invalid(
                "pinned active roots differ from the equal-sequence bundle",
            ));
        }
        if envelope.role != CORE_ROOT_ROLE && envelope.role != CORE_ROTATION_ROLE {
            return Err(invalid("idempotent trust bundle has an invalid root role"));
        }
        verify_envelope(
            bundle_value,
            envelope,
            CORE_BUNDLE_SIGNATURE_DOMAIN,
            &envelope.role,
            bundle.sequence,
            &trusted_keys,
            trusted.threshold,
            &trusted_revoked,
        )?;
    } else {
        let rotation = trusted_keys != roots;
        let role_name = if rotation {
            CORE_ROTATION_ROLE
        } else {
            CORE_ROOT_ROLE
        };
        verify_envelope(
            bundle_value,
            envelope,
            CORE_BUNDLE_SIGNATURE_DOMAIN,
            role_name,
            bundle.sequence,
            &trusted_keys,
            trusted.threshold,
            &trusted_revoked,
        )?;
        if rotation {
            verify_envelope(
                bundle_value,
                envelope,
                CORE_BUNDLE_SIGNATURE_DOMAIN,
                CORE_ROTATION_ROLE,
                bundle.sequence,
                &roots,
                bundle.roots.threshold,
                &revoked,
            )?;
        }
    }
    Ok(AuthenticatedBundle {
        sequence: bundle.sequence,
        digest,
        roots,
        release_keys,
        revoked,
    })
}

fn validate_trusted_root(trusted: &TrustedRootState, policy: TrustPolicy) -> Result<(), PortError> {
    if trusted.trust_domain != CORE_DOMAIN
        || trusted.sequence == 0
        || !is_sha256(&trusted.bundle_sha256)
        || trusted.threshold != 2
        || trusted.keys.len() != 3
    {
        return Err(invalid("independent pinned root state is invalid"));
    }
    let keys = pinned_key_map(&trusted.keys)?;
    let revoked: BTreeSet<&str> = trusted.revoked_key_ids.iter().map(String::as_str).collect();
    if revoked.len() != trusted.revoked_key_ids.len()
        || revoked.iter().any(|key| !is_key_id(key))
        || keys
            .keys()
            .filter(|key| !revoked.contains(key.as_str()))
            .count()
            < trusted.threshold.into()
    {
        return Err(invalid("pinned root revocation state is invalid"));
    }
    match policy {
        TrustPolicy::Production if trusted.keys.iter().any(|key| key.test_fixture) => Err(invalid(
            "production policy rejects test-fixture bootstrap roots",
        )),
        TrustPolicy::TestFixtures if trusted.keys.iter().any(|key| !key.test_fixture) => Err(
            invalid("test-fixture policy requires explicitly marked bootstrap roots"),
        ),
        _ => Ok(()),
    }
}

fn authorize_release_freshness(
    freshness: &ReleaseFreshness,
    index: &PayloadIndex,
    index_digest: &str,
    bundle: &AuthenticatedBundle,
) -> Result<(u64, String), PortError> {
    match freshness {
        ReleaseFreshness::FirstInstallExactDigest(required) => {
            if !is_sha256(required) || required != index_digest {
                return Err(invalid(
                    "offline first-install exact digest is not satisfied",
                ));
            }
            Ok((index.sequence, index_digest.into()))
        }
        ReleaseFreshness::FirstInstallMinimumSequence(minimum) => {
            if *minimum == 0 || index.sequence < *minimum {
                return Err(invalid(
                    "offline first-install minimum sequence is not satisfied",
                ));
            }
            Ok((index.sequence, index_digest.into()))
        }
        ReleaseFreshness::Existing {
            sequence,
            digest: stored_digest,
            rollback,
        } => {
            if *sequence == 0 || !is_sha256(stored_digest) {
                return Err(invalid("stored release high-water state is invalid"));
            }
            if index.sequence > *sequence {
                return Ok((index.sequence, index_digest.into()));
            }
            if index.sequence == *sequence {
                if index_digest == stored_digest {
                    return Ok((*sequence, stored_digest.clone()));
                }
                return Err(invalid(
                    "equal release sequence has a different canonical digest",
                ));
            }
            let authorization = rollback.as_ref().ok_or_else(|| {
                invalid("lower release sequence lacks root rollback authorization")
            })?;
            verify_rollback(authorization, index, index_digest, bundle)?;
            Ok((*sequence, stored_digest.clone()))
        }
    }
}

fn verify_rollback(
    material: &RollbackMaterial,
    index: &PayloadIndex,
    index_digest: &str,
    bundle: &AuthenticatedBundle,
) -> Result<(), PortError> {
    let authorization_value = parse(&material.authorization).map_err(invalid)?;
    let envelope_value = parse_canonical_envelope(&material.signatures)?;
    let authorization: RollbackAuthorization =
        serde_json::from_value(authorization_value.clone()).map_err(invalid)?;
    let envelope: SignatureEnvelope = serde_json::from_value(envelope_value).map_err(invalid)?;
    if authorization.schema != "repository-harness-rollback-authorization/v1"
        || authorization.trust_domain != CORE_DOMAIN
        || authorization.role != CORE_RELEASE_ROLE
        || authorization.root_bundle_sequence != bundle.sequence
        || authorization.authorized_sequence != index.sequence
        || authorization.authorized_digest != index_digest
        || !is_sha256(&authorization.authorized_digest)
    {
        return Err(invalid(
            "rollback authorization does not bind the requested release",
        ));
    }
    verify_envelope(
        &authorization_value,
        &envelope,
        CORE_ROLLBACK_SIGNATURE_DOMAIN,
        CORE_ROOT_ROLE,
        bundle.sequence,
        &bundle.roots,
        2,
        &bundle.revoked,
    )
}

fn parse_canonical_envelope(bytes: &[u8]) -> Result<serde_json::Value, PortError> {
    let value = parse(bytes).map_err(invalid)?;
    if canonical(&value).map_err(invalid)? != bytes {
        return Err(invalid(
            "detached signature envelope bytes are not canonical JCS",
        ));
    }
    Ok(value)
}

// Keep every signed-envelope binding visible at each trust-lifecycle call site.
#[allow(clippy::too_many_arguments)]
fn verify_envelope(
    payload: &serde_json::Value,
    envelope: &SignatureEnvelope,
    signature_domain: &str,
    expected_role: &str,
    expected_sequence: u64,
    keys: &BTreeMap<String, [u8; 32]>,
    threshold: u8,
    revoked: &BTreeSet<String>,
) -> Result<(), PortError> {
    let expected_digest = digest(payload).map_err(invalid)?;
    if envelope.schema != "repository-harness-signature-envelope/v1"
        || envelope.trust_domain != CORE_DOMAIN
        || envelope.role != expected_role
        || envelope.sequence != expected_sequence
        || envelope.payload_sha256 != expected_digest
        || !is_sha256(&envelope.payload_sha256)
        || envelope.signatures.is_empty()
    {
        return Err(invalid("detached signature envelope identity is invalid"));
    }
    let message = signed_message(signature_domain, payload).map_err(invalid)?;
    let mut valid = BTreeSet::new();
    for detached in &envelope.signatures {
        if detached.algorithm != "ed25519"
            || revoked.contains(&detached.key_id)
            || valid.contains(&detached.key_id)
        {
            continue;
        }
        let Some(public_key) = keys.get(&detached.key_id) else {
            continue;
        };
        let Ok(signature_bytes) = decode_base64(&detached.signature) else {
            continue;
        };
        let Ok(signature) = <[u8; 64]>::try_from(signature_bytes.as_slice()) else {
            continue;
        };
        if strict_verify(public_key, &message, &signature) {
            valid.insert(detached.key_id.clone());
        }
    }
    if valid.len() < threshold.into() {
        return Err(invalid("signature threshold is not met"));
    }
    Ok(())
}

fn validate_index_identity(index: &PayloadIndex) -> Result<(), PortError> {
    if index.schema != CORE_INDEX_SCHEMA
        || index.trust_domain != CORE_DOMAIN
        || index.role != CORE_RELEASE_ROLE
        || index.sequence == 0
        || Version::parse(&index.release).is_err()
        || index.tag != format!("harness-v1-core-v{}", index.release)
        || index.source_commit.len() != 40
        || !index
            .source_commit
            .bytes()
            .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
        || index.assets.is_empty()
    {
        return Err(invalid("payload index core identity is invalid"));
    }
    Ok(())
}

fn validate_ledger_header(ledger: &PathLedger) -> Result<(), PortError> {
    let expected = [
        "managed-v1",
        "optional-v1",
        "source-only",
        "target-owned-destination",
        "bridge-only-legacy",
        "forbidden-v0-operational",
    ];
    if ledger.schema != "repository-harness-path-dispositions/v1"
        || ledger
            .allowed_dispositions
            .iter()
            .map(String::as_str)
            .collect::<Vec<_>>()
            != expected
    {
        return Err(invalid("Phase 1 path ledger header changed"));
    }
    Ok(())
}

fn decode_keys(
    keys: &[PublicKey],
    policy: TrustPolicy,
) -> Result<BTreeMap<String, [u8; 32]>, PortError> {
    let mut result = BTreeMap::new();
    for key in keys {
        match policy {
            TrustPolicy::Production if key.test_fixture.is_some() => {
                return Err(invalid(
                    "production policy rejects test-fixture bundle keys",
                ));
            }
            TrustPolicy::TestFixtures if key.test_fixture != Some(true) => {
                return Err(invalid("test-fixture policy requires marked bundle keys"));
            }
            _ => {}
        }
        let raw = decode_base64(&key.public_key_base64).map_err(invalid)?;
        let raw: [u8; 32] = raw
            .try_into()
            .map_err(|_| invalid("Ed25519 public key is not 32 bytes"))?;
        if key.algorithm != "ed25519"
            || key.key_id != format!("ed25519-sha256:{}", hex_sha256(&raw))
            || !strict_public_key(&raw)
            || result.insert(key.key_id.clone(), raw).is_some()
        {
            return Err(invalid("invalid or duplicate Ed25519 key"));
        }
    }
    Ok(result)
}

fn pinned_key_map(keys: &[PinnedRootKey]) -> Result<BTreeMap<String, [u8; 32]>, PortError> {
    let mut result = BTreeMap::new();
    for key in keys {
        if key.key_id != format!("ed25519-sha256:{}", hex_sha256(&key.public_key))
            || !strict_public_key(&key.public_key)
            || result.insert(key.key_id.clone(), key.public_key).is_some()
        {
            return Err(invalid(
                "independent pinned root key is invalid or duplicated",
            ));
        }
    }
    Ok(result)
}

fn strict_public_key(public_key: &[u8; 32]) -> bool {
    canonical_torsion_free_point(public_key) && VerifyingKey::from_bytes(public_key).is_ok()
}

fn canonical_torsion_free_point(encoded: &[u8; 32]) -> bool {
    let compressed = CompressedEdwardsY(*encoded);
    let Some(point) = compressed.decompress() else {
        return false;
    };
    point.compress().to_bytes() == *encoded && !point.is_small_order() && point.is_torsion_free()
}

fn strict_verify(public_key: &[u8; 32], message: &[u8], signature: &[u8; 64]) -> bool {
    let encoded_r: &[u8; 32] = signature[..32].try_into().expect("fixed signature prefix");
    let encoded_s: &[u8; 32] = signature[32..].try_into().expect("fixed signature suffix");
    let scalar = Option::<Scalar>::from(Scalar::from_canonical_bytes(*encoded_s));
    if !strict_public_key(public_key)
        || !canonical_torsion_free_point(encoded_r)
        || scalar.is_none_or(|value| value == Scalar::ZERO)
    {
        return false;
    }
    let Ok(verifying_key) = VerifyingKey::from_bytes(public_key) else {
        return false;
    };
    verifying_key
        .verify_strict(message, &Signature::from_bytes(signature))
        .is_ok()
}

fn decode_base64(value: &str) -> Result<Vec<u8>, String> {
    if !value.len().is_multiple_of(4) || !value.is_ascii() {
        return Err("invalid base64 length".into());
    }
    let mut result = Vec::with_capacity(value.len() / 4 * 3);
    for (index, chunk) in value.as_bytes().chunks_exact(4).enumerate() {
        let padding = usize::from(chunk[3] == b'=') + usize::from(chunk[2] == b'=');
        if padding > 0 && index + 1 != value.len() / 4 {
            return Err("base64 padding occurs before the final quartet".into());
        }
        let a = base64_value(chunk[0])?;
        let b = base64_value(chunk[1])?;
        let c = if chunk[2] == b'=' {
            0
        } else {
            base64_value(chunk[2])?
        };
        let d = if chunk[3] == b'=' {
            0
        } else {
            base64_value(chunk[3])?
        };
        if chunk[2] == b'=' && chunk[3] != b'='
            || padding == 2 && b & 0x0f != 0
            || padding == 1 && c & 0x03 != 0
        {
            return Err("non-canonical base64 padding".into());
        }
        let bits = (u32::from(a) << 18) | (u32::from(b) << 12) | (u32::from(c) << 6) | u32::from(d);
        result.push((bits >> 16) as u8);
        if padding < 2 {
            result.push((bits >> 8) as u8);
        }
        if padding == 0 {
            result.push(bits as u8);
        }
    }
    Ok(result)
}

fn base64_value(byte: u8) -> Result<u8, String> {
    match byte {
        b'A'..=b'Z' => Ok(byte - b'A'),
        b'a'..=b'z' => Ok(byte - b'a' + 26),
        b'0'..=b'9' => Ok(byte - b'0' + 52),
        b'+' => Ok(62),
        b'/' => Ok(63),
        _ => Err("invalid base64 character".into()),
    }
}

fn is_sha256(value: &str) -> bool {
    value.len() == 64
        && value
            .bytes()
            .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
}

fn is_key_id(value: &str) -> bool {
    value.strip_prefix("ed25519-sha256:").is_some_and(is_sha256)
}

fn is_lower_kebab(value: &str) -> bool {
    !value.is_empty()
        && value
            .bytes()
            .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'-')
        && value.as_bytes()[0].is_ascii_alphanumeric()
        && value.as_bytes()[value.len() - 1].is_ascii_alphanumeric()
}

fn is_lower_snake(value: &str) -> bool {
    !value.is_empty()
        && value.as_bytes()[0].is_ascii_lowercase()
        && value
            .bytes()
            .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'_')
}

fn invalid(message: impl ToString) -> PortError {
    PortError::ReleaseInvalid(message.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn strict_base64_decoder_rejects_noncanonical_input() {
        assert_eq!(decode_base64("TQ==").unwrap(), b"M");
        assert!(decode_base64("TR==").is_err());
        assert!(decode_base64("TQ=A").is_err());
    }

    #[test]
    fn strict_verifier_rejects_identity_zero_scalar_forgery() {
        let mut identity = [0_u8; 32];
        identity[0] = 1;
        let mut signature = [0_u8; 64];
        signature[..32].copy_from_slice(&identity);
        assert!(!strict_verify(&identity, b"forged", &signature));
    }

    #[test]
    fn signed_optional_fields_reject_schema_invalid_nulls() {
        let empty_bundle = serde_json::json!({});
        for field in ["role", "template"] {
            let mut index = serde_json::json!({"assets": [{}]});
            index["assets"][0][field] = serde_json::Value::Null;
            assert!(reject_schema_nulls(&index, &empty_bundle).is_err());
        }
        for field in ["previous_bundle_sha256", "test_fixture_notice"] {
            let mut bundle = serde_json::json!({});
            bundle[field] = serde_json::Value::Null;
            assert!(reject_schema_nulls(&serde_json::json!({}), &bundle).is_err());
        }
        let bundle = serde_json::json!({
            "roots": {"keys": [{"test_fixture": null}]},
            "roles": []
        });
        assert!(reject_schema_nulls(&serde_json::json!({}), &bundle).is_err());
    }
}
