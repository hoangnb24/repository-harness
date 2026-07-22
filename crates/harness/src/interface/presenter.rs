use serde::Serialize;

use crate::application::ExecutableRecoveryReport;
use crate::domain::{
    ConflictReason, DoctorReport, FileChangeKind, InstallReport, InstallationCondition,
    StatusReport, UpdateReport,
};

pub struct CommandExit {
    pub code: i32,
    pub stdout: String,
    pub stderr: String,
}

pub fn present_install(report: &InstallReport, json: bool) -> CommandExit {
    let output = InstallOutput {
        operation: "install",
        version: &report.version,
        dry_run: report.dry_run,
        applied: report.applied,
        changes: report
            .changes
            .iter()
            .map(|change| ChangeOutput {
                path: change.path.as_str(),
                kind: change_kind(&change.kind),
            })
            .collect(),
        backup_path: report.backup_path.as_deref(),
        recovered_interrupted_transaction: report.recovered_interrupted_transaction,
    };
    success(render(
        json,
        &output,
        format!(
            "Harness core {} {}.\n{}",
            report.version,
            if report.dry_run {
                "install preview"
            } else {
                "installed"
            },
            render_changes(&report.changes)
        ),
    ))
}

pub fn present_update(report: &UpdateReport, json: bool) -> CommandExit {
    let output = UpdateOutput {
        operation: "update",
        from_version: &report.from_version,
        to_version: &report.to_version,
        dry_run: report.dry_run,
        applied: report.applied,
        changes: report
            .changes
            .iter()
            .map(|change| ChangeOutput {
                path: change.path.as_str(),
                kind: change_kind(&change.kind),
            })
            .collect(),
        conflicts: report
            .conflicts
            .iter()
            .map(|conflict| ConflictOutput {
                path: conflict.path.as_str(),
                reason: conflict_reason(&conflict.reason),
                detail: &conflict.detail,
            })
            .collect(),
        resolution_staged: report.resolution_staged,
        backup_path: report.backup_path.as_deref(),
        recovered_interrupted_transaction: report.recovered_interrupted_transaction,
    };
    let human = if report.conflicts.is_empty() {
        format!(
            "Harness core {} -> {} {}.\n{}",
            report.from_version,
            report.to_version,
            if report.dry_run {
                "update preview"
            } else {
                "updated"
            },
            render_changes(&report.changes)
        )
    } else {
        let conflicts = report
            .conflicts
            .iter()
            .map(|conflict| {
                format!(
                    "conflict {} ({:?}): {}",
                    conflict.path, conflict.reason, conflict.detail
                )
            })
            .collect::<Vec<_>>()
            .join("\n");
        let resolution = if report.resolution_staged {
            let paths = report
                .conflicts
                .iter()
                .map(|conflict| format!("  .harness-core/update/resolved/{}", conflict.path))
                .collect::<Vec<_>>()
                .join("\n");
            format!(
                "\nResolve after human direction:\n{paths}\nThen run: harness update --continue\nAbort with: harness update --abort\n"
            )
        } else {
            String::new()
        };
        format!("Update stopped; no files changed.\n{conflicts}\n{resolution}")
    };
    CommandExit {
        code: if report.conflicts.is_empty() { 0 } else { 2 },
        stdout: render(json, &output, human),
        stderr: String::new(),
    }
}

pub fn present_abort(removed: bool, json: bool) -> CommandExit {
    #[derive(Serialize)]
    struct AbortOutput {
        operation: &'static str,
        removed: bool,
    }
    success(render(
        json,
        &AbortOutput {
            operation: "update_abort",
            removed,
        },
        if removed {
            "Staged update resolution aborted; managed files were unchanged.\n".to_owned()
        } else {
            "No staged update resolution exists.\n".to_owned()
        },
    ))
}

pub fn present_executable_recovery(report: &ExecutableRecoveryReport, json: bool) -> CommandExit {
    #[derive(Serialize)]
    struct RecoveryOutput<'a> {
        operation: &'static str,
        executable_version: &'a str,
        core_version: &'a str,
        dry_run: bool,
        applied: bool,
    }
    success(render(
        json,
        &RecoveryOutput {
            operation: "executable_recovery",
            executable_version: &report.executable_version,
            core_version: &report.core_version,
            dry_run: report.dry_run,
            applied: report.applied,
        },
        format!(
            "{} Harness executable {} to match installed core {}.\n",
            if report.dry_run {
                "Would recover"
            } else {
                "Recovered"
            },
            report.executable_version,
            report.core_version
        ),
    ))
}

