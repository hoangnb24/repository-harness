use std::io::{self, Write};
use std::path::Path;
use std::process::ExitCode;

use harness_core::application::{io_failure_envelope, version_envelope, HarnessCore};
use harness_core::domain::Command;
use harness_core::infrastructure::{
    DirectoryReleasePort, JsonManifestPort, JsonTrustPort, OsFileSystem, UnavailableReleasePort,
    UnavailableTrustPort,
};
use harness_core::interface::{help, parse, render, Parsed};
use harness_core::ports::{ReleasePort, TrustPort};
use harness_core::recovery::OsMutationPort;
use sha2::{Digest, Sha256};

fn main() -> ExitCode {
    if let Err(error) = authenticate_executable_and_platform() {
        write_error(&format!("harness execution refused: {error}"));
        return ExitCode::from(70);
    }
    let parsed = match parse(std::env::args_os().skip(1)) {
        Ok(parsed) => parsed,
        Err(error) => {
            write_error(&format!("harness usage error: {}", error.0));
            return ExitCode::from(64);
        }
    };
    let Parsed::Command(command) = parsed else {
        return write_stdout(&help(), 0, 74);
    };
    if matches!(&command, Command::Version { .. }) {
        let envelope = version_envelope();
        return emit(&envelope, command.json());
    }
    let root = match std::env::current_dir() {
        Ok(root) => root,
        Err(_) => {
            let envelope = io_failure_envelope(
                command.name(),
                ".",
                "current repository directory is unavailable",
            );
            return emit(&envelope, command.json());
        }
    };
    let filesystem = match OsFileSystem::new(&root) {
        Ok(filesystem) => filesystem,
        Err(_) => {
            let envelope = io_failure_envelope(
                command.name(),
                ".",
                "safe repository root handle is unavailable",
            );
            return emit(&envelope, command.json());
        }
    };
    let manifests = JsonManifestPort;
    let release_directory = std::env::var_os("HARNESS_V1_RELEASE_DIRECTORY");
    let trust_state = std::env::var_os("HARNESS_V1_TRUST_STATE");
    if release_directory.is_some() != trust_state.is_some() {
        let envelope = io_failure_envelope(
            command.name(),
            ".",
            "release directory and independent trust state must be supplied together",
        );
        return emit(&envelope, command.json());
    }
    let unavailable_release = UnavailableReleasePort;
    let unavailable_trust = UnavailableTrustPort;
    let mut external_release = None;
    let mut external_trust = None;
    if let (Some(release_directory), Some(trust_state)) = (release_directory, trust_state) {
        let release_directory = std::path::PathBuf::from(release_directory);
        let trust_state = std::path::PathBuf::from(trust_state);
        if !outside_repository(&root, &release_directory)
            || !outside_repository(&root, &trust_state)
        {
            let envelope = io_failure_envelope(
                command.name(),
                ".",
                "release signatures and independent trust state must remain outside the target repository",
            );
            return emit(&envelope, command.json());
        }
        external_release = match DirectoryReleasePort::new(release_directory) {
            Ok(port) => Some(port),
            Err(error) => {
                let envelope = io_failure_envelope(command.name(), ".", &error.to_string());
                return emit(&envelope, command.json());
            }
        };
        external_trust = match JsonTrustPort::new(trust_state) {
            Ok(port) => Some(port),
            Err(error) => {
                let envelope = io_failure_envelope(command.name(), ".", &error.to_string());
                return emit(&envelope, command.json());
            }
        };
    }
    let releases: &dyn ReleasePort = external_release
        .as_ref()
        .map(|port| port as &dyn ReleasePort)
        .unwrap_or(&unavailable_release);
    let trust: &dyn TrustPort = external_trust
        .as_ref()
        .map(|port| port as &dyn TrustPort)
        .unwrap_or(&unavailable_trust);
    let mutations = match OsMutationPort::new(&root) {
        Ok(mutations) => mutations,
        Err(error) => {
            let envelope = io_failure_envelope(command.name(), ".", &error.to_string());
            return emit(&envelope, command.json());
        }
    };
    let core = HarnessCore::with_mutations(&filesystem, &manifests, releases, trust, &mutations);
    let envelope = core.execute(&command);
    emit(&envelope, command.json())
}

