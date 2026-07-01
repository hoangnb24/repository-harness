use std::fs;
use std::path::{Component, Path, PathBuf};

use serde::Deserialize;
use thiserror::Error;

pub const CONFIG_PATH: &str = ".harness/symphony.yml";

#[derive(Debug, Error)]
pub enum ConfigError {
    #[error("config read failed at {path}: {source}")]
    Read {
        path: String,
        source: std::io::Error,
    },
    #[error("config parse failed at {path}: {source}")]
    Parse {
        path: String,
        source: serde_yaml::Error,
    },
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ResolvedConfig {
    pub version: u32,
    pub repo_root: PathBuf,
    pub harness_db: PathBuf,
    pub state_db: PathBuf,
    pub runs_dir: PathBuf,
    pub worktrees_dir: PathBuf,
    pub single_active_run: bool,
    pub agent_adapter: String,
    pub agent_command: Vec<String>,
    pub agent_model: Option<String>,
    pub agent_timeout_minutes: u32,
    pub pull_request_create: String,
    pub pull_request_provider: String,
    pub pull_request_draft_for: Vec<String>,
    pub changeset_directory: PathBuf,
    pub changeset_render_in_summary: bool,
    pub allow_here_for_tiny: bool,
    pub compact_keep_last: u32,
    pub keep_failed_worktrees: bool,
    pub cleanup_after_sync: bool,
    pub auto_source: String,
    pub auto_poll_interval_seconds: u64,
    pub auto_max_attempts: u32,
}

#[derive(Debug, Clone, Deserialize, PartialEq, Eq)]
pub struct SymphonyConfig {
    #[serde(default = "default_version")]
    pub version: u32,
    #[serde(default)]
    pub repo: RepoConfig,
    #[serde(default)]
    pub symphony: SymphonyRuntimeConfig,
    #[serde(default)]
    pub agent: AgentConfig,
    #[serde(default)]
    pub pull_request: PullRequestConfig,
    #[serde(default)]
    pub changeset: ChangesetConfig,
    #[serde(default)]
    pub runs: RunsConfig,
    #[serde(default)]
    pub cleanup: CleanupConfig,
    #[serde(default)]
    pub auto: AutoConfig,
}

#[derive(Debug, Clone, Deserialize, PartialEq, Eq)]
pub struct RepoConfig {
    #[serde(default = "default_repo_root")]
    pub root: PathBuf,
    #[serde(default = "default_harness_db")]
    pub harness_db: PathBuf,
}

#[derive(Debug, Clone, Deserialize, PartialEq, Eq)]
pub struct SymphonyRuntimeConfig {
    #[serde(default = "default_state_db")]
    pub state_db: PathBuf,
    #[serde(default = "default_runs_dir")]
    pub runs_dir: PathBuf,
    #[serde(default = "default_worktrees_dir")]
    pub worktrees_dir: PathBuf,
    #[serde(default = "default_true")]
    pub single_active_run: bool,
}

#[derive(Debug, Clone, Deserialize, PartialEq, Eq)]
pub struct AgentConfig {
    #[serde(default = "default_agent_adapter")]
    pub adapter: String,
    #[serde(default)]
    pub command: Vec<String>,
    #[serde(default)]
    pub model: Option<String>,
    #[serde(default = "default_timeout_minutes")]
    pub timeout_minutes: u32,
}

#[derive(Debug, Clone, Deserialize, PartialEq, Eq)]
pub struct PullRequestConfig {
    #[serde(default = "default_pull_request_create")]
    pub create: String,
    #[serde(default = "default_pull_request_provider")]
    pub provider: String,
    #[serde(default = "default_draft_for")]
    pub draft_for: Vec<String>,
}

#[derive(Debug, Clone, Deserialize, PartialEq, Eq)]
pub struct ChangesetConfig {
    #[serde(default = "default_changeset_directory")]
    pub directory: PathBuf,
    #[serde(default = "default_true")]
    pub render_in_summary: bool,
}

#[derive(Debug, Clone, Deserialize, PartialEq, Eq)]
pub struct RunsConfig {
    #[serde(default = "default_true")]
    pub allow_here_for_tiny: bool,
    #[serde(default = "default_compact_keep_last")]
    pub compact_keep_last: u32,
}

#[derive(Debug, Clone, Deserialize, PartialEq, Eq)]
pub struct CleanupConfig {
    #[serde(default = "default_true")]
    pub keep_failed_worktrees: bool,
    #[serde(default)]
    pub cleanup_after_sync: bool,
}

#[derive(Debug, Clone, Deserialize, PartialEq, Eq)]
pub struct AutoConfig {
    #[serde(default = "default_auto_source")]
    pub source: String,
    #[serde(default = "default_auto_poll_interval_seconds")]
    pub poll_interval_seconds: u64,
    #[serde(default = "default_auto_max_attempts")]
    pub max_attempts: u32,
}

impl Default for SymphonyConfig {
    fn default() -> Self {
        Self {
            version: default_version(),
            repo: RepoConfig::default(),
            symphony: SymphonyRuntimeConfig::default(),
            agent: AgentConfig::default(),
            pull_request: PullRequestConfig::default(),
            changeset: ChangesetConfig::default(),
            runs: RunsConfig::default(),
            cleanup: CleanupConfig::default(),
            auto: AutoConfig::default(),
        }
    }
}

impl Default for RepoConfig {
    fn default() -> Self {
        Self {
            root: default_repo_root(),
            harness_db: default_harness_db(),
        }
    }
}

impl Default for SymphonyRuntimeConfig {
    fn default() -> Self {
        Self {
            state_db: default_state_db(),
            runs_dir: default_runs_dir(),
            worktrees_dir: default_worktrees_dir(),
            single_active_run: true,
        }
    }
}

impl Default for AgentConfig {
    fn default() -> Self {
        Self {
            adapter: default_agent_adapter(),
            command: Vec::new(),
            model: None,
            timeout_minutes: default_timeout_minutes(),
        }
    }
}

impl Default for PullRequestConfig {
    fn default() -> Self {
        Self {
            create: default_pull_request_create(),
            provider: default_pull_request_provider(),
            draft_for: default_draft_for(),
        }
    }
}

impl Default for ChangesetConfig {
    fn default() -> Self {
        Self {
            directory: default_changeset_directory(),
            render_in_summary: true,
        }
    }
}

impl Default for RunsConfig {
    fn default() -> Self {
        Self {
            allow_here_for_tiny: true,
            compact_keep_last: default_compact_keep_last(),
        }
    }
}

impl Default for CleanupConfig {
    fn default() -> Self {
        Self {
            keep_failed_worktrees: true,
            cleanup_after_sync: false,
        }
    }
}

impl Default for AutoConfig {
    fn default() -> Self {
        Self {
            source: default_auto_source(),
            poll_interval_seconds: default_auto_poll_interval_seconds(),
            max_attempts: default_auto_max_attempts(),
        }
    }
}

impl SymphonyConfig {
    pub fn load(repo_root: &Path) -> Result<Self, ConfigError> {
        let path = repo_root.join(CONFIG_PATH);
        if !path.exists() {
            return Ok(Self::default());
        }

        let text = fs::read_to_string(&path).map_err(|source| ConfigError::Read {
            path: path.display().to_string(),
            source,
        })?;
        serde_yaml::from_str(&text).map_err(|source| ConfigError::Parse {
            path: path.display().to_string(),
            source,
        })
    }

