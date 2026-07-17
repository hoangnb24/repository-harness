use std::iter;
use std::path::{Path, PathBuf};
use std::str::FromStr;

use age::x25519;
use serde::{Deserialize, Serialize};

use crate::capture::{capture_members_digest, hex_sha256, Capture};
use crate::interface::ArchiveOptions;
use crate::journal::Journal;
use crate::secure_fs::SecureRoot;
use crate::{BridgeError, Result};

pub const ARCHIVE_SCHEMA: &str = "repository-harness-v0-archive-manifest/v1";

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct ArchiveManifest {
    pub schema: String,
    pub conversion_id: String,
    pub source_schema: u32,
    pub confidentiality_mode: String,
    pub recipient_fingerprints: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub plaintext_risk_acknowledged: Option<bool>,
    pub members: Vec<ArchiveMember>,
    pub standalone_backup_sha256: String,
    pub archive_sha256: String,
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
    pub path: String,
    pub archive_sha256: String,
    pub manifest_sha256: String,
    pub capture_members_sha256: String,
    pub export_sha256: String,
    pub confidentiality_mode: String,
    pub recipient_fingerprints: Vec<String>,
    pub plaintext_risk_acknowledged: Option<bool>,
}

struct ConfidentialPayload {
    name: &'static str,
    bytes: Vec<u8>,
    mode: String,
    fingerprints: Vec<String>,
    acknowledged: Option<bool>,
}

pub(crate) fn prepare_or_verify(
    root: &SecureRoot,
    journal: &Journal,
    capture: &Capture,
    export_bytes: &[u8],
    options: &ArchiveOptions,
) -> Result<(ArchiveEvidence, bool)> {
    root.validate_root()?;
    let conversion_id = &journal.conversion_id;
    let final_dir = archive_directory(conversion_id);
    let staging_dir = staging_directory(conversion_id);
    let final_exists = directory_exists(root, &final_dir)?;
    let staging_exists = directory_exists(root, &staging_dir)?;
    if final_exists && staging_exists {
        return Err(BridgeError::Conflict(
            "both final and staged conversion archives exist".into(),
        ));
    }
    if final_exists {
        let evidence = verify_directory(root, &final_dir, journal, capture, export_bytes, options)?;
        return Ok((evidence, true));
    }
    if staging_exists {
        let evidence =
            verify_directory(root, &staging_dir, journal, capture, export_bytes, options)?;
        return Ok((evidence, false));
    }

    root.open_dir(".harness", true, false)?;
    root.open_dir(".harness/legacy", true, true)?;
    root.open_dir(".harness/legacy/v0-conversion", true, true)?;
    root.open_dir(".harness/recovery", true, true)?;
    root.open_dir(".harness/recovery/v0-conversion", true, true)?;
    root.create_dir_exact(&staging_dir)?;

    let payload = encode_payload(capture, export_bytes)?;
    let payload = confidentiality_payload(payload, options)?;
    let archive_sha256 = hex_sha256(&payload.bytes);
    root.write_new(&format!("{staging_dir}/{}", payload.name), &payload.bytes)?;
    let manifest = expected_manifest(
        conversion_id,
        capture,
        &payload.mode,
        payload.fingerprints.clone(),
        payload.acknowledged,
        archive_sha256.clone(),
    );
    let mut manifest_bytes = serde_json::to_vec(&manifest)?;
    manifest_bytes.push(b'\n');
    root.write_new(
        &format!("{staging_dir}/archive-manifest.json"),
        &manifest_bytes,
    )?;
    root.validate_root()?;
    Ok((
        ArchiveEvidence {
            path: format!("{final_dir}/{}", payload.name),
            archive_sha256,
            manifest_sha256: hex_sha256(&manifest_bytes),
            capture_members_sha256: capture_members_digest(capture),
            export_sha256: hex_sha256(export_bytes),
            confidentiality_mode: payload.mode,
            recipient_fingerprints: payload.fingerprints,
            plaintext_risk_acknowledged: payload.acknowledged,
        },
        false,
    ))
}

pub(crate) fn publish(root: &SecureRoot, conversion_id: &str) -> Result<()> {
    let staging = staging_directory(conversion_id);
    let destination = archive_directory(conversion_id);
    root.rename_no_replace(&staging, &destination)?;
    root.validate_root()
}

pub(crate) fn verify_published(
    root: &SecureRoot,
    journal: &Journal,
    capture: &Capture,
    export_bytes: &[u8],
    options: &ArchiveOptions,
) -> Result<ArchiveEvidence> {
    verify_directory(
        root,
        &archive_directory(&journal.conversion_id),
        journal,
        capture,
        export_bytes,
        options,
    )
}

