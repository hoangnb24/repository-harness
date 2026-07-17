use std::collections::BTreeSet;
use std::fs::File;
use std::io::{Read, Seek, SeekFrom, Write};
use std::path::Path;
use std::time::Duration;

use rusqlite::{backup::Backup, Connection, OpenFlags};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::secure_fs::SecureRoot;
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

#[derive(Deserialize)]
struct ChangesetMatrix {
    operations: Vec<MatrixOperation>,
}

#[derive(Deserialize)]
struct MatrixOperation {
    op: String,
    versions: Vec<u64>,
    #[serde(default)]
    v2_requires: Vec<String>,
    #[serde(default)]
    v2_validates: Vec<String>,
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
    {
        let root = SecureRoot::open(root)?;
        capture_pinned(&root)
    }
}

#[cfg(unix)]
pub(crate) fn capture_pinned(root: &SecureRoot) -> Result<Capture> {
    use rustix::fs::{fcntl_lock, fstat, FlockOperation};

    root.validate_root()?;
    let root_names_before = root.list_names_fd(root.root_descriptor(), ".")?;
    let db = File::from(root.open_required_regular("harness.db")?);
    let mut sources = vec![(
        "harness.db".to_owned(),
        "filesystem.harness.db".to_owned(),
        db,
    )];

    for (name, category) in [
        ("harness.db-wal", "filesystem.harness.db-wal"),
        ("harness.db-shm", "filesystem.harness.db-shm-forensic-only"),
    ] {
        if let Some(handle) = root.open_optional_regular(name)? {
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
    recognized_metadata.insert("v0-provenance.json".to_owned());
    let mut unknown_metadata = Vec::new();
    let harness_handle = match root.open_dir_fd(".harness", false, false) {
        Ok(handle) => Some(handle),
        Err(BridgeError::Errno(error)) if error == rustix::io::Errno::NOENT => None,
        Err(error) => return Err(error),
    };
    let harness_identity = harness_handle
        .as_ref()
        .map(directory_identity)
        .transpose()?;
    let harness_names_before = harness_handle
        .as_ref()
        .map(|handle| root.list_names_fd(handle, ".harness"))
        .transpose()?;
    let mut changeset_handle = None;
    let mut changeset_identity = None;
    let mut changeset_names_before = None;
    if let Some(names) = &harness_names_before {
        for name in names {
            if !recognized_metadata.contains(name.as_str()) {
                unknown_metadata.push(format!(".harness/{name}"));
            }
        }
    }
    unknown_metadata.sort();

    if harness_handle.is_some() {
        if let Some(provenance) = root.open_optional_regular(".harness/v0-provenance.json")? {
            sources.push((
                ".harness/v0-provenance.json".into(),
                "filesystem.recognized-installer-provenance".into(),
                File::from(provenance),
            ));
        }
        let opened_changeset_dir = match root.open_dir_fd(".harness/changesets", false, false) {
            Ok(handle) => Some(handle),
            Err(BridgeError::Errno(error)) if error == rustix::io::Errno::NOENT => None,
            Err(error) => return Err(error),
        };
        if let Some(opened_changeset_dir) = opened_changeset_dir {
            changeset_identity = Some(directory_identity(&opened_changeset_dir)?);
            let complete_names =
                root.list_names_fd(&opened_changeset_dir, ".harness/changesets")?;
            changeset_names_before = Some(complete_names.clone());
            let mut names = Vec::new();
            for name in complete_names {
                if name.ends_with(".changeset.jsonl") {
                    names.push(name);
                } else {
                    unknown_metadata.push(format!(".harness/changesets/{name}"));
                }
            }
            names.sort();
            for name in names {
                let relative = format!(".harness/changesets/{name}");
                let handle = root.open_required_regular(&relative)?;
                sources.push((
                    relative,
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
    root.validate_root()?;
    if let (Some(expected), Some(original)) = (harness_identity, harness_handle.as_ref()) {
        let reopened = root.open_dir_fd(".harness", false, false)?;
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
        let _ = parent;
        let reopened = root.open_dir_fd(".harness/changesets", false, false)?;
        if directory_identity(&reopened)? != expected || directory_identity(original)? != expected {
            return Err(BridgeError::Conflict(
                "changeset ancestor changed during capture".into(),
            ));
        }
    }
    for (path, expected, retained) in &retained_handles {
        let reopened = root.open_required_regular(path)?;
        let reopened = File::from(reopened);
        if identity(&reopened)? != *expected || identity(retained)? != *expected {
            return Err(BridgeError::Conflict(format!(
                "source pathname identity changed during capture: {path}"
            )));
        }
    }
    for name in ["harness.db", "harness.db-wal", "harness.db-shm"] {
        let present = root.open_optional_regular(name)?.is_some();
        if present != captured_sqlite_names.contains(name) {
            return Err(BridgeError::Conflict(format!(
                "SQLite source set changed during capture: {name}"
            )));
        }
    }
    if root.list_names_fd(root.root_descriptor(), ".")? != root_names_before {
        return Err(BridgeError::Conflict(
            "repository-root name set changed during capture".into(),
        ));
    }
    if let (Some(handle), Some(expected)) = (&harness_handle, &harness_names_before) {
        if root.list_names_fd(handle, ".harness")? != *expected {
            return Err(BridgeError::Conflict(
                ".harness name set changed during capture".into(),
            ));
        }
    }
    if let (Some(handle), Some(expected)) = (&changeset_handle, &changeset_names_before) {
        if root.list_names_fd(handle, ".harness/changesets")? != *expected {
            return Err(BridgeError::Conflict(
                "changeset name set changed during capture".into(),
            ));
        }
    }
    for (_, _, handle) in &retained_handles {
        let _ = fstat(handle).map_err(BridgeError::from)?;
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

#[cfg(not(unix))]
pub(crate) fn capture_pinned(_root: &SecureRoot) -> Result<Capture> {
    Err(BridgeError::Unsupported(
        "descriptor-anchored V0 capture is unavailable on this platform; Phase 7 remains closed"
            .into(),
    ))
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
    let expected = expected_schema_objects(maximum)?;
    let actual = schema_objects(connection)?;
    if actual != expected {
        return Err(BridgeError::Unsupported(format!(
            "V0 schema {maximum} has unknown, missing, or altered tables, columns, indexes, views, or triggers"
        )));
    }
    Ok(maximum)
}

fn schema_objects(connection: &Connection) -> Result<BTreeSet<(String, String, String, String)>> {
    let mut statement = connection.prepare(
        "SELECT type, name, tbl_name, COALESCE(sql, '')
         FROM sqlite_master
         WHERE name NOT LIKE 'sqlite_%'
           AND type IN ('table','index','view','trigger')
         ORDER BY type, name",
    )?;
    let objects = statement
        .query_map([], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, String>(2)?,
                normalize_schema_sql(&row.get::<_, String>(3)?),
            ))
        })?
        .collect::<std::result::Result<BTreeSet<_>, _>>()?;
    Ok(objects)
}

fn normalize_schema_sql(value: &str) -> String {
    value.split_whitespace().collect::<Vec<_>>().join(" ")
}

fn expected_schema_objects(version: u32) -> Result<BTreeSet<(String, String, String, String)>> {
    const MIGRATIONS: [&str; 13] = [
        include_str!("../../../scripts/schema/001-init.sql"),
        include_str!("../../../scripts/schema/002-story-verify.sql"),
        include_str!("../../../scripts/schema/003-tool-registry.sql"),
        include_str!("../../../scripts/schema/004-intervention.sql"),
        include_str!("../../../scripts/schema/005-tool-extensions.sql"),
        include_str!("../../../scripts/schema/006-changeset-applied.sql"),
        include_str!("../../../scripts/schema/007-story-dependencies.sql"),
        include_str!("../../../scripts/schema/008-story-hierarchy.sql"),
        include_str!("../../../scripts/schema/009-improvement-identity.sql"),
        include_str!("../../../scripts/schema/010-story-backlog-links.sql"),
        include_str!("../../../scripts/schema/011-legacy-evidence-snapshots.sql"),
        include_str!("../../../scripts/schema/012-review-finding-closure.sql"),
        include_str!("../../../scripts/schema/013-changeset-content-sha.sql"),
    ];
    let expected = Connection::open_in_memory()?;
    for migration in MIGRATIONS.iter().take(version as usize) {
        expected.execute_batch(migration)?;
    }
    schema_objects(&expected)
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
    let header_keys = header.keys().map(String::as_str).collect::<BTreeSet<_>>();
    if header_keys != BTreeSet::from(["base_schema_version", "op", "run_id", "version"]) {
        return Err(BridgeError::Unsupported(
            "changeset header has unknown or missing members".into(),
        ));
    }
    let matrix: ChangesetMatrix = serde_json::from_str(include_str!(
        "../../../release/contracts/v1/v0-changeset-operation-matrix.json"
    ))?;
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
        let Some(rule) = matrix.operations.iter().find(|rule| rule.op == operation) else {
            return Err(BridgeError::Unsupported(format!(
                "unknown changeset operation/version: {operation}"
            )));
        };
        let Some(version) = version else {
            return Err(BridgeError::Unsupported(format!(
                "unknown changeset operation/version: {operation}"
            )));
        };
        if !rule.versions.contains(&version) {
            return Err(BridgeError::Unsupported(format!(
                "unknown changeset operation/version: {operation}"
            )));
        }
        if version == 2 {
            validate_v2_rule(object, rule)?;
        }
    }
    Ok(())
}

fn validate_v2_rule(
    operation: &serde_json::Map<String, serde_json::Value>,
    rule: &MatrixOperation,
) -> Result<()> {
    let payload = operation
        .get("payload")
        .and_then(serde_json::Value::as_object)
        .ok_or_else(|| BridgeError::Unsupported("version 2 operation payload is absent".into()))?;
    for requirement in &rule.v2_requires {
        match requirement.as_str() {
            "payload.completed_at" => require_timestamp(payload, "completed_at")?,
            "payload.linked_at" => require_timestamp(payload, "linked_at")?,
            "payload.verified_at" => require_timestamp(payload, "verified_at")?,
            "payload.evidence[].observed_at when evidence exists" => {
                if let Some(evidence) = payload.get("evidence") {
                    let evidence = evidence.as_array().ok_or_else(|| {
                        BridgeError::Unsupported("payload.evidence must be an array".into())
                    })?;
                    for item in evidence {
                        let item = item.as_object().ok_or_else(|| {
                            BridgeError::Unsupported(
                                "payload.evidence item must be an object".into(),
                            )
                        })?;
                        require_timestamp(item, "observed_at")?;
                    }
                }
            }
            unknown => {
                return Err(BridgeError::Unsupported(format!(
                    "unimplemented frozen v2 requirement: {unknown}"
                )))
            }
        }
    }
    for validation in &rule.v2_validates {
        match validation.as_str() {
            "payload.accepted_at" => optional_timestamp(payload, "accepted_at")?,
            "payload.closed_at" => optional_timestamp(payload, "closed_at")?,
            "payload.evidence[].observed_at" => {
                if let Some(evidence) = payload.get("evidence") {
                    let evidence = evidence.as_array().ok_or_else(|| {
                        BridgeError::Unsupported("payload.evidence must be an array".into())
                    })?;
                    for item in evidence {
                        let item = item.as_object().ok_or_else(|| {
                            BridgeError::Unsupported(
                                "payload.evidence item must be an object".into(),
                            )
                        })?;
                        require_timestamp(item, "observed_at")?;
                    }
                }
            }
            unknown => {
                return Err(BridgeError::Unsupported(format!(
                    "unimplemented frozen v2 validation: {unknown}"
                )))
            }
        }
    }
    Ok(())
}

fn require_timestamp(
    object: &serde_json::Map<String, serde_json::Value>,
    field: &str,
) -> Result<()> {
    let value = object
        .get(field)
        .and_then(serde_json::Value::as_str)
        .ok_or_else(|| BridgeError::Unsupported(format!("version 2 requires {field}")))?;
    validate_timestamp(value, field)
}

fn optional_timestamp(
    object: &serde_json::Map<String, serde_json::Value>,
    field: &str,
) -> Result<()> {
    if let Some(value) = object.get(field) {
        let value = value.as_str().ok_or_else(|| {
            BridgeError::Unsupported(format!("version 2 {field} must be a timestamp string"))
        })?;
        validate_timestamp(value, field)?;
    }
    Ok(())
}

fn validate_timestamp(value: &str, field: &str) -> Result<()> {
    use chrono::NaiveDateTime;
    let parsed = NaiveDateTime::parse_from_str(value, "%Y-%m-%d %H:%M:%S").map_err(|_| {
        BridgeError::Unsupported(format!(
            "version 2 {field} must use canonical YYYY-MM-DD HH:MM:SS"
        ))
    })?;
    if parsed.format("%Y-%m-%d %H:%M:%S").to_string() != value {
        return Err(BridgeError::Unsupported(format!(
            "version 2 {field} must use canonical YYYY-MM-DD HH:MM:SS"
        )));
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

pub fn capture_members_digest(capture: &Capture) -> String {
    let mut digest = Sha256::new();
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
