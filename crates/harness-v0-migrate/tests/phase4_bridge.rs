use std::collections::BTreeMap;
use std::io::Read;
use std::path::{Path, PathBuf};
use std::str::FromStr;
use std::sync::Mutex;

use age::x25519;
use harness_v0_migrate::archive::ArchiveManifest;
use harness_v0_migrate::capture::{capture, hex_sha256};
use harness_v0_migrate::interface::{ArchiveOptions, Command};
use harness_v0_migrate::journal::{self, JournalState};
use harness_v0_migrate::{Bridge, BridgeError};

static ENVIRONMENT: Mutex<()> = Mutex::new(());

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

fn source_snapshot(root: &Path) -> BTreeMap<String, String> {
    let mut paths = vec![
        "harness.db".to_owned(),
        "harness.db-wal".to_owned(),
        "harness.db-shm".to_owned(),
    ];
    let changesets = root.join(".harness/changesets");
    if changesets.is_dir() {
        for path in std::fs::read_dir(changesets).unwrap() {
            let path = path.unwrap().path();
            paths.push(
                path.strip_prefix(root)
                    .unwrap()
                    .to_string_lossy()
                    .into_owned(),
            );
        }
    }
    for path in [".harness/v0-provenance.json", ".harness/foreign-tool.bin"] {
        if root.join(path).is_file() {
            paths.push(path.into());
        }
    }
    paths.sort();
    paths
        .into_iter()
        .filter_map(|path| {
            let full = root.join(&path);
            full.is_file()
                .then(|| (path, hex_sha256(&std::fs::read(full).unwrap())))
        })
        .collect()
}

#[test]
fn immutable_reader_accepts_every_frozen_schema_and_preserves_unknown_metadata() {
    for version in 1..=13 {
        let fixture = fixtures().join(format!("schema-{version:02}"));
        let before = source_snapshot(&fixture);
        let captured = capture(&fixture).unwrap();
        assert_eq!(captured.schema_version, version);
        assert_eq!(source_snapshot(&fixture), before);
    }
    let captured = capture(&fixtures().join("schema-13")).unwrap();
    assert!(captured
        .unknown_metadata
        .contains(&".harness/foreign-tool.bin".to_owned()));
    assert!(!captured
        .members
        .iter()
        .any(|member| member.path.ends_with("foreign-tool.bin")));
}

#[test]
fn wal_only_commit_is_present_in_standalone_backup_and_shm_is_forensic_only() {
    let fixture = fixtures().join("wal-only-schema-13");
    let before = source_snapshot(&fixture);
    let captured = capture(&fixture).unwrap();
    assert!(captured
        .members
        .iter()
        .any(|member| member.path == "harness.db-shm"));
    let temporary = tempfile::NamedTempFile::new().unwrap();
    std::fs::write(temporary.path(), &captured.standalone_backup).unwrap();
    let connection = rusqlite::Connection::open_with_flags(
        temporary.path(),
        rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY,
    )
    .unwrap();
    let title: String = connection
        .query_row("SELECT title FROM story WHERE id='US-WAL'", [], |row| {
            row.get(0)
        })
        .unwrap();
    assert_eq!(title, "wal-only-committed-row");
    assert_eq!(source_snapshot(&fixture), before);
}

#[test]
fn changeset_unknown_operation_duplicate_member_and_foreign_schema_fail_closed() {
    for contents in [
        "{\"op\":\"changeset.header\",\"version\":1,\"run_id\":\"bad\",\"base_schema_version\":13}\n{\"op\":\"unknown.operation\"}\n",
        "{\"op\":\"changeset.header\",\"op\":\"changeset.header\",\"version\":1,\"run_id\":\"bad\",\"base_schema_version\":13}\n",
    ] {
        let temporary = copy_fixture("schema-13");
        let path = temporary
            .path()
            .join(".harness/changesets/fixture.changeset.jsonl");
        std::fs::write(&path, contents).unwrap();
        let before = std::fs::read(&path).unwrap();
        assert!(matches!(
            capture(temporary.path()),
            Err(BridgeError::Unsupported(_))
        ));
        assert_eq!(std::fs::read(path).unwrap(), before);
    }

    let temporary = copy_fixture("schema-13");
    let connection = rusqlite::Connection::open(temporary.path().join("harness.db")).unwrap();
    connection
        .execute("CREATE TABLE foreign_table(value)", [])
        .unwrap();
    drop(connection);
    assert!(matches!(
        capture(temporary.path()),
        Err(BridgeError::Unsupported(_))
    ));
}

