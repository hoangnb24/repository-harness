#![cfg(unix)]

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use age::secrecy::ExposeSecret;
use age::x25519;
use harness_v0_migrate::capture::{capture, hex_sha256};
use harness_v0_migrate::interface::{ArchiveOptions, Command, SourceOptions};
use harness_v0_migrate::Bridge;

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

fn source_snapshot(root: &Path) -> BTreeMap<String, String> {
    fn visit(root: &Path, current: &Path, result: &mut BTreeMap<String, String>) {
        for entry in std::fs::read_dir(current).unwrap() {
            let path = entry.unwrap().path();
            let relative = path.strip_prefix(root).unwrap().to_string_lossy();
            if relative.starts_with(".harness-v0-archive") || relative == "v0-export.json" {
                continue;
            }
            if path.is_dir() {
                visit(root, &path, result);
            } else {
                result.insert(
                    relative.into_owned(),
                    hex_sha256(&std::fs::read(path).unwrap()),
                );
            }
        }
    }
    let mut result = BTreeMap::new();
    visit(root, root, &mut result);
    result
}

fn plaintext() -> ArchiveOptions {
    ArchiveOptions {
        age_recipient: None,
        plaintext: true,
        plaintext_risk_acknowledged: true,
    }
}

#[test]
fn inspect_accepts_every_frozen_schema_and_never_changes_source_bytes() {
    for version in 1..=13 {
        let fixture = copy_fixture(&format!("schema-{version:02}"));
        let before = source_snapshot(fixture.path());
        let report = Bridge::new(fixture.path())
            .execute(&Command::Inspect {
                json: true,
                source: SourceOptions::default(),
            })
            .unwrap();
        assert_eq!(report.source_schema, Some(version));
        assert_eq!(source_snapshot(fixture.path()), before);
    }
}

#[test]
fn wal_only_commit_reaches_live_export_while_shm_stays_forensic_only() {
    let fixture = copy_fixture("wal-only-schema-13");
    let before = source_snapshot(fixture.path());
    let captured = capture(fixture.path()).unwrap();
    assert!(captured.members.iter().any(
        |member| member.path == "harness.db-shm" && member.category.ends_with("forensic-only")
    ));
    let report = Bridge::new(fixture.path())
        .execute(&Command::Export {
            output: "v0-export.json".into(),
            source: SourceOptions::default(),
        })
        .unwrap();
    let export = std::fs::read(fixture.path().join("v0-export.json")).unwrap();
    assert_eq!(
        report.export_sha256.as_deref(),
        Some(hex_sha256(&export).as_str())
    );
    assert!(String::from_utf8_lossy(&export).contains("wal-only-committed-row"));
    assert_eq!(source_snapshot(fixture.path()), before);
}

#[test]
fn plaintext_archive_is_append_only_and_can_recreate_the_exact_export() {
    let fixture = copy_fixture("schema-13");
    let before = source_snapshot(fixture.path());
    let first = Bridge::new(fixture.path())
        .execute(&Command::Archive {
            archive: plaintext(),
        })
        .unwrap();
    let abandoned = fixture
        .path()
        .join(".harness-v0-archive/.staging-abandoned-crash");
    std::fs::create_dir(&abandoned).unwrap();
    std::fs::write(abandoned.join("foreign.partial"), b"do not overwrite").unwrap();
    let second = Bridge::new(fixture.path())
        .execute(&Command::Archive {
            archive: plaintext(),
        })
        .unwrap();
    assert_ne!(first.archive_id, second.archive_id);
    assert_ne!(first.archive_manifest_path, second.archive_manifest_path);
    assert_eq!(
        std::fs::read(abandoned.join("foreign.partial")).unwrap(),
        b"do not overwrite"
    );
    assert!(fixture
        .path()
        .join(first.archive_manifest_path.as_ref().unwrap())
        .is_file());
    assert!(fixture
        .path()
        .join(second.archive_manifest_path.as_ref().unwrap())
        .is_file());
    assert!(!fixture.path().join(".harness/manifest.json").exists());
    assert!(!fixture.path().join("harness-v1.db").exists());

    let archive_manifest = first.archive_manifest_path.clone().unwrap();
    let exported = Bridge::new(fixture.path())
        .execute(&Command::Export {
            output: "v0-export.json".into(),
            source: SourceOptions {
                archive_manifest: Some(archive_manifest),
                age_identity_file: None,
            },
        })
        .unwrap();
    assert_eq!(exported.export_sha256, first.export_sha256);
    assert_eq!(source_snapshot(fixture.path()), before);
}

#[test]
fn encrypted_archive_requires_identity_for_inner_export_and_round_trips() {
    let fixture = copy_fixture("schema-13");
    let identity = x25519::Identity::generate();
    let recipient = identity.to_public().to_string();
    std::fs::write(
        fixture.path().join("identity.txt"),
        format!("{}\n", identity.to_string().expose_secret()),
    )
    .unwrap();
    let archived = Bridge::new(fixture.path())
        .execute(&Command::Archive {
            archive: ArchiveOptions {
                age_recipient: Some(recipient),
                plaintext: false,
                plaintext_risk_acknowledged: false,
            },
        })
        .unwrap();
    let manifest = archived.archive_manifest_path.clone().unwrap();
    let without_identity = Bridge::new(fixture.path()).execute(&Command::Export {
        output: "v0-export.json".into(),
        source: SourceOptions {
            archive_manifest: Some(manifest.clone()),
            age_identity_file: None,
        },
    });
    assert!(without_identity.is_err());
    let exported = Bridge::new(fixture.path())
        .execute(&Command::Export {
            output: "v0-export.json".into(),
            source: SourceOptions {
                archive_manifest: Some(manifest),
                age_identity_file: Some("identity.txt".into()),
            },
        })
        .unwrap();
    assert_eq!(exported.export_sha256, archived.export_sha256);
}

#[test]
fn foreign_legacy_and_recovery_content_is_reported_and_never_used_as_custody() {
    let fixture = copy_fixture("schema-13");
    std::fs::create_dir_all(fixture.path().join(".harness/legacy")).unwrap();
    std::fs::create_dir_all(fixture.path().join(".harness/recovery")).unwrap();
    std::fs::write(
        fixture.path().join(".harness/legacy/foreign.bin"),
        b"legacy",
    )
    .unwrap();
    std::fs::write(
        fixture.path().join(".harness/recovery/foreign.bin"),
        b"recovery",
    )
    .unwrap();
    let report = Bridge::new(fixture.path())
        .execute(&Command::Archive {
            archive: plaintext(),
        })
        .unwrap();
    assert!(report.unknown_unowned.contains(&".harness/legacy".into()));
    assert!(report.unknown_unowned.contains(&".harness/recovery".into()));
    assert_eq!(
        std::fs::read(fixture.path().join(".harness/legacy/foreign.bin")).unwrap(),
        b"legacy"
    );
    assert_eq!(
        std::fs::read(fixture.path().join(".harness/recovery/foreign.bin")).unwrap(),
        b"recovery"
    );
}
