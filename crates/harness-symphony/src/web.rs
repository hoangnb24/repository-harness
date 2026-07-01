use std::fs;
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::{Path, PathBuf};

use serde::Serialize;
use serde_json::Value;
use thiserror::Error;

use crate::agent::{all_agent_readiness, AgentReadiness};
use crate::changeset::{render_changeset, render_markdown, ChangesetError};
use crate::config::ResolvedConfig;
use crate::pr::{create_pr, PrError};
use crate::run::{execute_prepared_run, prepare_run, PreparedRun, RunError};
use crate::state::{RunStateStore, StateError};
use crate::sync::{sync_changeset, SyncChange, SyncError};
use crate::work::{list_board, BoardItem, WorkError};

const WEB_DIST_DIR_ENV: &str = "HARNESS_SYMPHONY_WEB_DIST_DIR";

#[derive(Debug, Error)]
pub enum WebError {
    #[error("{0}")]
    Work(#[from] WorkError),
    #[error("{0}")]
    Run(#[from] RunError),
    #[error("{0}")]
    State(#[from] StateError),
    #[error("{0}")]
    Changeset(#[from] ChangesetError),
    #[error("{0}")]
    Pr(#[from] PrError),
    #[error("{0}")]
    Sync(#[from] SyncError),
    #[error("web server io error: {0}")]
    Io(#[from] std::io::Error),
    #[error("json error: {0}")]
    Json(#[from] serde_json::Error),
    #[error("requested web asset is outside the web UI dist directory")]
    InvalidAssetPath,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WebServerOptions {
    pub host: String,
    pub port: u16,
}

#[derive(Debug, Serialize)]
struct BoardResponse {
    items: Vec<BoardItemResponse>,
}

#[derive(Debug, Serialize)]
struct BoardItemResponse {
    id: String,
    title: String,
    board_state: String,
    story_status: String,
    lane: String,
    verify: String,
    blockers: Vec<String>,
    unblocks: Vec<String>,
    parent_id: Option<String>,
    children: Vec<String>,
    hierarchy_depth: usize,
    run_id: Option<String>,
    active_run: Option<String>,
    reason: String,
}

#[derive(Debug, Serialize)]
struct AgentsResponse {
    agents: Vec<AgentReadiness>,
}

#[derive(Debug, Serialize)]
struct ErrorResponse {
    error: String,
}

#[derive(Debug, Serialize)]
struct StartRunResponse {
    run_id: String,
    story_id: String,
    status: String,
}

#[derive(Debug, Serialize)]
struct EventsResponse {
    run_id: String,
    events: Vec<Value>,
}

#[derive(Debug, Serialize)]
struct ReviewResponse {
    run_id: String,
    story_id: String,
    status: String,
    outcome: Option<String>,
    summary: Option<String>,
    result: Option<Value>,
    validation: Option<Value>,
    changed_files: Vec<String>,
    changeset_preview: Option<String>,
    pr_url: Option<String>,
    pr_status: String,
    artifact_paths: Vec<String>,
    events: Vec<Value>,
    suggested_next_action: String,
}

#[derive(Debug, Serialize)]
struct SyncRunResponse {
    run_id: String,
    applied: bool,
    changes: Vec<SyncChangeResponse>,
}

#[derive(Debug, Serialize)]
struct PrMergedResponse {
    run_id: String,
    pr_status: String,
}

#[derive(Debug, Serialize)]
struct SyncChangeResponse {
    id: String,
    path: String,
    applied: bool,
    operations: usize,
}

pub fn run_web_server(config: &ResolvedConfig, options: WebServerOptions) -> Result<(), WebError> {
    let listener = TcpListener::bind(format!("{}:{}", options.host, options.port))?;
    let address = listener.local_addr()?;
    println!("Symphony Web UI Controller listening at http://{address}");
    for stream in listener.incoming() {
        let mut stream = stream?;
        let response = handle_stream(config, &mut stream)?;
        stream.write_all(response.as_bytes())?;
    }
    Ok(())
}

fn handle_stream(config: &ResolvedConfig, stream: &mut TcpStream) -> Result<String, WebError> {
    let mut buffer = [0_u8; 8192];
    let bytes = stream.read(&mut buffer)?;
    let request = String::from_utf8_lossy(&buffer[..bytes]);
    match handle_request(config, &request) {
        Ok(response) => Ok(response),
        Err(error) => json_response(
            500,
            &ErrorResponse {
                error: error.to_string(),
            },
        ),
    }
}

fn handle_request(config: &ResolvedConfig, request: &str) -> Result<String, WebError> {
    let (method, path) = parse_request_line(request);
    match (method.as_deref(), path.as_deref()) {
        (Some("GET"), Some("/health")) => json_response(200, &serde_json::json!({"ok": true})),
        (Some("GET"), Some("/api/board")) => {
            let items = list_board(&config.harness_db, &config.state_db)?;
            json_response(
                200,
                &BoardResponse {
                    items: items.into_iter().map(BoardItemResponse::from).collect(),
                },
            )
        }
        (Some("GET"), Some("/api/agents")) => agents_response(config),
        (Some("POST"), Some(path)) if start_path_story_id(path).is_some() => {
            let story_id = start_path_story_id(path).unwrap_or_default();
            start_run_response(config, &story_id, start_adapter_override(path))
        }
        (Some("GET"), Some(path)) if events_path_run_id(path).is_some() => {
            let run_id = events_path_run_id(path).unwrap_or_default();
            events_response(config, &run_id)
        }
        (Some("GET"), Some(path)) if review_path_run_id(path).is_some() => {
            let run_id = review_path_run_id(path).unwrap_or_default();
            review_response(config, &run_id)
        }
        (Some("POST"), Some(path)) if sync_path_run_id(path).is_some() => {
            let run_id = sync_path_run_id(path).unwrap_or_default();
            sync_run_response(config, &run_id)
        }
        (Some("POST"), Some(path)) if pr_merged_path_run_id(path).is_some() => {
            let run_id = pr_merged_path_run_id(path).unwrap_or_default();
            pr_merged_response(config, &run_id)
        }
        (Some("GET"), Some(path)) => static_response(config, path),
        (Some(_), Some("/health" | "/api/board" | "/api/agents")) => json_response(
            405,
            &ErrorResponse {
                error: "method not allowed".to_owned(),
            },
        ),
        (Some(_), Some(path))
            if start_path_story_id(path).is_some()
                || events_path_run_id(path).is_some()
                || review_path_run_id(path).is_some()
                || sync_path_run_id(path).is_some()
                || pr_merged_path_run_id(path).is_some() =>
        {
            json_response(
                405,
                &ErrorResponse {
                    error: "method not allowed".to_owned(),
                },
            )
        }
        _ => json_response(
            404,
            &ErrorResponse {
                error: "not found".to_owned(),
            },
        ),
    }
}

fn agents_response(config: &ResolvedConfig) -> Result<String, WebError> {
    let body = AgentsResponse {
        agents: all_agent_readiness(config),
    };
    json_response(200, &body)
}

fn sync_run_response(config: &ResolvedConfig, run_id: &str) -> Result<String, WebError> {
    if !safe_identifier(run_id) {
        return json_response(
            400,
            &ErrorResponse {
                error: "invalid run id".to_owned(),
            },
        );
    }
    let run = match RunStateStore::new(config.state_db.clone()).show_run(run_id) {
        Ok(run) => run,
        Err(StateError::RunNotFound(_)) => {
            return json_response(
                404,
                &ErrorResponse {
                    error: "run not found".to_owned(),
                },
            );
        }
        Err(error) => return Err(error.into()),
    };
    if run.pr_status != "merged" {
        return json_response(
            409,
            &ErrorResponse {
                error: "pull request must be marked merged before sync".to_owned(),
            },
        );
    }
    let result = sync_changeset(config, run_id)?;
    let changes = result
        .changes
        .into_iter()
        .map(SyncChangeResponse::from)
        .collect::<Vec<_>>();
    let applied = changes
        .iter()
        .any(|change| change.id == run_id && change.applied);
    json_response(
        200,
        &SyncRunResponse {
            run_id: run_id.to_owned(),
            applied,
            changes,
        },
    )
}

fn pr_merged_response(config: &ResolvedConfig, run_id: &str) -> Result<String, WebError> {
    if !safe_identifier(run_id) {
        return json_response(
            400,
            &ErrorResponse {
                error: "invalid run id".to_owned(),
            },
        );
    }
    let store = RunStateStore::new(config.state_db.clone());
    match store.show_run(run_id) {
        Ok(run) if run.pr_url.is_some() => {
            store.update_pr_status(run_id, "merged")?;
            json_response(
                200,
                &PrMergedResponse {
                    run_id: run_id.to_owned(),
                    pr_status: "merged".to_owned(),
                },
            )
        }
        Ok(_) => json_response(
            409,
            &ErrorResponse {
                error: "pull request has not been created".to_owned(),
            },
        ),
        Err(StateError::RunNotFound(_)) => json_response(
            404,
            &ErrorResponse {
                error: "run not found".to_owned(),
            },
        ),
        Err(error) => Err(error.into()),
    }
}

fn start_run_response(
    config: &ResolvedConfig,
    story_id: &str,
    adapter: Option<String>,
) -> Result<String, WebError> {
    let run_config = match adapter {
        Some(adapter) => match config_with_adapter(config, &adapter) {
            Ok(cfg) => cfg,
            Err(error) => return json_response(400, &ErrorResponse { error }),
        },
        None => config.clone(),
    };
    if let Some(active) = RunStateStore::new(run_config.state_db.clone()).active_run()? {
        return json_response(
            409,
            &ErrorResponse {
                error: format!("active run already exists: {}", active.run_id),
            },
        );
    }
    match prepare_run(&run_config, story_id) {
        Ok(prepared) => {
            let response = StartRunResponse {
                run_id: prepared.run_id.clone(),
                story_id: prepared.story_id.clone(),
                status: "started".to_owned(),
            };
            spawn_run(run_config.clone(), prepared);
            json_response(202, &response)
        }
        Err(RunError::State(StateError::ActiveRunExists(run_id))) => json_response(
            409,
            &ErrorResponse {
                error: format!("active run already exists: {run_id}"),
            },
        ),
        Err(error) => json_response(
            400,
            &ErrorResponse {
                error: error.to_string(),
            },
        ),
    }
}

fn spawn_run(config: ResolvedConfig, prepared: PreparedRun) {
    std::thread::spawn(move || {
        let run_id = prepared.run_id.clone();
        match execute_prepared_run(&config, prepared) {
            Ok(completed) if completed.outcome == "completed" => {
                if let Err(error) = create_review_pr(&config, &run_id) {
                    eprintln!("web run {run_id} PR creation failed: {error}");
                }
            }
            Ok(_) => {}
            Err(error) => eprintln!("web run {run_id} failed: {error}"),
        }
    });
}

fn create_review_pr(config: &ResolvedConfig, run_id: &str) -> Result<(), WebError> {
    if let Err(error) = create_pr(config, run_id, false) {
        RunStateStore::new(config.state_db.clone()).update_status(
            run_id,
            "failed",
            &format!("pull request creation failed: {error}"),
        )?;
        return Err(error.into());
    }
    Ok(())
}

fn events_response(config: &ResolvedConfig, run_id: &str) -> Result<String, WebError> {
    if !safe_identifier(run_id) {
        return json_response(
            400,
            &ErrorResponse {
                error: "invalid run id".to_owned(),
            },
        );
    }
    let event_path = config.runs_dir.join(run_id).join("APP_SERVER_EVENTS.jsonl");
    let events = read_events(&event_path)?;
    json_response(
        200,
        &EventsResponse {
            run_id: run_id.to_owned(),
            events,
        },
    )
}

fn review_response(config: &ResolvedConfig, run_id: &str) -> Result<String, WebError> {
    if !safe_identifier(run_id) {
        return json_response(
            400,
            &ErrorResponse {
                error: "invalid run id".to_owned(),
            },
        );
    }

    let run = match RunStateStore::new(config.state_db.clone()).show_run(run_id) {
        Ok(run) => run,
        Err(StateError::RunNotFound(_)) => {
            return json_response(
                404,
                &ErrorResponse {
                    error: "run not found".to_owned(),
                },
            );
        }
        Err(error) => return Err(error.into()),
    };

    let run_dir = config.runs_dir.join(run_id);
    let summary_path = run_dir.join("SUMMARY.md");
    let result_path = run_dir.join("RESULT.json");
    let review_changeset_path = run_dir.join("changeset.jsonl");
    let committed_changeset_path = config
        .changeset_directory
        .join(format!("{run_id}.changeset.jsonl"));
    let changeset_path = if review_changeset_path.exists() {
        review_changeset_path
    } else {
        committed_changeset_path
    };
    let event_path = run_dir.join("APP_SERVER_EVENTS.jsonl");

    let summary = read_optional_text(&summary_path)?;
    let result = read_optional_json(&result_path)?;
    let validation = result
        .as_ref()
        .and_then(|value| value.get("validation").cloned());
    let outcome = result
        .as_ref()
        .and_then(|value| value.get("outcome"))
        .and_then(Value::as_str)
        .map(str::to_owned);
    let changed_files = result
        .as_ref()
        .and_then(|value| value.get("changed_files"))
        .and_then(Value::as_array)
        .map(|values| {
            values
                .iter()
                .filter_map(Value::as_str)
                .map(str::to_owned)
                .collect::<Vec<_>>()
        })
        .unwrap_or_default();
    let changeset_preview = if changeset_path.exists() {
        let rendered = render_changeset(&changeset_path)?;
        Some(render_markdown(
            &rendered,
            &changeset_display_path(&config.repo_root, &changeset_path),
        ))
    } else {
        None
    };
    let artifact_paths = [&summary_path, &result_path, &changeset_path, &event_path]
        .into_iter()
        .filter(|path| path.exists())
        .map(|path| path.display().to_string())
        .collect::<Vec<_>>();
    let pr_status = run.pr_status.clone();
    let suggested_next_action = review_next_action(&run, summary.is_some(), result.is_some());

    json_response(
        200,
        &ReviewResponse {
            run_id: run.run_id,
            story_id: run.story_id,
            status: run.status,
            outcome,
            summary,
            result,
            validation,
            changed_files,
            changeset_preview,
            pr_url: run.pr_url,
            pr_status,
            artifact_paths,
            events: read_events(&event_path)?,
            suggested_next_action,
        },
    )
}

fn changeset_display_path(repo_root: &Path, path: &Path) -> String {
    path.strip_prefix(repo_root)
        .unwrap_or(path)
        .display()
        .to_string()
}

fn read_optional_text(path: &Path) -> Result<Option<String>, WebError> {
    if path.exists() {
        Ok(Some(fs::read_to_string(path)?))
    } else {
        Ok(None)
    }
}

fn read_optional_json(path: &Path) -> Result<Option<Value>, WebError> {
    if path.exists() {
        Ok(Some(serde_json::from_str(&fs::read_to_string(path)?)?))
    } else {
        Ok(None)
    }
}

fn read_events(path: &Path) -> Result<Vec<Value>, WebError> {
    if !path.exists() {
        return Ok(Vec::new());
    }
    let text = fs::read_to_string(path)?;
    Ok(text
        .lines()
        .filter_map(|line| serde_json::from_str::<Value>(line).ok())
        .collect::<Vec<_>>())
}

fn review_next_action(
    run: &crate::state::RunRecord,
    has_summary: bool,
    has_result: bool,
) -> String {
    if matches!(
        run.status.as_str(),
        "failed" | "cancelled" | "partial" | "blocked"
    ) || !has_summary
        || !has_result
    {
        "Inspect run artifacts and retry when safe.".to_owned()
    } else if run.pr_url.is_none() {
        "Create or retry the pull request for this run.".to_owned()
    } else {
        run.next_action.clone()
    }
}

fn parse_request_line(request: &str) -> (Option<String>, Option<String>) {
    let mut parts = request
        .lines()
        .next()
        .unwrap_or_default()
        .split_whitespace();
    (
        parts.next().map(str::to_owned),
        parts.next().map(str::to_owned),
    )
}

fn start_path_story_id(path: &str) -> Option<String> {
    let path = path.split('?').next().unwrap_or(path);
    let path = path.trim_end_matches('/');
    let story_id = path.strip_prefix("/api/tasks/")?.strip_suffix("/start")?;
    safe_identifier(story_id).then(|| story_id.to_owned())
}

/// Optional `?adapter=<name>` override on the start request, letting a single
/// run use a different agent than the globally configured one.
fn start_adapter_override(path: &str) -> Option<String> {
    let query = path.split('?').nth(1)?;
    query.split('&').find_map(|pair| {
        let (key, value) = pair.split_once('=')?;
        (key == "adapter" && !value.is_empty()).then(|| value.to_owned())
    })
}

/// Clone the resolved config with a per-run agent adapter override. Named
/// adapters resolve their own default command, so `agent_command` is only kept
/// for the `custom` adapter.
fn config_with_adapter(base: &ResolvedConfig, adapter: &str) -> Result<ResolvedConfig, String> {
    if !matches!(adapter, "custom" | "codex" | "claudecode") {
        return Err(format!(
            "unknown agent adapter '{adapter}'. Supported: custom, codex, claudecode"
        ));
    }
    let mut config = base.clone();
    config.agent_adapter = adapter.to_owned();
    if adapter != "custom" {
        config.agent_command = Vec::new();
    }
    Ok(config)
}

fn events_path_run_id(path: &str) -> Option<String> {
    let path = path.trim_end_matches('/');
    let run_id = path.strip_prefix("/api/runs/")?.strip_suffix("/events")?;
    safe_identifier(run_id).then(|| run_id.to_owned())
}

fn review_path_run_id(path: &str) -> Option<String> {
    let path = path.trim_end_matches('/');
    let run_id = path.strip_prefix("/api/runs/")?.strip_suffix("/review")?;
    safe_identifier(run_id).then(|| run_id.to_owned())
}

fn sync_path_run_id(path: &str) -> Option<String> {
    let path = path.trim_end_matches('/');
    let run_id = path.strip_prefix("/api/runs/")?.strip_suffix("/sync")?;
    safe_identifier(run_id).then(|| run_id.to_owned())
}

fn pr_merged_path_run_id(path: &str) -> Option<String> {
    let path = path.trim_end_matches('/');
    let run_id = path
        .strip_prefix("/api/runs/")?
        .strip_suffix("/pr-merged")?;
    safe_identifier(run_id).then(|| run_id.to_owned())
}

fn safe_identifier(value: &str) -> bool {
    !value.is_empty()
        && value
            .chars()
            .all(|character| character.is_ascii_alphanumeric() || matches!(character, '-' | '_'))
}

fn json_response<T: Serialize>(status: u16, body: &T) -> Result<String, WebError> {
    let status_text = match status {
        200 => "OK",
        202 => "Accepted",
        400 => "Bad Request",
        404 => "Not Found",
        405 => "Method Not Allowed",
        409 => "Conflict",
        503 => "Service Unavailable",
        _ => "Internal Server Error",
    };
    let body = serde_json::to_string(body)?;
    Ok(format!(
        "HTTP/1.1 {status} {status_text}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
        body.len()
    ))
}

fn static_response(config: &ResolvedConfig, request_path: &str) -> Result<String, WebError> {
    let dist_dir = web_dist_dir(config);
    if !dist_dir.exists() {
        if request_path != "/" {
            return json_response(
                404,
                &ErrorResponse {
                    error: "not found".to_owned(),
                },
            );
        }
        return json_response(
            503,
            &ErrorResponse {
                error: "web UI assets are not built; run npm --prefix crates/harness-symphony/web-ui run build".to_owned(),
            },
        );
    }

    let asset_path = resolve_asset_path(&dist_dir, request_path)?;
    if !asset_path.exists() || !asset_path.is_file() {
        return json_response(
            404,
            &ErrorResponse {
                error: "not found".to_owned(),
            },
        );
    }

    let body = fs::read(&asset_path)?;
    let content_type = content_type(&asset_path);
    Ok(format!(
        "HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
        body.len(),
        String::from_utf8_lossy(&body)
    ))
}

fn web_dist_dir(config: &ResolvedConfig) -> PathBuf {
    web_dist_dir_with_override(config, std::env::var_os(WEB_DIST_DIR_ENV))
}

fn web_dist_dir_with_override(
    config: &ResolvedConfig,
    override_path: Option<std::ffi::OsString>,
) -> PathBuf {
    if let Some(path) = override_path {
        if !path.is_empty() {
            return PathBuf::from(path);
        }
    }
    config
        .repo_root
        .join("crates")
        .join("harness-symphony")
        .join("web-ui")
        .join("dist")
}

fn resolve_asset_path(dist_dir: &Path, request_path: &str) -> Result<PathBuf, WebError> {
    let path = request_path.split('?').next().unwrap_or(request_path);
    let relative = if path == "/" {
        PathBuf::from("index.html")
    } else {
        let trimmed = path.trim_start_matches('/');
        if trimmed.split('/').any(|segment| segment == "..") {
            return Err(WebError::InvalidAssetPath);
        }
        PathBuf::from(trimmed)
    };
    Ok(dist_dir.join(relative))
}

fn content_type(path: &Path) -> &'static str {
    match path.extension().and_then(|value| value.to_str()) {
        Some("css") => "text/css; charset=utf-8",
        Some("js") => "application/javascript; charset=utf-8",
        Some("svg") => "image/svg+xml",
        Some("json") => "application/json; charset=utf-8",
        Some("html") | None => "text/html; charset=utf-8",
        _ => "application/octet-stream",
    }
}

impl From<BoardItem> for BoardItemResponse {
    fn from(item: BoardItem) -> Self {
        Self {
            id: item.id,
            title: item.title,
            board_state: item.board_state.label().to_owned(),
            story_status: item.story_status,
            lane: item.lane,
            verify: item.verify,
            blockers: item.blockers,
            unblocks: item.unblocks,
            parent_id: item.parent_id,
            children: item.children,
            hierarchy_depth: item.hierarchy_depth,
            run_id: item.run_id,
            active_run: item.active_run,
            reason: item.reason,
        }
    }
}

impl From<SyncChange> for SyncChangeResponse {
    fn from(change: SyncChange) -> Self {
        Self {
            id: change.id,
            path: change.path.display().to_string(),
            applied: change.applied,
            operations: change.operations,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::SymphonyConfig;
    use rusqlite::{params, Connection};
    use std::fs;
    use std::process::Command;

    fn test_config(temp_dir: &tempfile::TempDir) -> ResolvedConfig {
        SymphonyConfig::default().resolve(temp_dir.path())
    }

    fn seed_story(db_path: &std::path::Path) {
        let connection = Connection::open(db_path).unwrap();
        connection
            .execute_batch(
                "CREATE TABLE story (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    risk_lane TEXT NOT NULL,
                    verify_command TEXT
                );",
            )
            .unwrap();
        connection
            .execute(
                "INSERT INTO story (id, title, status, risk_lane, verify_command)
                 VALUES (?1, ?2, 'planned', 'normal', 'cargo test');",
                params!["US-WEB", "Web backend"],
            )
            .unwrap();
    }

    fn seed_runnable_story(db_path: &std::path::Path, story_id: &str) {
        let connection = Connection::open(db_path).unwrap();
        connection
            .execute_batch(
                "CREATE TABLE story (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    risk_lane TEXT NOT NULL,
                    verify_command TEXT
                );",
            )
            .unwrap();
        connection
            .execute(
                "INSERT INTO story (id, title, status, risk_lane, verify_command)
                 VALUES (?1, ?2, 'planned', 'normal', 'cargo test');",
                params![story_id, "Runnable"],
            )
            .unwrap();
    }

    fn init_git_repo(path: &std::path::Path) {
        for args in [
            vec!["init"],
            vec!["config", "user.email", "test@example.invalid"],
            vec!["config", "user.name", "Test User"],
        ] {
            let output = Command::new("git")
                .args(args)
                .current_dir(path)
                .output()
                .unwrap();
            assert!(output.status.success());
        }
        fs::write(path.join("README.md"), "test\n").unwrap();
        let add = Command::new("git")
            .args(["add", "README.md"])
            .current_dir(path)
            .output()
            .unwrap();
        assert!(add.status.success());
        let commit = Command::new("git")
            .args(["commit", "-m", "init"])
            .current_dir(path)
            .output()
            .unwrap();
        assert!(commit.status.success());
    }

    #[cfg(unix)]
    fn make_executable(path: &std::path::Path) {
        use std::os::unix::fs::PermissionsExt;
        let mut permissions = fs::metadata(path).unwrap().permissions();
        permissions.set_mode(0o755);
        fs::set_permissions(path, permissions).unwrap();
    }

    #[cfg(not(unix))]
    fn make_executable(_path: &std::path::Path) {}

    #[test]
    fn health_request_returns_ok_json() {
        let temp_dir = tempfile::tempdir().unwrap();
        let config = test_config(&temp_dir);

        let response = handle_request(&config, "GET /health HTTP/1.1\r\n\r\n").unwrap();

        assert!(response.starts_with("HTTP/1.1 200 OK"));
        assert!(response.ends_with(r#"{"ok":true}"#));
    }

    #[test]
    fn board_request_returns_board_items_json() {
        let temp_dir = tempfile::tempdir().unwrap();
        let config = test_config(&temp_dir);
        seed_story(&config.harness_db);

        let response = handle_request(&config, "GET /api/board HTTP/1.1\r\n\r\n").unwrap();

        assert!(response.starts_with("HTTP/1.1 200 OK"));
        assert!(response.contains(r#""id":"US-WEB""#));
        assert!(response.contains(r#""board_state":"Ready""#));
    }

    #[test]
    fn agents_request_returns_agent_readiness_json() {
        let temp_dir = tempfile::tempdir().unwrap();
        let config = test_config(&temp_dir);

        let response = handle_request(&config, "GET /api/agents HTTP/1.1\r\n\r\n").unwrap();

        assert!(response.starts_with("HTTP/1.1 200 OK"));
        assert!(response.contains(r#""agents":["#));
        assert!(response.contains(r#""adapter":"claudecode""#));
        assert!(response.contains(r#""adapter":"codex""#));
        assert!(response.contains(r#""adapter":"custom""#));
    }

    #[test]
    fn unsupported_path_returns_json_404() {
        let temp_dir = tempfile::tempdir().unwrap();
        let config = test_config(&temp_dir);

        let response = handle_request(&config, "GET /nope HTTP/1.1\r\n\r\n").unwrap();

        assert!(response.starts_with("HTTP/1.1 404 Not Found"));
        assert!(response.contains(r#""error":"not found""#));
    }

    #[test]
    fn run_start_path_extracts_story_id() {
        assert_eq!(
            start_path_story_id("/api/tasks/US-050/start"),
            Some("US-050".to_owned())
        );
        assert_eq!(start_path_story_id("/api/tasks/../start"), None);
        // A query string must not break story-id extraction.
        assert_eq!(
            start_path_story_id("/api/tasks/US-050/start?adapter=codex"),
            Some("US-050".to_owned())
        );
    }

    #[test]
    fn start_adapter_override_reads_query() {
        assert_eq!(
            start_adapter_override("/api/tasks/US-050/start?adapter=codex"),
            Some("codex".to_owned())
        );
        assert_eq!(start_adapter_override("/api/tasks/US-050/start"), None);
        assert_eq!(
            start_adapter_override("/api/tasks/US-050/start?adapter="),
            None
        );
    }

    #[test]
    fn config_with_adapter_overrides_named_adapter_and_clears_command() {
        let temp_dir = tempfile::tempdir().unwrap();
        let mut base = test_config(&temp_dir);
        base.agent_adapter = "custom".to_owned();
        base.agent_command = vec!["./run.sh".to_owned()];

        let claude = config_with_adapter(&base, "claudecode").unwrap();
        assert_eq!(claude.agent_adapter, "claudecode");
        assert!(claude.agent_command.is_empty());

        // custom keeps its configured command
        let custom = config_with_adapter(&base, "custom").unwrap();
        assert_eq!(custom.agent_command, vec!["./run.sh".to_owned()]);

        assert!(config_with_adapter(&base, "bogus").is_err());
    }

    #[test]
    fn events_request_returns_jsonl_events() {
        let temp_dir = tempfile::tempdir().unwrap();
        let config = test_config(&temp_dir);
        let run_dir = config.runs_dir.join("run_1");
        fs::create_dir_all(&run_dir).unwrap();
        fs::write(
            run_dir.join("APP_SERVER_EVENTS.jsonl"),
            "{\"method\":\"turn/started\"}\nnot json\n{\"method\":\"turn/completed\"}\n",
        )
        .unwrap();

        let response =
            handle_request(&config, "GET /api/runs/run_1/events HTTP/1.1\r\n\r\n").unwrap();

        assert!(response.starts_with("HTTP/1.1 200 OK"));
        assert!(response.contains(r#""run_id":"run_1""#));
        assert!(response.contains(r#""method":"turn/started""#));
        assert!(response.contains(r#""method":"turn/completed""#));
        assert!(!response.contains("not json"));
    }

    #[test]
    fn review_request_returns_run_artifacts_and_changeset_preview() {
        let temp_dir = tempfile::tempdir().unwrap();
        let config = test_config(&temp_dir);
        let store = RunStateStore::new(config.state_db.clone());
        store
            .add_run(crate::state::NewRunRecord {
                run_id: "run_review".to_owned(),
                story_id: "US-REVIEW".to_owned(),
                branch: Some("symphony/run_review".to_owned()),
                worktree: temp_dir.path().join("worktree"),
                lightweight: false,
                status: "completed".to_owned(),
                result_path: Some(PathBuf::from(".harness/runs/run_review/RESULT.json")),
                sync_status: "not_applied".to_owned(),
                next_action: "review pull request".to_owned(),
            })
            .unwrap();
        store
            .update_pr_url("run_review", "https://example.test/pr/1")
            .unwrap();
        let run_dir = config.runs_dir.join("run_review");
        fs::create_dir_all(&run_dir).unwrap();
        fs::write(run_dir.join("SUMMARY.md"), "# Summary\n\nDone.\n").unwrap();
        fs::write(
            run_dir.join("RESULT.json"),
            r#"{"version":1,"run_id":"run_review","story_id":"US-REVIEW","outcome":"completed","changed_files":["src/lib.rs"],"validation":{"commands":[{"command":"cargo test","result":"pass"}]}}"#,
        )
        .unwrap();
        fs::write(
            run_dir.join("changeset.jsonl"),
            r#"{"op":"changeset.header","version":1,"run_id":"run_review"}
{"op":"story.update","version":1,"id":"US-REVIEW","payload":{"status":"implemented"}}"#,
        )
        .unwrap();
        fs::write(
            run_dir.join("APP_SERVER_EVENTS.jsonl"),
            "{\"method\":\"turn/completed\"}\n",
        )
        .unwrap();

        let response =
            handle_request(&config, "GET /api/runs/run_review/review HTTP/1.1\r\n\r\n").unwrap();

        assert!(response.starts_with("HTTP/1.1 200 OK"));
        assert!(response.contains(r#""story_id":"US-REVIEW""#));
        assert!(response.contains(r#""outcome":"completed""#));
        assert!(response.contains("Harness Changes"));
        assert!(response.contains("https://example.test/pr/1"));
        assert!(response.contains("src/lib.rs"));
        assert!(response.contains("turn/completed"));
    }

    #[test]
    fn sync_request_returns_not_found_for_unknown_run() {
        let temp_dir = tempfile::tempdir().unwrap();
        let config = test_config(&temp_dir);

        let response =
            handle_request(&config, "POST /api/runs/run_missing/sync HTTP/1.1\r\n\r\n").unwrap();

        assert!(response.starts_with("HTTP/1.1 404 Not Found"));
        assert!(response.contains("run not found"));
    }

    #[test]
    fn pr_merged_endpoint_marks_review_run_merged() {
        let temp_dir = tempfile::tempdir().unwrap();
        let config = test_config(&temp_dir);
        let store = RunStateStore::new(config.state_db.clone());
        store
            .add_run(crate::state::NewRunRecord {
                run_id: "run_merge".to_owned(),
                story_id: "US-MERGE".to_owned(),
                branch: Some("symphony/run_merge".to_owned()),
                worktree: temp_dir.path().join("worktree"),
                lightweight: false,
                status: "completed".to_owned(),
                result_path: Some(PathBuf::from(".harness/runs/run_merge/RESULT.json")),
                sync_status: "not_applied".to_owned(),
                next_action: "review pull request".to_owned(),
            })
            .unwrap();
        store
            .update_pr_url("run_merge", "https://example.test/pr/1")
            .unwrap();

        let response = handle_request(
            &config,
            "POST /api/runs/run_merge/pr-merged HTTP/1.1\r\n\r\n",
        )
        .unwrap();

        assert!(response.starts_with("HTTP/1.1 200 OK"));
        assert!(response.contains(r#""pr_status":"merged""#));
        assert_eq!(store.show_run("run_merge").unwrap().pr_status, "merged");
    }

    #[test]
    fn create_review_pr_failure_moves_run_to_attention_state() {
        let temp_dir = tempfile::tempdir().unwrap();
        let mut config = test_config(&temp_dir);
        config.pull_request_create = "disabled".to_owned();
        let store = RunStateStore::new(config.state_db.clone());
        store
            .add_run(crate::state::NewRunRecord {
                run_id: "run_pr_fail".to_owned(),
                story_id: "US-PR".to_owned(),
                branch: Some("symphony/run_pr_fail".to_owned()),
                worktree: temp_dir.path().join("worktree"),
                lightweight: false,
                status: "completed".to_owned(),
                result_path: Some(PathBuf::from(".harness/runs/run_pr_fail/RESULT.json")),
                sync_status: "not_applied".to_owned(),
                next_action: "review run result".to_owned(),
            })
            .unwrap();

        let error = create_review_pr(&config, "run_pr_fail").unwrap_err();

        assert!(matches!(error, WebError::Pr(PrError::Disabled)));
        let run = store.show_run("run_pr_fail").unwrap();
        assert_eq!(run.status, "failed");
        assert!(run.next_action.contains("pull request creation failed"));
    }

    #[test]
    fn sync_request_requires_merged_pr() {
        let temp_dir = tempfile::tempdir().unwrap();
        let config = test_config(&temp_dir);
        let store = RunStateStore::new(config.state_db.clone());
        store
            .add_run(crate::state::NewRunRecord {
                run_id: "run_sync".to_owned(),
                story_id: "US-SYNC".to_owned(),
                branch: Some("symphony/run_sync".to_owned()),
                worktree: temp_dir.path().join("worktree"),
                lightweight: false,
                status: "completed".to_owned(),
                result_path: Some(PathBuf::from(".harness/runs/run_sync/RESULT.json")),
                sync_status: "not_applied".to_owned(),
                next_action: "review pull request".to_owned(),
            })
            .unwrap();
        store
            .update_pr_url("run_sync", "https://example.test/pr/1")
            .unwrap();

        let response =
            handle_request(&config, "POST /api/runs/run_sync/sync HTTP/1.1\r\n\r\n").unwrap();

        assert!(response.starts_with("HTTP/1.1 409 Conflict"));
        assert!(response.contains("pull request must be marked merged"));
    }

    #[test]
    fn sync_request_applies_only_requested_run_changeset() {
        let temp_dir = tempfile::tempdir().unwrap();
        let config = test_config(&temp_dir);
        fs::create_dir_all(&config.changeset_directory).unwrap();
        fs::create_dir_all(temp_dir.path().join("scripts/bin")).unwrap();
        fs::write(
            config.changeset_directory.join("run_sync.changeset.jsonl"),
            r#"{"op":"changeset.header","version":1,"run_id":"run_sync"}
{"op":"story.update","version":1,"id":"US-SYNC","payload":{"status":"implemented"}}
"#,
        )
        .unwrap();
        fs::write(
            config.changeset_directory.join("run_other.changeset.jsonl"),
            r#"{"op":"changeset.header","version":1,"run_id":"run_other"}
{"op":"story.update","version":1,"id":"US-OTHER","payload":{"status":"implemented"}}
"#,
        )
        .unwrap();
        let cli_path = temp_dir.path().join("scripts/bin/harness-cli");
        fs::write(
            &cli_path,
            "#!/bin/sh\nprintf '%s\\n' \"$@\" >> sync-args.log\necho 'Changeset run_sync applied (2 operation(s)).'\n",
        )
        .unwrap();
        make_executable(&cli_path);

        let store = RunStateStore::new(config.state_db.clone());
        store
            .add_run(crate::state::NewRunRecord {
                run_id: "run_sync".to_owned(),
                story_id: "US-SYNC".to_owned(),
                branch: Some("symphony/run_sync".to_owned()),
                worktree: temp_dir.path().join("worktree"),
                lightweight: false,
                status: "completed".to_owned(),
                result_path: Some(PathBuf::from(".harness/runs/run_sync/RESULT.json")),
                sync_status: "not_applied".to_owned(),
                next_action: "review pull request".to_owned(),
            })
            .unwrap();
        store
            .update_pr_url("run_sync", "https://example.test/pr/1")
            .unwrap();
        store.update_pr_status("run_sync", "merged").unwrap();

        let response =
            handle_request(&config, "POST /api/runs/run_sync/sync HTTP/1.1\r\n\r\n").unwrap();

        assert!(response.starts_with("HTTP/1.1 200 OK"));
        assert!(response.contains(r#""id":"run_sync""#));
        assert!(!response.contains("run_other"));
        let args = fs::read_to_string(temp_dir.path().join("sync-args.log")).unwrap();
        assert!(args.contains(".harness/changesets/run_sync.changeset.jsonl"));
        assert!(!args.contains("run_other.changeset.jsonl"));
    }

    #[test]
    fn start_request_refuses_when_active_run_exists() {
        let temp_dir = tempfile::tempdir().unwrap();
        let config = test_config(&temp_dir);
        seed_runnable_story(&config.harness_db, "US-START");
        crate::state::RunStateStore::new(config.state_db.clone())
            .add_run(crate::state::NewRunRecord {
                run_id: "run_active".to_owned(),
                story_id: "US-OTHER".to_owned(),
                branch: Some("symphony/run_active".to_owned()),
                worktree: temp_dir.path().join("worktree"),
                lightweight: false,
                status: "running".to_owned(),
                result_path: None,
                sync_status: "not_applied".to_owned(),
                next_action: "wait".to_owned(),
            })
            .unwrap();

        let response =
            handle_request(&config, "POST /api/tasks/US-START/start HTTP/1.1\r\n\r\n").unwrap();

        assert!(response.starts_with("HTTP/1.1 409 Conflict"));
        assert!(response.contains("active run already exists"));
    }

    #[test]
    fn start_request_prepares_run_and_returns_active_record() {
        let temp_dir = tempfile::tempdir().unwrap();
        init_git_repo(temp_dir.path());
        let mut config = test_config(&temp_dir);
        config.agent_adapter = "custom".to_owned();
        config.agent_command = vec!["sh".to_owned(), "-c".to_owned(), "sleep 1".to_owned()];
        seed_runnable_story(&config.harness_db, "US-START");

        let response =
            handle_request(&config, "POST /api/tasks/US-START/start HTTP/1.1\r\n\r\n").unwrap();

        assert!(response.starts_with("HTTP/1.1 202 Accepted"));
        assert!(response.contains(r#""story_id":"US-START""#));
        let active = RunStateStore::new(config.state_db.clone())
            .active_run()
            .unwrap()
            .unwrap();
        assert_eq!(active.story_id, "US-START");
    }

    #[test]
    fn root_serves_built_web_ui_index() {
        let temp_dir = tempfile::tempdir().unwrap();
        let config = test_config(&temp_dir);
        let dist = web_dist_dir(&config);
        fs::create_dir_all(&dist).unwrap();
        fs::write(dist.join("index.html"), "<div id=\"root\"></div>").unwrap();

        let response = handle_request(&config, "GET / HTTP/1.1\r\n\r\n").unwrap();

        assert!(response.starts_with("HTTP/1.1 200 OK"));
        assert!(response.contains("text/html"));
        assert!(response.ends_with("<div id=\"root\"></div>"));
    }

    #[test]
    fn web_dist_dir_supports_packaged_desktop_override() {
        let temp_dir = tempfile::tempdir().unwrap();
        let config = test_config(&temp_dir);
        let override_dir = temp_dir.path().join("packaged-web-ui-dist");

        let dist = web_dist_dir_with_override(&config, Some(override_dir.clone().into_os_string()));

        assert_eq!(dist, override_dir);
    }

    #[test]
    fn root_reports_missing_built_assets() {
        let temp_dir = tempfile::tempdir().unwrap();
        let config = test_config(&temp_dir);

        let response = handle_request(&config, "GET / HTTP/1.1\r\n\r\n").unwrap();

        assert!(response.starts_with("HTTP/1.1 503 Service Unavailable"));
        assert!(response.contains("web UI assets are not built"));
    }
}