#[test]
fn plaintext_apply_commits_receipt_last_is_idempotent_and_rolls_back_safely() {
    let _guard = ENVIRONMENT
        .lock()
        .unwrap_or_else(|error| error.into_inner());
    std::env::remove_var("HARNESS_V0_MIGRATE_TEST_KILL_AFTER");
    let temporary = copy_fixture("schema-13");
    let before = source_snapshot(temporary.path());
    let (conversion_id, digest) = preview(temporary.path());
    let report = Bridge::new(temporary.path())
        .execute(&Command::Apply {
            accepted_preview_sha256: digest.clone(),
            archive: plaintext(),
        })
        .unwrap();
    assert_eq!(report.repository_mode, "converted-v1-with-archive");
    assert_eq!(report.journal_state.as_deref(), Some("completed"));
    let manifest: serde_json::Value = serde_json::from_slice(
        &std::fs::read(temporary.path().join(".harness/manifest.json")).unwrap(),
    )
    .unwrap();
    assert_eq!(manifest["repository_mode"], "converted-v1-with-archive");
    assert_eq!(
        manifest["conversion_receipt"]["confidentiality_mode"],
        "plaintext-explicit-override"
    );
    assert!(temporary
        .path()
        .join(format!(
            ".harness/legacy/v0-conversion/{conversion_id}/conversion.bin"
        ))
        .is_file());
    assert_eq!(source_snapshot(temporary.path()), before);

    let idempotent = Bridge::new(temporary.path())
        .execute(&Command::Apply {
            accepted_preview_sha256: digest,
            archive: plaintext(),
        })
        .unwrap();
    assert_eq!(idempotent.journal_state.as_deref(), Some("completed"));

    let rolled_back = Bridge::new(temporary.path())
        .execute(&Command::Rollback {
            conversion_id: conversion_id.clone(),
        })
        .unwrap();
    assert_eq!(rolled_back.outcome, "rolled-back");
    assert!(!temporary.path().join(".harness/manifest.json").exists());
    assert!(temporary
        .path()
        .join(format!(
            ".harness/legacy/v0-conversion/{conversion_id}/archive-manifest.json"
        ))
        .is_file());
    assert_eq!(source_snapshot(temporary.path()), before);
}

#[test]
fn encrypted_archive_is_real_age_x25519_and_binds_ciphertext_digest() {
    let _guard = ENVIRONMENT
        .lock()
        .unwrap_or_else(|error| error.into_inner());
    std::env::remove_var("HARNESS_V0_MIGRATE_TEST_KILL_AFTER");
    let temporary = copy_fixture("schema-13");
    let identity = x25519::Identity::generate();
    let recipient = identity.to_public().to_string();
    let options = ArchiveOptions {
        age_recipient: Some(recipient.clone()),
        plaintext: false,
        plaintext_risk_acknowledged: false,
    };
    let (conversion_id, digest) = preview(temporary.path());
    Bridge::new(temporary.path())
        .execute(&Command::Apply {
            accepted_preview_sha256: digest,
            archive: options,
        })
        .unwrap();
    let archive_root = temporary
        .path()
        .join(format!(".harness/legacy/v0-conversion/{conversion_id}"));
    let ciphertext = std::fs::read(archive_root.join("conversion.age")).unwrap();
    let manifest: ArchiveManifest =
        serde_json::from_slice(&std::fs::read(archive_root.join("archive-manifest.json")).unwrap())
            .unwrap();
    assert_eq!(manifest.confidentiality_mode, "encrypted-age-x25519");
    assert_eq!(manifest.recipient_fingerprints, vec![recipient]);
    assert_eq!(manifest.archive_sha256, hex_sha256(&ciphertext));
    let decryptor = age::Decryptor::new(ciphertext.as_slice()).unwrap();
    let mut reader = decryptor
        .decrypt(std::iter::once(&identity as &dyn age::Identity))
        .unwrap();
    let mut plaintext = Vec::new();
    reader.read_to_end(&mut plaintext).unwrap();
    assert!(plaintext.starts_with(b"repository-harness-v0-archive-payload/v1\0"));
}

