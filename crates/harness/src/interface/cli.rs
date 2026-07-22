use std::path::PathBuf;

use clap::{Parser, Subcommand};

use crate::application::{
    CoreApplication, CoreDistributionPort, InstallationStatePort, SelfUpdateApplication,
    SelfUpdateExit, ThreeWayMergePort, UpdateCandidatePort,
};
use crate::interface::presenter::{
    present_abort, present_doctor, present_executable_recovery, present_install, present_status,
    present_update, CommandExit,
};

#[derive(Debug, Parser)]
#[command(
    name = "harness",
    version,
    about = "Install and safely maintain a repository Harness core"
)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Command,
}

#[derive(Debug, Subcommand)]
pub enum Command {
    /// Install a fresh core or adopt an existing copy-on-install core.
    Install {
        #[arg(long, default_value = ".")]
        directory: PathBuf,
        #[arg(long)]
        dry_run: bool,
        #[arg(long)]
        json: bool,
    },
    /// Preview or apply a conflict-safe three-way core update.
    Update {
        #[arg(long, default_value = ".")]
        directory: PathBuf,
        #[arg(long)]
        dry_run: bool,
        #[arg(long)]
        json: bool,
        /// Continue an agent-resolved staged conflict session.
        #[arg(long = "continue", conflicts_with = "abort")]
        continue_update: bool,
        /// Abort and remove a staged conflict session.
        #[arg(long, conflicts_with_all = ["continue_update", "dry_run"])]
        abort: bool,
        /// Apply this executable's embedded core; used by a verified candidate.
        #[arg(long, hide = true)]
        candidate: bool,
    },
    /// Inspect installed version and consumer modifications without mutation.
    Status {
        #[arg(long, default_value = ".")]
        directory: PathBuf,
        #[arg(long)]
        json: bool,
    },
    /// Validate provenance, paths, merge support, and transaction health.
    Doctor {
        #[arg(long, default_value = ".")]
        directory: PathBuf,
        #[arg(long)]
        json: bool,
    },
}

pub fn execute<D, S, M, C, U>(
    cli: Cli,
    application: &CoreApplication<D, S, M>,
    self_update: &SelfUpdateApplication<C, U>,
) -> CommandExit
where
    D: CoreDistributionPort,
    S: InstallationStatePort,
    M: ThreeWayMergePort,
    C: UpdateCandidatePort,
    U: InstallationStatePort,
{
    let result: Result<CommandExit, String> = match cli.command {
        Command::Install {
            directory,
            dry_run,
            json,
        } => application
            .install(&directory, dry_run)
            .map(|report| present_install(&report, json))
            .map_err(|error| error.to_string()),
        Command::Update {
            directory,
            dry_run,
            json,
            continue_update,
            abort,
            candidate,
        } => {
            if abort {
                self_update
                    .discard_retained_candidate(&directory)
                    .and_then(|_| {
                        application
                            .abort_update(&directory)
                            .map_err(|error| crate::application::PortError::new(error.to_string()))
                    })
                    .map(|removed| present_abort(removed, json))
                    .map_err(|error| error.to_string())
            } else if !candidate {
                self_update
                    .execute(&directory, dry_run, continue_update, json)
                    .map(|exit| match exit {
                        SelfUpdateExit::Forwarded {
                            code,
                            stdout,
                            stderr,
                        } => CommandExit {
                            code,
                            stdout: String::from_utf8_lossy(&stdout).into_owned(),
                            stderr: String::from_utf8_lossy(&stderr).into_owned(),
                        },
                        SelfUpdateExit::Recovery(report) => {
                            present_executable_recovery(&report, json)
                        }
                    })
                    .map_err(|error| error.to_string())
            } else if continue_update {
                application
                    .continue_update(&directory, dry_run)
                    .map(|report| present_update(&report, json))
                    .map_err(|error| error.to_string())
            } else {
                application
                    .update(&directory, dry_run)
                    .map(|report| present_update(&report, json))
                    .map_err(|error| error.to_string())
            }
        }
        Command::Status { directory, json } => application
            .status(&directory)
            .map(|report| present_status(&report, json))
            .map_err(|error| error.to_string()),
        Command::Doctor { directory, json } => application
            .doctor(&directory)
            .map(|report| present_doctor(&report, json))
            .map_err(|error| error.to_string()),
    };
    result.unwrap_or_else(present_error)
}

fn present_error(error: String) -> CommandExit {
    CommandExit {
        code: 1,
        stdout: String::new(),
        stderr: format!("Error: {error}\n"),
    }
}
