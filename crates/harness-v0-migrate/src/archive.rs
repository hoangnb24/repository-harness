use std::collections::{BTreeMap, BTreeSet};
use std::io::Read;
use std::iter;
use std::str::FromStr;

use age::x25519;
use hmac::{Hmac, Mac};
use serde::{Deserialize, Serialize};
use sha2::Sha256;

use crate::capture::{capture_members_digest, hex_sha256, source_digest, Capture};
use crate::interface::ArchiveOptions;
use crate::secure_fs::{RootIdentity, SecureRoot};
use crate::{BridgeError, Result};

pub const ARCHIVE_SCHEMA: &str = "repository-harness-v0-archive-manifest/v1";
pub const CUSTODY_ROOT: &str = ".harness-v0-archive";
const CUSTODY_SCHEMA: &str = "repository-harness-v0-archive-custody/v1";
const PAYLOAD_SCHEMA: &[u8] = b"repository-harness-v0-archive-payload/v1\0";

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct ArchiveManifest {
    pub schema: String,
    pub archive_id: String,
    pub bridge_release: String,
    pub source_schema: u32,
    pub source_sha256: String,
    pub capture_members_sha256: String,
    pub export_sha256: String,
    pub standalone_backup_sha256: String,
    pub confidentiality_mode: String,
    pub recipient_fingerprints: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub plaintext_risk_acknowledged: Option<bool>,
    pub payload_path: String,
    pub payload_sha256: String,
    pub payload_bytes: u64,
    pub members: Vec<ArchiveMember>,
    pub custody: String,
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct ArchiveMember {
    pub path: String,
    pub sha256: String,
    pub bytes: u64,
    pub capture: String,
}

#[derive(Clone, Debug)]
pub struct ArchiveEvidence {
    pub archive_id: String,
    pub manifest_path: String,
    pub manifest_sha256: String,
    pub export_sha256: String,
    pub payload_sha256: String,
    pub source_sha256: String,
    pub confidentiality_mode: String,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct CustodyMarker {
    schema: String,
    path: String,
    root: RootIdentity,
    key_sha256: String,
    authentication: String,
}

struct ConfidentialPayload {
    name: &'static str,
    bytes: Vec<u8>,
    mode: String,
    fingerprints: Vec<String>,
    acknowledged: Option<bool>,
}

pub fn create(
    root: &SecureRoot,
    capture: &Capture,
    export_bytes: &[u8],
    options: &ArchiveOptions,
) -> Result<ArchiveEvidence> {
    #[cfg(not(unix))]
    {
        let _ = (root, capture, export_bytes, options);
        return Err(BridgeError::Unsupported(
            "archive publication is unavailable on Windows until Phase 7".into(),
        ));
    }
    #[cfg(unix)]
    {
        root.validate_root()?;
        let clear_payload = encode_payload(capture, export_bytes)?;
        let payload = confidentiality_payload(clear_payload, options)?;
        ensure_custody(root)?;

        let archive_nonce = nonce_hex()?;
        let archive_id = format!(
            "v0-{}-{}",
            &source_digest(capture)[..16],
            &archive_nonce[..12]
        );
        let staging = format!("{CUSTODY_ROOT}/.staging-{}", nonce_hex()?);
        let destination = format!("{CUSTODY_ROOT}/{archive_id}");
        root.create_dir_exact(&staging)?;

        let payload_path = format!("{staging}/{}", payload.name);
        root.write_new(&payload_path, &payload.bytes)?;
        let manifest = ArchiveManifest {
            schema: ARCHIVE_SCHEMA.into(),
            archive_id: archive_id.clone(),
            bridge_release: crate::command_spec::BRIDGE_VERSION.into(),
            source_schema: capture.schema_version,
            source_sha256: source_digest(capture),
            capture_members_sha256: capture_members_digest(capture),
            export_sha256: hex_sha256(export_bytes),
            standalone_backup_sha256: capture.standalone_backup_sha256.clone(),
            confidentiality_mode: payload.mode,
            recipient_fingerprints: payload.fingerprints,
            plaintext_risk_acknowledged: payload.acknowledged,
            payload_path: payload.name.into(),
            payload_sha256: hex_sha256(&payload.bytes),
            payload_bytes: payload.bytes.len() as u64,
            members: archive_members(capture, export_bytes),
            custody: "repository-owner-indefinite-write-once".into(),
        };
        let mut manifest_bytes = serde_json::to_vec(&manifest)?;
        manifest_bytes.push(b'\n');
        root.write_new(&format!("{staging}/archive-manifest.json"), &manifest_bytes)?;
        verify_directory(root, &staging, None)?;
        root.validate_root()?;
        root.rename_no_replace(&staging, &destination)?;
        let published_manifest = format!("{destination}/archive-manifest.json");
        let (published, _) = verify_manifest(root, &published_manifest, None)?;
        if published != manifest {
            return Err(BridgeError::Conflict(
                "published archive differs from verified staging".into(),
            ));
        }
        Ok(ArchiveEvidence {
            archive_id,
            manifest_path: published_manifest,
            manifest_sha256: hex_sha256(&manifest_bytes),
            export_sha256: manifest.export_sha256,
            payload_sha256: manifest.payload_sha256,
            source_sha256: manifest.source_sha256,
            confidentiality_mode: manifest.confidentiality_mode,
        })
    }
}

/// Verifies the immutable outer archive. With an identity, it also decrypts
/// and checks every inner member and returns the neutral export bytes.
pub fn verify_manifest(
    root: &SecureRoot,
    manifest_path: &str,
    identity_file: Option<&str>,
) -> Result<(ArchiveManifest, Option<Vec<u8>>)> {
    validate_manifest_path(manifest_path)?;
    verify_custody(root)?;
    let directory = manifest_path
        .strip_suffix("/archive-manifest.json")
        .ok_or_else(|| BridgeError::Usage("archive manifest path has the wrong filename".into()))?;
    verify_directory(root, directory, identity_file)
}

fn verify_directory(
    root: &SecureRoot,
    directory: &str,
    identity_file: Option<&str>,
) -> Result<(ArchiveManifest, Option<Vec<u8>>)> {
    let manifest_path = format!("{directory}/archive-manifest.json");
    let manifest_bytes = root.read(&manifest_path)?;
    let value = crate::strict_json::parse(&manifest_bytes)
        .map_err(|error| BridgeError::Invalid(format!("archive manifest is malformed: {error}")))?;
    let manifest: ArchiveManifest = serde_json::from_value(value)
        .map_err(|error| BridgeError::Invalid(format!("archive manifest is invalid: {error}")))?;
    let expected_directory = format!("{CUSTODY_ROOT}/{}", manifest.archive_id);
    let unique_staging = directory.starts_with(&format!("{CUSTODY_ROOT}/.staging-"));
    if (!unique_staging && directory != expected_directory)
        || manifest.schema != ARCHIVE_SCHEMA
        || manifest.bridge_release != crate::command_spec::BRIDGE_VERSION
        || !(1..=13).contains(&manifest.source_schema)
        || manifest.custody != "repository-owner-indefinite-write-once"
        || !is_sha256(&manifest.source_sha256)
        || !is_sha256(&manifest.capture_members_sha256)
        || !is_sha256(&manifest.export_sha256)
        || !is_sha256(&manifest.standalone_backup_sha256)
        || !is_sha256(&manifest.payload_sha256)
        || manifest.members.is_empty()
        || manifest.members.iter().any(|member| {
            harness_core::path::validate_repository_relative(&member.path).is_err()
                || !is_sha256(&member.sha256)
                || !matches!(
                    member.capture.as_str(),
                    "pre-copy-post-equal"
                        | "private-staged-wal-recovery-online-backup"
                        | "neutral-read-only-export"
                )
        })
    {
        return Err(BridgeError::Invalid(
            "archive manifest identity or digest fields are invalid".into(),
        ));
    }
    match manifest.confidentiality_mode.as_str() {
        "encrypted-age-x25519"
            if manifest.recipient_fingerprints.len() == 1
                && manifest.plaintext_risk_acknowledged.is_none()
                && manifest.payload_path == "archive.age" => {}
        "plaintext-explicit-override"
            if manifest.recipient_fingerprints.is_empty()
                && manifest.plaintext_risk_acknowledged == Some(true)
                && manifest.payload_path == "archive.bin" => {}
        _ => {
            return Err(BridgeError::Invalid(
                "archive confidentiality record is invalid".into(),
            ))
        }
    }
    let expected_names = BTreeSet::from([
        "archive-manifest.json".to_owned(),
        manifest.payload_path.clone(),
    ]);
    if root
        .list_names(directory)?
        .into_iter()
        .collect::<BTreeSet<_>>()
        != expected_names
    {
        return Err(BridgeError::Conflict(
            "archive directory contains an incomplete or foreign member set".into(),
        ));
    }
    let payload = root.read(&format!("{directory}/{}", manifest.payload_path))?;
    if payload.len() as u64 != manifest.payload_bytes
        || hex_sha256(&payload) != manifest.payload_sha256
    {
        return Err(BridgeError::Conflict(
            "archive payload digest or length differs from its manifest".into(),
        ));
    }

    let clear = match manifest.confidentiality_mode.as_str() {
        "plaintext-explicit-override" => Some(payload),
        "encrypted-age-x25519" if identity_file.is_some() => Some(decrypt_payload(
            root,
            &payload,
            identity_file.expect("checked"),
        )?),
        "encrypted-age-x25519" => None,
        _ => unreachable!("confidentiality was checked"),
    };
    let export = if let Some(clear) = clear {
        let entries = decode_payload(&clear)?;
        let expected = manifest
            .members
            .iter()
            .map(|member| (member.path.clone(), (member.sha256.clone(), member.bytes)))
            .collect::<BTreeMap<_, _>>();
        let actual = entries
            .iter()
            .map(|(path, bytes)| (path.clone(), (hex_sha256(bytes), bytes.len() as u64)))
            .collect::<BTreeMap<_, _>>();
        if actual != expected {
            return Err(BridgeError::Conflict(
                "archive inner member set differs from its manifest".into(),
            ));
        }
        let export = entries
            .get("export/export.json")
            .ok_or_else(|| BridgeError::Conflict("archive neutral export is absent".into()))?
            .clone();
        if hex_sha256(&export) != manifest.export_sha256 {
            return Err(BridgeError::Conflict(
                "archive neutral export digest differs from its manifest".into(),
            ));
        }
        Some(export)
    } else {
        None
    };
    Ok((manifest, export))
}

fn ensure_custody(root: &SecureRoot) -> Result<()> {
    if root.directory_exists(CUSTODY_ROOT)? {
        return verify_custody(root);
    }
    let staging = format!("{CUSTODY_ROOT}.init-{}", nonce_hex()?);
    root.create_dir_exact(&staging)?;
    let mut key = [0_u8; 32];
    getrandom::getrandom(&mut key)
        .map_err(|error| BridgeError::Io(std::io::Error::other(error.to_string())))?;
    root.write_new(&format!("{staging}/custody.key"), &key)?;
    let authentication = custody_authentication(&key, &root.identity())?;
    let marker = CustodyMarker {
        schema: CUSTODY_SCHEMA.into(),
        path: CUSTODY_ROOT.into(),
        root: root.identity(),
        key_sha256: hex_sha256(&key),
        authentication,
    };
    let mut bytes = serde_json::to_vec(&marker)?;
    bytes.push(b'\n');
    root.write_new(&format!("{staging}/custody.json"), &bytes)?;
    root.rename_no_replace(&staging, CUSTODY_ROOT)?;
    verify_custody(root)
}

fn verify_custody(root: &SecureRoot) -> Result<()> {
    if !root.directory_exists(CUSTODY_ROOT)? {
        return Err(BridgeError::Invalid(
            "reserved V0 archive custody is absent".into(),
        ));
    }
    #[cfg(unix)]
    root.open_dir_fd(CUSTODY_ROOT, false, true)?;
    let key = root.read_private(&format!("{CUSTODY_ROOT}/custody.key"), Some(32))?;
    let marker_bytes = root.read_private(&format!("{CUSTODY_ROOT}/custody.json"), None)?;
    let value = crate::strict_json::parse(&marker_bytes)
        .map_err(|_| BridgeError::Conflict("archive custody marker is malformed".into()))?;
    let marker: CustodyMarker = serde_json::from_value(value)
        .map_err(|_| BridgeError::Conflict("archive custody marker is invalid".into()))?;
    let expected = custody_authentication(&key, &root.identity())?;
    if marker.schema != CUSTODY_SCHEMA
        || marker.path != CUSTODY_ROOT
        || marker.root != root.identity()
        || marker.key_sha256 != hex_sha256(&key)
        || marker.authentication != expected
    {
        return Err(BridgeError::Conflict(
            "reserved archive custody is foreign or unauthenticated".into(),
        ));
    }
    Ok(())
}

fn custody_authentication(key: &[u8], root: &RootIdentity) -> Result<String> {
    let message = format!(
        "{CUSTODY_SCHEMA}\0{CUSTODY_ROOT}\0{}\0{}",
        root.device, root.inode
    );
    let mut mac = Hmac::<Sha256>::new_from_slice(key)
        .map_err(|_| BridgeError::Invalid("archive custody HMAC key is invalid".into()))?;
    mac.update(message.as_bytes());
    Ok(format!("{:x}", mac.finalize().into_bytes()))
}

fn confidentiality_payload(
    payload: Vec<u8>,
    options: &ArchiveOptions,
) -> Result<ConfidentialPayload> {
    if options.plaintext {
        if !options.plaintext_risk_acknowledged {
            return Err(BridgeError::Usage(
                "plaintext archive requires the separate risk acknowledgement".into(),
            ));
        }
        return Ok(ConfidentialPayload {
            name: "archive.bin",
            bytes: payload,
            mode: "plaintext-explicit-override".into(),
            fingerprints: Vec::new(),
            acknowledged: Some(true),
        });
    }
    let recipient_text = options
        .age_recipient
        .as_ref()
        .ok_or_else(|| BridgeError::Usage("encrypted archive requires an age recipient".into()))?;
    let recipient = x25519::Recipient::from_str(recipient_text)
        .map_err(|error| BridgeError::Usage(format!("invalid age/X25519 recipient: {error}")))?;
    let encryptor = age::Encryptor::with_recipients(iter::once(&recipient as _))?;
    let mut ciphertext = Vec::new();
    let mut writer = encryptor.wrap_output(&mut ciphertext)?;
    std::io::Write::write_all(&mut writer, &payload)?;
    writer.finish()?;
    Ok(ConfidentialPayload {
        name: "archive.age",
        bytes: ciphertext,
        mode: "encrypted-age-x25519".into(),
        fingerprints: vec![recipient_text.clone()],
        acknowledged: None,
    })
}

fn decrypt_payload(root: &SecureRoot, payload: &[u8], identity_file: &str) -> Result<Vec<u8>> {
    let identity_bytes = root.read(identity_file)?;
    let identity_text = std::str::from_utf8(&identity_bytes)
        .map_err(|_| BridgeError::Usage("age identity file must be UTF-8".into()))?;
    let encoded = identity_text
        .lines()
        .map(str::trim)
        .find(|line| !line.is_empty() && !line.starts_with('#'))
        .ok_or_else(|| BridgeError::Usage("age identity file contains no identity".into()))?;
    let identity = x25519::Identity::from_str(encoded)
        .map_err(|error| BridgeError::Usage(format!("invalid age/X25519 identity: {error}")))?;
    let decryptor = age::Decryptor::new(payload)?;
    let mut reader = decryptor.decrypt(iter::once(&identity as &dyn age::Identity))?;
    let mut clear = Vec::new();
    reader.read_to_end(&mut clear)?;
    Ok(clear)
}

fn archive_members(capture: &Capture, export: &[u8]) -> Vec<ArchiveMember> {
    let mut members = capture
        .members
        .iter()
        .map(|member| ArchiveMember {
            path: format!("raw/{}", member.path),
            sha256: member.sha256.clone(),
            bytes: member.bytes,
            capture: "pre-copy-post-equal".into(),
        })
        .collect::<Vec<_>>();
    members.push(ArchiveMember {
        path: "standalone/standalone.db".into(),
        sha256: capture.standalone_backup_sha256.clone(),
        bytes: capture.standalone_backup.len() as u64,
        capture: "private-staged-wal-recovery-online-backup".into(),
    });
    members.push(ArchiveMember {
        path: "export/export.json".into(),
        sha256: hex_sha256(export),
        bytes: export.len() as u64,
        capture: "neutral-read-only-export".into(),
    });
    members.sort_by(|left, right| left.path.cmp(&right.path));
    members
}

fn encode_payload(capture: &Capture, export: &[u8]) -> Result<Vec<u8>> {
    let mut entries = capture
        .members
        .iter()
        .map(|member| {
            (
                format!("raw/{}", member.path),
                member.captured_bytes.as_slice(),
            )
        })
        .collect::<Vec<_>>();
    entries.push((
        "standalone/standalone.db".into(),
        &capture.standalone_backup,
    ));
    entries.push(("export/export.json".into(), export));
    entries.sort_by(|left, right| left.0.cmp(&right.0));
    let mut output = PAYLOAD_SCHEMA.to_vec();
    for (name, bytes) in entries {
        let name = name.as_bytes();
        let name_len = u32::try_from(name.len())
            .map_err(|_| BridgeError::Invalid("archive member name is too long".into()))?;
        let byte_len = u64::try_from(bytes.len())
            .map_err(|_| BridgeError::Invalid("archive member is too large".into()))?;
        output.extend_from_slice(&name_len.to_be_bytes());
        output.extend_from_slice(name);
        output.extend_from_slice(&byte_len.to_be_bytes());
        output.extend_from_slice(bytes);
    }
    Ok(output)
}

fn decode_payload(payload: &[u8]) -> Result<BTreeMap<String, Vec<u8>>> {
    let Some(mut remaining) = payload.strip_prefix(PAYLOAD_SCHEMA) else {
        return Err(BridgeError::Invalid(
            "archive payload schema is invalid".into(),
        ));
    };
    let mut entries = BTreeMap::new();
    while !remaining.is_empty() {
        if remaining.len() < 4 {
            return Err(BridgeError::Invalid("archive payload is truncated".into()));
        }
        let name_len = u32::from_be_bytes(remaining[..4].try_into().expect("four bytes")) as usize;
        remaining = &remaining[4..];
        if remaining.len() < name_len + 8 {
            return Err(BridgeError::Invalid("archive payload is truncated".into()));
        }
        let name = std::str::from_utf8(&remaining[..name_len])
            .map_err(|_| BridgeError::Invalid("archive member path is not UTF-8".into()))?
            .to_owned();
        harness_core::path::validate_repository_relative(&name)
            .map_err(|_| BridgeError::Invalid("archive member path is unsafe".into()))?;
        remaining = &remaining[name_len..];
        let byte_len = u64::from_be_bytes(remaining[..8].try_into().expect("eight bytes"));
        remaining = &remaining[8..];
        let byte_len = usize::try_from(byte_len)
            .map_err(|_| BridgeError::Invalid("archive member is too large".into()))?;
        if remaining.len() < byte_len {
            return Err(BridgeError::Invalid("archive payload is truncated".into()));
        }
        if entries
            .insert(name, remaining[..byte_len].to_vec())
            .is_some()
        {
            return Err(BridgeError::Invalid(
                "archive payload contains a duplicate member".into(),
            ));
        }
        remaining = &remaining[byte_len..];
    }
    Ok(entries)
}

fn validate_manifest_path(path: &str) -> Result<()> {
    harness_core::path::validate_repository_relative(path)
        .map_err(|_| BridgeError::Usage("archive manifest path is unsafe".into()))?;
    let parts = path.split('/').collect::<Vec<_>>();
    if parts.len() != 3
        || parts[0] != CUSTODY_ROOT
        || parts[1].starts_with('.')
        || parts[2] != "archive-manifest.json"
    {
        return Err(BridgeError::Usage(format!(
            "archive manifest must be {CUSTODY_ROOT}/<archive-id>/archive-manifest.json"
        )));
    }
    Ok(())
}

fn nonce_hex() -> Result<String> {
    let mut bytes = [0_u8; 16];
    getrandom::getrandom(&mut bytes)
        .map_err(|error| BridgeError::Io(std::io::Error::other(error.to_string())))?;
    Ok(hex_sha256(&bytes)[..24].to_owned())
}

fn is_sha256(value: &str) -> bool {
    value.len() == 64
        && value
            .bytes()
            .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
}