#[test]
fn every_required_kill_point_has_no_false_success_and_resumes_deterministically() {
    let _guard = ENVIRONMENT
        .lock()
        .unwrap_or_else(|error| error.into_inner());
    std::env::remove_var("HARNESS_V0_MIGRATE_TEST_KILL_AFTER");
    for kill_point in [
        "detection",
        "export",
        "archive",
        "temporary-receipt",
        "temporary-manifest",
        "operation-1",
        "atomic-commit",
    ] {
        let temporary = copy_fixture("schema-13");
        let before = source_snapshot(temporary.path());
        let (conversion_id, digest) = preview(temporary.path());
        std::env::set_var("HARNESS_V0_MIGRATE_TEST_KILL_AFTER", kill_point);
        let stopped = Bridge::new(temporary.path()).execute(&Command::Apply {
            accepted_preview_sha256: digest,
            archive: plaintext(),
        });
        std::env::remove_var("HARNESS_V0_MIGRATE_TEST_KILL_AFTER");
        assert!(matches!(stopped, Err(BridgeError::KillPoint(_))));
        assert_eq!(source_snapshot(temporary.path()), before);
        if !matches!(kill_point, "operation-1" | "atomic-commit") {
            assert!(
                !temporary.path().join(".harness/manifest.json").exists(),
                "false success at {kill_point}"
            );
        }
        let resumed = Bridge::new(temporary.path())
            .execute(&Command::Resume {
                conversion_id: conversion_id.clone(),
            })
            .unwrap_or_else(|error| panic!("resume failed after {kill_point}: {error}"));
        assert_eq!(resumed.journal_state.as_deref(), Some("completed"));
        assert_eq!(source_snapshot(temporary.path()), before);
    }
}

#[test]
fn rollback_refuses_human_edit_and_archive_tamper_blocks_resume() {
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
    std::fs::write(
        temporary.path().join(".harness/manifest.json"),
        b"human edit\n",
    )
    .unwrap();
    assert!(matches!(
        Bridge::new(temporary.path()).execute(&Command::Rollback {
            conversion_id: conversion_id.clone()
        }),
        Err(BridgeError::Conflict(_))
    ));
    assert_eq!(
        std::fs::read(temporary.path().join(".harness/manifest.json")).unwrap(),
        b"human edit\n"
    );
    assert_eq!(
        journal::load(temporary.path(), &conversion_id)
            .unwrap()
            .state,
        JournalState::RecoveryRequired
    );

    let temporary = copy_fixture("schema-13");
    let (conversion_id, digest) = preview(temporary.path());
    std::env::set_var("HARNESS_V0_MIGRATE_TEST_KILL_AFTER", "archive");
    let _ = Bridge::new(temporary.path()).execute(&Command::Apply {
        accepted_preview_sha256: digest,
        archive: plaintext(),
    });
    std::env::remove_var("HARNESS_V0_MIGRATE_TEST_KILL_AFTER");
    let payload = temporary.path().join(format!(
        ".harness/legacy/v0-conversion/{conversion_id}/conversion.bin"
    ));
    std::fs::write(&payload, b"tampered archive").unwrap();
    assert!(matches!(
        Bridge::new(temporary.path()).execute(&Command::Resume { conversion_id }),
        Err(BridgeError::Conflict(_))
    ));
}

#[test]
fn mixed_manifest_and_symlinked_source_fail_without_source_mutation() {
    let _guard = ENVIRONMENT
        .lock()
        .unwrap_or_else(|error| error.into_inner());
    std::env::remove_var("HARNESS_V0_MIGRATE_TEST_KILL_AFTER");
    let temporary = copy_fixture("schema-13");
    std::fs::write(
        temporary.path().join(".harness/manifest.json"),
        b"{\"schema\":\"repository-harness-manifest/v1\"}\n",
    )
    .unwrap();
    let (_, digest) = preview(temporary.path());
    assert!(matches!(
        Bridge::new(temporary.path()).execute(&Command::Apply {
            accepted_preview_sha256: digest,
            archive: plaintext()
        }),
        Err(BridgeError::Invalid(_))
    ));

    #[cfg(unix)]
    {
        let temporary = copy_fixture("schema-13");
        let original = temporary.path().join("original.db");
        std::fs::rename(temporary.path().join("harness.db"), &original).unwrap();
        std::os::unix::fs::symlink(&original, temporary.path().join("harness.db")).unwrap();
        assert!(capture(temporary.path()).is_err());
        assert!(original.is_file());
    }
}

#[test]
fn frozen_age_recipient_parser_rejects_non_x25519_values() {
    assert!(x25519::Recipient::from_str("not-an-age-recipient").is_err());
}
