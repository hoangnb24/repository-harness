use std::fs::OpenOptions;
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::mpsc;
use std::time::{Duration, Instant};

use serde::Serialize;
use serde_json::{json, Value};
use thiserror::Error;

use crate::config::ResolvedConfig;
use crate::run::PreparedRun;

#[cfg(not(test))]
const CODEX_IDLE_RECONCILE_SECONDS: u64 = 30;
#[cfg(test)]
const CODEX_IDLE_RECONCILE_SECONDS: u64 = 1;

#[derive(Debug, Error)]
pub enum AgentError {
    #[error("agent.command is not configured. Set agent.command in .harness/symphony.yml.")]
    MissingCommand,
    #[error("unsupported agent adapter '{0}'. Supported adapters: custom, codex, claudecode")]
    UnsupportedAdapter(String),
    #[error("agent command failed with status {status}: {stderr}")]
    CommandFailed { status: String, stderr: String },
    #[error("codex app-server failed: {0}")]
    Codex(String),
    #[error("claude code failed: {0}")]
    ClaudeCode(String),
    #[error("agent io error: {0}")]
    Io(#[from] std::io::Error),
    #[error("agent json error: {0}")]
    Json(#[from] serde_json::Error),
}

pub fn run_agent(config: &ResolvedConfig, prepared: &PreparedRun) -> Result<(), AgentError> {
    match config.agent_adapter.as_str() {
        "custom" => run_custom_agent(config, prepared),
        "codex" => run_codex_agent(config, prepared),
        "claudecode" => run_claude_code_agent(config, prepared),
        other => Err(AgentError::UnsupportedAdapter(other.to_owned())),
    }
}

pub fn resolved_agent_command(config: &ResolvedConfig) -> Vec<String> {
    if !config.agent_command.is_empty() {
        return config.agent_command.clone();
    }
    if config.agent_adapter == "codex" {
        return vec!["codex".to_owned(), "app-server".to_owned()];
    }
    if config.agent_adapter == "claudecode" {
        return vec![resolve_claude_binary()];
    }
    Vec::new()
}

pub fn agent_adapter_status(config: &ResolvedConfig) -> Result<String, AgentError> {
    match config.agent_adapter.as_str() {
        "custom" => {
            let command = resolved_agent_command(config);
            if command.is_empty() {
                Err(AgentError::MissingCommand)
            } else {
                Ok(format!("custom command: {}", command.join(" ")))
            }
        }
        "codex" => Ok(format!(
            "codex app-server command: {}",
            resolved_agent_command(config).join(" ")
        )),
        "claudecode" => Ok(format!(
            "claude command: {}",
            resolved_agent_command(config).join(" ")
        )),
        other => Err(AgentError::UnsupportedAdapter(other.to_owned())),
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "kebab-case")]
pub enum Readiness {
    Ready,
    NeedsSetup,
    NotInstalled,
    Unknown,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct AgentReadiness {
    pub adapter: String,
    pub active: bool,
    pub binary_present: bool,
    pub binary_detail: String,
    pub auth_ready: bool,
    pub auth_detail: String,
    pub overall: Readiness,
    pub next: Option<String>,
}

/// Pure decision layer: map probe results to an overall readiness and next hint.
fn resolve_readiness(
    adapter: &str,
    binary_present: bool,
    auth_ready: bool,
    command_configured: bool,
) -> (Readiness, Option<String>) {
    match adapter {
        "custom" => {
            if command_configured {
                (Readiness::Ready, None)
            } else {
                (
                    Readiness::NeedsSetup,
                    Some("Set agent.command in .harness/symphony.yml.".to_owned()),
                )
            }
        }
        "claudecode" => {
            if !binary_present {
                (
                    Readiness::NotInstalled,
                    Some("Install Claude Code: npm i -g @anthropic-ai/claude-code".to_owned()),
                )
            } else if !auth_ready {
                (
                    Readiness::NeedsSetup,
                    Some(
                        "Authenticate: run `claude` and log in, or set ANTHROPIC_API_KEY."
                            .to_owned(),
                    ),
                )
            } else {
                (Readiness::Ready, None)
            }
        }
        "codex" => {
            if !binary_present {
                (
                    Readiness::NotInstalled,
                    Some("Install Codex CLI.".to_owned()),
                )
            } else if !auth_ready {
                (Readiness::NeedsSetup, Some("Run: codex login".to_owned()))
            } else {
                (Readiness::Ready, None)
            }
        }
        _ => (
            Readiness::Unknown,
            Some("Set agent.adapter to custom, codex, or claudecode.".to_owned()),
        ),
    }
}

fn agent_binary_name(adapter: &str, config: &ResolvedConfig) -> Option<String> {
    match adapter {
        "claudecode" => Some(resolve_claude_binary()),
        "codex" => Some("codex".to_owned()),
        "custom" => config.agent_command.first().cloned(),
        _ => None,
    }
}

fn probe_binary(bin: &str) -> (bool, String) {
    // Bound the probe: a bad custom command or a `--version` that hangs on a TTY
    // prompt must not freeze doctor or the future /api/agents endpoint.
    let mut child = match Command::new(bin)
        .arg("--version")
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
    {
        Ok(child) => child,
        Err(error) => return (false, format!("{bin} is not runnable: {error}")),
    };
    let deadline = Instant::now() + Duration::from_secs(5);
    loop {
        match child.try_wait() {
            Ok(Some(status)) => {
                if !status.success() {
                    return (false, format!("{bin} --version returned a failure status"));
                }
                let mut stdout = String::new();
                if let Some(mut handle) = child.stdout.take() {
                    use std::io::Read;
                    let _ = handle.read_to_string(&mut stdout);
                }
                return (true, stdout.trim().to_owned());
            }
            Ok(None) => {
                if Instant::now() >= deadline {
                    let _ = child.kill();
                    let _ = child.wait();
                    return (false, format!("{bin} --version timed out"));
                }
                std::thread::sleep(Duration::from_millis(50));
            }
            Err(error) => return (false, format!("{bin} is not runnable: {error}")),
        }
    }
}

fn home_dir() -> Option<PathBuf> {
    std::env::var_os("HOME").map(PathBuf::from)
}

fn expand_tilde(path: &str, home: &Path) -> PathBuf {
    if path == "~" {
        return home.to_path_buf();
    }
    if let Some(rest) = path.strip_prefix("~/") {
        return home.join(rest);
    }
    PathBuf::from(path)
}

/// Resolve the Claude Code executable, honoring an explicit `CLAUDE_EXECUTABLE`
/// override before falling back to `claude` on `PATH`.
fn resolve_claude_binary() -> String {
    if let Some(value) = std::env::var_os("CLAUDE_EXECUTABLE") {
        let raw = value.to_string_lossy().to_string();
        if !raw.is_empty() {
            let candidate = match home_dir() {
                Some(home) => expand_tilde(&raw, &home),
                None => PathBuf::from(&raw),
            };
            if candidate.is_file() {
                return candidate.to_string_lossy().into_owned();
            }
        }
    }
    "claude".to_owned()
}

/// True when `~/.claude.json` records a completed Claude Code login. The OAuth
/// token itself lives outside this file (e.g. the OS keychain), so its presence
/// here is the reliable signal that the CLI is authenticated and usable.
fn config_indicates_login(value: &Value) -> bool {
    value
        .get("oauthAccount")
        .is_some_and(|account| !account.is_null())
        || value
            .get("userID")
            .and_then(Value::as_str)
            .is_some_and(|id| !id.is_empty())
}

fn claude_config_login() -> bool {
    let Some(home) = home_dir() else {
        return false;
    };
    let Ok(text) = std::fs::read_to_string(home.join(".claude.json")) else {
        return false;
    };
    serde_json::from_str::<Value>(&text)
        .map(|value| config_indicates_login(&value))
        .unwrap_or(false)
}

fn env_nonempty(key: &str) -> bool {
    std::env::var(key)
        .map(|value| !value.is_empty())
        .unwrap_or(false)
}

fn probe_auth(adapter: &str) -> (bool, String) {
    match adapter {
        "claudecode" => {
            if env_nonempty("ANTHROPIC_API_KEY") {
                return (true, "ANTHROPIC_API_KEY is set".to_owned());
            }
            if std::env::var_os("CLAUDE_CODE_USE_BEDROCK").is_some()
                || std::env::var_os("CLAUDE_CODE_USE_VERTEX").is_some()
            {
                return (true, "cloud provider auth is configured".to_owned());
            }
            if home_dir().is_some_and(|home| home.join(".claude/.credentials.json").exists()) {
                return (true, "~/.claude/.credentials.json exists".to_owned());
            }
            if claude_config_login() {
                return (
                    true,
                    "logged in via Claude Code (~/.claude.json)".to_owned(),
                );
            }
            (false, "no Claude Code credentials found".to_owned())
        }
        "codex" => {
            if env_nonempty("OPENAI_API_KEY") {
                return (true, "OPENAI_API_KEY is set".to_owned());
            }
            if home_dir().is_some_and(|home| home.join(".codex/auth.json").exists()) {
                return (true, "~/.codex/auth.json exists".to_owned());
            }
            (false, "no Codex credentials found".to_owned())
        }
        _ => (true, "auth not required".to_owned()),
    }
}

pub fn agent_readiness(config: &ResolvedConfig, adapter: &str) -> AgentReadiness {
    let (binary_present, binary_detail) = match agent_binary_name(adapter, config) {
        Some(bin) => probe_binary(&bin),
        None => (false, "no agent binary configured".to_owned()),
    };
    let (auth_ready, auth_detail) = probe_auth(adapter);
    let command_configured = !config.agent_command.is_empty();
    let (overall, next) =
        resolve_readiness(adapter, binary_present, auth_ready, command_configured);
    AgentReadiness {
        adapter: adapter.to_owned(),
        active: adapter == config.agent_adapter,
        binary_present,
        binary_detail,
        auth_ready,
        auth_detail,
        overall,
        next,
    }
}

pub fn all_agent_readiness(config: &ResolvedConfig) -> Vec<AgentReadiness> {
    ["claudecode", "codex", "custom"]
        .into_iter()
        .map(|adapter| agent_readiness(config, adapter))
        .collect()
}

fn run_custom_agent(config: &ResolvedConfig, prepared: &PreparedRun) -> Result<(), AgentError> {
    let command = resolved_agent_command(config);
    if command.is_empty() {
        return Err(AgentError::MissingCommand);
    }
    let output = base_command(&command, prepared).output()?;
    if output.status.success() {
        return Ok(());
    }
    Err(AgentError::CommandFailed {
        status: output.status.to_string(),
        stderr: String::from_utf8_lossy(&output.stderr).trim().to_owned(),
    })
}

fn run_codex_agent(config: &ResolvedConfig, prepared: &PreparedRun) -> Result<(), AgentError> {
    let command = resolved_agent_command(config);
    if command.is_empty() {
        return Err(AgentError::MissingCommand);
    }

    let mut child = base_command(&command, prepared)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()?;

    let mut stdin = child
        .stdin
        .take()
        .ok_or_else(|| AgentError::Codex("failed to open app-server stdin".to_owned()))?;
    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| AgentError::Codex("failed to open app-server stdout".to_owned()))?;
    let stderr = child
        .stderr
        .take()
        .ok_or_else(|| AgentError::Codex("failed to open app-server stderr".to_owned()))?;

    let (line_tx, line_rx) = mpsc::channel::<String>();
    std::thread::spawn(move || {
        let reader = BufReader::new(stdout);
        for line in reader.lines().map_while(Result::ok) {
            if line_tx.send(line).is_err() {
                break;
            }
        }
    });

    send(
        &mut stdin,
        json!({
            "method": "initialize",
            "id": 0,
            "params": {
                "clientInfo": {
                    "name": "harness_symphony",
                    "title": "Harness Symphony",
                    "version": env!("CARGO_PKG_VERSION")
                },
                "capabilities": {
                    "experimentalApi": true,
                    "requestAttestation": false
                }
            }
        }),
    )?;

    let deadline = Instant::now() + Duration::from_secs(config.agent_timeout_minutes as u64 * 60);
    let event_log_path = prepared
        .contract_path
        .parent()
        .unwrap_or(&prepared.worktree)
        .join("APP_SERVER_EVENTS.jsonl");
    let mut thread_id: Option<String> = None;
    let mut turn_id: Option<String> = None;
    let mut turn_started = false;
    let mut last_event_at = Instant::now();
    let mut last_observed_method = "none".to_owned();
    let mut event_count: u64 = 0;
    let mut next_request_id: i64 = 3;
    let mut pending_state_query: Option<i64> = None;
    loop {
        if Instant::now() >= deadline {
            terminate_child(&mut child);
            return Err(AgentError::Codex(format!(
                "timed out after {} minute(s). Last app-server method: {last_observed_method}; events: {event_count}; see {}",
                config.agent_timeout_minutes,
                event_log_path.display()
            )));
        }

        let line = match line_rx.recv_timeout(Duration::from_millis(250)) {
            Ok(line) => line,
            Err(mpsc::RecvTimeoutError::Timeout) => {
                if let Some(status) = child.try_wait()? {
                    let stderr = read_child_stderr(stderr)?;
                    return Err(AgentError::CommandFailed {
                        status: status.to_string(),
                        stderr,
                    });
                }
                if pending_state_query.is_some()
                    && last_event_at.elapsed() >= Duration::from_secs(CODEX_IDLE_RECONCILE_SECONDS)
                {
                    terminate_child(&mut child);
                    return Err(AgentError::Codex(format!(
                        "no app-server events or turn-state response for {} second(s) after reconciliation request. Last app-server method: {last_observed_method}; events: {event_count}; see {}",
                        CODEX_IDLE_RECONCILE_SECONDS,
                        event_log_path.display()
                    )));
                }
                if let (Some(thread_id), Some(_turn_id)) = (&thread_id, &turn_id) {
                    if pending_state_query.is_none()
                        && turn_started
                        && last_event_at.elapsed()
                            >= Duration::from_secs(CODEX_IDLE_RECONCILE_SECONDS)
                    {
                        let request_id = next_request_id;
                        next_request_id += 1;
                        send_turn_state_query(&mut stdin, request_id, thread_id)?;
                        pending_state_query = Some(request_id);
                        last_event_at = Instant::now();
                    }
                }
                continue;
            }
            Err(mpsc::RecvTimeoutError::Disconnected) => {
                let status = child.wait()?;
                let stderr = read_child_stderr(stderr)?;
                return Err(AgentError::CommandFailed {
                    status: status.to_string(),
                    stderr,
                });
            }
        };

        append_event_log(&event_log_path, &line)?;
        let message: Value = serde_json::from_str(&line)?;
        event_count += 1;
        last_event_at = Instant::now();
        if let Some(method) = message.get("method").and_then(Value::as_str) {
            last_observed_method = method.to_owned();
        } else if let Some(id) = message.get("id").and_then(Value::as_i64) {
            last_observed_method = format!("response:{id}");
        }
        if let Some(error) = message.get("error") {
            if pending_state_query == message.get("id").and_then(Value::as_i64) {
                terminate_child(&mut child);
                return Err(AgentError::Codex(format!(
                    "turn-state query failed: {error}. Last app-server method: {last_observed_method}; events: {event_count}; see {}",
                    event_log_path.display()
                )));
            }
            terminate_child(&mut child);
            return Err(AgentError::Codex(error.to_string()));
        }

        if message.get("id").is_some() && message.get("method").is_some() {
            let method = message
                .get("method")
                .and_then(Value::as_str)
                .unwrap_or("unknown");
            terminate_child(&mut child);
            return Err(AgentError::Codex(format!(
                "unsupported app-server request '{method}'. See {}",
                event_log_path.display()
            )));
        }

        let response_id = message.get("id").and_then(Value::as_i64);
        match response_id {
            Some(0) => {
                send(&mut stdin, json!({ "method": "initialized", "params": {} }))?;
                send(
                    &mut stdin,
                    json!({
                        "method": "thread/start",
                        "id": 1,
                        "params": {
                            "cwd": prepared.worktree,
                            "runtimeWorkspaceRoots": [prepared.worktree],
                            "approvalPolicy": "never",
                            "sandbox": "danger-full-access"
                        }
                    }),
                )?;
            }
            Some(1) => {
                let id = message
                    .pointer("/result/thread/id")
                    .and_then(Value::as_str)
                    .ok_or_else(|| {
                        AgentError::Codex("thread/start response missing thread id".to_owned())
                    })?
                    .to_owned();
                thread_id = Some(id.clone());
                send_turn_start(&mut stdin, config, &id, prepared)?;
            }
            Some(2) => {
                turn_id = message
                    .pointer("/result/turn/id")
                    .and_then(Value::as_str)
                    .map(str::to_owned);
            }
            _ => {}
        }

        if pending_state_query == response_id {
            pending_state_query = None;
            if let Some(turn_id) = &turn_id {
                match turn_status_from_query(&message, turn_id) {
                    Some("completed") => {
                        terminate_child(&mut child);
                        return Ok(());
                    }
                    Some("failed") | Some("interrupted") => {
                        let detail = turn_error_from_query(&message, turn_id)
                            .unwrap_or("turn did not complete successfully");
                        terminate_child(&mut child);
                        return Err(AgentError::Codex(format!(
                            "turn status was {} from state query: {detail}",
                            turn_status_from_query(&message, turn_id).unwrap_or("unknown")
                        )));
                    }
                    Some("inProgress") => {
                        last_observed_method = "turn-state:inProgress".to_owned();
                    }
                    Some(other) => {
                        terminate_child(&mut child);
                        return Err(AgentError::Codex(format!(
                            "turn-state query returned unknown status '{other}'. See {}",
                            event_log_path.display()
                        )));
                    }
                    None => {
                        last_observed_method = format!("turn-state:notFound:{turn_id}");
                    }
                }
            }
        }

        if message.get("method").and_then(Value::as_str) == Some("turn/started") {
            turn_started = true;
        }

        if message.get("method").and_then(Value::as_str) == Some("turn/completed") {
            let status = message
                .pointer("/params/turn/status")
                .and_then(Value::as_str)
                .unwrap_or("unknown");
            terminate_child(&mut child);
            if status == "completed" {
                return Ok(());
            }
            let detail = message
                .pointer("/params/turn/error/message")
                .and_then(Value::as_str)
                .unwrap_or("turn did not complete successfully");
            return Err(AgentError::Codex(format!(
                "turn status was {status}: {detail}"
            )));
        }
    }
}

fn claude_code_args(config: &ResolvedConfig, prompt: &str) -> Vec<String> {
    let mut args = vec![
        "-p".to_owned(),
        prompt.to_owned(),
        "--output-format".to_owned(),
        "stream-json".to_owned(),
        "--verbose".to_owned(),
        "--dangerously-skip-permissions".to_owned(),
    ];
    if let Some(model) = &config.agent_model {
        args.push("--model".to_owned());
        args.push(model.clone());
    }
    args
}

fn record_claude_line(
    event_log_path: &Path,
    line: &str,
    final_is_error: &mut Option<bool>,
    final_subtype: &mut Option<String>,
) -> Result<(), AgentError> {
    append_event_log(event_log_path, line)?;
    // The claude adapter deliberately tolerates non-JSON or partial stdout lines
    // (still logged to the event file above) rather than hard-erroring on a parse
    // failure the way run_codex_agent does.
    if let Ok(message) = serde_json::from_str::<Value>(line) {
        if message.get("type").and_then(Value::as_str) == Some("result") {
            *final_is_error = Some(
                message
                    .get("is_error")
                    .and_then(Value::as_bool)
                    .unwrap_or(false),
            );
            *final_subtype = message
                .get("subtype")
                .and_then(Value::as_str)
                .map(str::to_owned);
        }
    }
    Ok(())
}

fn run_claude_code_agent(
    config: &ResolvedConfig,
    prepared: &PreparedRun,
) -> Result<(), AgentError> {
    let command = resolved_agent_command(config);
    if command.is_empty() {
        return Err(AgentError::MissingCommand);
    }

    let prompt = agent_prompt(config, prepared);
    let mut process = base_command(&command, prepared);
    process
        .args(claude_code_args(config, &prompt))
        // When the harness itself runs inside a Claude Code session these flags
        // are inherited; strip them so the spawned agent starts as a clean
        // top-level session instead of a nested child.
        .env_remove("CLAUDECODE")
        .env_remove("CLAUDE_CODE_CHILD_SESSION")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    let mut child = process.spawn()?;

    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| AgentError::ClaudeCode("failed to open claude stdout".to_owned()))?;
    let stderr = child
        .stderr
        .take()
        .ok_or_else(|| AgentError::ClaudeCode("failed to open claude stderr".to_owned()))?;

    // Drain stderr continuously on its own thread so a chatty Node CLI cannot fill
    // the pipe buffer, block its own write(), and burn the whole timeout.
    let stderr_handle = std::thread::spawn(move || {
        let mut buffer = String::new();
        std::io::Read::read_to_string(&mut BufReader::new(stderr), &mut buffer).ok();
        buffer
    });

    let (line_tx, line_rx) = mpsc::channel::<String>();
    std::thread::spawn(move || {
        let reader = BufReader::new(stdout);
        for line in reader.lines().map_while(Result::ok) {
            if line_tx.send(line).is_err() {
                break;
            }
        }
    });

    let event_log_path = prepared
        .contract_path
        .parent()
        .unwrap_or(&prepared.worktree)
        .join("CLAUDE_CODE_EVENTS.jsonl");
    let deadline = Instant::now() + Duration::from_secs(config.agent_timeout_minutes as u64 * 60);
    let mut final_is_error: Option<bool> = None;
    let mut final_subtype: Option<String> = None;

    loop {
        if Instant::now() >= deadline {
            terminate_child(&mut child);
            return Err(AgentError::ClaudeCode(format!(
                "timed out after {} minute(s); see {}",
                config.agent_timeout_minutes,
                event_log_path.display()
            )));
        }

        match line_rx.recv_timeout(Duration::from_millis(250)) {
            Ok(line) => {
                record_claude_line(
                    &event_log_path,
                    &line,
                    &mut final_is_error,
                    &mut final_subtype,
                )?;
            }
            Err(mpsc::RecvTimeoutError::Timeout) => {
                if child.try_wait()?.is_some() {
                    break;
                }
            }
            Err(mpsc::RecvTimeoutError::Disconnected) => {
                break;
            }
        }
    }

    // Child exited or stdout closed. Drain every remaining line with a BLOCKING
    // recv: it returns Err only once the reader thread hits EOF and drops the
    // sender, so no buffered line (including the terminal `result`) can be lost to
    // a race. It cannot hang: the child has exited, so stdout closes and the
    // reader reaches EOF within microseconds.
    while let Ok(line) = line_rx.recv() {
        record_claude_line(
            &event_log_path,
            &line,
            &mut final_is_error,
            &mut final_subtype,
        )?;
    }

    // Reap the child; a `stream-json` result is authoritative, so the exit status
    // itself is not part of the success decision.
    child.wait()?;
    let stderr_text = stderr_handle.join().unwrap_or_default();
    match final_is_error {
        Some(true) => {
            let detail =
                final_subtype.unwrap_or_else(|| "claude reported an error result".to_owned());
            Err(AgentError::ClaudeCode(detail))
        }
        // is_error:false is an authoritative success signal, so the process exit
        // status is intentionally not consulted on this arm.
        Some(false) => Ok(()),
        None => {
            // A real `--output-format stream-json` run always emits a terminal
            // result event, so its absence is anomalous regardless of exit status.
            let mut detail = format!(
                "claude exited without a result event; see {}",
                event_log_path.display()
            );
            if !stderr_text.trim().is_empty() {
                detail.push_str(&format!(" (stderr: {})", stderr_text.trim()));
            }
            Err(AgentError::ClaudeCode(detail))
        }
    }
}

fn base_command(command: &[String], prepared: &PreparedRun) -> Command {
    let mut process = Command::new(&command[0]);
    process
        .args(&command[1..])
        .current_dir(&prepared.worktree)
        .env("HARNESS_DB_PATH", &prepared.harness_db_path)
        .env("HARNESS_RUN_ID", &prepared.run_id)
        .env("HARNESS_RUN_MODE", "execute");
    process
}

fn send(stdin: &mut impl Write, message: Value) -> Result<(), AgentError> {
    writeln!(stdin, "{message}")?;
    stdin.flush()?;
    Ok(())
}

fn append_event_log(path: &Path, line: &str) -> Result<(), AgentError> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    let mut file = OpenOptions::new().create(true).append(true).open(path)?;
    writeln!(file, "{line}")?;
    Ok(())
}