    pub fn resolve(&self, current_root: &Path) -> ResolvedConfig {
        let repo_root = normalize_path(current_root, &self.repo.root);
        ResolvedConfig {
            version: self.version,
            harness_db: normalize_path(&repo_root, &self.repo.harness_db),
            state_db: normalize_path(&repo_root, &self.symphony.state_db),
            runs_dir: normalize_path(&repo_root, &self.symphony.runs_dir),
            worktrees_dir: normalize_path(&repo_root, &self.symphony.worktrees_dir),
            single_active_run: self.symphony.single_active_run,
            agent_adapter: self.agent.adapter.clone(),
            agent_command: self.agent.command.clone(),
            agent_model: self.agent.model.clone(),
            agent_timeout_minutes: self.agent.timeout_minutes,
            pull_request_create: self.pull_request.create.clone(),
            pull_request_provider: self.pull_request.provider.clone(),
            pull_request_draft_for: self.pull_request.draft_for.clone(),
            changeset_directory: normalize_path(&repo_root, &self.changeset.directory),
            changeset_render_in_summary: self.changeset.render_in_summary,
            allow_here_for_tiny: self.runs.allow_here_for_tiny,
            compact_keep_last: self.runs.compact_keep_last,
            keep_failed_worktrees: self.cleanup.keep_failed_worktrees,
            cleanup_after_sync: self.cleanup.cleanup_after_sync,
            auto_source: self.auto.source.clone(),
            auto_poll_interval_seconds: self.auto.poll_interval_seconds,
            auto_max_attempts: self.auto.max_attempts,
            repo_root,
        }
    }
}

fn normalize_path(base: &Path, value: &Path) -> PathBuf {
    let path = if value.is_absolute() {
        value.to_path_buf()
    } else {
        base.join(value)
    };
    normalize_components(&path)
}

fn normalize_components(path: &Path) -> PathBuf {
    let mut normalized = PathBuf::new();
    for component in path.components() {
        match component {
            Component::CurDir => {}
            Component::ParentDir => {
                normalized.pop();
            }
            _ => normalized.push(component.as_os_str()),
        }
    }
    normalized
}

fn default_version() -> u32 {
    1
}

fn default_repo_root() -> PathBuf {
    PathBuf::from(".")
}

fn default_harness_db() -> PathBuf {
    PathBuf::from("harness.db")
}

fn default_state_db() -> PathBuf {
    PathBuf::from(".symphony/state.db")
}

fn default_runs_dir() -> PathBuf {
    PathBuf::from(".harness/runs")
}

fn default_worktrees_dir() -> PathBuf {
    PathBuf::from(".symphony/worktrees")
}

fn default_agent_adapter() -> String {
    "custom".to_owned()
}

fn default_timeout_minutes() -> u32 {
    10
}

fn default_pull_request_create() -> String {
    "ask".to_owned()
}

fn default_pull_request_provider() -> String {
    "github".to_owned()
}

fn default_draft_for() -> Vec<String> {
    vec![
        "blocked".to_owned(),
        "needs_intake".to_owned(),
        "partial".to_owned(),
    ]
}

fn default_changeset_directory() -> PathBuf {
    PathBuf::from(".harness/changesets")
}

fn default_compact_keep_last() -> u32 {
    50
}

fn default_true() -> bool {
    true
}

fn default_auto_source() -> String {
    "harness-db".to_owned()
}

fn default_auto_poll_interval_seconds() -> u64 {
    30
}

fn default_auto_max_attempts() -> u32 {
    3
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn defaults_match_scope_paths() {
        let config = SymphonyConfig::default();
        let resolved = config.resolve(Path::new("/repo"));

        assert_eq!(resolved.version, 1);
        assert_eq!(resolved.repo_root, PathBuf::from("/repo"));
        assert_eq!(resolved.harness_db, PathBuf::from("/repo/harness.db"));
        assert_eq!(resolved.state_db, PathBuf::from("/repo/.symphony/state.db"));
        assert_eq!(resolved.runs_dir, PathBuf::from("/repo/.harness/runs"));
        assert_eq!(
            resolved.worktrees_dir,
            PathBuf::from("/repo/.symphony/worktrees")
        );
        assert_eq!(
            resolved.changeset_directory,
            PathBuf::from("/repo/.harness/changesets")
        );
        assert!(resolved.single_active_run);
        assert_eq!(resolved.agent_adapter, "custom");
        assert_eq!(resolved.agent_timeout_minutes, 10);
        assert_eq!(resolved.pull_request_create, "ask");
        assert_eq!(resolved.pull_request_provider, "github");
        assert_eq!(resolved.pull_request_draft_for, default_draft_for());
        assert!(resolved.changeset_render_in_summary);
        assert!(resolved.allow_here_for_tiny);
        assert_eq!(resolved.compact_keep_last, 50);
        assert!(resolved.keep_failed_worktrees);
        assert!(!resolved.cleanup_after_sync);
        assert_eq!(resolved.auto_source, "harness-db");
        assert_eq!(resolved.auto_poll_interval_seconds, 30);
        assert_eq!(resolved.auto_max_attempts, 3);
    }

    #[test]
    fn parses_partial_yaml_and_normalizes_paths() {
        let config: SymphonyConfig = serde_yaml::from_str(
            r#"
version: 1
repo:
  root: "workspace"
  harness_db: "db/copy.db"
agent:
  command:
    - "codex"
    - "app-server"
runs:
  compact_keep_last: 10
cleanup:
  cleanup_after_sync: true
auto:
  poll_interval_seconds: 5
  max_attempts: 2
"#,
        )
        .unwrap();

        let resolved = config.resolve(Path::new("/repo"));
        assert_eq!(resolved.repo_root, PathBuf::from("/repo/workspace"));
        assert_eq!(
            resolved.harness_db,
            PathBuf::from("/repo/workspace/db/copy.db")
        );
        assert_eq!(resolved.agent_command, vec!["codex", "app-server"]);
        assert_eq!(resolved.compact_keep_last, 10);
        assert!(resolved.cleanup_after_sync);
        assert_eq!(resolved.auto_source, "harness-db");
        assert_eq!(resolved.auto_poll_interval_seconds, 5);
        assert_eq!(resolved.auto_max_attempts, 2);
        assert_eq!(
            resolved.worktrees_dir,
            PathBuf::from("/repo/workspace/.symphony/worktrees")
        );
    }

    #[test]
    fn resolve_propagates_agent_model() {
        let config: SymphonyConfig = serde_yaml::from_str(
            r#"
version: 1
agent:
  adapter: claudecode
  model: sonnet
"#,
        )
        .unwrap();

        let resolved = config.resolve(Path::new("/repo"));
        assert_eq!(resolved.agent_model.as_deref(), Some("sonnet"));

        let defaults = SymphonyConfig::default().resolve(Path::new("/repo"));
        assert_eq!(defaults.agent_model, None);
    }

    #[test]
    fn invalid_yaml_returns_actionable_parse_error() {
        let temp_dir = tempfile::tempdir().unwrap();
        let config_dir = temp_dir.path().join(".harness");
        fs::create_dir_all(&config_dir).unwrap();
        fs::write(config_dir.join("symphony.yml"), "version: [").unwrap();

        let error = SymphonyConfig::load(temp_dir.path()).unwrap_err();
        assert!(error.to_string().contains("config parse failed"));
        assert!(error.to_string().contains(".harness/symphony.yml"));
    }
}
