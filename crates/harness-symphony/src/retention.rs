use std::fs;
use std::path::PathBuf;

use thiserror::Error;

use crate::config::ResolvedConfig;

#[derive(Debug, Error)]
pub enum RetentionError {
    #[error("--keep-last must be at least 1")]
    UnsafeKeepLast,
    #[error("retention io error: {0}")]
    Io(#[from] std::io::Error),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CompactResult {
    pub kept: Vec<PathBuf>,
    pub removed: Vec<PathBuf>,
}

pub fn compact_runs(
    config: &ResolvedConfig,
    keep_last: u32,
) -> Result<CompactResult, RetentionError> {
    if keep_last == 0 {
        return Err(RetentionError::UnsafeKeepLast);
    }
    let mut runs = run_dirs(config)?;
    runs.sort_by(|left, right| right.0.cmp(&left.0).then_with(|| right.1.cmp(&left.1)));

    let keep = keep_last as usize;
    let mut kept = Vec::new();
    let mut removed = Vec::new();
    for (index, (_, path)) in runs.into_iter().enumerate() {
        if index < keep {
            kept.push(path);
        } else {
            fs::remove_dir_all(&path)?;
            removed.push(path);
        }
    }
    Ok(CompactResult { kept, removed })
}

fn run_dirs(
    config: &ResolvedConfig,
) -> Result<Vec<(std::time::SystemTime, PathBuf)>, RetentionError> {
    let mut runs = Vec::new();
    if !config.runs_dir.exists() {
        return Ok(runs);
    }
    for entry in fs::read_dir(&config.runs_dir)? {
        let entry = entry?;
        let path = entry.path();
        if path.is_dir() {
            let modified = entry
                .metadata()
                .and_then(|metadata| metadata.modified())
                .unwrap_or(std::time::SystemTime::UNIX_EPOCH);
            runs.push((modified, path));
        }
    }
    Ok(runs)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::ResolvedConfig;

    fn config(root: &std::path::Path) -> ResolvedConfig {
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

    #[test]
    fn compacts_run_dirs_without_touching_changesets() {
        let temp_dir = tempfile::tempdir().unwrap();
        let config = config(temp_dir.path());
        fs::create_dir_all(config.runs_dir.join("run_1")).unwrap();
        fs::create_dir_all(config.runs_dir.join("run_2")).unwrap();
        fs::create_dir_all(config.changeset_directory.clone()).unwrap();
        fs::write(
            config.changeset_directory.join("run_1.changeset.jsonl"),
            "{}",
        )
        .unwrap();

        let result = compact_runs(&config, 1).unwrap();

        assert_eq!(result.kept.len(), 1);
        assert_eq!(result.removed.len(), 1);
        assert!(config
            .changeset_directory
            .join("run_1.changeset.jsonl")
            .exists());
    }

    #[test]
    fn refuses_zero_keep_last() {
        let temp_dir = tempfile::tempdir().unwrap();
        let config = config(temp_dir.path());

        assert!(matches!(
            compact_runs(&config, 0).unwrap_err(),
            RetentionError::UnsafeKeepLast
        ));
    }
}