fn authenticate_executable_and_platform() -> Result<(), String> {
    let expected_digest = std::env::var("HARNESS_V1_ARTIFACT_SHA256")
        .map_err(|_| "HARNESS_V1_ARTIFACT_SHA256 is required before execution".to_string())?;
    if expected_digest.len() != 64
        || !expected_digest
            .bytes()
            .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
    {
        return Err(
            "HARNESS_V1_ARTIFACT_SHA256 must be 64 lowercase hexadecimal characters".into(),
        );
    }
    let executable = std::env::current_exe()
        .map_err(|_| "current executable identity is unavailable".to_string())?;
    let first = std::fs::read(&executable)
        .map_err(|_| "current executable cannot be read for authentication".to_string())?;
    let second = std::fs::read(&executable)
        .map_err(|_| "current executable cannot be re-read for authentication".to_string())?;
    if first != second {
        return Err("current executable changed during authentication".into());
    }
    let actual = format!("{:x}", Sha256::digest(&first));
    if actual != expected_digest {
        return Err(
            "current executable digest does not match the authenticated expectation".into(),
        );
    }
    let supplied_platform = std::env::var("HARNESS_V1_PLATFORM")
        .map_err(|_| "HARNESS_V1_PLATFORM is required before execution".to_string())?;
    let native_platform = native_platform().ok_or_else(|| {
        "this operating-system and architecture pair is not supported by Harness V1".to_string()
    })?;
    if supplied_platform != native_platform {
        return Err(format!(
            "platform identity mismatch: expected native {native_platform}"
        ));
    }
    Ok(())
}

fn native_platform() -> Option<&'static str> {
    match (std::env::consts::OS, std::env::consts::ARCH) {
        ("macos", "aarch64") => Some("macos-arm64"),
        ("macos", "x86_64") => Some("macos-x64"),
        ("linux", "x86_64") => Some("linux-x64"),
        ("linux", "aarch64") => Some("linux-arm64"),
        ("windows", "x86_64") => Some("windows-x64"),
        _ => None,
    }
}

fn outside_repository(root: &Path, external: &Path) -> bool {
    let Ok(root) = root.canonicalize() else {
        return false;
    };
    let Ok(external) = external.canonicalize() else {
        return false;
    };
    !external.starts_with(root)
}

fn emit(envelope: &harness_core::domain::Envelope, json: bool) -> ExitCode {
    let output = match render(envelope, json) {
        Ok(output) => output,
        Err(error) => {
            write_error(&format!("harness internal invariant failure: {error}"));
            return ExitCode::from(70);
        }
    };
    let output_failure_code = if envelope.command == "version" {
        70
    } else {
        74
    };
    write_stdout(&output, envelope.exit_code, output_failure_code)
}

fn write_stdout(output: &str, success_code: u8, failure_code: u8) -> ExitCode {
    let mut stdout = io::stdout().lock();
    let mut stderr = io::stderr().lock();
    write_output(&mut stdout, &mut stderr, output, success_code, failure_code)
}

fn write_output(
    stdout: &mut impl Write,
    stderr: &mut impl Write,
    output: &str,
    success_code: u8,
    failure_code: u8,
) -> ExitCode {
    if let Err(error) = stdout
        .write_all(output.as_bytes())
        .and_then(|()| stdout.flush())
    {
        let _ = writeln!(stderr, "harness output I/O failure: {error}");
        return ExitCode::from(failure_code);
    }
    ExitCode::from(success_code)
}

fn write_error(message: &str) {
    let _ = writeln!(io::stderr().lock(), "{message}");
}

#[cfg(test)]
mod tests {
    use super::*;

    struct FailingWriter;

    impl Write for FailingWriter {
        fn write(&mut self, _buffer: &[u8]) -> io::Result<usize> {
            Err(io::Error::other("deterministic output failure"))
        }

        fn flush(&mut self) -> io::Result<()> {
            Ok(())
        }
    }

    #[test]
    fn output_write_failures_use_contracted_exit_instead_of_panicking() {
        let mut stderr = Vec::new();
        let exit = write_output(&mut FailingWriter, &mut stderr, "output", 0, 74);
        assert_eq!(exit, ExitCode::from(74));
        assert!(String::from_utf8(stderr)
            .unwrap()
            .contains("output I/O failure"));

        let exit = write_output(&mut FailingWriter, &mut Vec::new(), "version", 0, 70);
        assert_eq!(exit, ExitCode::from(70));
    }
}