fn send_turn_start(
    stdin: &mut impl Write,
    config: &ResolvedConfig,
    thread_id: &str,
    prepared: &PreparedRun,
) -> Result<(), AgentError> {
    send(
        stdin,
        json!({
            "method": "turn/start",
            "id": 2,
            "params": {
                "threadId": thread_id,
                "cwd": prepared.worktree,
                "runtimeWorkspaceRoots": [prepared.worktree],
                "approvalPolicy": "never",
                "sandboxPolicy": { "type": "dangerFullAccess" },
                "input": [
                    {
                        "type": "text",
                        "text": agent_prompt(config, prepared),
                        "text_elements": []
                    }
                ]
            }
        }),
    )
}

fn send_turn_state_query(
    stdin: &mut impl Write,
    request_id: i64,
    thread_id: &str,
) -> Result<(), AgentError> {
    send(
        stdin,
        json!({
            "method": "thread/turns/list",
            "id": request_id,
            "params": {
                "threadId": thread_id,
                "limit": 10,
                "sortDirection": "desc",
                "itemsView": "notLoaded"
            }
        }),
    )
}

fn turn_status_from_query<'a>(message: &'a Value, turn_id: &str) -> Option<&'a str> {
    message
        .pointer("/result/data")
        .and_then(Value::as_array)?
        .iter()
        .find(|turn| turn.get("id").and_then(Value::as_str) == Some(turn_id))?
        .get("status")
        .and_then(Value::as_str)
}

