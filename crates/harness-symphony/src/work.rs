use std::collections::{HashMap, HashSet};
use std::path::Path;

use rusqlite::{params, Connection};
use thiserror::Error;

use crate::state::{RunRecord, RunStateStore, StateError};

#[derive(Debug, Error)]
pub enum WorkError {
    #[error("harness database not found at {0}. Run: scripts/bin/harness-cli init")]
    MissingDatabase(String),
    #[error("story {0} not found")]
    StoryNotFound(String),
    #[error("{0}")]
    InvalidInput(String),
    #[error("sqlite error: {0}")]
    Sqlite(#[from] rusqlite::Error),
    #[error("{0}")]
    State(#[from] StateError),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WorkItem {
    pub id: String,
    pub status: String,
    pub lane: String,
    pub verify: String,
    pub runnable: String,
    pub reason: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WorkCandidate {
    pub story_id: String,
    pub source: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BoardItem {
    pub id: String,
    pub title: String,
    pub story_status: String,
    pub lane: String,
    pub verify: String,
    pub board_state: BoardState,
    pub reason: String,
    pub blockers: Vec<String>,
    pub unblocks: Vec<String>,
    pub parent_id: Option<String>,
    pub children: Vec<String>,
    pub hierarchy_depth: usize,
    pub run_id: Option<String>,
    pub active_run: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GuidedIntakeDraft {
    pub idea: String,
    pub audience: String,
    pub outcome: String,
    pub non_goals: String,
    pub validation: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CreatedStory {
    pub story_id: String,
    pub title: String,
    pub status: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BoardState {
    Ready,
    Blocked,
    InProgress,
    Review,
    NeedsAttention,
    Done,
}

impl BoardState {
    pub fn label(&self) -> &'static str {
        match self {
            BoardState::Ready => "Ready",
            BoardState::Blocked => "Blocked",
            BoardState::InProgress => "In Progress",
            BoardState::Review => "Review",
            BoardState::NeedsAttention => "Needs Attention",
            BoardState::Done => "Done",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct StoryRow {
    id: String,
    title: String,
    status: String,
    lane: String,
    verify_command: Option<String>,
}

pub trait WorkSource {
    fn name(&self) -> &'static str;
    fn poll(&self) -> Result<Vec<WorkCandidate>, WorkError>;
}

pub struct HarnessDbWorkSource<'a> {
    db_path: &'a Path,
}

impl<'a> HarnessDbWorkSource<'a> {
    pub fn new(db_path: &'a Path) -> Self {
        Self { db_path }
    }
}

impl WorkSource for HarnessDbWorkSource<'_> {
    fn name(&self) -> &'static str {
        "harness-db"
    }

    fn poll(&self) -> Result<Vec<WorkCandidate>, WorkError> {
        Ok(list_work(self.db_path)?
            .into_iter()
            .filter(is_auto_eligible)
            .map(|item| WorkCandidate {
                story_id: item.id,
                source: self.name().to_owned(),
            })
            .collect())
    }
}

pub const EXTERNAL_WORK_SOURCE_BOUNDARIES: &[&str] =
    &["github-issues", "linear", "jira", "remote-harness"];

pub fn list_work(db_path: &Path) -> Result<Vec<WorkItem>, WorkError> {
    if !db_path.exists() {
        return Err(WorkError::MissingDatabase(db_path.display().to_string()));
    }
    let connection = Connection::open(db_path)?;
    let mut statement = connection.prepare(
        "SELECT id, status, risk_lane, verify_command
         FROM story
         ORDER BY id;",
    )?;
    let rows = statement.query_map(params![], |row| {
        let id = row.get::<_, String>(0)?;
        let status = row.get::<_, String>(1)?;
        let lane = row.get::<_, String>(2)?;
        let verify_command = row.get::<_, Option<String>>(3)?;
        Ok(classify(id, status, lane, verify_command))
    })?;

    rows.collect::<std::result::Result<Vec<_>, _>>()
        .map_err(WorkError::from)
}

pub fn list_board(harness_db: &Path, state_db: &Path) -> Result<Vec<BoardItem>, WorkError> {
    if !harness_db.exists() {
        return Err(WorkError::MissingDatabase(harness_db.display().to_string()));
    }
    let connection = Connection::open(harness_db)?;
    let stories = load_story_rows(&connection)?;
    let stories = stories
        .into_iter()
        .filter(|story| story.status != "retired")
        .collect::<Vec<_>>();
    let story_ids = stories
        .iter()
        .map(|story| story.id.clone())
        .collect::<HashSet<_>>();
    let dependencies = load_dependency_edges(&connection, &story_ids)?;
    let blockers_by_story = blockers_by_story(&dependencies);
    let unblocks_by_story = unblocks_by_story(&dependencies);
    let hierarchy = load_hierarchy_edges(&connection, &story_ids)?;
    let parent_by_child = parent_by_child(&hierarchy);
    let children_by_parent = children_by_parent(&hierarchy);
    let cycle_members = cycle_members(&story_ids, &dependencies);
    let runs = latest_runs_by_story(RunStateStore::new(state_db.to_path_buf()).list_runs()?);

    let done_ids = stories
        .iter()
        .filter(|story| {
            story.status == "implemented"
                || runs
                    .get(&story.id)
                    .is_some_and(|run| run.status == "completed" && is_synced(run))
        })
        .map(|story| story.id.clone())
        .collect::<HashSet<_>>();

    let mut items = stories
        .into_iter()
        .map(|story| {
            let blockers = sorted_vec(
                blockers_by_story
                    .get(&story.id)
                    .cloned()
                    .unwrap_or_default(),
            );
            let unblocks = sorted_vec(
                unblocks_by_story
                    .get(&story.id)
                    .cloned()
                    .unwrap_or_default(),
            );
            let run = runs.get(&story.id);
            let in_cycle = cycle_members.contains(&story.id);
            let parent_id = parent_by_child.get(&story.id).cloned();
            let children = sorted_vec(
                children_by_parent
                    .get(&story.id)
                    .cloned()
                    .unwrap_or_default(),
            );
            let hierarchy_depth = hierarchy_depth(&story.id, &parent_by_child);
            let derivation = BoardDerivation {
                blockers,
                unblocks,
                parent_id,
                children,
                hierarchy_depth,
                in_cycle,
                run,
                done_ids: &done_ids,
            };
            derive_board_item(story, derivation)
        })
        .collect::<Vec<_>>();
    items.sort_by(|left, right| left.id.cmp(&right.id));
    Ok(items)
}

pub fn create_story_from_guided_intake(
    harness_db: &Path,
    draft: GuidedIntakeDraft,
) -> Result<CreatedStory, WorkError> {
    if !harness_db.exists() {
        return Err(WorkError::MissingDatabase(harness_db.display().to_string()));
    }
    let title = required(draft.idea.trim(), "rough idea")?.to_owned();
    let outcome = required(draft.outcome.trim(), "outcome")?;
    let validation = required(draft.validation.trim(), "validation")?.to_owned();
    let mut connection = Connection::open(harness_db)?;
    let transaction = connection.transaction()?;
    let story_id = next_story_id(&transaction)?;
    let notes = format!(
        "Audience: {}\nOutcome: {}\nNon-goals: {}\nValidation: {}",
        value_or_dash(draft.audience.trim()),
        outcome,
        value_or_dash(draft.non_goals.trim()),
        validation
    );
    transaction.execute(
        "INSERT INTO intake (input_type, summary, risk_lane, affected_docs, story_id, notes)
         VALUES ('change_request', ?1, 'normal', ?2, ?3, ?4);",
        params![
            title,
            serde_json::json!(["docs/product/symphony-web-ui-controller.md"]).to_string(),
            story_id,
            notes,
        ],
    )?;
    transaction.execute(
        "INSERT INTO story (id, title, risk_lane, contract_doc, verify_command, notes)
         VALUES (?1, ?2, 'normal', 'docs/product/symphony-web-ui-controller.md', ?3, ?4);",
        params![story_id, title, validation, notes],
    )?;
    transaction.commit()?;
    Ok(CreatedStory {
        story_id,
        title,
        status: "planned".to_owned(),
    })
}

pub fn retire_story(harness_db: &Path, story_id: &str) -> Result<(), WorkError> {
    if !harness_db.exists() {
        return Err(WorkError::MissingDatabase(harness_db.display().to_string()));
    }
    let connection = Connection::open(harness_db)?;
    connection.execute(
        "UPDATE story SET status='retired' WHERE id=?1;",
        params![story_id],
    )?;
    if connection.changes() == 0 {
        return Err(WorkError::StoryNotFound(story_id.to_owned()));
    }
    Ok(())
}

fn next_story_id(connection: &Connection) -> Result<String, WorkError> {
    let mut statement = connection.prepare("SELECT id FROM story WHERE id LIKE 'US-%';")?;
    let ids = statement.query_map(params![], |row| row.get::<_, String>(0))?;
    let mut max_id = 0_u32;
    for id in ids {
        let id = id?;
        if let Some(number) = id
            .strip_prefix("US-")
            .and_then(|value| value.parse::<u32>().ok())
        {
            max_id = max_id.max(number);
        }
    }
    Ok(format!("US-{:03}", max_id + 1))
}

fn required<'a>(value: &'a str, field: &str) -> Result<&'a str, WorkError> {
    if value.is_empty() {
        Err(WorkError::InvalidInput(format!("{field} is required")))
    } else {
        Ok(value)
    }
}

fn value_or_dash(value: &str) -> &str {
    if value.is_empty() {
        "-"
    } else {
        value
    }
}

fn classify(id: String, status: String, lane: String, verify_command: Option<String>) -> WorkItem {
    let has_verify = verify_command
        .as_deref()
        .map(str::trim)
        .is_some_and(|value| !value.is_empty());
    let verify = if has_verify { "configured" } else { "missing" }.to_owned();
    let (runnable, reason) = match status.as_str() {
        "planned" | "in_progress" if has_verify => ("yes", "ready"),
        "planned" | "in_progress" => ("warn", "proof command missing"),
        "implemented" => ("no", "already implemented"),
        "retired" => ("no", "retired"),
        "changed" => ("warn", "changed story needs human review"),
        _ => ("no", "unknown story status"),
    };

    WorkItem {
        id,
        status,
        lane,
        verify,
        runnable: runnable.to_owned(),
        reason: reason.to_owned(),
    }
}

fn load_story_rows(connection: &Connection) -> Result<Vec<StoryRow>, WorkError> {
    let mut statement = connection.prepare(
        "SELECT id, title, status, risk_lane, verify_command
         FROM story
         ORDER BY id;",
    )?;
    let rows = statement.query_map(params![], |row| {
        Ok(StoryRow {
            id: row.get(0)?,
            title: row.get(1)?,
            status: row.get(2)?,
            lane: row.get(3)?,
            verify_command: row.get(4)?,
        })
    })?;

    rows.collect::<std::result::Result<Vec<_>, _>>()
        .map_err(WorkError::from)
}

fn load_dependency_edges(
    connection: &Connection,
    story_ids: &HashSet<String>,
) -> Result<Vec<(String, String)>, WorkError> {
    if !table_exists(connection, "story_dependency")? {
        return Ok(Vec::new());
    }
    let mut statement = connection.prepare(
        "SELECT story_id, blocks_story_id
         FROM story_dependency
         ORDER BY story_id, blocks_story_id;",
    )?;
    let rows = statement.query_map(params![], |row| {
        Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
    })?;
    let edges = rows
        .collect::<std::result::Result<Vec<_>, _>>()?
        .into_iter()
        .filter(|(blocker, blocked)| story_ids.contains(blocker) && story_ids.contains(blocked))
        .collect();
    Ok(edges)
}

fn load_hierarchy_edges(
    connection: &Connection,
    story_ids: &HashSet<String>,
) -> Result<Vec<(String, String)>, WorkError> {
    if !table_exists(connection, "story_hierarchy")? {
        return Ok(Vec::new());
    }
    let mut statement = connection.prepare(
        "SELECT parent_story_id, child_story_id
         FROM story_hierarchy
         ORDER BY parent_story_id, child_story_id;",
    )?;
    let rows = statement.query_map(params![], |row| {
        Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
    })?;
    Ok(rows
        .collect::<std::result::Result<Vec<_>, _>>()?
        .into_iter()
        .filter(|(parent, child)| story_ids.contains(parent) && story_ids.contains(child))
        .collect())
}

fn table_exists(connection: &Connection, table: &str) -> Result<bool, WorkError> {
    let exists = connection.query_row(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?1;",
        params![table],
        |_| Ok(()),
    );
    match exists {
        Ok(()) => Ok(true),
        Err(rusqlite::Error::QueryReturnedNoRows) => Ok(false),
        Err(error) => Err(WorkError::Sqlite(error)),
    }
}

fn blockers_by_story(edges: &[(String, String)]) -> HashMap<String, HashSet<String>> {
    let mut blockers: HashMap<String, HashSet<String>> = HashMap::new();
    for (blocker, blocked) in edges {
        blockers
            .entry(blocked.clone())
            .or_default()
            .insert(blocker.clone());
    }
    blockers
}

fn unblocks_by_story(edges: &[(String, String)]) -> HashMap<String, HashSet<String>> {
    let mut unblocks: HashMap<String, HashSet<String>> = HashMap::new();
    for (blocker, blocked) in edges {
        unblocks
            .entry(blocker.clone())
            .or_default()
            .insert(blocked.clone());
    }
    unblocks
}

fn parent_by_child(edges: &[(String, String)]) -> HashMap<String, String> {
    let mut parents = HashMap::new();
    for (parent, child) in edges {
        parents
            .entry(child.clone())
            .or_insert_with(|| parent.clone());
    }
    parents
}

fn children_by_parent(edges: &[(String, String)]) -> HashMap<String, HashSet<String>> {
    let mut children: HashMap<String, HashSet<String>> = HashMap::new();
    for (parent, child) in edges {
        children
            .entry(parent.clone())
            .or_default()
            .insert(child.clone());
    }
    children
}

fn hierarchy_depth(story_id: &str, parent_by_child: &HashMap<String, String>) -> usize {
    let mut depth = 0;
    let mut current = story_id;
    let mut seen = HashSet::new();
    while let Some(parent) = parent_by_child.get(current) {
        if !seen.insert(parent.clone()) {
            break;
        }
        depth += 1;
        current = parent;
    }
    depth
}

fn cycle_members(story_ids: &HashSet<String>, edges: &[(String, String)]) -> HashSet<String> {
    let mut graph: HashMap<String, Vec<String>> = HashMap::new();
    for (blocker, blocked) in edges {
        graph
            .entry(blocker.clone())
            .or_default()
            .push(blocked.clone());
    }

    let mut members = HashSet::new();
    for story_id in story_ids {
        let mut stack = Vec::new();
        let mut visited = HashSet::new();
        if reaches(story_id, story_id, &graph, &mut visited, &mut stack) {
            members.extend(stack);
            members.insert(story_id.clone());
        }
    }
    members
}

fn reaches(
    start: &str,
    current: &str,
    graph: &HashMap<String, Vec<String>>,
    visited: &mut HashSet<String>,
    stack: &mut Vec<String>,
) -> bool {
    if !visited.insert(current.to_owned()) {
        return false;
    }
    stack.push(current.to_owned());
    for next in graph.get(current).into_iter().flatten() {
        if next == start || reaches(start, next, graph, visited, stack) {
            return true;
        }
    }
    stack.pop();
    false
}

fn latest_runs_by_story(runs: Vec<RunRecord>) -> HashMap<String, RunRecord> {
    let mut by_story = HashMap::new();
    for run in runs {
        by_story.entry(run.story_id.clone()).or_insert(run);
    }
    by_story
}

struct BoardDerivation<'a> {
    blockers: Vec<String>,
    unblocks: Vec<String>,
    parent_id: Option<String>,
    children: Vec<String>,
    hierarchy_depth: usize,
    in_cycle: bool,
    run: Option<&'a RunRecord>,
    done_ids: &'a HashSet<String>,
}

fn derive_board_item(story: StoryRow, derivation: BoardDerivation<'_>) -> BoardItem {
    let verify = if story
        .verify_command
        .as_deref()
        .map(str::trim)
        .is_some_and(|value| !value.is_empty())
    {
        "configured"
    } else {
        "missing"
    }
    .to_owned();

    let incomplete_blockers = derivation
        .blockers
        .iter()
        .filter(|blocker| !derivation.done_ids.contains(*blocker))
        .cloned()
        .collect::<Vec<_>>();

    let (board_state, reason) = if story.status == "implemented" {
        (BoardState::Done, "story implemented".to_owned())
    } else if derivation.in_cycle {
        (
            BoardState::Blocked,
            "dependency cycle detected; fix task breakdown".to_owned(),
        )
    } else if let Some(run) = derivation.run {
        match run.status.as_str() {
            "prepared" | "running" => {
                (BoardState::InProgress, format!("active run {}", run.run_id))
            }
            "failed" | "cancelled" | "partial" | "blocked" | "needs_intake" => {
                (BoardState::NeedsAttention, run.next_action.clone())
            }
            "completed" if is_synced(run) => (BoardState::Done, "synced locally".to_owned()),
            "completed" if run.pr_url.is_some() => {
                (BoardState::Review, "review pull request".to_owned())
            }
            "completed" if run.pr_status == "failed" => {
                (BoardState::NeedsAttention, run.next_action.clone())
            }
            "completed" => (
                BoardState::NeedsAttention,
                "completed run is missing required PR review artifact".to_owned(),
            ),
            _ if !incomplete_blockers.is_empty() => (
                BoardState::Blocked,
                format!("waiting for {}", incomplete_blockers.join(", ")),
            ),
            _ => (BoardState::Ready, "ready".to_owned()),
        }
    } else if !incomplete_blockers.is_empty() {
        (
            BoardState::Blocked,
            format!("waiting for {}", incomplete_blockers.join(", ")),
        )
    } else if matches!(story.status.as_str(), "planned" | "in_progress" | "changed") {
        (BoardState::Ready, "ready".to_owned())
    } else if story.status == "retired" {
        (BoardState::Done, "retired".to_owned())
    } else {
        (
            BoardState::NeedsAttention,
            format!("unknown story status {}", story.status),
        )
    };

    BoardItem {
        id: story.id,
        title: story.title,
        story_status: story.status,
        lane: story.lane,
        verify,
        board_state,
        reason,
        blockers: derivation.blockers,
        unblocks: derivation.unblocks,
        parent_id: derivation.parent_id,
        children: derivation.children,
        hierarchy_depth: derivation.hierarchy_depth,
        run_id: derivation.run.map(|run| run.run_id.clone()),
        active_run: derivation.run.and_then(|run| {
            matches!(run.status.as_str(), "prepared" | "running").then(|| run.run_id.clone())
        }),
    }
}

fn is_synced(run: &RunRecord) -> bool {
    matches!(
        run.sync_status.as_str(),
        "applied" | "synced" | "synced_locally"
    )
}

fn sorted_vec(values: HashSet<String>) -> Vec<String> {
    let mut values = values.into_iter().collect::<Vec<_>>();
    values.sort();
    values
}

fn is_auto_eligible(item: &WorkItem) -> bool {
    item.runnable == "yes" && matches!(item.status.as_str(), "planned" | "in_progress")
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::state::{NewRunRecord, RunStateStore};
    use std::path::PathBuf;

    fn create_harness_db(
        temp_dir: &tempfile::TempDir,
        with_dependencies: bool,
    ) -> std::path::PathBuf {
        let db_path = temp_dir.path().join("harness.db");
        let connection = Connection::open(&db_path).unwrap();
        let dependency_sql = if with_dependencies {
            "CREATE TABLE story_dependency (
                story_id TEXT NOT NULL,
                blocks_story_id TEXT NOT NULL,
                PRIMARY KEY (story_id, blocks_story_id),
                CHECK (story_id <> blocks_story_id)
            );"
        } else {
            ""
        };
        connection
            .execute_batch(&format!(
                "CREATE TABLE story (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    risk_lane TEXT NOT NULL,
                    verify_command TEXT
                );
                CREATE TABLE story_hierarchy (
                    parent_story_id TEXT NOT NULL,
                    child_story_id TEXT NOT NULL,
                    PRIMARY KEY (parent_story_id, child_story_id),
                    CHECK (parent_story_id <> child_story_id)
                );
                {dependency_sql}"
            ))
            .unwrap();
        db_path
    }

    fn insert_story(db_path: &Path, id: &str, status: &str) {
        let connection = Connection::open(db_path).unwrap();
        connection
            .execute(
                "INSERT INTO story (id, title, status, risk_lane, verify_command)
                 VALUES (?1, ?2, ?3, 'normal', 'cargo test');",
                params![id, format!("{id} title"), status],
            )
            .unwrap();
    }

    fn insert_dependency(db_path: &Path, blocker: &str, blocked: &str) {
        let connection = Connection::open(db_path).unwrap();
        connection
            .execute(
                "INSERT INTO story_dependency (story_id, blocks_story_id)
                 VALUES (?1, ?2);",
                params![blocker, blocked],
            )
            .unwrap();
    }

    fn insert_hierarchy(db_path: &Path, parent: &str, child: &str) {
        let connection = Connection::open(db_path).unwrap();
        connection
            .execute(
                "INSERT INTO story_hierarchy (parent_story_id, child_story_id)
                 VALUES (?1, ?2);",
                params![parent, child],
            )
            .unwrap();
    }

    fn add_run(
        state_db: PathBuf,
        story_id: &str,
        run_id: &str,
        status: &str,
        sync_status: &str,
        pr_url: Option<&str>,
    ) {
        let store = RunStateStore::new(state_db);
        store
            .add_run(NewRunRecord {
                run_id: run_id.to_owned(),
                story_id: story_id.to_owned(),
                branch: Some(format!("symphony/{run_id}")),
                worktree: PathBuf::from(format!(".symphony/worktrees/{run_id}")),
                lightweight: false,
                status: status.to_owned(),
                result_path: Some(PathBuf::from(format!(".harness/runs/{run_id}/RESULT.json"))),
                sync_status: sync_status.to_owned(),
                next_action: "inspect run".to_owned(),
            })
            .unwrap();
        if let Some(url) = pr_url {
            store.update_pr_url(run_id, url).unwrap();
        }
    }

    #[test]
    fn classifies_planned_story_with_verify_as_ready() {
        let item = classify(
            "US-1".to_owned(),
            "planned".to_owned(),
            "normal".to_owned(),
            Some("cargo test".to_owned()),
        );

        assert_eq!(item.verify, "configured");
        assert_eq!(item.runnable, "yes");
        assert_eq!(item.reason, "ready");
    }

    #[test]
    fn missing_verify_is_warning_not_status_change() {
        let item = classify(
            "US-2".to_owned(),
            "in_progress".to_owned(),
            "normal".to_owned(),
            None,
        );

        assert_eq!(item.status, "in_progress");
        assert_eq!(item.verify, "missing");
        assert_eq!(item.runnable, "warn");
        assert_eq!(item.reason, "proof command missing");
    }

    #[test]
    fn implemented_and_retired_are_not_runnable() {
        for status in ["implemented", "retired"] {
            let item = classify(
                "US-3".to_owned(),
                status.to_owned(),
                "normal".to_owned(),
                Some("true".to_owned()),
            );
            assert_eq!(item.runnable, "no");
        }
    }

    #[test]
    fn list_work_reads_story_rows_from_database() {
        let temp_dir = tempfile::tempdir().unwrap();
        let db_path = temp_dir.path().join("harness.db");
        let connection = Connection::open(&db_path).unwrap();
        connection
            .execute_batch(
                "CREATE TABLE story (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    risk_lane TEXT NOT NULL,
                    verify_command TEXT
                );
                INSERT INTO story (id, status, risk_lane, verify_command)
                VALUES
                    ('US-READY', 'planned', 'normal', 'cargo test'),
                    ('US-WARN', 'planned', 'normal', NULL),
                    ('US-DONE', 'implemented', 'normal', 'true');",
            )
            .unwrap();
        drop(connection);

        let items = list_work(&db_path).unwrap();

        assert_eq!(items.len(), 3);
        assert_eq!(items[0].id, "US-DONE");
        assert_eq!(items[0].runnable, "no");
        assert_eq!(items[1].id, "US-READY");
        assert_eq!(items[1].runnable, "yes");
        assert_eq!(items[2].id, "US-WARN");
        assert_eq!(items[2].runnable, "warn");
    }

