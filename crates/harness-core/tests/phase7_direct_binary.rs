use std::process::Command;

use sha2::{Digest, Sha256};

fn binary() -> &'static str {
    env!("CARGO_BIN_EXE_harness")
}

fn digest() -> String {
    format!("{:x}", Sha256::digest(std::fs::read(binary()).unwrap()))
}

fn platform() -> &'static str {
    match (std::env::consts::OS, std::env::consts::ARCH) {
        ("macos", "aarch64") => "macos-arm64",
        ("macos", "x86_64") => "macos-x64",
        ("linux", "x86_64") => "linux-x64",
        ("linux", "aarch64") => "linux-arm64",
        ("windows", "x86_64") => "windows-x64",
        other => panic!("unsupported test platform: {other:?}"),
    }
}

#[test]
fn artifact_authentication_precedes_platform_and_command_execution() {
    let absent = Command::new(binary()).arg("version").output().unwrap();
    assert_eq!(absent.status.code(), Some(70));
    assert!(String::from_utf8(absent.stderr)
        .unwrap()
        .contains("ARTIFACT_SHA256 is required before execution"));
    assert!(absent.stdout.is_empty());

    let wrong_both = Command::new(binary())
        .arg("version")
        .env("HARNESS_V1_ARTIFACT_SHA256", "0".repeat(64))
        .env("HARNESS_V1_PLATFORM", "unsupported-platform")
        .output()
        .unwrap();
    assert_eq!(wrong_both.status.code(), Some(70));
    let error = String::from_utf8(wrong_both.stderr).unwrap();
    assert!(error.contains("digest does not match"));
    assert!(!error.contains("platform identity mismatch"));
    assert!(wrong_both.stdout.is_empty());

    let mismatched_platform = if platform() == "windows-x64" {
        "linux-x64"
    } else {
        "windows-x64"
    };
    let wrong_platform = Command::new(binary())
        .arg("version")
        .env("HARNESS_V1_ARTIFACT_SHA256", digest())
        .env("HARNESS_V1_PLATFORM", mismatched_platform)
        .output()
        .unwrap();
    assert_eq!(wrong_platform.status.code(), Some(70));
    assert!(String::from_utf8(wrong_platform.stderr)
        .unwrap()
        .contains("platform identity mismatch"));
}

#[test]
fn authenticated_native_binary_executes_machine_help_status_and_version() {
    for arguments in [
        vec!["--help"],
        vec!["status", "--json"],
        vec!["version", "--json"],
    ] {
        let output = Command::new(binary())
            .args(arguments)
            .env("HARNESS_V1_ARTIFACT_SHA256", digest())
            .env("HARNESS_V1_PLATFORM", platform())
            .output()
            .unwrap();
        assert_eq!(output.status.code(), Some(0));
        assert!(output.stderr.is_empty());
        let value: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
        assert!(value.is_object());
    }
}
