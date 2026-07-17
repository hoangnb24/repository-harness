use std::io::{self, Write};
use std::process::ExitCode;

use harness_core::application::{io_failure_envelope, version_envelope, HarnessCore};
use harness_core::domain::Command;
use harness_core::infrastructure::{
    JsonManifestPort, OsFileSystem, UnavailableReleasePort, UnavailableTrustPort,
};
use harness_core::interface::{help, parse, render, Parsed};

fn main() -> ExitCode {
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
    let filesystem = match OsFileSystem::new(root) {
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
    let releases = UnavailableReleasePort;
    let trust = UnavailableTrustPort;
    let core = HarnessCore::new(&filesystem, &manifests, &releases, &trust);
    let envelope = core.execute(&command);
    emit(&envelope, command.json())
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
