use std::collections::BTreeSet;
use std::fs::File;
use std::io::{Read, Seek, SeekFrom, Write};
use std::path::{Path, PathBuf};
use std::time::Duration;

use rusqlite::{backup::Backup, Connection, OpenFlags};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::{BridgeError, Result};

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct CapturedMember {
    pub path: String,
    pub category: String,
    pub sha256: String,
    pub bytes: u64,
    #[serde(skip)]
    pub captured_bytes: Vec<u8>,
}

#[derive(Debug)]
pub struct Capture {
    pub schema_version: u32,
    pub members: Vec<CapturedMember>,
    pub unknown_metadata: Vec<String>,
    pub standalone_backup: Vec<u8>,
    pub standalone_backup_sha256: String,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct Identity {
    device: u64,
    inode: u64,
    size: u64,
}

pub fn capture(root: &Path) -> Result<Capture> {
    #[cfg(not(unix))]
    {
        let _ = root;
        return Err(BridgeError::Unsupported(
            "descriptor-anchored V0 capture is unavailable on this platform; Phase 7 remains closed"
                .into(),
        ));
    }
    #[cfg(unix)]
    capture_unix(root)
}

#[cfg(unix)]
fn capture_unix(root: &Path) -> Result<Capture> {
    use rustix::fs::{fcntl_lock, open, openat, FlockOperation, Mode, OFlags};

    let root_handle = open(
        root,
        OFlags::RDONLY | OFlags::DIRECTORY | OFlags::NOFOLLOW | OFlags::CLOEXEC,
        Mode::empty(),
    )?;
    let root_identity = directory_identity(&root_handle)?;
    let db = openat(
        &root_handle,
        "harness.db",
        OFlags::RDONLY | OFlags::NOFOLLOW | OFlags::CLOEXEC,
        Mode::empty(),
    )
    .map_err(|_| {
        BridgeError::Unsupported("recognized repository-root harness.db is absent".into())
    })?;
    let db = File::from(db);
    let mut sources = vec![(
        "harness.db".to_owned(),
        "filesystem.harness.db".to_owned(),
        db,
    )];

    for (name, category) in [
        ("harness.db-wal", "filesystem.harness.db-wal"),
        ("harness.db-shm", "filesystem.harness.db-shm-forensic-only"),
    ] {
        if let Ok(handle) = openat(
            &root_handle,
            name,
            OFlags::RDONLY | OFlags::NOFOLLOW | OFlags::CLOEXEC,
            Mode::empty(),
        ) {
            sources.push((name.into(), category.into(), File::from(handle)));
        }
    }
    let captured_sqlite_names = sources
        .iter()
        .map(|(path, _, _)| path.clone())
        .collect::<BTreeSet<_>>();
    for (path, _, handle) in &sources {
        fcntl_lock(handle, FlockOperation::NonBlockingLockShared).map_err(|error| {
            BridgeError::Conflict(format!(
                "source V0 database is not quiesced; an SQLite writer holds a conflicting lock on {path}: {error}"
            ))
        })?;
    }

    let mut recognized_metadata = BTreeSet::new();
    recognized_metadata.insert("changesets".to_owned());
    recognized_metadata.insert("manifest.json".to_owned());
    recognized_metadata.insert("v0-provenance.json".to_owned());
    let harness_dir_path = root.join(".harness");
    let mut unknown_metadata = Vec::new();
    let harness_handle = openat(
        &root_handle,
        ".harness",
        OFlags::RDONLY | OFlags::DIRECTORY | OFlags::NOFOLLOW | OFlags::CLOEXEC,
        Mode::empty(),
    )
    .ok();
    let harness_identity = harness_handle
        .as_ref()
        .map(directory_identity)
        .transpose()?;
    let mut changeset_handle = None;
    let mut changeset_identity = None;
    if harness_dir_path.is_dir() {
        for entry in std::fs::read_dir(&harness_dir_path)? {
            let entry = entry?;
            let name = entry.file_name().into_string().map_err(|_| {
                BridgeError::Unsupported("non-UTF-8 .harness metadata is unowned".into())
            })?;
            if !recognized_metadata.contains(&name) && name != "legacy" && name != "recovery" {
                unknown_metadata.push(format!(".harness/{name}"));
            }
        }
    }
    unknown_metadata.sort();

    if let Some(harness_handle) = &harness_handle {
        if let Ok(provenance) = openat(
            harness_handle,
            "v0-provenance.json",
            OFlags::RDONLY | OFlags::NOFOLLOW | OFlags::CLOEXEC,
            Mode::empty(),
        ) {
            sources.push((
                ".harness/v0-provenance.json".into(),
                "filesystem.recognized-installer-provenance".into(),
                File::from(provenance),
            ));
        }
        if let Ok(opened_changeset_dir) = openat(
            harness_handle,
            "changesets",
            OFlags::RDONLY | OFlags::DIRECTORY | OFlags::NOFOLLOW | OFlags::CLOEXEC,
            Mode::empty(),
        ) {
            changeset_identity = Some(directory_identity(&opened_changeset_dir)?);
            let changeset_path = harness_dir_path.join("changesets");
            let mut names = Vec::new();
            for entry in std::fs::read_dir(&changeset_path)? {
                let entry = entry?;
                let name = entry.file_name().into_string().map_err(|_| {
                    BridgeError::Unsupported("non-UTF-8 changeset name is unsupported".into())
                })?;
                if name.ends_with(".changeset.jsonl") {
                    names.push(name);
                } else {
                    unknown_metadata.push(format!(".harness/changesets/{name}"));
                }
            }
            names.sort();
            for name in names {
                let handle = openat(
                    &opened_changeset_dir,
                    name.as_str(),
                    OFlags::RDONLY | OFlags::NOFOLLOW | OFlags::CLOEXEC,
                    Mode::empty(),
                )?;
                sources.push((
                    format!(".harness/changesets/{name}"),
                    "filesystem.recognized-changeset-jsonl".into(),
                    File::from(handle),
                ));
            }
            changeset_handle = Some(opened_changeset_dir);
        }
    }
    unknown_metadata.sort();

    let staging = tempfile::Builder::new()
        .prefix("harness-v0-capture-")
        .tempdir()?;
    let mut members = Vec::new();
    let mut retained_handles = Vec::new();
    for (path, category, mut handle) in sources {
        let before_identity = identity(&handle)?;
        let pre = digest_handle(&mut handle)?;
        let mut captured_bytes = Vec::with_capacity(before_identity.size as usize);
        handle.seek(SeekFrom::Start(0))?;
        handle.read_to_end(&mut captured_bytes)?;
        let copy_digest = hex_sha256(&captured_bytes);
        let post = digest_handle(&mut handle)?;
        let after = identity(&handle)?;
        if before_identity != after
            || pre != copy_digest
            || pre != post
            || before_identity.size != captured_bytes.len() as u64
        {
            return Err(BridgeError::Conflict(format!(
                "source changed during same-handle capture: {path}"
            )));
        }
        if category == "filesystem.recognized-changeset-jsonl" {
            validate_changeset(&captured_bytes)?;
        }
        let destination = staging.path().join(path.replace('/', "__"));
        let mut output = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(destination)?;
        output.write_all(&captured_bytes)?;
        output.sync_all()?;
        members.push(CapturedMember {
            path: path.clone(),
            category,
            sha256: pre,
            bytes: before_identity.size,
            captured_bytes,
        });
        retained_handles.push((path, before_identity, handle));
    }
    let reopened_root = open(
        root,
        OFlags::RDONLY | OFlags::DIRECTORY | OFlags::NOFOLLOW | OFlags::CLOEXEC,
        Mode::empty(),
    )?;
    if directory_identity(&reopened_root)? != root_identity {
        return Err(BridgeError::Conflict(
            "repository-root pathname changed during capture".into(),
        ));
    }
    if let (Some(expected), Some(original)) = (harness_identity, harness_handle.as_ref()) {
        let reopened = openat(
            &root_handle,
            ".harness",
            OFlags::RDONLY | OFlags::DIRECTORY | OFlags::NOFOLLOW | OFlags::CLOEXEC,
            Mode::empty(),
        )?;
        if directory_identity(&reopened)? != expected || directory_identity(original)? != expected {
            return Err(BridgeError::Conflict(
                ".harness ancestor changed during capture".into(),
            ));
        }
    }
    if let (Some(expected), Some(original), Some(parent)) = (
        changeset_identity,
        changeset_handle.as_ref(),
        harness_handle.as_ref(),
    ) {
        let reopened = openat(
            parent,
            "changesets",
            OFlags::RDONLY | OFlags::DIRECTORY | OFlags::NOFOLLOW | OFlags::CLOEXEC,
            Mode::empty(),
        )?;
        if directory_identity(&reopened)? != expected || directory_identity(original)? != expected {
            return Err(BridgeError::Conflict(
                "changeset ancestor changed during capture".into(),
            ));
        }
    }
    for (path, expected, retained) in &retained_handles {
        let reopened = if let Some(name) = path.strip_prefix(".harness/changesets/") {
            openat(
                changeset_handle.as_ref().ok_or_else(|| {
                    BridgeError::Conflict("changeset parent handle is absent".into())
                })?,
                name,
                OFlags::RDONLY | OFlags::NOFOLLOW | OFlags::CLOEXEC,
                Mode::empty(),
            )?
        } else if path == ".harness/v0-provenance.json" {
            openat(
                harness_handle.as_ref().ok_or_else(|| {
                    BridgeError::Conflict(".harness parent handle is absent".into())
                })?,
                "v0-provenance.json",
                OFlags::RDONLY | OFlags::NOFOLLOW | OFlags::CLOEXEC,
                Mode::empty(),
            )?
        } else {
            openat(
                &root_handle,
                path.as_str(),
                OFlags::RDONLY | OFlags::NOFOLLOW | OFlags::CLOEXEC,
                Mode::empty(),
            )?
        };
        let reopened = File::from(reopened);
        if identity(&reopened)? != *expected || identity(retained)? != *expected {
            return Err(BridgeError::Conflict(format!(
                "source pathname identity changed during capture: {path}"
            )));
        }
    }
    for name in ["harness.db", "harness.db-wal", "harness.db-shm"] {
        let present = openat(
            &root_handle,
            name,
            OFlags::RDONLY | OFlags::NOFOLLOW | OFlags::CLOEXEC,
            Mode::empty(),
        )
        .is_ok();
        if present != captured_sqlite_names.contains(name) {
            return Err(BridgeError::Conflict(format!(
                "SQLite source set changed during capture: {name}"
            )));
        }
    }
    members.sort_by(|left, right| left.path.cmp(&right.path));

    let db_member = members
        .iter()
        .find(|member| member.path == "harness.db")
        .ok_or_else(|| BridgeError::Unsupported("harness.db capture is absent".into()))?;
    let staged_db = staging.path().join("recovery.db");
    std::fs::write(&staged_db, &db_member.captured_bytes)?;
    if let Some(wal) = members
        .iter()
        .find(|member| member.path == "harness.db-wal")
    {
        std::fs::write(staging.path().join("recovery.db-wal"), &wal.captured_bytes)?;
    }

    let source = Connection::open_with_flags(
        &staged_db,
        OpenFlags::SQLITE_OPEN_READ_ONLY | OpenFlags::SQLITE_OPEN_URI,
    )?;
    source.pragma_update(None, "query_only", true)?;
    let schema_version = validate_schema(&source)?;
    let standalone_path = staging.path().join("standalone.db");
    let mut destination = Connection::open(&standalone_path)?;
    let backup = Backup::new(&source, &mut destination)?;
    backup.run_to_completion(128, Duration::from_millis(1), None)?;
    drop(backup);
    destination.close().map_err(|(_, error)| error)?;
    drop(source);
    let standalone_backup = std::fs::read(standalone_path)?;
    let standalone_backup_sha256 = hex_sha256(&standalone_backup);
    Ok(Capture {
        schema_version,
        members,
        unknown_metadata,
        standalone_backup,
        standalone_backup_sha256,
    })
}

#[cfg(unix)]
fn identity(file: &File) -> std::io::Result<Identity> {
    use std::os::unix::fs::MetadataExt;
    let metadata = file.metadata()?;
    if !metadata.is_file() {
        return Err(std::io::Error::other(
            "captured input is not a regular file",
        ));
    }
    Ok(Identity {
        device: metadata.dev(),
        inode: metadata.ino(),
        size: metadata.len(),
    })
}

#[cfg(unix)]
fn directory_identity(file: impl std::os::fd::AsFd) -> Result<(u64, u64)> {
    let stat = rustix::fs::fstat(file)?;
    Ok((stat.st_dev as u64, stat.st_ino as u64))
}

fn digest_handle(file: &mut File) -> std::io::Result<String> {
    file.seek(SeekFrom::Start(0))?;
    let mut digest = Sha256::new();
    let mut buffer = [0_u8; 64 * 1024];
    loop {
        let count = file.read(&mut buffer)?;
        if count == 0 {
            break;
        }
        digest.update(&buffer[..count]);
    }
    Ok(format!("{:x}", digest.finalize()))
}

fn validate_schema(connection: &Connection) -> Result<u32> {
    let versions = connection
        .prepare("SELECT version FROM schema_version ORDER BY version")?
        .query_map([], |row| row.get::<_, u32>(0))?
        .collect::<std::result::Result<Vec<_>, _>>()?;
    let maximum = versions.last().copied().ok_or_else(|| {
        BridgeError::Unsupported("schema_version has no applied migration".into())
    })?;
    if !(1..=13).contains(&maximum) || versions != (1..=maximum).collect::<Vec<_>>() {
        return Err(BridgeError::Unsupported(
            "V0 schema_version must be a gap-free sequence within 1..=13".into(),
        ));
    }
    let expected = expected_tables(maximum);
    let mut statement = connection.prepare(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name",
    )?;
    let actual = statement
        .query_map([], |row| row.get::<_, String>(0))?
        .collect::<std::result::Result<BTreeSet<_>, _>>()?;
    if actual != expected {
        return Err(BridgeError::Unsupported(format!(
            "V0 schema {maximum} has unknown, missing, or foreign tables"
        )));
    }
    Ok(maximum)
}

fn expected_tables(version: u32) -> BTreeSet<String> {
    let mut names = [
        "backlog",
        "decision",
        "intake",
        "schema_version",
        "story",
        "trace",
    ]
    .into_iter()
    .map(str::to_owned)
    .collect::<BTreeSet<_>>();
    for (minimum, table) in [
        (3, "tool"),
        (4, "intervention"),
        (6, "changeset_applied"),
        (7, "story_dependency"),
        (8, "story_hierarchy"),
        (9, "proposal_evidence_link"),
        (9, "audit_evidence_episode"),
        (9, "backlog_outcome_observation"),
        (10, "story_backlog_link"),
        (11, "legacy_evidence_snapshot"),
    ] {
        if version >= minimum {
            names.insert(table.to_owned());
        }
    }
    names
}

fn validate_changeset(bytes: &[u8]) -> Result<()> {
    let text = std::str::from_utf8(bytes)
        .map_err(|_| BridgeError::Unsupported("changeset is not UTF-8".into()))?;
    let mut values = Vec::new();
    for (index, line) in text.lines().enumerate() {
        if line.trim().is_empty() {
            continue;
        }
        let value = crate::strict_json::parse(line.as_bytes()).map_err(|error| {
            BridgeError::Unsupported(format!("invalid changeset line {}: {error}", index + 1))
        })?;
        values.push(value);
    }
    let header = values
        .first()
        .and_then(serde_json::Value::as_object)
        .ok_or_else(|| BridgeError::Unsupported("changeset header is absent".into()))?;
    if header.get("op").and_then(serde_json::Value::as_str) != Some("changeset.header")
        || header.get("version").and_then(serde_json::Value::as_u64) != Some(1)
        || header
            .get("run_id")
            .and_then(serde_json::Value::as_str)
            .is_none_or(|value| value.trim().is_empty())
        || header
            .get("base_schema_version")
            .and_then(serde_json::Value::as_u64)
            .is_none_or(|value| !(1..=13).contains(&value))
    {
        return Err(BridgeError::Unsupported(
            "changeset header is outside the frozen grammar".into(),
        ));
    }
    let operations = [
        "audit.evidence.clear",
        "audit.evidence.open",
        "backlog.add",
        "backlog.close",
        "backlog.complete",
        "backlog.legacy.reconcile",
        "backlog.outcome.observe",
        "backlog.proposal.decision",
        "decision.add",
        "decision.verify",
        "intake.add",
        "intervention.add",
        "legacy.evidence.capture",
        "story.add",
        "story.backlog.link",
        "story.backlog.unlink",
        "story.complete",
        "story.dependency.add",
        "story.dependency.remove",
        "story.hierarchy.add",
        "story.hierarchy.remove",
        "story.update",
        "story.verify",
        "tool.check",
        "tool.register",
        "tool.remove",
        "trace.add",
    ];
    for value in values.iter().skip(1) {
        let object = value.as_object().ok_or_else(|| {
            BridgeError::Unsupported("changeset operation must be an object".into())
        })?;
        let operation = object
            .get("op")
            .and_then(serde_json::Value::as_str)
            .ok_or_else(|| BridgeError::Unsupported("changeset operation name is absent".into()))?;
        let version = object
            .get("version")
            .map(|value| value.as_u64())
            .unwrap_or(Some(1));
        if !operations.contains(&operation) || !matches!(version, Some(1 | 2)) {
            return Err(BridgeError::Unsupported(format!(
                "unknown changeset operation/version: {operation}"
            )));
        }
    }
    Ok(())
}

pub fn hex_sha256(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

pub fn source_digest(capture: &Capture) -> String {
    let mut digest = Sha256::new();
    digest.update(capture.schema_version.to_be_bytes());
    for member in &capture.members {
        digest.update(member.path.as_bytes());
        digest.update([0]);
        digest.update(member.category.as_bytes());
        digest.update([0]);
        digest.update(member.sha256.as_bytes());
        digest.update(member.bytes.to_be_bytes());
    }
    format!("{:x}", digest.finalize())
}

pub fn safe_output_path(root: &Path, value: &str) -> Result<PathBuf> {
    let path = Path::new(value);
    if path.is_absolute()
        || value.is_empty()
        || path.components().any(|component| {
            matches!(
                component,
                std::path::Component::ParentDir
                    | std::path::Component::RootDir
                    | std::path::Component::Prefix(_)
            )
        })
    {
        return Err(BridgeError::Usage(
            "output path must be safe and repository-relative".into(),
        ));
    }
    Ok(root.join(path))
}
