use std::io::{self, Write};
use std::process::ExitCode;

use harness_v0_migrate::interface::{machine_help, parse, Command};
use harness_v0_migrate::{Bridge, BridgeError};

fn main() -> ExitCode {
    let command = match parse(std::env::args_os().skip(1)) {
        Ok(command) => command,
        Err(error) => return error_exit(&BridgeError::Usage(error.0)),
    };
    if command == Command::Help {
        return write_stdout(&machine_help(), 0);
    }
    let json = matches!(
        command,
        Command::Inspect { json: true }
            | Command::Preview { json: true }
            | Command::Version { json: true }
    );
    let root = match std::env::current_dir() {
        Ok(root) => root,
        Err(error) => return error_exit(&BridgeError::Io(error)),
    };
    match Bridge::new(root).execute(&command) {
        Ok(report) => {
            let output = if json {
                serde_json::to_string(&report).map(|value| format!("{value}\n"))
            } else {
                serde_json::to_string_pretty(&report).map(|value| format!("{value}\n"))
            };
            match output {
                Ok(output) => write_stdout(&output, 0),
                Err(error) => error_exit(&BridgeError::Json(error)),
            }
        }
        Err(error) => error_exit(&error),
    }
}

fn write_stdout(value: &str, code: u8) -> ExitCode {
    let result = io::stdout()
        .lock()
        .write_all(value.as_bytes())
        .and_then(|()| io::stdout().lock().flush());
    if let Err(error) = result {
        let _ = writeln!(
            io::stderr().lock(),
            "harness-v0-migrate output failure: {error}"
        );
        return ExitCode::from(74);
    }
    ExitCode::from(code)
}

fn error_exit(error: &BridgeError) -> ExitCode {
    let _ = writeln!(io::stderr().lock(), "harness-v0-migrate: {error}");
    ExitCode::from(error.exit_code())
}
