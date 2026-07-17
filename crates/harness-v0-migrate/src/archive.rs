use std::fs::{File, OpenOptions};
use std::io::Write;
use std::iter;
use std::path::{Path, PathBuf};
use std::str::FromStr;

use age::x25519;
use serde::{Deserialize, Serialize};

use crate::capture::{hex_sha256, Capture};
use crate::interface::ArchiveOptions;
use crate::{BridgeError, Result};

pub const ARCHIVE_SCHEMA: &str = "repository-harness-v0-archive-manifest/v1";

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
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
    pub confidentiality_mode: String,
    pub recipient_fingerprints: Vec<String>,
    pub plaintext_risk_acknowledged: Option<bool>,
}

pub fn create(
    root: &Path,
    conversion_id: &str,
    capture: &Capture,
    export_bytes: &[u8],
    options: &ArchiveOptions,
) -> Result<ArchiveEvidence> {
    let archive_root = root
        .join(".harness/legacy/v0-conversion")
        .join(conversion_id);
    if archive_root.exists() {
        return verify_existing(&archive_root, conversion_id, capture, options);
    }
    ensure_safe_directory(root, ".harness")?;
    ensure_safe_directory(root, ".harness/legacy")?;
    ensure_safe_directory(root, ".harness/legacy/v0-conversion")?;

    let staging_parent = root.join(".harness/recovery/v0-conversion");
    ensure_safe_directory(root, ".harness/recovery")?;
    ensure_safe_directory(root, ".harness/recovery/v0-conversion")?;
    let staging = staging_parent.join(format!("{conversion_id}.archive-staging"));
    if staging.exists() {
        return Err(BridgeError::Conflict(
            "archive staging already exists; resume with the matching journal".into(),
        ));
    }
    std::fs::create_dir(&staging)?;

    let payload = encode_payload(capture, export_bytes)?;
    let (payload_name, payload_bytes, mode, fingerprints, acknowledged) = if options.plaintext {
        (
            "conversion.bin",
            payload,
            "plaintext-explicit-override".to_owned(),
            Vec::new(),
            Some(true),
        )
    } else {
        let recipient_text = options.age_recipient.as_ref().ok_or_else(|| {
            BridgeError::Usage("encrypted archive requires an age recipient".into())
        })?;
        let recipient = x25519::Recipient::from_str(recipient_text).map_err(|error| {
            BridgeError::Usage(format!("invalid age/X25519 recipient: {error}"))
        })?;
        let encryptor = age::Encryptor::with_recipients(iter::once(&recipient as _))?;
        let mut ciphertext = Vec::new();
        let mut writer = encryptor.wrap_output(&mut ciphertext)?;
        writer.write_all(&payload)?;
        writer.finish()?;
        (
            "conversion.age",
            ciphertext,
            "encrypted-age-x25519".to_owned(),
            vec![recipient_text.clone()],
            None,
        )
    };
    let archive_sha256 = hex_sha256(&payload_bytes);
    write_new_synced(&staging.join(payload_name), &payload_bytes)?;
    let manifest = ArchiveManifest {
        schema: ARCHIVE_SCHEMA.into(),
        conversion_id: conversion_id.into(),
        source_schema: capture.schema_version,
        confidentiality_mode: mode.clone(),
        recipient_fingerprints: fingerprints.clone(),
        plaintext_risk_acknowledged: acknowledged,
        members: capture
            .members
            .iter()
            .map(|member| ArchiveMember {
                path: format!("raw/{}", member.path),
                sha256: member.sha256.clone(),
                bytes: member.bytes,
                capture: "pre-copy-post-equal".into(),
            })
            .collect(),
        standalone_backup_sha256: capture.standalone_backup_sha256.clone(),
        archive_sha256: archive_sha256.clone(),
        custody: "repository-owner-indefinite-write-once".into(),
    };
    let mut manifest_bytes = serde_json::to_vec(&manifest)?;
    manifest_bytes.push(b'\n');
    write_new_synced(&staging.join("archive-manifest.json"), &manifest_bytes)?;
    sync_directory(&staging)?;
    std::fs::rename(&staging, &archive_root)?;
    sync_directory(archive_root.parent().expect("archive has parent"))?;
    Ok(ArchiveEvidence {
        path: format!(".harness/legacy/v0-conversion/{conversion_id}/{payload_name}"),
        archive_sha256,
        confidentiality_mode: mode,
        recipient_fingerprints: fingerprints,
        plaintext_risk_acknowledged: acknowledged,
    })
}

fn verify_existing(
    path: &Path,
    conversion_id: &str,
    capture: &Capture,
    options: &ArchiveOptions,
) -> Result<ArchiveEvidence> {
    let manifest: ArchiveManifest =
        serde_json::from_slice(&std::fs::read(path.join("archive-manifest.json"))?)?;
    if manifest.schema != ARCHIVE_SCHEMA
        || manifest.conversion_id != conversion_id
        || manifest.source_schema != capture.schema_version
        || manifest.standalone_backup_sha256 != capture.standalone_backup_sha256
        || manifest.custody != "repository-owner-indefinite-write-once"
    {
        return Err(BridgeError::Conflict(
            "existing conversion archive does not match current evidence".into(),
        ));
    }
    let expected_mode = if options.plaintext {
        "plaintext-explicit-override"
    } else {
        "encrypted-age-x25519"
    };
    if manifest.confidentiality_mode != expected_mode
        || (!options.plaintext
            && manifest.recipient_fingerprints
                != vec![options.age_recipient.clone().unwrap_or_default()])
    {
        return Err(BridgeError::Conflict(
            "existing archive confidentiality decision differs".into(),
        ));
    }
    let name = if options.plaintext {
        "conversion.bin"
    } else {
        "conversion.age"
    };
    let bytes = std::fs::read(path.join(name))?;
    if hex_sha256(&bytes) != manifest.archive_sha256 {
        return Err(BridgeError::Conflict(
            "existing write-once archive payload was tampered".into(),
        ));
    }
    Ok(ArchiveEvidence {
        path: format!(".harness/legacy/v0-conversion/{conversion_id}/{name}"),
        archive_sha256: manifest.archive_sha256,
        confidentiality_mode: manifest.confidentiality_mode,
        recipient_fingerprints: manifest.recipient_fingerprints,
        plaintext_risk_acknowledged: manifest.plaintext_risk_acknowledged,
    })
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

fn ensure_safe_directory(root: &Path, relative: &str) -> Result<()> {
    let path = root.join(relative);
    if path.exists() {
        let metadata = std::fs::symlink_metadata(&path)?;
        if !metadata.is_dir() || metadata.file_type().is_symlink() {
            return Err(BridgeError::Conflict(format!(
                "conversion path is not a no-follow directory: {relative}"
            )));
        }
    } else {
        std::fs::create_dir(&path)?;
    }
    Ok(())
}

fn write_new_synced(path: &Path, bytes: &[u8]) -> Result<()> {
    let mut file = OpenOptions::new().write(true).create_new(true).open(path)?;
    file.write_all(bytes)?;
    file.sync_all()?;
    Ok(())
}

fn sync_directory(path: &Path) -> Result<()> {
    File::open(path)?.sync_all()?;
    Ok(())
}

pub fn archive_manifest_path(root: &Path, conversion_id: &str) -> PathBuf {
    root.join(".harness/legacy/v0-conversion")
        .join(conversion_id)
        .join("archive-manifest.json")
}