fn turn_error_from_query<'a>(message: &'a Value, turn_id: &str) -> Option<&'a str> {
    message
        .pointer("/result/data")
        .and_then(Value::as_array)?
        .iter()
        .find(|turn| turn.get("id").and_then(Value::as_str) == Some(turn_id))?
        .pointer("/error/message")
        .and_then(Value::as_str)
}

fn agent_prompt(config: &ResolvedConfig, prepared: &PreparedRun) -> String {
    let harness_cli = config.repo_root.join("scripts/bin/harness-cli");
    format!(
        "You are running inside a Harness Symphony worktree. Read AGENTS.md and the run contract at {}. Complete only story {} for run {}. Do not change unrelated product code. Write all required artifacts under the current working directory: .harness/runs/{}/SUMMARY.md and .harness/runs/{}/RESULT.json. Use Harness CLI writes with HARNESS_DB_PATH, HARNESS_RUN_ID, and HARNESS_RUN_MODE from the environment so .harness/changesets/{}.changeset.jsonl is produced in this worktree. If scripts/bin/harness-cli is absent in the worktree, run the root binary at {} while keeping the current worktree as cwd. RESULT.json must have version 1, run_id {}, story_id {}, an allowed outcome, summary_path .harness/runs/{}/SUMMARY.md, and a top-level validation object. Do not write validation_evidence. validation must be either {{\"commands\":[{{\"command\":\"exact command\",\"result\":\"pass\"}}]}} with each result set to pass, fail, or unavailable, or {{\"unavailable\":\"non-empty reason\"}}.",
        prepared.contract_path.display(),
        prepared.story_id,
        prepared.run_id,
        prepared.run_id,
        prepared.run_id,
        prepared.run_id,
        harness_cli.display(),
        prepared.run_id,
        prepared.story_id,
        prepared.run_id
    )
}

