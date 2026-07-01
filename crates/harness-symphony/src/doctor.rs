use std::fs;
use std::path::Path;
use std::process::Command;

use thiserror::Error;

use crate::agent::{agent_adapter_status, agent_readiness, AgentError, Readiness};
use crate::config::ResolvedConfig;
use crate::sync::unapplied_changesets;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CheckStatus {
    Pass,
    Warn,
    Fail,
}

impl CheckStatus {
    fn label(self) -> &'static str {
        match self {
            Self::Pass => "PASS",
            Self::Warn => "WARN",
            Self::Fail => "FAIL",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DoctorCheck {
    pub name: &'static str,
    pub status: CheckStatus,
    pub detail: String,
    pub next: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DoctorReport {
    pub checks: Vec<DoctorCheck>,
}

impl DoctorReport {
    pub fn has_failures(&self) -> bool {
        self.checks
            .iter()
            .any(|check| check.status == CheckStatus::Fail)
    }
}

#[derive(Debug, Error)]
pub enum DoctorError {
    #[error("doctor io error: {0}")]
    Io(#[from] std::io::Error),
}

pub fn run_doctor(config: &ResolvedConfig) -> Result<DoctorReport, DoctorError> {
    let checks = vec![
        check_git_available(),
        check_git_worktree_support(),
        check_repo_root(&config.repo_root),
        check_database_or_changesets(config),
        check_harness_cli_exists(config),
        check_harness_db_path_support(config)?,
        check_operation_log_support(config)?,
        check_unapplied_changesets(config),
        check_gitignore(config),
        check_agent_adapter(config),
        check_agent_prerequisites(config),
        check_pr_adapter(config),
    ];
    Ok(DoctorReport { checks })
}

fn check_unapplied_changesets(config: &ResolvedConfig) -> DoctorCheck {
    match unapplied_changesets(config) {
        Ok(paths) if paths.is_empty() => DoctorCheck {
            name: "changeset sync",
            status: CheckStatus::Pass,
            detail: "all committed changesets are applied locally".to_owned(),
            next: None,
        },
        Ok(paths) => DoctorCheck {
            name: "changeset sync",
            status: CheckStatus::Warn,
            detail: format!("{} committed changeset(s) are unapplied", paths.len()),
            next: Some("Run: harness-symphony sync".to_owned()),
        },
        Err(error) => DoctorCheck {
            name: "changeset sync",
            status: CheckStatus::Warn,
            detail: format!("could not inspect changesets: {error}"),
            next: Some("Run: harness-symphony sync".to_owned()),
        },
    }
}

pub fn print_report(report: &DoctorReport) {
    println!("Harness Symphony Doctor");
    for check in &report.checks {
        println!(
            "[{}] {} - {}",
            check.status.label(),
            check.name,
            check.detail
        );
        if let Some(next) = &check.next {
            println!("  Next: {next}");
        }
    }
}

fn check_git_available() -> DoctorCheck {
    match Command::new("git").arg("--version").output() {
        Ok(output) if output.status.success() => DoctorCheck {
            name: "git",
            status: CheckStatus::Pass,
            detail: String::from_utf8_lossy(&output.stdout).trim().to_owned(),
            next: None,
        },
        _ => DoctorCheck {
            name: "git",
            status: CheckStatus::Fail,
            detail: "git is not available".to_owned(),
            next: Some("Install git and ensure it is on PATH.".to_owned()),
        },
    }
}

fn check_git_worktree_support() -> DoctorCheck {
    match Command::new("git").args(["worktree", "list"]).output() {
        Ok(output) if output.status.success() => DoctorCheck {
            name: "git worktree",
            status: CheckStatus::Pass,
            detail: "git worktree is available".to_owned(),
            next: None,
        },
        _ => DoctorCheck {
            name: "git worktree",
            status: CheckStatus::Fail,
            detail: "git worktree list failed".to_owned(),
            next: Some("Use a Git version that supports worktrees.".to_owned()),
        },
    }
}

fn check_repo_root(repo_root: &Path) -> DoctorCheck {
    match Command::new("git")
        .args(["rev-parse", "--show-toplevel"])
        .current_dir(repo_root)
        .output()
    {
        Ok(output) if output.status.success() => DoctorCheck {
            name: "repo root",
            status: CheckStatus::Pass,
            detail: String::from_utf8_lossy(&output.stdout).trim().to_owned(),
            next: None,
        },
        _ => DoctorCheck {
            name: "repo root",
            status: CheckStatus::Fail,
            detail: format!("{} is not inside a Git repository", repo_root.display()),
            next: Some(
                "Run harness-symphony from the repository root or pass --repo-root.".to_owned(),
            ),
        },
    }
}

fn check_database_or_changesets(config: &ResolvedConfig) -> DoctorCheck {
    if config.harness_db.exists() {
        return DoctorCheck {
            name: "harness database",
            status: CheckStatus::Pass,
            detail: format!("database exists at {}", config.harness_db.display()),
            next: None,
        };
    }
    if config.changeset_directory.exists() {
        return DoctorCheck {
            name: "harness database",
            status: CheckStatus::Warn,
            detail: "database is absent but changesets are available".to_owned(),
            next: Some(format!(
                "Run: scripts/bin/harness-cli db rebuild --from {}",
                config.changeset_directory.display()
            )),
        };
    }
    DoctorCheck {
        name: "harness database",
        status: CheckStatus::Fail,
        detail: "harness.db is absent and no changesets directory exists".to_owned(),
        next: Some("Run: scripts/bin/harness-cli init".to_owned()),
    }
}

fn check_harness_cli_exists(config: &ResolvedConfig) -> DoctorCheck {
    let cli = harness_cli_path(config);
    match Command::new(&cli).arg("--version").output() {
        Ok(output) if output.status.success() => DoctorCheck {
            name: "harness-cli",
            status: CheckStatus::Pass,
            detail: String::from_utf8_lossy(&output.stdout).trim().to_owned(),
            next: None,
        },
        _ => DoctorCheck {
            name: "harness-cli",
            status: CheckStatus::Fail,
            detail: format!("{} is not runnable", cli.display()),
            next: Some("Build or install scripts/bin/harness-cli.".to_owned()),
        },
    }
}

fn check_harness_db_path_support(config: &ResolvedConfig) -> Result<DoctorCheck, DoctorError> {
    let temp_dir = tempfile::tempdir()?;
    prepare_temp_schema(config, temp_dir.path())?;
    let path_db = temp_dir.path().join("path.db");
    let legacy_db = temp_dir.path().join("legacy.db");
    let cli = harness_cli_path(config);
    let output = Command::new(&cli)
        .arg("init")
        .env("HARNESS_REPO_ROOT", temp_dir.path())
        .env("HARNESS_DB_PATH", &path_db)
        .env("HARNESS_DB", &legacy_db)
        .output();

    match output {
        Ok(output) if output.status.success() && path_db.exists() && !legacy_db.exists() => {
            Ok(DoctorCheck {
                name: "HARNESS_DB_PATH",
                status: CheckStatus::Pass,
                detail: "harness-cli writes to HARNESS_DB_PATH".to_owned(),
                next: None,
            })
        }
        _ => Ok(DoctorCheck {
            name: "HARNESS_DB_PATH",
            status: CheckStatus::Fail,
            detail: "harness-cli did not isolate writes to HARNESS_DB_PATH".to_owned(),
            next: Some("Complete E04 US-028 or rebuild scripts/bin/harness-cli.".to_owned()),
        }),
    }
}

fn check_operation_log_support(config: &ResolvedConfig) -> Result<DoctorCheck, DoctorError> {
    let temp_dir = tempfile::tempdir()?;
    prepare_temp_schema(config, temp_dir.path())?;
    let db = temp_dir.path().join("harness.db");
    let cli = harness_cli_path(config);
    let init = Command::new(&cli)
        .arg("init")
        .env("HARNESS_REPO_ROOT", temp_dir.path())
        .env("HARNESS_DB_PATH", &db)
        .output();
    if !init.is_ok_and(|output| output.status.success()) {
        return Ok(DoctorCheck {
            name: "operation log",
            status: CheckStatus::Fail,
            detail: "could not initialize temp DB for operation-log probe".to_owned(),
            next: Some("Run: scripts/bin/harness-cli init".to_owned()),
        });
    }

    let run_id = "doctor_probe";
    let output = Command::new(&cli)
        .args([
            "intake",
            "--type",
            "Harness improvement",
            "--summary",
            "Doctor operation log probe",
            "--lane",
            "tiny",
        ])
        .env("HARNESS_REPO_ROOT", temp_dir.path())
        .env("HARNESS_DB_PATH", &db)
        .env("HARNESS_RUN_ID", run_id)
        .output();
    let changeset = temp_dir
        .path()
        .join(".harness/changesets/doctor_probe.changeset.jsonl");

    match output {
        Ok(output) if output.status.success() && changeset.exists() => Ok(DoctorCheck {
            name: "operation log",
            status: CheckStatus::Pass,
            detail: "harness-cli writes semantic changesets for HARNESS_RUN_ID".to_owned(),
            next: None,
        }),
        _ => Ok(DoctorCheck {
            name: "operation log",
            status: CheckStatus::Fail,
            detail: "harness-cli did not write an operation log".to_owned(),
            next: Some("Complete E04 US-029 or rebuild scripts/bin/harness-cli.".to_owned()),
        }),
    }
}

fn check_gitignore(config: &ResolvedConfig) -> DoctorCheck {
    let path = config.repo_root.join(".gitignore");
    let Ok(text) = fs::read_to_string(&path) else {
        return DoctorCheck {
            name: ".gitignore",
            status: CheckStatus::Fail,
            detail: ".gitignore is missing".to_owned(),
            next: Some(
                "Add harness.db, harness.db-wal, harness.db-shm, and .symphony/.".to_owned(),
            ),
        };
    };
    let required = [
        "harness.db",
        "harness.db-wal",
        "harness.db-shm",
        ".symphony/",
    ];
    let missing = required
        .iter()
        .filter(|entry| !text.lines().any(|line| line.trim() == **entry))
        .copied()
        .collect::<Vec<_>>();
    if missing.is_empty() {
        DoctorCheck {
            name: ".gitignore",
            status: CheckStatus::Pass,
            detail: "local DB and Symphony runtime files are ignored".to_owned(),
            next: None,
        }
    } else {
        DoctorCheck {
            name: ".gitignore",
            status: CheckStatus::Fail,
            detail: format!("missing ignore entries: {}", missing.join(", ")),
            next: Some(format!("Add to .gitignore: {}", missing.join(", "))),
        }
    }
}

fn check_agent_adapter(config: &ResolvedConfig) -> DoctorCheck {
    match agent_adapter_status(config) {
        Ok(detail) => DoctorCheck {
            name: "agent adapter",
            status: CheckStatus::Pass,
            detail,
            next: None,
        },
        Err(AgentError::MissingCommand) => DoctorCheck {
            name: "agent adapter",
            status: CheckStatus::Warn,
            detail: "custom agent command is not configured".to_owned(),
            next: Some(
                "Set agent.command in .harness/symphony.yml before launching runs.".to_owned(),
            ),
        },
        Err(error) => DoctorCheck {
            name: "agent adapter",
            status: CheckStatus::Fail,
            detail: error.to_string(),
            next: Some("Set agent.adapter to custom or codex in .harness/symphony.yml.".to_owned()),
        },
    }
}

fn check_agent_prerequisites(config: &ResolvedConfig) -> DoctorCheck {
    let readiness = agent_readiness(config, &config.agent_adapter);
    let status = match readiness.overall {
        Readiness::Ready => CheckStatus::Pass,
        // Warn-only: probes are environment-dependent and must not turn a
        // working config red just because a binary or credential is absent here.
        Readiness::NeedsSetup | Readiness::NotInstalled | Readiness::Unknown => CheckStatus::Warn,
    };
    DoctorCheck {
        name: "agent prerequisites",
        status,
        detail: format!(
            "{}: {}; auth: {}",
            readiness.adapter, readiness.binary_detail, readiness.auth_detail
        ),
        next: readiness.next,
    }
}

fn check_pr_adapter(config: &ResolvedConfig) -> DoctorCheck {
    if config.pull_request_create == "disabled" || config.pull_request_create == "never" {
        return DoctorCheck {
            name: "PR adapter",
            status: CheckStatus::Warn,
            detail: "PR creation is disabled".to_owned(),
            next: None,
        };
    }
    if config.pull_request_provider == "github" {
        match Command::new("gh").arg("--version").output() {
            Ok(output) if output.status.success() => DoctorCheck {
                name: "PR adapter",
                status: CheckStatus::Pass,
                detail: "GitHub CLI is available".to_owned(),
                next: None,
            },
            _ => DoctorCheck {
                name: "PR adapter",
                status: CheckStatus::Warn,
                detail: "GitHub CLI is not available".to_owned(),
                next: Some("Install gh or set pull_request.create: disabled.".to_owned()),
            },
        }
    } else {
        DoctorCheck {
            name: "PR adapter",
            status: CheckStatus::Warn,
            detail: format!("unsupported PR provider '{}'", config.pull_request_provider),
            next: Some("Set pull_request.provider: github or disable PR creation.".to_owned()),
        }
    }
}

fn harness_cli_path(config: &ResolvedConfig) -> std::path::PathBuf {
    config.repo_root.join("scripts/bin/harness-cli")
}

fn prepare_temp_schema(config: &ResolvedConfig, temp_root: &Path) -> Result<(), DoctorError> {
    let source = config.repo_root.join("scripts/schema");
    let target = temp_root.join("scripts/schema");
    fs::create_dir_all(&target)?;
    for entry in fs::read_dir(source)? {
        let entry = entry?;
        let path = entry.path();
        if path.extension().and_then(|value| value.to_str()) == Some("sql") {
            fs::copy(&path, target.join(entry.file_name()))?;
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn base_config() -> ResolvedConfig {
        ResolvedConfig {
            version: 1,
            repo_root: Path::new("/repo").to_path_buf(),
            harness_db: Path::new("/repo/harness.db").to_path_buf(),
            state_db: Path::new("/repo/.symphony/state.db").to_path_buf(),
            runs_dir: Path::new("/repo/.harness/runs").to_path_buf(),
            worktrees_dir: Path::new("/repo/.symphony/worktrees").to_path_buf(),
            single_active_run: true,
            agent_adapter: "custom".to_owned(),
            agent_command: Vec::new(),
            agent_model: None,
            agent_timeout_minutes: 120,
            pull_request_create: "ask".to_owned(),
            pull_request_provider: "github".to_owned(),
            pull_request_draft_for: vec![],
            changeset_directory: Path::new("/repo/.harness/changesets").to_path_buf(),
            changeset_render_in_summary: true,
            allow_here_for_tiny: true,
            compact_keep_last: 50,
            keep_failed_worktrees: true,
            cleanup_after_sync: false,
            auto_source: "harness-db".to_owned(),
            auto_poll_interval_seconds: 30,
            auto_max_attempts: 3,
        }
    }

    #[test]
    fn report_failure_detection() {
        let report = DoctorReport {
            checks: vec![DoctorCheck {
                name: "x",
                status: CheckStatus::Fail,
                detail: "failed".to_owned(),
                next: Some("fix it".to_owned()),
            }],
        };

        assert!(report.has_failures());
    }

    #[test]
    fn missing_agent_command_is_warning() {
        let config = base_config();
        let check = check_agent_adapter(&config);

        assert_eq!(check.status, CheckStatus::Warn);
        assert!(check.next.unwrap().contains("agent.command"));
    }

    #[test]
    fn unsupported_agent_adapter_fails() {
        let mut config = base_config();
        config.agent_adapter = "unknown".to_owned();
        let check = check_agent_adapter(&config);

        assert_eq!(check.status, CheckStatus::Fail);
        assert!(check.next.unwrap().contains("agent.adapter"));
    }

    #[test]
    fn agent_prerequisites_warn_for_unconfigured_custom() {
        // custom + no command is deterministic (no real binary probe involved):
        // NeedsSetup maps to Warn, never Fail.
        let config = base_config();
        let check = check_agent_prerequisites(&config);

        assert_eq!(check.name, "agent prerequisites");
        assert_eq!(check.status, CheckStatus::Warn);
        assert!(check.next.unwrap().contains("agent.command"));
    }

    #[test]
    fn codex_agent_adapter_passes_without_explicit_command() {
        let mut config = base_config();
        config.agent_adapter = "codex".to_owned();
        let check = check_agent_adapter(&config);

        assert_eq!(check.status, CheckStatus::Pass);
        assert!(check.detail.contains("codex app-server"));
    }
}
