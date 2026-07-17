#![cfg(unix)]

use std::path::{Path, PathBuf};

use harness_v0_migrate::interface::{ArchiveOptions, Command, SourceOptions};
use harness_v0_migrate::{Bridge, BridgeError};

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

#[test]
fn foreign_reserved_custody_is_never_adopted_or_overwritten() {
    let fixture = copy_fixture("schema-13");
    std::fs::create_dir(fixture.path().join(".harness-v0-archive")).unwrap();
    std::fs::write(
        fixture.path().join(".harness-v0-archive/foreign.bin"),
        b"foreign custody",
    )
    .unwrap();
    let result = Bridge::new(fixture.path()).execute(&Command::Archive {
        archive: plaintext(),
    });
    assert!(matches!(
        result,
        Err(BridgeError::Unsupported(_) | BridgeError::Conflict(_))
    ));
    assert_eq!(
        std::fs::read(fixture.path().join(".harness-v0-archive/foreign.bin")).unwrap(),
        b"foreign custody"
    );
}

#[test]
fn tampered_archive_payload_blocks_inspect_and_export() {
    let fixture = copy_fixture("schema-13");
    let archived = Bridge::new(fixture.path())
        .execute(&Command::Archive {
            archive: plaintext(),
        })
        .unwrap();
    let manifest = archived.archive_manifest_path.unwrap();
    let payload = Path::new(&manifest).parent().unwrap().join("archive.bin");
    std::fs::write(fixture.path().join(payload), b"tampered").unwrap();
    let inspected = Bridge::new(fixture.path()).execute(&Command::Inspect {
        json: true,
        source: SourceOptions {
            archive_manifest: Some(manifest.clone()),
            age_identity_file: None,
        },
    });
    assert!(matches!(inspected, Err(BridgeError::Conflict(_))));
    assert!(!fixture.path().join("v0-export.json").exists());
    let exported = Bridge::new(fixture.path()).execute(&Command::Export {
        output: "v0-export.json".into(),
        source: SourceOptions {
            archive_manifest: Some(manifest),
            age_identity_file: None,
        },
    });
    assert!(matches!(exported, Err(BridgeError::Conflict(_))));
    assert!(!fixture.path().join("v0-export.json").exists());
}

#[test]
fn symlinked_source_and_unsafe_output_fail_closed() {
    use std::os::unix::fs::symlink;

    let fixture = copy_fixture("schema-13");
    std::fs::rename(
        fixture.path().join("harness.db-wal"),
        fixture.path().join("real-wal"),
    )
    .unwrap();
    symlink("real-wal", fixture.path().join("harness.db-wal")).unwrap();
    let result = Bridge::new(fixture.path()).execute(&Command::Inspect {
        json: true,
        source: SourceOptions::default(),
    });
    assert!(matches!(
        result,
        Err(BridgeError::Conflict(_) | BridgeError::Io(_))
    ));
    assert!(!fixture.path().join(".harness-v0-archive").exists());

    let safe = copy_fixture("schema-13");
    let result = Bridge::new(safe.path()).execute(&Command::Export {
        output: ".harness/manifest.json".into(),
        source: SourceOptions::default(),
    });
    assert!(matches!(result, Err(BridgeError::Usage(_))));
    assert!(!safe.path().join(".harness/manifest.json").exists());
}

#[test]
fn prepositioned_export_and_archive_manifest_path_are_never_replaced() {
    let fixture = copy_fixture("schema-13");
    std::fs::write(fixture.path().join("v0-export.json"), b"foreign").unwrap();
    let result = Bridge::new(fixture.path()).execute(&Command::Export {
        output: "v0-export.json".into(),
        source: SourceOptions::default(),
    });
    assert!(matches!(result, Err(BridgeError::Conflict(_))));
    assert_eq!(
        std::fs::read(fixture.path().join("v0-export.json")).unwrap(),
        b"foreign"
    );

    let result = Bridge::new(fixture.path()).execute(&Command::Inspect {
        json: true,
        source: SourceOptions {
            archive_manifest: Some(".harness/legacy/archive-manifest.json".into()),
            age_identity_file: None,
        },
    });
    assert!(matches!(result, Err(BridgeError::Usage(_))));
}