    #[test]
    fn harness_db_work_source_polls_only_ready_stories() {
        let temp_dir = tempfile::tempdir().unwrap();
        let db_path = temp_dir.path().join("harness.db");
        let connection = Connection::open(&db_path).unwrap();
        connection
            .execute_batch(
                "CREATE TABLE story (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    risk_lane TEXT NOT NULL,
                    verify_command TEXT
                );
                INSERT INTO story (id, status, risk_lane, verify_command)
                VALUES
                    ('US-READY', 'planned', 'normal', 'cargo test'),
                    ('US-WARN', 'planned', 'normal', NULL),
                    ('US-DONE', 'implemented', 'normal', 'true');",
            )
            .unwrap();
        drop(connection);

        let source = HarnessDbWorkSource::new(&db_path);
        let candidates = source.poll().unwrap();

        assert_eq!(
            candidates,
            vec![WorkCandidate {
                story_id: "US-READY".to_owned(),
                source: "harness-db".to_owned(),
            }]
        );
        assert!(EXTERNAL_WORK_SOURCE_BOUNDARIES.contains(&"github-issues"));
    }

    #[test]
    fn board_marks_story_ready_without_incomplete_blockers() {
        let temp_dir = tempfile::tempdir().unwrap();
        let db_path = create_harness_db(&temp_dir, false);
        let state_db = temp_dir.path().join(".symphony/state.db");
        insert_story(&db_path, "US-READY", "planned");

        let items = list_board(&db_path, &state_db).unwrap();

        assert_eq!(items[0].board_state, BoardState::Ready);
        assert_eq!(items[0].reason, "ready");
    }

    #[test]
    fn board_omits_retired_stories_from_active_work() {
        let temp_dir = tempfile::tempdir().unwrap();
        let db_path = create_harness_db(&temp_dir, false);
        let state_db = temp_dir.path().join(".symphony/state.db");
        insert_story(&db_path, "US-READY", "planned");
        insert_story(&db_path, "US-RETIRED", "retired");

        let items = list_board(&db_path, &state_db).unwrap();

        assert_eq!(items.len(), 1);
        assert_eq!(items[0].id, "US-READY");
    }

    #[test]
    fn board_marks_story_blocked_by_incomplete_dependency() {
        let temp_dir = tempfile::tempdir().unwrap();
        let db_path = create_harness_db(&temp_dir, true);
        let state_db = temp_dir.path().join(".symphony/state.db");
        insert_story(&db_path, "US-A", "planned");
        insert_story(&db_path, "US-B", "planned");
        insert_dependency(&db_path, "US-A", "US-B");

        let items = list_board(&db_path, &state_db).unwrap();
        let blocked = items.iter().find(|item| item.id == "US-B").unwrap();

        assert_eq!(blocked.board_state, BoardState::Blocked);
        assert_eq!(blocked.blockers, vec!["US-A"]);
        assert_eq!(blocked.reason, "waiting for US-A");
    }

    #[test]
    fn board_detects_dependency_cycles_as_breakdown_problems() {
        let temp_dir = tempfile::tempdir().unwrap();
        let db_path = create_harness_db(&temp_dir, true);
        let state_db = temp_dir.path().join(".symphony/state.db");
        insert_story(&db_path, "US-A", "planned");
        insert_story(&db_path, "US-B", "planned");
        insert_dependency(&db_path, "US-A", "US-B");
        insert_dependency(&db_path, "US-B", "US-A");

        let items = list_board(&db_path, &state_db).unwrap();

        assert!(items
            .iter()
            .all(|item| item.board_state == BoardState::Blocked));
        assert!(items
            .iter()
            .all(|item| item.reason.contains("dependency cycle")));
    }

    #[test]
    fn board_exposes_parent_child_hierarchy() {
        let temp_dir = tempfile::tempdir().unwrap();
        let db_path = create_harness_db(&temp_dir, false);
        let state_db = temp_dir.path().join(".symphony/state.db");
        insert_story(&db_path, "US-PARENT", "planned");
        insert_story(&db_path, "US-CHILD", "planned");
        insert_story(&db_path, "US-GRANDCHILD", "planned");
        insert_hierarchy(&db_path, "US-PARENT", "US-CHILD");
        insert_hierarchy(&db_path, "US-CHILD", "US-GRANDCHILD");

        let items = list_board(&db_path, &state_db).unwrap();
        let parent = items.iter().find(|item| item.id == "US-PARENT").unwrap();
        let child = items.iter().find(|item| item.id == "US-CHILD").unwrap();
        let grandchild = items
            .iter()
            .find(|item| item.id == "US-GRANDCHILD")
            .unwrap();

        assert_eq!(parent.children, vec!["US-CHILD"]);
        assert_eq!(parent.hierarchy_depth, 0);
        assert_eq!(child.parent_id, Some("US-PARENT".to_owned()));
        assert_eq!(child.children, vec!["US-GRANDCHILD"]);
        assert_eq!(child.hierarchy_depth, 1);
        assert_eq!(grandchild.parent_id, Some("US-CHILD".to_owned()));
        assert_eq!(grandchild.hierarchy_depth, 2);
    }

    #[test]
    fn board_overlays_active_review_attention_and_done_run_states() {
        let temp_dir = tempfile::tempdir().unwrap();
        let db_path = create_harness_db(&temp_dir, false);
        let state_db = temp_dir.path().join(".symphony/state.db");
        insert_story(&db_path, "US-RUNNING", "planned");
        insert_story(&db_path, "US-REVIEW", "planned");
        insert_story(&db_path, "US-FAILED", "planned");
        insert_story(&db_path, "US-SYNCED", "planned");
        insert_story(&db_path, "US-DONE", "implemented");

        add_run(
            state_db.clone(),
            "US-REVIEW",
            "run_2",
            "completed",
            "not_applied",
            Some("https://example.test/pr/2"),
        );
        add_run(
            state_db.clone(),
            "US-FAILED",
            "run_3",
            "failed",
            "not_applied",
            None,
        );
        add_run(
            state_db.clone(),
            "US-SYNCED",
            "run_4",
            "completed",
            "applied",
            Some("https://example.test/pr/4"),
        );
        add_run(
            state_db.clone(),
            "US-RUNNING",
            "run_1",
            "running",
            "not_applied",
            None,
        );

        let items = list_board(&db_path, &state_db).unwrap();
        let state_for = |id: &str| {
            items
                .iter()
                .find(|item| item.id == id)
                .unwrap()
                .board_state
                .clone()
        };

        assert_eq!(state_for("US-RUNNING"), BoardState::InProgress);
        assert_eq!(state_for("US-REVIEW"), BoardState::Review);
        assert_eq!(state_for("US-FAILED"), BoardState::NeedsAttention);
        assert_eq!(state_for("US-SYNCED"), BoardState::Done);
        assert_eq!(state_for("US-DONE"), BoardState::Done);
    }
}
