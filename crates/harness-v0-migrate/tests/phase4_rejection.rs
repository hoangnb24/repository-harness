use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::sync::Mutex;

use harness_core::application::HarnessCore;
use harness_core::domain::{Command as CoreCommand, RepositoryMode};
use harness_core::infrastructure::{JsonManifestPort, OsFileSystem};
use harness_core::ports::{PortError, ReleaseMaterial, ReleasePort, ReleaseTrustInput, TrustPort};
use harness_v0_migrate::archive::{ArchiveManifest, ARCHIVE_SCHEMA};
use harness_v0_migrate::capture::{capture, hex_sha256};
use harness_v0_migrate::interface::{ArchiveOptions, Command};
use harness_v0_migrate::journal::{self, JournalState};
use harness_v0_migrate::{Bridge, BridgeError};

static ENVIRONMENT: Mutex<()> = Mutex::new(());

struct UnusedRelease;

impl ReleasePort for UnusedRelease {
    fn load(&self) -> Result<ReleaseMaterial, PortError> {
        Err(PortError::ReleaseUnavailable(
            "converted status must not request release material".into(),
        ))
    }
}

impl TrustPort for UnusedRelease {
    fn load(&self) -> Result<ReleaseTrustInput, PortError> {
        Err(PortError::ReleaseUnavailable(
            "converted status must not request trust material".into(),
        ))
    }
}

fn fixtures() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../tests/fixtures/v1-phase4")
        .canonicalize()
        .unwrap()
}

fn copy_fixture(name: &str) -> tempfile::TempDir {
    let temporary = tempfile::tempdir().unwrap();
    copy_tree(&fixtures().join(name), temporary.path());
    temporary
}

fn copy_tree(source: &Path, destination: &Path) {
    for entry in std::fs::read_dir(source).unwrap() {
        let entry = entry.unwrap();
        let target = destination.join(entry.file_name());
        if entry.file_type().unwrap().is_dir() {
            std::fs::create_dir(&target).unwrap();
            copy_tree(&entry.path(), &target);
        } else {
            std::fs::copy(entry.path(), target).unwrap();
        }
    }
}

fn plaintext() -> ArchiveOptions {
    ArchiveOptions {
        age_recipient: None,
        plaintext: true,
        plaintext_risk_acknowledged: true,
    }
}

fn preview(root: &Path) -> (String, String) {
    let report = Bridge::new(root)
        .execute(&Command::Preview { json: true })
        .unwrap();
    (
        report.conversion_id.unwrap(),
        report.preview_sha256.unwrap(),
    )
}

fn apply_until(root: &Path, digest: String, kill_point: &str) -> (String, BridgeError) {
    let (conversion_id, _) = preview(root);
    std::env::set_var("HARNESS_V0_MIGRATE_TEST_KILL_AFTER", kill_point);
    let error = Bridge::new(root)
        .execute(&Command::Apply {
            accepted_preview_sha256: digest,
            archive: plaintext(),
        })
        .unwrap_err();
    std::env::remove_var("HARNESS_V0_MIGRATE_TEST_KILL_AFTER");
    (conversion_id, error)
}

fn tracked_source_snapshot(root: &Path) -> BTreeMap<String, Vec<u8>> {
    let mut snapshot = BTreeMap::new();
    for relative in [
        "harness.db",
        "harness.db-wal",
        "harness.db-shm",
        ".harness/changesets/fixture.changeset.jsonl",
        ".harness/v0-provenance.json",
        "AGENTS.md",
    ] {
        let path = root.join(relative);
        if path.is_file() {
            snapshot.insert(relative.to_owned(), std::fs::read(path).unwrap());
        }
    }
    snapshot
}