fn terminate_child(child: &mut std::process::Child) {
    let _ = child.kill();
    let _ = child.wait();
}

fn read_child_stderr(stderr: std::process::ChildStderr) -> Result<String, AgentError> {
    let mut reader = BufReader::new(stderr);
    let mut text = String::new();
    use std::io::Read;
    reader.read_to_string(&mut text)?;
    Ok(text.trim().to_owned())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::ResolvedConfig;
    use std::fs;
    use std::os::unix::fs::PermissionsExt;
    use std::path::Path;

    fn config(adapter: &str, command: Vec<&str>) -> ResolvedConfig {
        ResolvedConfig {
            version: 1,
            repo_root: Path::new("/repo").to_path_buf(),
            harness_db: Path::new("/repo/harness.db").to_path_buf(),
            state_db: Path::new("/repo/.symphony/state.db").to_path_buf(),
            runs_dir: Path::new("/repo/.harness/runs").to_path_buf(),
            worktrees_dir: Path::new("/repo/.symphony/worktrees").to_path_buf(),
            single_active_run: true,
            agent_adapter: adapter.to_owned(),
            agent_command: command.into_iter().map(str::to_owned).collect(),
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

    fn prepared() -> PreparedRun {
        PreparedRun {
            run_id: "run_1".to_owned(),
            story_id: "US-046".to_owned(),
            branch: Some("symphony/run_1".to_owned()),
            worktree: Path::new("/repo/.symphony/worktrees/run_1").to_path_buf(),
            contract_path: Path::new("/repo/.harness/runs/run_1/RUN_CONTRACT.json").to_path_buf(),
            harness_db_path: Path::new("/repo/.symphony/worktrees/run_1/harness.db").to_path_buf(),
            lightweight: false,
        }
    }

    #[test]
    fn codex_adapter_defaults_to_app_server_command() {
        let config = config("codex", vec![]);

        assert_eq!(
            resolved_agent_command(&config),
            vec!["codex".to_owned(), "app-server".to_owned()]
        );
        assert!(agent_adapter_status(&config)
            .unwrap()
            .contains("codex app-server"));
    }

    #[test]
    fn custom_adapter_requires_command() {
        let config = config("custom", vec![]);

        assert!(matches!(
            agent_adapter_status(&config).unwrap_err(),
            AgentError::MissingCommand
        ));
    }

    #[test]
    fn agent_prompt_points_to_worktree_artifacts_and_run_env() {
        let config = config("codex", vec![]);
        let prompt = agent_prompt(&config, &prepared());

        assert!(prompt.contains("US-046"));
        assert!(prompt.contains(".harness/runs/run_1/SUMMARY.md"));
        assert!(prompt.contains(".harness/changesets/run_1.changeset.jsonl"));
        assert!(prompt.contains("/repo/scripts/bin/harness-cli"));
        assert!(prompt.contains("HARNESS_DB_PATH"));
        assert!(prompt.contains("top-level validation object"));
        assert!(prompt.contains("Do not write validation_evidence"));
        assert!(prompt.contains("\"result\":\"pass\""));
    }

    #[test]
    fn codex_adapter_completes_json_rpc_handshake() {
        let temp_dir = tempfile::tempdir().unwrap();
        let worktree = temp_dir.path().join("worktree");
        fs::create_dir_all(&worktree).unwrap();
        let fake_server = temp_dir.path().join("fake-codex-app-server");
        fs::write(
            &fake_server,
            r#"#!/usr/bin/env sh
read initialize
printf '%s\n' '{"id":0,"result":{"userAgent":"fake","codexHome":"/tmp","platformFamily":"unix","platformOs":"macos"}}'
read initialized
read thread_start
printf '%s\n' '{"id":1,"result":{"thread":{"id":"thr_1"}}}'
printf '%s\n' '{"method":"thread/started","params":{"thread":{"id":"thr_1"}}}'
read turn_start
printf '%s\n' '{"id":2,"result":{}}'
printf '%s\n' '{"method":"turn/completed","params":{"threadId":"thr_1","turn":{"id":"turn_1","items":[],"itemsView":{"type":"complete"},"status":"completed","error":null,"startedAt":1,"completedAt":2,"durationMs":1000}}}'
"#,
        )
        .unwrap();
        let mut permissions = fs::metadata(&fake_server).unwrap().permissions();
        permissions.set_mode(0o755);
        fs::set_permissions(&fake_server, permissions).unwrap();

        let mut config = config("codex", vec![fake_server.to_str().unwrap()]);
        config.agent_timeout_minutes = 1;
        let mut prepared = prepared();
        prepared.worktree = worktree.clone();
        prepared.harness_db_path = worktree.join("harness.db");
        prepared.contract_path = worktree.join(".harness/runs/run_1/RUN_CONTRACT.json");

        run_codex_agent(&config, &prepared).unwrap();
    }

    #[test]
    fn claudecode_defaults_to_claude_command() {
        let config = config("claudecode", vec![]);

        assert_eq!(resolved_agent_command(&config), vec!["claude".to_owned()]);
        assert!(agent_adapter_status(&config).unwrap().contains("claude"));
    }

    #[test]
    fn claude_code_args_include_model_when_set() {
        let mut config = config("claudecode", vec![]);
        config.agent_model = Some("sonnet".to_owned());
        let args = claude_code_args(&config, "do the work");

        assert_eq!(
            args,
            vec![
                "-p".to_owned(),
                "do the work".to_owned(),
                "--output-format".to_owned(),
                "stream-json".to_owned(),
                "--verbose".to_owned(),
                "--dangerously-skip-permissions".to_owned(),
                "--model".to_owned(),
                "sonnet".to_owned(),
            ]
        );
    }

    #[test]
    fn claude_code_args_omit_model_when_absent() {
        let config = config("claudecode", vec![]);
        let args = claude_code_args(&config, "do the work");

        assert!(!args.contains(&"--model".to_owned()));
        assert_eq!(args.first().map(String::as_str), Some("-p"));
        assert!(args.contains(&"stream-json".to_owned()));
    }

    #[test]
    fn claudecode_adapter_completes_via_fake_claude() {
        let temp_dir = tempfile::tempdir().unwrap();
        let worktree = temp_dir.path().join("worktree");
        fs::create_dir_all(&worktree).unwrap();
        let fake_claude = temp_dir.path().join("fake-claude");
        fs::write(
            &fake_claude,
            r#"#!/usr/bin/env sh
printf '%s\n' '{"type":"system","subtype":"init"}'
printf '%s\n' '{"type":"assistant","message":{"role":"assistant"}}'
printf '%s\n' '{"type":"result","subtype":"success","is_error":false}'
"#,
        )
        .unwrap();
        let mut permissions = fs::metadata(&fake_claude).unwrap().permissions();
        permissions.set_mode(0o755);
        fs::set_permissions(&fake_claude, permissions).unwrap();

        let mut config = config("claudecode", vec![fake_claude.to_str().unwrap()]);
        config.agent_timeout_minutes = 1;
        let mut prepared = prepared();
        prepared.worktree = worktree.clone();
        prepared.harness_db_path = worktree.join("harness.db");
        prepared.contract_path = worktree.join(".harness/runs/run_1/RUN_CONTRACT.json");

        run_claude_code_agent(&config, &prepared).unwrap();

        let event_log = worktree.join(".harness/runs/run_1/CLAUDE_CODE_EVENTS.jsonl");
        assert!(event_log.exists());
    }

    #[test]
    fn claudecode_adapter_reports_error_result() {
        let temp_dir = tempfile::tempdir().unwrap();
        let worktree = temp_dir.path().join("worktree");
        fs::create_dir_all(&worktree).unwrap();
        let fake_claude = temp_dir.path().join("fake-claude");
        fs::write(
            &fake_claude,
            r#"#!/usr/bin/env sh
printf '%s\n' '{"type":"result","subtype":"error_max_turns","is_error":true}'
"#,
        )
        .unwrap();
        let mut permissions = fs::metadata(&fake_claude).unwrap().permissions();
        permissions.set_mode(0o755);
        fs::set_permissions(&fake_claude, permissions).unwrap();

        let mut config = config("claudecode", vec![fake_claude.to_str().unwrap()]);
        config.agent_timeout_minutes = 1;
        let mut prepared = prepared();
        prepared.worktree = worktree.clone();
        prepared.harness_db_path = worktree.join("harness.db");
        prepared.contract_path = worktree.join(".harness/runs/run_1/RUN_CONTRACT.json");

        assert!(matches!(
            run_claude_code_agent(&config, &prepared).unwrap_err(),
            AgentError::ClaudeCode(_)
        ));
    }

    #[test]
    fn claudecode_adapter_errors_without_result_event() {
        let temp_dir = tempfile::tempdir().unwrap();
        let worktree = temp_dir.path().join("worktree");
        fs::create_dir_all(&worktree).unwrap();
        let fake_claude = temp_dir.path().join("fake-claude");
        fs::write(
            &fake_claude,
            r#"#!/usr/bin/env sh
printf '%s\n' '{"type":"system","subtype":"init"}'
"#,
        )
        .unwrap();
        let mut permissions = fs::metadata(&fake_claude).unwrap().permissions();
        permissions.set_mode(0o755);
        fs::set_permissions(&fake_claude, permissions).unwrap();

        let mut config = config("claudecode", vec![fake_claude.to_str().unwrap()]);
        config.agent_timeout_minutes = 1;
        let mut prepared = prepared();
        prepared.worktree = worktree.clone();
        prepared.harness_db_path = worktree.join("harness.db");
        prepared.contract_path = worktree.join(".harness/runs/run_1/RUN_CONTRACT.json");

        assert!(matches!(
            run_claude_code_agent(&config, &prepared).unwrap_err(),
            AgentError::ClaudeCode(_)
        ));
    }

    #[test]
    fn resolve_readiness_covers_all_branches() {
        assert_eq!(
            resolve_readiness("custom", false, true, true).0,
            Readiness::Ready
        );
        let (status, next) = resolve_readiness("custom", false, true, false);
        assert_eq!(status, Readiness::NeedsSetup);
        assert!(next.unwrap().contains("agent.command"));

        let (status, next) = resolve_readiness("claudecode", false, false, false);
        assert_eq!(status, Readiness::NotInstalled);
        assert!(next.unwrap().contains("npm i -g @anthropic-ai/claude-code"));
        let (status, next) = resolve_readiness("claudecode", true, false, false);
        assert_eq!(status, Readiness::NeedsSetup);
        assert!(next.unwrap().contains("ANTHROPIC_API_KEY"));
        assert_eq!(
            resolve_readiness("claudecode", true, true, false).0,
            Readiness::Ready
        );

        let (status, next) = resolve_readiness("codex", false, false, false);
        assert_eq!(status, Readiness::NotInstalled);
        assert!(next.unwrap().contains("Codex"));
        let (status, next) = resolve_readiness("codex", true, false, false);
        assert_eq!(status, Readiness::NeedsSetup);
        assert!(next.unwrap().contains("codex login"));
        assert_eq!(
            resolve_readiness("codex", true, true, false).0,
            Readiness::Ready
        );

        let (status, next) = resolve_readiness("mystery", true, true, true);
        assert_eq!(status, Readiness::Unknown);
        assert!(next.unwrap().contains("agent.adapter"));
    }

    #[test]
    fn all_agent_readiness_marks_active_adapter() {
        let config = config("claudecode", vec![]);
        let all = all_agent_readiness(&config);

        assert_eq!(all.len(), 3);
        let active: Vec<&str> = all
            .iter()
            .filter(|entry| entry.active)
            .map(|entry| entry.adapter.as_str())
            .collect();
        assert_eq!(active, vec!["claudecode"]);
    }

    #[test]
    fn readiness_serializes_kebab_case() {
        assert_eq!(
            serde_json::to_string(&Readiness::NotInstalled).unwrap(),
            "\"not-installed\""
        );
    }

    #[test]
    fn config_indicates_login_detects_oauth_account_or_user_id() {
        let with_oauth = json!({ "oauthAccount": { "emailAddress": "person@example.com" } });
        assert!(config_indicates_login(&with_oauth));

        let with_user_id = json!({ "userID": "abc123" });
        assert!(config_indicates_login(&with_user_id));

        assert!(!config_indicates_login(&json!({})));
        assert!(!config_indicates_login(&json!({ "oauthAccount": null })));
        assert!(!config_indicates_login(&json!({ "userID": "" })));
    }

    #[test]
    fn expand_tilde_resolves_home_prefix_only() {
        let home = Path::new("/home/agent");
        assert_eq!(expand_tilde("~", home), home.to_path_buf());
        assert_eq!(expand_tilde("~/bin/claude", home), home.join("bin/claude"));
        assert_eq!(
            expand_tilde("/usr/local/bin/claude", home),
            PathBuf::from("/usr/local/bin/claude")
        );
        // A bare "~name" is not a home reference and must be left untouched.
        assert_eq!(expand_tilde("~other/x", home), PathBuf::from("~other/x"));
    }

    #[test]
    fn codex_adapter_recovers_completed_turn_from_state_query() {
        let temp_dir = tempfile::tempdir().unwrap();
        let worktree = temp_dir.path().join("worktree");
        fs::create_dir_all(&worktree).unwrap();
        let fake_server = temp_dir.path().join("fake-codex-app-server");
        fs::write(
            &fake_server,
            r#"#!/usr/bin/env sh
read initialize
printf '%s\n' '{"id":0,"result":{"userAgent":"fake","codexHome":"/tmp","platformFamily":"unix","platformOs":"macos"}}'
read initialized
read thread_start
printf '%s\n' '{"id":1,"result":{"thread":{"id":"thr_1"}}}'
read turn_start
printf '%s\n' '{"id":2,"result":{"turn":{"id":"turn_1","items":[],"itemsView":"notLoaded","status":"inProgress","error":null,"startedAt":null,"completedAt":null,"durationMs":null}}}'
printf '%s\n' '{"method":"turn/started","params":{"threadId":"thr_1","turn":{"id":"turn_1","items":[],"itemsView":"notLoaded","status":"inProgress","error":null,"startedAt":1,"completedAt":null,"durationMs":null}}}'
read state_query
printf '%s\n' '{"id":3,"result":{"data":[{"id":"turn_1","items":[],"itemsView":"notLoaded","status":"completed","error":null,"startedAt":1,"completedAt":2,"durationMs":1000}],"nextCursor":null,"backwardsCursor":null}}'
"#,
        )
        .unwrap();
        let mut permissions = fs::metadata(&fake_server).unwrap().permissions();
        permissions.set_mode(0o755);
        fs::set_permissions(&fake_server, permissions).unwrap();

        let mut config = config("codex", vec![fake_server.to_str().unwrap()]);
        config.agent_timeout_minutes = 1;
        let mut prepared = prepared();
        prepared.worktree = worktree.clone();
        prepared.harness_db_path = worktree.join("harness.db");
        prepared.contract_path = worktree.join(".harness/runs/run_1/RUN_CONTRACT.json");

        run_codex_agent(&config, &prepared).unwrap();
    }
}