pub fn present_status(report: &StatusReport, json: bool) -> CommandExit {
    let output = StatusOutput {
        operation: "status",
        condition: condition(&report.condition),
        installed_version: report.installed_version.as_deref(),
        target_version: &report.target_version,
        files: report
            .files
            .iter()
            .map(|file| FileStatusOutput {
                path: file.path.as_str(),
                modified: file.modified,
                missing: file.missing,
            })
            .collect(),
    };
    let modified = report.files.iter().filter(|file| file.modified).count();
    let missing = report.files.iter().filter(|file| file.missing).count();
    CommandExit {
        code: if report.condition == InstallationCondition::NotInstalled {
            1
        } else {
            0
        },
        stdout: render(
            json,
            &output,
            format!(
                "Harness core: {} (installed={}, target={}, modified={}, missing={})\n",
                condition(&report.condition),
                report.installed_version.as_deref().unwrap_or("none"),
                report.target_version,
                modified,
                missing
            ),
        ),
        stderr: String::new(),
    }
}

pub fn present_doctor(report: &DoctorReport, json: bool) -> CommandExit {
    let output = DoctorOutput {
        operation: "doctor",
        healthy: report.healthy,
        checks: report
            .checks
            .iter()
            .map(|check| DoctorCheckOutput {
                name: &check.name,
                passed: check.passed,
                detail: &check.detail,
            })
            .collect(),
    };
    let human = report
        .checks
        .iter()
        .map(|check| {
            format!(
                "{} {}: {}",
                if check.passed { "pass" } else { "fail" },
                check.name,
                check.detail
            )
        })
        .collect::<Vec<_>>()
        .join("\n")
        + "\n";
    CommandExit {
        code: if report.healthy { 0 } else { 1 },
        stdout: render(json, &output, human),
        stderr: String::new(),
    }
}

fn success(stdout: String) -> CommandExit {
    CommandExit {
        code: 0,
        stdout,
        stderr: String::new(),
    }
}

fn render<T: Serialize>(json: bool, output: &T, human: String) -> String {
    if json {
        serde_json::to_string(output).expect("serializable presenter output") + "\n"
    } else {
        human
    }
}

fn render_changes(changes: &[crate::domain::PlannedFileChange]) -> String {
    changes
        .iter()
        .map(|change| format!("{} {}", change_kind(&change.kind), change.path))
        .collect::<Vec<_>>()
        .join("\n")
        + "\n"
}

fn change_kind(kind: &FileChangeKind) -> &'static str {
    match kind {
        FileChangeKind::Create => "create",
        FileChangeKind::Update => "update",
        FileChangeKind::Delete => "delete",
        FileChangeKind::Preserve => "preserve",
        FileChangeKind::Adopt => "adopt",
    }
}

fn conflict_reason(reason: &ConflictReason) -> &'static str {
    match reason {
        ConflictReason::OverlappingChanges => "overlapping_changes",
        ConflictReason::MissingManagedFile => "missing_managed_file",
        ConflictReason::ExistingUnmanagedPath => "existing_unmanaged_path",
        ConflictReason::ModifiedRemovedFile => "modified_removed_file",
        ConflictReason::UnsafePath => "unsafe_path",
    }
}

fn condition(value: &InstallationCondition) -> &'static str {
    match value {
        InstallationCondition::NotInstalled => "not_installed",
        InstallationCondition::Current => "current",
        InstallationCondition::UpdateAvailable => "update_available",
        InstallationCondition::ExecutableOutdated => "executable_outdated",
    }
}

#[derive(Serialize)]
struct InstallOutput<'a> {
    operation: &'static str,
    version: &'a str,
    dry_run: bool,
    applied: bool,
    changes: Vec<ChangeOutput<'a>>,
    backup_path: Option<&'a str>,
    recovered_interrupted_transaction: bool,
}

#[derive(Serialize)]
struct UpdateOutput<'a> {
    operation: &'static str,
    from_version: &'a str,
    to_version: &'a str,
    dry_run: bool,
    applied: bool,
    changes: Vec<ChangeOutput<'a>>,
    conflicts: Vec<ConflictOutput<'a>>,
    resolution_staged: bool,
    backup_path: Option<&'a str>,
    recovered_interrupted_transaction: bool,
}

#[derive(Serialize)]
struct StatusOutput<'a> {
    operation: &'static str,
    condition: &'static str,
    installed_version: Option<&'a str>,
    target_version: &'a str,
    files: Vec<FileStatusOutput<'a>>,
}

#[derive(Serialize)]
struct DoctorOutput<'a> {
    operation: &'static str,
    healthy: bool,
    checks: Vec<DoctorCheckOutput<'a>>,
}

#[derive(Serialize)]
struct ChangeOutput<'a> {
    path: &'a str,
    kind: &'static str,
}

#[derive(Serialize)]
struct ConflictOutput<'a> {
    path: &'a str,
    reason: &'static str,
    detail: &'a str,
}

#[derive(Serialize)]
struct FileStatusOutput<'a> {
    path: &'a str,
    modified: bool,
    missing: bool,
}

#[derive(Serialize)]
struct DoctorCheckOutput<'a> {
    name: &'a str,
    passed: bool,
    detail: &'a str,
}