#[cfg(unix)]
#[test]
fn optional_inputs_and_changeset_ancestors_fail_closed_instead_of_becoming_absent() {
    use std::os::unix::fs::symlink;

    for relative in ["harness.db-wal", "harness.db-shm"] {
        let temporary = copy_fixture("schema-13");
        let source = temporary.path().join(relative);
        let outside = temporary.path().join(format!("outside-{relative}"));
        std::fs::rename(&source, &outside).unwrap();
        symlink(&outside, &source).unwrap();
        let before = tracked_source_snapshot(temporary.path());
        assert!(
            capture(temporary.path()).is_err(),
            "accepted symlinked {relative}"
        );
        assert_eq!(tracked_source_snapshot(temporary.path()), before);
        assert!(!temporary.path().join(".harness/recovery").exists());
        assert!(!temporary.path().join(".harness/legacy").exists());
    }

    let temporary = copy_fixture("schema-13");
    let changesets = temporary.path().join(".harness/changesets");
    let outside = temporary.path().join("outside-changesets");
    std::fs::rename(&changesets, &outside).unwrap();
    symlink(&outside, &changesets).unwrap();
    assert!(capture(temporary.path()).is_err());
    assert!(!temporary.path().join(".harness/recovery").exists());
    assert!(!temporary.path().join(".harness/legacy").exists());
}

#[test]
fn prepositioned_archive_needs_authenticated_journal_member_and_export_binding() {
    let _guard = ENVIRONMENT
        .lock()
        .unwrap_or_else(|error| error.into_inner());
    std::env::remove_var("HARNESS_V0_MIGRATE_TEST_KILL_AFTER");
    let temporary = copy_fixture("schema-13");
    let captured = capture(temporary.path()).unwrap();
    let (conversion_id, digest) = preview(temporary.path());
    let archive = temporary
        .path()
        .join(format!(".harness/legacy/v0-conversion/{conversion_id}"));
    std::fs::create_dir_all(&archive).unwrap();
    std::fs::write(archive.join("conversion.bin"), []).unwrap();
    let fake = ArchiveManifest {
        schema: ARCHIVE_SCHEMA.into(),
        conversion_id: conversion_id.clone(),
        source_schema: captured.schema_version,
        confidentiality_mode: "plaintext-explicit-override".into(),
        recipient_fingerprints: Vec::new(),
        plaintext_risk_acknowledged: Some(true),
        members: Vec::new(),
        standalone_backup_sha256: captured.standalone_backup_sha256,
        archive_sha256: hex_sha256(&[]),
        custody: "repository-owner-indefinite-write-once".into(),
    };
    std::fs::write(
        archive.join("archive-manifest.json"),
        serde_json::to_vec(&fake).unwrap(),
    )
    .unwrap();

    assert!(matches!(
        Bridge::new(temporary.path()).execute(&Command::Apply {
            accepted_preview_sha256: digest,
            archive: plaintext(),
        }),
        Err(BridgeError::Conflict(_))
    ));
    assert!(!temporary.path().join(".harness/manifest.json").exists());
}

#[test]
fn copied_or_edited_journal_authorizes_zero_mutation() {
    let _guard = ENVIRONMENT
        .lock()
        .unwrap_or_else(|error| error.into_inner());
    std::env::remove_var("HARNESS_V0_MIGRATE_TEST_KILL_AFTER");

    let source = copy_fixture("schema-13");
    let (conversion_id, digest) = preview(source.path());
    let (_, error) = apply_until(source.path(), digest, "detection");
    assert!(matches!(error, BridgeError::KillPoint(_)));

    let copied = copy_fixture("schema-13");
    let source_recovery = journal::path(source.path(), &conversion_id)
        .parent()
        .unwrap()
        .to_path_buf();
    let copied_recovery = journal::path(copied.path(), &conversion_id)
        .parent()
        .unwrap()
        .to_path_buf();
    std::fs::create_dir_all(copied_recovery.parent().unwrap()).unwrap();
    std::fs::create_dir(&copied_recovery).unwrap();
    copy_tree(&source_recovery, &copied_recovery);
    assert!(Bridge::new(copied.path())
        .execute(&Command::Resume {
            conversion_id: conversion_id.clone(),
        })
        .is_err());
    assert!(!copied.path().join(".harness/manifest.json").exists());

    let journal_path = journal::path(source.path(), &conversion_id);
    let mut value: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&journal_path).unwrap()).unwrap();
    value["forged_unknown_field"] = serde_json::json!(true);
    std::fs::write(&journal_path, serde_json::to_vec(&value).unwrap()).unwrap();
    assert!(Bridge::new(source.path())
        .execute(&Command::Resume { conversion_id })
        .is_err());
    assert!(!source.path().join(".harness/manifest.json").exists());
}

