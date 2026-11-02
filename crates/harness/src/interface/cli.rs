use std::path::PathBuf;

use clap::{Parser, Subcommand};

use crate::application::{
    CoreApplication, CoreDistributionPort, InspectionApplication, InspectionError,
    InstallationStatePort, SelfUpdateApplication, SelfUpdateExit, SessionLogPort,
    ThreeWayMergePort, UpdateCandidatePort,
};
use crate::interface::inspection_presenter::{present_skill_report, EXIT_FAILED, EXIT_USAGE};
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
    /// Report skill receipt compliance and token use from Claude Code sessions.
    ///
    /// Read-only. Pass session JSONL files explicitly; nothing is scanned or
    /// written. Prints aggregates only, never prompt or answer text.
    SkillReport {
        #[arg(long)]
        json: bool,
        /// Claude Code session files (`~/.claude/projects/<project>/<id>.jsonl`).
        #[arg(required = true)]
        sessions: Vec<PathBuf>,
    },
}

pub fn execute<D, S, M, C, U, L>(
    cli: Cli,
    application: &CoreApplication<D, S, M>,
    self_update: &SelfUpdateApplication<C, U>,
    inspection: &InspectionApplication<L>,
) -> CommandExit
where
    D: CoreDistributionPort,
    S: InstallationStatePort,
    M: ThreeWayMergePort,
    C: UpdateCandidatePort,
    U: InstallationStatePort,
    L: SessionLogPort,
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
        Command::SkillReport { json, sessions } => {
            return inspection
                .skill_report(&sessions)
                .map(|report| present_skill_report(&report, json))
                .unwrap_or_else(present_inspection_error);
        }
    };
    result.unwrap_or_else(present_error)
}

fn present_inspection_error(error: InspectionError) -> CommandExit {
    let (code, fix) = match &error {
        InspectionError::Usage(_) => (
            EXIT_USAGE,
            "Pass Claude Code session JSONL files and rerun.",
        ),
        InspectionError::Port(_) => (EXIT_FAILED, "Resolve the I/O problem above and rerun."),
    };
    CommandExit {
        code,
        stdout: String::new(),
        stderr: format!(
            "ERROR: {error}\nWHY: The command cannot produce trustworthy results from this input.\nFIX: {fix}\n"
        ),
    }
}

fn present_error(error: String) -> CommandExit {
    CommandExit {
        code: 1,
        stdout: String::new(),
        stderr: format!("Error: {error}\n"),
    }
}
