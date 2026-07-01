use std::thread;
use std::time::Duration;

use thiserror::Error;

use crate::config::ResolvedConfig;
use crate::run::{execute_run, RunError};
use crate::state::{RunStateStore, StateError};
use crate::work::{HarnessDbWorkSource, WorkError, WorkSource, EXTERNAL_WORK_SOURCE_BOUNDARIES};

#[derive(Debug, Error)]
pub enum AutoError {
    #[error("auto-mode is opt-in. Re-run with --enable to start unattended work polling.")]
    NotEnabled,
    #[error(
        "work source '{0}' is an adapter boundary for future integration; US-045 implements HarnessDbWorkSource first without changing run contracts"
    )]
    AdapterBoundary(String),
    #[error("unsupported work source '{0}'. Supported source: harness-db")]
    UnsupportedSource(String),
    #[error("{0}")]
    State(#[from] StateError),
    #[error("{0}")]
    Work(#[from] WorkError),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AutoRunOptions {
    pub enabled: bool,
    pub source: String,
    pub once: bool,
    pub max_runs: Option<u32>,
    pub max_attempts: u32,
    pub poll_interval_seconds: u64,
    pub max_idle_cycles: Option<u32>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AutoRunSummary {
    pub source: String,
    pub enqueued: u32,
    pub completed: u32,
    pub failed: u32,
    pub idle_cycles: u32,
    pub stopped_reason: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct StoryRunResult {
    run_id: String,
    outcome: String,
}

trait StoryRunner {
    fn run_story(&mut self, story_id: &str) -> Result<StoryRunResult, String>;
}

struct SymphonyStoryRunner<'a> {
    config: &'a ResolvedConfig,
}

impl StoryRunner for SymphonyStoryRunner<'_> {
    fn run_story(&mut self, story_id: &str) -> Result<StoryRunResult, String> {
        execute_run(self.config, story_id)
            .map(|completed| StoryRunResult {
                run_id: completed.prepared.run_id,
                outcome: completed.outcome,
            })
            .map_err(format_run_error)
    }
}

pub fn options_from_config(config: &ResolvedConfig) -> AutoRunOptions {
    AutoRunOptions {
        enabled: false,
        source: config.auto_source.clone(),
        once: false,
        max_runs: None,
        max_attempts: config.auto_max_attempts,
        poll_interval_seconds: config.auto_poll_interval_seconds,
        max_idle_cycles: None,
    }
}

pub fn run_auto_mode(
    config: &ResolvedConfig,
    options: AutoRunOptions,
) -> Result<AutoRunSummary, AutoError> {
    let mut runner = SymphonyStoryRunner { config };
    run_auto_mode_with_runner(config, options, &mut runner)
}

fn run_auto_mode_with_runner(
    config: &ResolvedConfig,
    options: AutoRunOptions,
    runner: &mut dyn StoryRunner,
) -> Result<AutoRunSummary, AutoError> {
    if !options.enabled {
        return Err(AutoError::NotEnabled);
    }
    validate_source(&options.source)?;

    let store = RunStateStore::new(config.state_db.clone());
    let source = HarnessDbWorkSource::new(&config.harness_db);
    let mut summary = AutoRunSummary {
        source: source.name().to_owned(),
        enqueued: 0,
        completed: 0,
        failed: 0,
        idle_cycles: 0,
        stopped_reason: String::new(),
    };

    loop {
        for candidate in source.poll()? {
            let queued =
                store.enqueue_work(&candidate.story_id, &candidate.source, options.max_attempts)?;
            if queued.status == "queued" && queued.attempts == 0 {
                summary.enqueued += 1;
            }
        }

        let Some(item) = store.next_queued_work()? else {
            summary.idle_cycles += 1;
            if options.once {
                summary.stopped_reason = "one poll completed with no queued work".to_owned();
                break;
            }
            if options
                .max_idle_cycles
                .is_some_and(|max_idle| summary.idle_cycles >= max_idle)
            {
                summary.stopped_reason = "max idle cycles reached".to_owned();
                break;
            }
            thread::sleep(Duration::from_secs(options.poll_interval_seconds));
            continue;
        };

        summary.idle_cycles = 0;
        store.mark_queue_running(&item.story_id)?;
        match runner.run_story(&item.story_id) {
            Ok(result) if result.outcome == "completed" => {
                store.mark_queue_completed(&item.story_id, &result.run_id)?;
                summary.completed += 1;
            }
            Ok(result) => {
                let queue = store.mark_queue_failed(
                    &item.story_id,
                    Some(&result.run_id),
                    &format!("run outcome was {}", result.outcome),
                )?;
                if queue.status == "failed" {
                    summary.failed += 1;
                }
            }
            Err(error) => {
                let queue = store.mark_queue_failed(&item.story_id, None, &error)?;
                if queue.status == "failed" {
                    summary.failed += 1;
                }
            }
        }

        if options.once {
            summary.stopped_reason = "one queued run processed".to_owned();
            break;
        }
        if options
            .max_runs
            .is_some_and(|max_runs| summary.completed + summary.failed >= max_runs)
        {
            summary.stopped_reason = "max runs reached".to_owned();
            break;
        }
    }

    Ok(summary)
}

fn validate_source(source: &str) -> Result<(), AutoError> {
    if source == "harness-db" {
        return Ok(());
    }
    if EXTERNAL_WORK_SOURCE_BOUNDARIES.contains(&source) {
        return Err(AutoError::AdapterBoundary(source.to_owned()));
    }
    Err(AutoError::UnsupportedSource(source.to_owned()))
}

fn format_run_error(error: RunError) -> String {
    error.to_string()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::ResolvedConfig;
    use rusqlite::{params, Connection};
    use std::path::Path;

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
            agent_command: vec!["fake-agent".to_owned()],
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
            auto_poll_interval_seconds: 0,
            auto_max_attempts: 2,
        }
    }

    fn write_story_db(path: &Path, id: &str) {
        let connection = Connection::open(path).unwrap();
        connection
            .execute_batch(
                "CREATE TABLE story (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    risk_lane TEXT NOT NULL,
                    verify_command TEXT
                );",
            )
            .unwrap();
        connection
            .execute(
                "INSERT INTO story (id, title, status, risk_lane, verify_command)
                 VALUES (?1, 'fixture', 'planned', 'normal', 'cargo test');",
                params![id],
            )
            .unwrap();
    }

    #[derive(Default)]
    struct FakeRunner {
        failures_before_success: u32,
        calls: u32,
    }

    impl StoryRunner for FakeRunner {
        fn run_story(&mut self, story_id: &str) -> Result<StoryRunResult, String> {
            self.calls += 1;
            if self.calls <= self.failures_before_success {
                return Err("fixture failure".to_owned());
            }
            Ok(StoryRunResult {
                run_id: format!("run_{story_id}_{}", self.calls),
                outcome: "completed".to_owned(),
            })
        }
    }

    #[test]
    fn auto_mode_requires_explicit_enable_flag() {
        let temp_dir = tempfile::tempdir().unwrap();
        let config = config_for_root(temp_dir.path());
        let mut runner = FakeRunner::default();
        let options = AutoRunOptions {
            enabled: false,
            source: "harness-db".to_owned(),
            once: true,
            max_runs: Some(1),
            max_attempts: 1,
            poll_interval_seconds: 0,
            max_idle_cycles: Some(1),
        };

        let error = run_auto_mode_with_runner(&config, options, &mut runner).unwrap_err();

        assert!(matches!(error, AutoError::NotEnabled));
    }

    #[test]
    fn external_sources_are_adapter_boundaries() {
        let error = validate_source("github-issues").unwrap_err();

        assert!(matches!(error, AutoError::AdapterBoundary(source) if source == "github-issues"));
    }

    #[test]
    fn harness_db_source_feeds_one_queued_run() {
        let temp_dir = tempfile::tempdir().unwrap();
        let config = config_for_root(temp_dir.path());
        write_story_db(&config.harness_db, "US-AUTO");
        let mut runner = FakeRunner::default();
        let options = AutoRunOptions {
            enabled: true,
            source: "harness-db".to_owned(),
            once: true,
            max_runs: Some(1),
            max_attempts: 2,
            poll_interval_seconds: 0,
            max_idle_cycles: Some(1),
        };

        let summary = run_auto_mode_with_runner(&config, options, &mut runner).unwrap();

        assert_eq!(summary.enqueued, 1);
        assert_eq!(summary.completed, 1);
        assert_eq!(summary.failed, 0);
        let queue = RunStateStore::new(config.state_db)
            .queue_record("US-AUTO")
            .unwrap();
        assert_eq!(queue.status, "completed");
        assert_eq!(queue.attempts, 1);
    }

    #[test]
    fn failed_run_is_retried_until_success() {
        let temp_dir = tempfile::tempdir().unwrap();
        let config = config_for_root(temp_dir.path());
        write_story_db(&config.harness_db, "US-RETRY");
        let mut runner = FakeRunner {
            failures_before_success: 1,
            calls: 0,
        };
        let options = AutoRunOptions {
            enabled: true,
            source: "harness-db".to_owned(),
            once: false,
            max_runs: Some(1),
            max_attempts: 2,
            poll_interval_seconds: 0,
            max_idle_cycles: Some(1),
        };

        let summary = run_auto_mode_with_runner(&config, options, &mut runner).unwrap();

        assert_eq!(summary.completed, 1);
        assert_eq!(runner.calls, 2);
        let queue = RunStateStore::new(config.state_db)
            .queue_record("US-RETRY")
            .unwrap();
        assert_eq!(queue.status, "completed");
        assert_eq!(queue.attempts, 2);
    }
}