#[test]
fn rollback_preflights_all_evidence_before_manifest_removal() {
    let _guard = ENVIRONMENT
        .lock()
        .unwrap_or_else(|error| error.into_inner());
    std::env::remove_var("HARNESS_V0_MIGRATE_TEST_KILL_AFTER");
    let temporary = copy_fixture("schema-13");
    let (conversion_id, digest) = preview(temporary.path());
    Bridge::new(temporary.path())
        .execute(&Command::Apply {
            accepted_preview_sha256: digest,
            archive: plaintext(),
        })
        .unwrap();
    let archive_manifest = temporary.path().join(format!(
        ".harness/legacy/v0-conversion/{conversion_id}/archive-manifest.json"
    ));
    std::fs::write(&archive_manifest, b"tampered archive manifest\n").unwrap();
    let manifest = std::fs::read(temporary.path().join(".harness/manifest.json")).unwrap();
    let journal_path = journal::path(temporary.path(), &conversion_id);
    let journal_before = std::fs::read(&journal_path).unwrap();

    assert!(Bridge::new(temporary.path())
        .execute(&Command::Rollback {
            conversion_id: conversion_id.clone(),
        })
        .is_err());
    assert_eq!(
        std::fs::read(temporary.path().join(".harness/manifest.json")).unwrap(),
        manifest
    );
    assert_eq!(std::fs::read(journal_path).unwrap(), journal_before);
}

#[test]
fn schema_shape_and_v2_changeset_rules_are_complete() {
    for mutation in [
        "ALTER TABLE story ADD COLUMN foreign_column TEXT;",
        "CREATE INDEX foreign_story_index ON story(title);",
        "CREATE VIEW foreign_story_view AS SELECT id FROM story;",
        "CREATE TRIGGER foreign_story_trigger AFTER INSERT ON story BEGIN SELECT 1; END;",
    ] {
        let temporary = copy_fixture("schema-13");
        let connection = rusqlite::Connection::open(temporary.path().join("harness.db")).unwrap();
        connection.execute_batch(mutation).unwrap();
        drop(connection);
        assert!(matches!(
            capture(temporary.path()),
            Err(BridgeError::Unsupported(_))
        ));
    }

    for operation in [
        serde_json::json!({"op":"story.complete","version":2,"id":"US-X","payload":{"result":"pass"}}),
        serde_json::json!({"op":"story.verify","version":2,"id":"US-X","payload":{"result":"pass","verified_at":"not-a-timestamp"}}),
        serde_json::json!({"op":"backlog.proposal.decision","version":2,"uid":"blg_x","payload":{"accepted_at":"bad","evidence":[]}}),
    ] {
        let temporary = copy_fixture("schema-13");
        let path = temporary
            .path()
            .join(".harness/changesets/fixture.changeset.jsonl");
        let header = serde_json::json!({"op":"changeset.header","version":1,"run_id":"negative","base_schema_version":13});
        std::fs::write(path, format!("{}\n{}\n", header, operation)).unwrap();
        assert!(matches!(
            capture(temporary.path()),
            Err(BridgeError::Unsupported(_))
        ));
    }
}