fn verify_directory(
    root: &SecureRoot,
    directory: &str,
    journal: &Journal,
    capture: &Capture,
    export_bytes: &[u8],
    options: &ArchiveOptions,
) -> Result<ArchiveEvidence> {
    let handle = root.open_dir(directory, false, true)?;
    let expected_mode = expected_mode(options)?;
    let payload_name = if options.plaintext {
        "conversion.bin"
    } else {
        "conversion.age"
    };
    let expected_names = vec!["archive-manifest.json".to_owned(), payload_name.to_owned()];
    if root.list_names(&handle, directory)? != expected_names {
        return Err(BridgeError::Conflict(
            "archive member name set is incomplete or contains foreign entries".into(),
        ));
    }
    let manifest_bytes = root.read(&format!("{directory}/archive-manifest.json"))?;
    let manifest: ArchiveManifest = serde_json::from_slice(&manifest_bytes)?;
    let payload = root.read(&format!("{directory}/{payload_name}"))?;
    let expected_members = archive_members(capture);
    let expected_fingerprints = if options.plaintext {
        Vec::new()
    } else {
        vec![options.age_recipient.clone().unwrap_or_default()]
    };
    let expected_ack = options.plaintext.then_some(true);
    let archive_sha256 = hex_sha256(&payload);
    let manifest_sha256 = hex_sha256(&manifest_bytes);
    let archive_path = format!(
        "{}/{payload_name}",
        archive_directory(&journal.conversion_id)
    );
    if manifest.schema != ARCHIVE_SCHEMA
        || manifest.conversion_id != journal.conversion_id
        || manifest.source_schema != capture.schema_version
        || manifest.confidentiality_mode != expected_mode
        || manifest.recipient_fingerprints != expected_fingerprints
        || manifest.plaintext_risk_acknowledged != expected_ack
        || manifest.members != expected_members
        || manifest.standalone_backup_sha256 != capture.standalone_backup_sha256
        || manifest.archive_sha256 != archive_sha256
        || manifest.custody != "repository-owner-indefinite-write-once"
        || journal.archive_sha256.as_deref() != Some(archive_sha256.as_str())
        || journal.archive_manifest_sha256.as_deref() != Some(manifest_sha256.as_str())
        || journal.archive_path.as_deref() != Some(archive_path.as_str())
        || journal.capture_members_sha256 != capture_members_digest(capture)
        || journal.export_sha256.as_deref() != Some(hex_sha256(export_bytes).as_str())
    {
        return Err(BridgeError::Conflict(
            "existing archive is not authorized by the matching authenticated journal and exact evidence set"
                .into(),
        ));
    }
    Ok(ArchiveEvidence {
        path: archive_path,
        archive_sha256,
        manifest_sha256,
        capture_members_sha256: capture_members_digest(capture),
        export_sha256: hex_sha256(export_bytes),
        confidentiality_mode: manifest.confidentiality_mode,
        recipient_fingerprints: manifest.recipient_fingerprints,
        plaintext_risk_acknowledged: manifest.plaintext_risk_acknowledged,
    })
}

fn expected_manifest(
    conversion_id: &str,
    capture: &Capture,
    mode: &str,
    recipient_fingerprints: Vec<String>,
    plaintext_risk_acknowledged: Option<bool>,
    archive_sha256: String,
) -> ArchiveManifest {
    ArchiveManifest {
        schema: ARCHIVE_SCHEMA.into(),
        conversion_id: conversion_id.into(),
        source_schema: capture.schema_version,
        confidentiality_mode: mode.into(),
        recipient_fingerprints,
        plaintext_risk_acknowledged,
        members: archive_members(capture),
        standalone_backup_sha256: capture.standalone_backup_sha256.clone(),
        archive_sha256,
        custody: "repository-owner-indefinite-write-once".into(),
    }
}

fn archive_members(capture: &Capture) -> Vec<ArchiveMember> {
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
    members.sort_by(|left, right| left.path.cmp(&right.path));
    members
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
            name: "conversion.bin",
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
        name: "conversion.age",
        bytes: ciphertext,
        mode: "encrypted-age-x25519".into(),
        fingerprints: vec![recipient_text.clone()],
        acknowledged: None,
    })
}

fn expected_mode(options: &ArchiveOptions) -> Result<&'static str> {
    if options.plaintext {
        if !options.plaintext_risk_acknowledged {
            return Err(BridgeError::Usage(
                "plaintext archive requires the separate risk acknowledgement".into(),
            ));
        }
        Ok("plaintext-explicit-override")
    } else if options.age_recipient.is_some() {
        Ok("encrypted-age-x25519")
    } else {
        Err(BridgeError::Usage(
            "encrypted archive requires an age recipient".into(),
        ))
    }
}

fn directory_exists(root: &SecureRoot, relative: &str) -> Result<bool> {
    match root.open_dir(relative, false, true) {
        Ok(_) => Ok(true),
        Err(BridgeError::Errno(error)) if error == rustix::io::Errno::NOENT => Ok(false),
        Err(error) => Err(error),
    }
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
    let mut output = b"repository-harness-v0-archive-payload/v1\0".to_vec();
    for (name, bytes) in entries {
        let name = name.as_bytes();
        output.extend_from_slice(&(name.len() as u32).to_be_bytes());
        output.extend_from_slice(name);
        output.extend_from_slice(&(bytes.len() as u64).to_be_bytes());
        output.extend_from_slice(bytes);
    }
    Ok(output)
}

fn staging_directory(conversion_id: &str) -> String {
    format!(".harness/recovery/v0-conversion/{conversion_id}.archive-staging")
}

fn archive_directory(conversion_id: &str) -> String {
    format!(".harness/legacy/v0-conversion/{conversion_id}")
}

pub fn archive_manifest_path(root: &Path, conversion_id: &str) -> PathBuf {
    root.join(archive_directory(conversion_id))
        .join("archive-manifest.json")
}
