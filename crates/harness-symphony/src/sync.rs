use std::path::{Path, PathBuf};
use std::process::Command;

use rusqlite::{params, Connection, OptionalExtension};
use thiserror::Error;

use crate::changeset::{changeset_files, changeset_id, ChangesetError};
use crate::config::ResolvedConfig;
use crate::state::{RunStateStore, StateError};

#[derive(Debug, Error)]
pub enum SyncError {
    #[error("{0}")]
    Changeset(#[from] ChangesetError),
    #[error("{0}")]
    State(#[from] StateError),
    #[error("sqlite error: {0}")]
    Sqlite(#[from] rusqlite::Error),
    #[error("harness-cli failed for {path}: {stderr}")]
    ApplyFailed { path: String, stderr: String },
    #[error("sync io error: {0}")]
    Io(#[from] std::io::Error),
    #[error("git command failed: {0}")]
    GitFailed(String),
    #[error("checkout has local changes; commit, stash, or reset before syncing:\n{0}")]
    DirtyCheckout(String),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SyncChange {
    pub id: String,
    pub path: PathBuf,
    pub applied: bool,
    pub operations: usize,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SyncResult {
    pub changes: Vec<SyncChange>,
}

pub fn sync_changesets(config: &ResolvedConfig) -> Result<SyncResult, SyncError> {
    refresh_checkout_from_upstream(config)?;
    let store = RunStateStore::new(config.state_db.clone());
    store.init()?;
    let paths = changeset_files(&config.changeset_directory)?;
    let mut changes = Vec::new();
    for path in paths {
        changes.push(apply_changeset_path(config, &store, path)?);
    }
    Ok(SyncResult { changes })
}

pub fn sync_changeset(config: &ResolvedConfig, run_id: &str) -> Result<SyncResult, SyncError> {
    refresh_checkout_from_upstream(config)?;
    let store = RunStateStore::new(config.state_db.clone());
    store.init()?;
    let path = config
        .changeset_directory
        .join(format!("{run_id}.changeset.jsonl"));
    let change = apply_changeset_path(config, &store, path)?;
    Ok(SyncResult {
        changes: vec![change],
    })
}

pub fn refresh_checkout_from_upstream(config: &ResolvedConfig) -> Result<bool, SyncError> {
    if upstream_branch(&config.repo_root)?.is_none() {
        return Ok(false);
    }
    ensure_clean_checkout(&config.repo_root)?;
    git_command(&config.repo_root, &["pull", "--ff-only"])?;
    Ok(true)
}

pub fn unapplied_changesets(config: &ResolvedConfig) -> Result<Vec<PathBuf>, SyncError> {
    let store = RunStateStore::new(config.state_db.clone());
    store.init()?;
    let mut unapplied = Vec::new();
    for path in changeset_files(&config.changeset_directory)? {
        let id = changeset_id(&path)?;
        if !harness_db_has_changeset(&config.harness_db, &id)? || !store.changeset_synced(&id)? {
            unapplied.push(path);
        }
    }
    Ok(unapplied)
}

fn harness_db_has_changeset(db_path: &Path, id: &str) -> Result<bool, SyncError> {
    if !db_path.exists() {
        return Ok(false);
    }
    let connection = Connection::open(db_path)?;
    connection
        .query_row(
            "SELECT 1 FROM changeset_applied WHERE id=?1;",
            params![id],
            |_| Ok(()),
        )
        .optional()
        .map(|value| value.is_some())
        .map_err(SyncError::from)
}

fn apply_changeset_path(
    config: &ResolvedConfig,
    store: &RunStateStore,
    path: PathBuf,
) -> Result<SyncChange, SyncError> {
    let id = changeset_id(&path)?;
    if harness_db_has_changeset(&config.harness_db, &id)? && store.changeset_synced(&id)? {
        return Ok(SyncChange {
            id,
            path,
            applied: false,
            operations: 0,
        });
    }
    let output = Command::new(config.repo_root.join("scripts/bin/harness-cli"))
        .args(["db", "changeset", "apply"])
        .arg(&path)
        .env("HARNESS_DB_PATH", &config.harness_db)
        .current_dir(&config.repo_root)
        .output()?;
    if !output.status.success() {
        return Err(SyncError::ApplyFailed {
            path: path.display().to_string(),
            stderr: String::from_utf8_lossy(&output.stderr).trim().to_owned(),
        });
    }
    let stdout = String::from_utf8_lossy(&output.stdout);
    let applied = stdout.contains(" applied ");
    let operations = parse_operations(&stdout);
    store.record_changeset_synced(&id, &path, applied)?;
    if applied {
        let _ = store.update_sync_status(&id, "synced", "done");
    }
    Ok(SyncChange {
        id,
        path,
        applied,
        operations,
    })
}

fn upstream_branch(repo_root: &Path) -> Result<Option<String>, SyncError> {
    let output = Command::new("git")
        .args(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
        .current_dir(repo_root)
        .output()?;
    if output.status.success() {
        let upstream = String::from_utf8_lossy(&output.stdout).trim().to_owned();
        return Ok((!upstream.is_empty()).then_some(upstream));
    }
    Ok(None)
}

fn ensure_clean_checkout(repo_root: &Path) -> Result<(), SyncError> {
    let output = git_output(
        repo_root,
        &["status", "--porcelain", "--untracked-files=all"],
    )?;
    let status = String::from_utf8_lossy(&output.stdout)
        .lines()
        .map(str::trim)
        .filter(|line| !line.is_empty())
        .filter(|line| !is_ignorable_checkout_status(line))
        .collect::<Vec<_>>()
        .join("\n");
    if status.is_empty() {
        Ok(())
    } else {
        Err(SyncError::DirtyCheckout(status))
    }
}

fn is_ignorable_checkout_status(line: &str) -> bool {
    let path = porcelain_path(line);
    path == ".harness/symphony.yml"
        || path.starts_with(".harness/runs/")
        || path.ends_with(".tsbuildinfo")
}

fn porcelain_path(line: &str) -> &str {
    line.get(3..).unwrap_or(line).trim()
}

fn git_command(repo_root: &Path, args: &[&str]) -> Result<(), SyncError> {
    let output = git_output(repo_root, args)?;
    if output.status.success() {
        Ok(())
    } else {
        Err(SyncError::GitFailed(
            String::from_utf8_lossy(&output.stderr).trim().to_owned(),
        ))
    }
}

fn git_output(repo_root: &Path, args: &[&str]) -> Result<std::process::Output, SyncError> {
    Command::new("git")
        .args(args)
        .current_dir(repo_root)
        .output()
        .map_err(SyncError::from)
}

fn parse_operations(stdout: &str) -> usize {
    stdout
        .split('(')
        .nth(1)
        .and_then(|value| value.split_whitespace().next())
        .and_then(|value| value.parse::<usize>().ok())
        .unwrap_or(0)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::ResolvedConfig;
    use std::fs;
    use std::process::Command;

    #[test]
    fn parses_operation_count_from_cli_output() {
        assert_eq!(
            parse_operations("Changeset run_1 applied (3 operation(s))."),
            3
        );
        assert_eq!(
            parse_operations("Changeset run_1 already applied; skipped."),
            0
        );
    }

    #[test]
    fn sync_changeset_applies_only_requested_run() {
        let temp_dir = tempfile::tempdir().unwrap();
        let config = config_for_root(temp_dir.path());
        fs::create_dir_all(&config.changeset_directory).unwrap();
        fs::create_dir_all(temp_dir.path().join("scripts/bin")).unwrap();
        fs::write(
            config.changeset_directory.join("run_one.changeset.jsonl"),
            r#"{"op":"changeset.header","version":1,"run_id":"run_one"}
{"op":"story.update","version":1,"id":"US-ONE","payload":{"status":"implemented"}}
"#,
        )
        .unwrap();
        fs::write(
            config.changeset_directory.join("run_two.changeset.jsonl"),
            r#"{"op":"changeset.header","version":1,"run_id":"run_two"}
{"op":"story.update","version":1,"id":"US-TWO","payload":{"status":"implemented"}}
"#,
        )
        .unwrap();
        let cli_path = temp_dir.path().join("scripts/bin/harness-cli");
        fs::write(
            &cli_path,
            "#!/bin/sh\nprintf '%s\\n' \"$@\" >> sync-args.log\necho 'Changeset run_one applied (2 operation(s)).'\n",
        )
        .unwrap();
        make_executable(&cli_path);

        let result = sync_changeset(&config, "run_one").unwrap();

        assert_eq!(result.changes.len(), 1);
        assert_eq!(result.changes[0].id, "run_one");
        assert!(result.changes[0].applied);
        let args = fs::read_to_string(temp_dir.path().join("sync-args.log")).unwrap();
        assert!(args.contains(".harness/changesets/run_one.changeset.jsonl"));
        assert!(!args.contains("run_two.changeset.jsonl"));
    }

    #[test]
    fn refresh_checkout_fast_forwards_from_upstream() {
        let temp_dir = tempfile::tempdir().unwrap();
        let remote = temp_dir.path().join("remote.git");
        run_git(
            temp_dir.path(),
            &["init", "--bare", &remote.display().to_string()],
        );
        let local = temp_dir.path().join("local");
        let other = temp_dir.path().join("other");
        run_git(
            temp_dir.path(),
            &[
                "clone",
                &remote.display().to_string(),
                &local.display().to_string(),
            ],
        );
        configure_git(&local);
        fs::write(local.join("README.md"), "one\n").unwrap();
        run_git(&local, &["add", "README.md"]);
        run_git(&local, &["commit", "-m", "one"]);
        run_git(&local, &["push", "-u", "origin", "HEAD"]);
        run_git(
            temp_dir.path(),
            &[
                "clone",
                &remote.display().to_string(),
                &other.display().to_string(),
            ],
        );
        configure_git(&other);
        fs::write(other.join("README.md"), "two\n").unwrap();
        run_git(&other, &["commit", "-am", "two"]);
        run_git(&other, &["push"]);

        let refreshed = refresh_checkout_from_upstream(&config_for_root(&local)).unwrap();

        assert!(refreshed);
        assert_eq!(
            fs::read_to_string(local.join("README.md")).unwrap(),
            "two\n"
        );
    }

    #[test]
    fn refresh_checkout_refuses_dirty_checkout() {
        let temp_dir = tempfile::tempdir().unwrap();
        let remote = temp_dir.path().join("remote.git");
        run_git(
            temp_dir.path(),
            &["init", "--bare", &remote.display().to_string()],
        );
        let local = temp_dir.path().join("local");
        run_git(
            temp_dir.path(),
            &[
                "clone",
                &remote.display().to_string(),
                &local.display().to_string(),
            ],
        );
        configure_git(&local);
        fs::write(local.join("README.md"), "one\n").unwrap();
        run_git(&local, &["add", "README.md"]);
        run_git(&local, &["commit", "-m", "one"]);
        run_git(&local, &["push", "-u", "origin", "HEAD"]);
        fs::write(local.join("local.txt"), "dirty\n").unwrap();

        let error = refresh_checkout_from_upstream(&config_for_root(&local)).unwrap_err();

        assert!(matches!(error, SyncError::DirtyCheckout(status) if status.contains("local.txt")));
    }

    #[test]
    fn refresh_checkout_allows_only_local_symphony_artifacts() {
        let temp_dir = tempfile::tempdir().unwrap();
        let remote = temp_dir.path().join("remote.git");
        run_git(
            temp_dir.path(),
            &["init", "--bare", &remote.display().to_string()],
        );
        let local = temp_dir.path().join("local");
        run_git(
            temp_dir.path(),
            &[
                "clone",
                &remote.display().to_string(),
                &local.display().to_string(),
            ],
        );
        configure_git(&local);
        fs::write(local.join("README.md"), "one\n").unwrap();
        run_git(&local, &["add", "README.md"]);
        run_git(&local, &["commit", "-m", "one"]);
        run_git(&local, &["push", "-u", "origin", "HEAD"]);
        fs::create_dir_all(local.join(".harness/runs/run_1")).unwrap();
        fs::write(local.join(".harness/runs/run_1/RESULT.json"), "{}\n").unwrap();
        fs::write(local.join(".harness/symphony.yml"), "version: 1\n").unwrap();

        let refreshed = refresh_checkout_from_upstream(&config_for_root(&local)).unwrap();

        assert!(refreshed);
    }

    #[test]
    fn refresh_checkout_allows_generated_typescript_build_info() {
        let temp_dir = tempfile::tempdir().unwrap();
        let remote = temp_dir.path().join("remote.git");
        run_git(
            temp_dir.path(),
            &["init", "--bare", &remote.display().to_string()],
        );
        let local = temp_dir.path().join("local");
        run_git(
            temp_dir.path(),
            &[
                "clone",
                &remote.display().to_string(),
                &local.display().to_string(),
            ],
        );
        configure_git(&local);
        fs::write(local.join("README.md"), "one\n").unwrap();
        run_git(&local, &["add", "README.md"]);
        run_git(&local, &["commit", "-m", "one"]);
        run_git(&local, &["push", "-u", "origin", "HEAD"]);
        fs::create_dir_all(local.join("crates/harness-symphony/web-ui")).unwrap();
        fs::write(
            local.join("crates/harness-symphony/web-ui/tsconfig.tsbuildinfo"),
            "{}\n",
        )
        .unwrap();

        let refreshed = refresh_checkout_from_upstream(&config_for_root(&local)).unwrap();

        assert!(refreshed);
    }

    #[test]
    fn refresh_checkout_still_refuses_code_changes_with_local_symphony_artifacts() {
        let temp_dir = tempfile::tempdir().unwrap();
        let remote = temp_dir.path().join("remote.git");
        run_git(
            temp_dir.path(),
            &["init", "--bare", &remote.display().to_string()],
        );
        let local = temp_dir.path().join("local");
        run_git(
            temp_dir.path(),
            &[
                "clone",
                &remote.display().to_string(),
                &local.display().to_string(),
            ],
        );
        configure_git(&local);
        fs::write(local.join("README.md"), "one\n").unwrap();
        run_git(&local, &["add", "README.md"]);
        run_git(&local, &["commit", "-m", "one"]);
        run_git(&local, &["push", "-u", "origin", "HEAD"]);
        fs::create_dir_all(local.join(".harness/runs/run_1")).unwrap();
        fs::write(local.join(".harness/runs/run_1/RESULT.json"), "{}\n").unwrap();
        fs::write(local.join(".harness/symphony.yml"), "version: 1\n").unwrap();
        fs::write(local.join("local.txt"), "dirty\n").unwrap();

        let error = refresh_checkout_from_upstream(&config_for_root(&local)).unwrap_err();

        assert!(
            matches!(error, SyncError::DirtyCheckout(status) if status.contains("local.txt") && !status.contains(".harness/runs") && !status.contains(".harness/symphony.yml"))
        );
    }

    #[test]
    fn refresh_checkout_refuses_unapplied_harness_changesets() {
        let temp_dir = tempfile::tempdir().unwrap();
        let remote = temp_dir.path().join("remote.git");
        run_git(
            temp_dir.path(),
            &["init", "--bare", &remote.display().to_string()],
        );
        let local = temp_dir.path().join("local");
        run_git(
            temp_dir.path(),
            &[
                "clone",
                &remote.display().to_string(),
                &local.display().to_string(),
            ],
        );
        configure_git(&local);
        fs::write(local.join("README.md"), "one\n").unwrap();
        run_git(&local, &["add", "README.md"]);
        run_git(&local, &["commit", "-m", "one"]);
        run_git(&local, &["push", "-u", "origin", "HEAD"]);
        fs::create_dir_all(local.join(".harness/changesets")).unwrap();
        fs::write(
            local.join(".harness/changesets/run_1.changeset.jsonl"),
            "{}\n",
        )
        .unwrap();

        let error = refresh_checkout_from_upstream(&config_for_root(&local)).unwrap_err();

        assert!(
            matches!(error, SyncError::DirtyCheckout(status) if status.contains(".harness/changesets"))
        );
    }

    fn configure_git(repo: &Path) {
        run_git(repo, &["config", "user.email", "test@example.invalid"]);
        run_git(repo, &["config", "user.name", "Test User"]);
    }

    fn run_git(repo: &Path, args: &[&str]) {
        let output = Command::new("git")
            .args(args)
            .current_dir(repo)
            .output()
            .unwrap();
        assert!(
            output.status.success(),
            "git {:?} failed: {}",
            args,
            String::from_utf8_lossy(&output.stderr)
        );
    }

    #[cfg(unix)]
    fn make_executable(path: &Path) {
        use std::os::unix::fs::PermissionsExt;
        let mut permissions = fs::metadata(path).unwrap().permissions();
        permissions.set_mode(0o755);
        fs::set_permissions(path, permissions).unwrap();
    }

    #[cfg(not(unix))]
    fn make_executable(_path: &Path) {}

    fn config_for_root(root: &Path) -> ResolvedConfig {
        ResolvedConfig {
            version: 1,
            repo_root: root.to_path_buf(),
            harness_db: root.join("harness.db"),
            state_db: root.join(".symphony/state.db"),
            runs_dir: root.join(".harness/runs"),
            worktrees_dir: root.join(".symphony/worktrees"),
            single_active_run: true,
            agent_adapter: "custom".to_owned(),
            agent_command: vec![],
            agent_model: None,
            agent_timeout_minutes: 120,
            pull_request_create: "ask".to_owned(),
            pull_request_provider: "github".to_owned(),
            pull_request_draft_for: vec![],
            changeset_directory: root.join(".harness/changesets"),
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
}