#[test]
fn preview_and_resume_bind_adopted_document_bytes_before_mutation() {
    let _guard = ENVIRONMENT
        .lock()
        .unwrap_or_else(|error| error.into_inner());
    std::env::remove_var("HARNESS_V0_MIGRATE_TEST_KILL_AFTER");
    let temporary = copy_fixture("schema-13");
    let (_, digest) = preview(temporary.path());
    std::fs::write(
        temporary.path().join("AGENTS.md"),
        b"edited after preview\n",
    )
    .unwrap();
    assert!(matches!(
        Bridge::new(temporary.path()).execute(&Command::Apply {
            accepted_preview_sha256: digest,
            archive: plaintext(),
        }),
        Err(BridgeError::Conflict(_))
    ));
    assert!(!temporary.path().join(".harness/recovery").exists());
    assert!(!temporary.path().join(".harness/legacy").exists());
    assert!(!temporary.path().join(".harness/manifest.json").exists());

    let temporary = copy_fixture("schema-13");
    let (conversion_id, digest) = preview(temporary.path());
    let (_, error) = apply_until(temporary.path(), digest, "archive");
    assert!(matches!(error, BridgeError::KillPoint(_)));
    let journal_before = std::fs::read(journal::path(temporary.path(), &conversion_id)).unwrap();
    std::fs::write(
        temporary.path().join("AGENTS.md"),
        b"edited before resume\n",
    )
    .unwrap();
    assert!(Bridge::new(temporary.path())
        .execute(&Command::Resume {
            conversion_id: conversion_id.clone(),
        })
        .is_err());
    assert!(!temporary.path().join(".harness/manifest.json").exists());
    assert_eq!(
        std::fs::read(journal::path(temporary.path(), &conversion_id)).unwrap(),
        journal_before
    );
}

#[cfg(unix)]
#[test]
fn descriptor_output_and_temporary_symlink_attacks_do_not_escape() {
    use std::os::unix::fs::symlink;

    let _guard = ENVIRONMENT
        .lock()
        .unwrap_or_else(|error| error.into_inner());
    std::env::remove_var("HARNESS_V0_MIGRATE_TEST_KILL_AFTER");
    let temporary = copy_fixture("schema-13");
    let outside = tempfile::tempdir().unwrap();
    symlink(outside.path(), temporary.path().join("out")).unwrap();
    assert!(Bridge::new(temporary.path())
        .execute(&Command::Export {
            output: "out/export.json".into(),
            archive: plaintext(),
        })
        .is_err());
    assert!(!outside.path().join("export.json").exists());
    assert!(!temporary.path().join(".harness/recovery").exists());
    assert!(!temporary.path().join(".harness/legacy").exists());

    let temporary = copy_fixture("schema-13");
    let (conversion_id, digest) = preview(temporary.path());
    let (_, error) = apply_until(temporary.path(), digest, "detection");
    assert!(matches!(error, BridgeError::KillPoint(_)));
    let outside = temporary.path().join("outside-sentinel");
    std::fs::write(&outside, b"sentinel\n").unwrap();
    let temporary_journal = journal::path(temporary.path(), &conversion_id)
        .parent()
        .unwrap()
        .join("journal.json.tmp");
    symlink(&outside, temporary_journal).unwrap();
    assert!(Bridge::new(temporary.path())
        .execute(&Command::Resume { conversion_id })
        .is_err());
    assert_eq!(std::fs::read(outside).unwrap(), b"sentinel\n");
    assert!(!temporary.path().join(".harness/manifest.json").exists());
}

#[cfg(unix)]
#[test]
fn custody_permissions_ignore_a_permissive_umask() {
    use rustix::fs::Mode;
    use std::os::unix::fs::PermissionsExt;

    let _guard = ENVIRONMENT
        .lock()
        .unwrap_or_else(|error| error.into_inner());
    std::env::remove_var("HARNESS_V0_MIGRATE_TEST_KILL_AFTER");
    let temporary = copy_fixture("schema-13");
    let (conversion_id, digest) = preview(temporary.path());
    let previous = rustix::process::umask(Mode::empty());
    let result = Bridge::new(temporary.path()).execute(&Command::Apply {
        accepted_preview_sha256: digest,
        archive: plaintext(),
    });
    rustix::process::umask(previous);
    result.unwrap();

    for relative in [
        ".harness/recovery",
        ".harness/recovery/v0-conversion",
        &format!(".harness/recovery/v0-conversion/{conversion_id}"),
        ".harness/legacy",
        ".harness/legacy/v0-conversion",
        &format!(".harness/legacy/v0-conversion/{conversion_id}"),
    ] {
        let mode = std::fs::metadata(temporary.path().join(relative))
            .unwrap()
            .permissions()
            .mode()
            & 0o777;
        assert_eq!(mode, 0o700, "directory mode drift at {relative}: {mode:o}");
    }
    for relative in [
        format!(".harness/recovery/v0-conversion/{conversion_id}/journal.json"),
        format!(".harness/recovery/v0-conversion/{conversion_id}/receipt.staged.json"),
        format!(".harness/legacy/v0-conversion/{conversion_id}/conversion.bin"),
        format!(".harness/legacy/v0-conversion/{conversion_id}/archive-manifest.json"),
    ] {
        let mode = std::fs::metadata(temporary.path().join(&relative))
            .unwrap()
            .permissions()
            .mode()
            & 0o777;
        assert_eq!(mode, 0o600, "file mode drift at {relative}: {mode:o}");
    }
}

#[test]
fn filesystem_failures_map_to_frozen_exit_74() {
    let error = BridgeError::Io(std::io::Error::other("fixture I/O failure"));
    assert_eq!(error.exit_code(), 74);
    #[cfg(unix)]
    assert_eq!(BridgeError::Errno(rustix::io::Errno::IO).exit_code(), 74);
}

#[test]
fn recovery_state_is_not_silently_rewritten_by_a_failed_preflight() {
    let _guard = ENVIRONMENT
        .lock()
        .unwrap_or_else(|error| error.into_inner());
    std::env::remove_var("HARNESS_V0_MIGRATE_TEST_KILL_AFTER");
    let temporary = copy_fixture("schema-13");
    let (conversion_id, digest) = preview(temporary.path());
    Bridge::new(temporary.path())
        .execute(&Command::Apply {
            accepted_preview_sha256: digest,
            archive: plaintext(),
        })
        .unwrap();
    assert_eq!(
        journal::load(temporary.path(), &conversion_id)
            .unwrap()
            .state,
        JournalState::Completed
    );
}

#[test]
fn core_status_authenticates_receipt_archive_export_and_snapshot_without_bridge_or_sqlite() {
    let _guard = ENVIRONMENT
        .lock()
        .unwrap_or_else(|error| error.into_inner());
    std::env::remove_var("HARNESS_V0_MIGRATE_TEST_KILL_AFTER");
    let temporary = copy_fixture("schema-13");
    let (conversion_id, digest) = preview(temporary.path());
    Bridge::new(temporary.path())
        .execute(&Command::Apply {
            accepted_preview_sha256: digest,
            archive: plaintext(),
        })
        .unwrap();

    let filesystem = OsFileSystem::new(temporary.path()).unwrap();
    let result = HarnessCore::new(
        &filesystem,
        &JsonManifestPort,
        &UnusedRelease,
        &UnusedRelease,
    )
    .execute(&CoreCommand::Status { json: true });
    assert_eq!(result.exit_code, 0);
    assert_eq!(
        result.repository_mode,
        RepositoryMode::ConvertedV1WithArchive
    );

    std::fs::write(
        temporary.path().join(format!(
            ".harness/legacy/v0-conversion/{conversion_id}/conversion.bin"
        )),
        b"tampered archive",
    )
    .unwrap();
    let filesystem = OsFileSystem::new(temporary.path()).unwrap();
    let result = HarnessCore::new(
        &filesystem,
        &JsonManifestPort,
        &UnusedRelease,
        &UnusedRelease,
    )
    .execute(&CoreCommand::Status { json: true });
    assert_eq!(result.exit_code, 3);
    assert_eq!(result.repository_mode, RepositoryMode::MixedInvalid);
    assert!(result
        .details
        .violations
        .contains(&"conversion-evidence-invalid".to_owned()));
}
