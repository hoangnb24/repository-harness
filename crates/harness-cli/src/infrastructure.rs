use std::env;
use std::fs::{self, OpenOptions};
use std::io::{Seek, SeekFrom, Write};
use std::path::{Path, PathBuf};
use std::process::Command;
use std::str::FromStr;

use rusqlite::{params, types::ValueRef, Connection, OptionalExtension, Transaction};
use serde_json::{json, Value};
use thiserror::Error;

use crate::application::{
    BacklogAddInput, BacklogCloseInput, BrownfieldImportResult, ChangesetApplyResult,
    DbRebuildResult, DecisionAddInput, DecisionVerifyResult, HarnessContext, InitResult,
    IntakeInput, InterventionAddInput, InterventionFilter, MigrateResult, QueryTable,
    StoryAddInput, StoryDependencyInput, StoryDependencyRecord, StoryUpdateInput,
    StoryVerifyResult, ToolRegisterInput, TraceInput,
};
use crate::domain::{
    compiled_tool_registry, normalize_token, score_context, score_trace, validate_tool_description,
    AuditFinding, AuditResult, BacklogFilter, BacklogRecord, ContextScoreResult,
    ContextScoreSource, DecisionRecord, FrictionRecord, HarnessStats, ImprovementProposal,
    IntakeRecord, InterventionRecord, RiskLane, StoryMatrixRecord, StoryVerifyAllItem,
    StoryVerifyAllResult, StoryVerifyStatus, ToolArgSpec, ToolEntry, TraceRecord, TraceScoreResult,
    TraceScoreSource,
};

pub type Result<T> = std::result::Result<T, HarnessInfraError>;

#[derive(Debug, Error)]
pub enum HarnessInfraError {
    #[error("database not found at {0}. Run: harness init")]
    MissingDatabase(String),
    #[error("schema file missing: {0}")]
    MissingSchema(String),
    #[error("brownfield import: missing {0}")]
    MissingBrownfieldPath(String),
    #[error("decision {0} has no verify_command. Configure one with: harness-cli decision add --id {0} --title <title> --verify \"<command>\"")]
    MissingDecisionVerifyCommand(String),
    #[error("story {0} has no verify_command. Configure one with: harness-cli story update --id {0} --verify \"<command>\"")]
    MissingStoryVerifyCommand(String),
    #[error("story update: story '{0}' not found")]
    StoryNotFound(String),
    #[error("story dependency: a story cannot depend on itself ('{0}')")]
    StoryDependencySelf(String),
    #[error("story dependency: adding '{0}' -> '{1}' would create a cycle")]
    StoryDependencyCycle(String, String),
    #[error("tool register: tool '{0}' already exists with command '{1}'")]
    ToolAlreadyExists(String, String),
    #[error("tool remove: tool '{0}' not found")]
    ToolNotFound(String),
    #[error("tool register: command '{0}' was not found. Re-run with --force to register anyway.")]
    ToolCommandNotFound(String),
    #[error("{0}")]
    ToolValidation(#[from] crate::domain::ToolValidationError),
    #[error("backlog close: backlog item '{0}' not found")]
    BacklogNotFound(i64),
    #[error("trace '{0}' not found")]
    TraceNotFound(i64),
    #[error("no traces found")]
    NoTraces,
    #[error("story update: nothing to update")]
    EmptyStoryUpdate,
    #[error("changeset apply: {0}")]
    InvalidChangeset(String),
    #[error("changeset apply: unsupported operation '{0}'")]
    UnsupportedChangesetOp(String),
    #[error(
        "db rebuild: database already exists at {0}; remove it or choose an empty HARNESS_DB_PATH"
    )]
    RebuildDatabaseExists(String),
    #[error("sqlite error: {0}")]
    Sqlite(#[from] rusqlite::Error),
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
    #[error("json error: {0}")]
    Json(#[from] serde_json::Error),
}

/// Outcome of one `tool check` scan. The CLI reports these facts; the agent
/// applies policy (skip / degrade / use) based on `status`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ToolCheckResult {
    pub name: String,
    pub kind: String,
    pub capability: Option<String>,
    pub status: String,
    pub detail: String,
}

pub trait HarnessRepository {
    fn init(&self) -> Result<InitResult>;
    fn migrate(&self) -> Result<MigrateResult>;
    fn import_brownfield(&self) -> Result<BrownfieldImportResult>;
    fn record_intake(&self, input: IntakeInput) -> Result<i64>;
    fn add_story(&self, input: StoryAddInput) -> Result<()>;
    fn update_story(&self, input: StoryUpdateInput) -> Result<()>;
    fn add_story_dependency(&self, input: StoryDependencyInput) -> Result<bool>;
    fn remove_story_dependency(&self, input: StoryDependencyInput) -> Result<bool>;
    fn query_story_dependencies(&self, story: Option<&str>) -> Result<Vec<StoryDependencyRecord>>;
    fn verify_story(&self, id: &str) -> Result<StoryVerifyResult>;
    fn verify_all_stories(&self) -> Result<StoryVerifyAllResult>;
    fn add_decision(&self, input: DecisionAddInput) -> Result<()>;
    fn verify_decision(&self, id: &str) -> Result<DecisionVerifyResult>;
    fn add_backlog(&self, input: BacklogAddInput) -> Result<i64>;
    fn close_backlog(&self, input: BacklogCloseInput) -> Result<()>;
    fn register_tool(&self, input: ToolRegisterInput) -> Result<()>;
    fn remove_tool(&self, name: &str) -> Result<()>;
    fn check_tools(&self, name: Option<String>) -> Result<Vec<ToolCheckResult>>;
    fn add_intervention(&self, input: InterventionAddInput) -> Result<i64>;
    fn record_trace(&self, input: TraceInput) -> Result<i64>;
    fn score_trace(&self, id: Option<i64>) -> Result<TraceScoreResult>;
    fn score_context(&self, id: i64) -> Result<ContextScoreResult>;
    fn story_verify_status(&self, id: &str) -> Result<StoryVerifyStatus>;
    fn query_matrix(&self) -> Result<Vec<StoryMatrixRecord>>;
    fn query_backlog(&self, filter: BacklogFilter) -> Result<Vec<BacklogRecord>>;
    fn query_decisions(&self) -> Result<Vec<DecisionRecord>>;
    fn query_intakes(&self) -> Result<Vec<IntakeRecord>>;
    fn query_traces(&self) -> Result<Vec<TraceRecord>>;
    fn query_friction(&self) -> Result<Vec<FrictionRecord>>;
    fn query_tools(
        &self,
        responsibility: Option<String>,
        capability: Option<String>,
    ) -> Result<Vec<ToolEntry>>;
    fn query_interventions(&self, filter: InterventionFilter) -> Result<Vec<InterventionRecord>>;
    fn query_stats(&self) -> Result<HarnessStats>;
    fn audit(&self) -> Result<AuditResult>;
    fn propose(&self, commit: bool) -> Result<Vec<ImprovementProposal>>;
    fn query_sql(&self, sql: &str) -> Result<QueryTable>;
    fn apply_changeset(&self, path: &Path) -> Result<ChangesetApplyResult>;
    fn rebuild_db(&self, changeset_dir: &Path) -> Result<DbRebuildResult>;
}

#[derive(Debug)]
pub struct SqliteHarnessRepository {
    repo_root: PathBuf,
    db_path: PathBuf,
    schema_dir: PathBuf,
}

#[derive(Debug)]
struct ChangesetAppend {
    path: PathBuf,
    original_len: u64,
}

impl SqliteHarnessRepository {
    pub fn new(repo_root: PathBuf, db_path: PathBuf, schema_dir: PathBuf) -> Self {
        Self {
            repo_root,
            db_path,
            schema_dir,
        }
    }

    fn open_existing(&self) -> Result<Connection> {
        if !self.db_path.exists() {
            return Err(HarnessInfraError::MissingDatabase(
                self.db_path.display().to_string(),
            ));
        }

        let connection = Connection::open(&self.db_path)?;
        connection.pragma_update(None, "foreign_keys", "ON")?;
        Ok(connection)
    }

    fn open_or_create(&self) -> Result<Connection> {
        let connection = Connection::open(&self.db_path)?;
        connection.pragma_update(None, "foreign_keys", "ON")?;
        Ok(connection)
    }

    fn schema_version(connection: &Connection) -> Result<i64> {
        let version = connection
            .query_row(
                "SELECT COALESCE(MAX(version),0) FROM schema_version;",
                [],
                |row| row.get::<_, i64>(0),
            )
            .optional()?
            .unwrap_or(0);
        Ok(version)
    }

    fn apply_schema_v1(&self, connection: &Connection) -> Result<()> {
        let schema_path = self.schema_dir.join("001-init.sql");
        if !schema_path.exists() {
            return Err(HarnessInfraError::MissingSchema(
                schema_path.display().to_string(),
            ));
        }

        let schema = fs::read_to_string(schema_path)?;
        connection.execute_batch(&schema)?;
        Ok(())
    }

    fn apply_pending_migrations(
        &self,
        connection: &Connection,
        current_version: i64,
    ) -> Result<Vec<i64>> {
        let mut applied = Vec::new();
        for (version, path) in self.migration_files()? {
            if version > current_version {
                let sql = fs::read_to_string(path)?;
                connection.execute_batch(&sql)?;
                applied.push(version);
            }
        }
        Ok(applied)
    }

    fn migration_files(&self) -> Result<Vec<(i64, PathBuf)>> {
        let mut files = Vec::new();
        for entry in fs::read_dir(&self.schema_dir)? {
            let entry = entry?;
            let path = entry.path();
            if path.extension().and_then(|value| value.to_str()) != Some("sql") {
                continue;
            }
            let Some(file_name) = path.file_name().and_then(|value| value.to_str()) else {
                continue;
            };
            let Some(prefix) = file_name.split('-').next() else {
                continue;
            };
            let Ok(version) = prefix.trim_start_matches('0').parse::<i64>() else {
                continue;
            };
            files.push((version, path));
        }
        files.sort_by_key(|(version, _)| *version);
        Ok(files)
    }

    fn run_id() -> Option<String> {
        env::var("HARNESS_RUN_ID")
            .ok()
            .map(|value| value.trim().to_owned())
            .filter(|value| !value.is_empty())
    }

    fn changeset_path(&self, run_id: &str) -> PathBuf {
        self.repo_root
            .join(".harness")
            .join("changesets")
            .join(format!("{run_id}.changeset.jsonl"))
    }

    fn with_logged_write<T>(
        &self,
        connection: &mut Connection,
        write: impl FnOnce(&Transaction<'_>) -> Result<(T, Vec<Value>)>,
    ) -> Result<T> {
        let run_id = Self::run_id();
        self.with_logged_write_for_run(connection, run_id.as_deref(), write)
    }

    fn with_logged_write_for_run<T>(
        &self,
        connection: &mut Connection,
        run_id: Option<&str>,
        write: impl FnOnce(&Transaction<'_>) -> Result<(T, Vec<Value>)>,
    ) -> Result<T> {
        let transaction = connection.transaction()?;
        let (result, operations) = write(&transaction)?;
        let append = if let Some(run_id) = run_id {
            self.append_changeset_operations(&transaction, run_id, operations)?
        } else {
            None
        };

        match transaction.commit() {
            Ok(()) => Ok(result),
            Err(error) => {
                if let Some(append) = append {
                    rollback_changeset_append(&append)?;
                }
                Err(error.into())
            }
        }
    }

    fn append_changeset_operations(
        &self,
        connection: &Connection,
        run_id: &str,
        operations: Vec<Value>,
    ) -> Result<Option<ChangesetAppend>> {
        if operations.is_empty() {
            return Ok(None);
        }

        let path = self.changeset_path(run_id);
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        let original_len = fs::metadata(&path)
            .map(|metadata| metadata.len())
            .unwrap_or(0);
        let mut file = OpenOptions::new().create(true).append(true).open(&path)?;

        if original_len == 0 {
            let header = json!({
                "op": "changeset.header",
                "version": 1,
                "run_id": run_id,
                "base_schema_version": Self::schema_version(connection)?,
            });
            writeln!(file, "{}", serde_json::to_string(&header)?)?;
        }

        for operation in operations {
            writeln!(file, "{}", serde_json::to_string(&operation)?)?;
        }
        file.flush()?;
        file.sync_all()?;

        Ok(Some(ChangesetAppend { path, original_len }))
    }

    fn import_matrix(&self, connection: &Connection) -> Result<usize> {
        let matrix_path = self.repo_root.join("docs/TEST_MATRIX.md");
        if !matrix_path.exists() {
            return Err(HarnessInfraError::MissingBrownfieldPath(
                matrix_path.display().to_string(),
            ));
        }

        let content = fs::read_to_string(matrix_path)?;
        let mut story_count = 0;
        let mut columns: Option<MatrixColumns> = None;

        for line in content.lines() {
            if !line.trim_start().starts_with('|') {
                continue;
            }

            let fields = markdown_table_fields(line);
            if fields.len() < 2 {
                continue;
            }

            if columns.is_none() {
                let candidate = MatrixColumns::from_header(&fields);
                if candidate.story.is_some() && candidate.status.is_some() {
                    columns = Some(candidate);
                }
                continue;
            }

            let columns = columns.as_ref().expect("matrix columns discovered");
            let id = field_at(&fields, columns.story).unwrap_or_default();
            let token = normalize_token(&id);
            if matches!(
                token.as_str(),
                "" | "story" | "tbd" | "todo" | "example" | "examples"
            ) || id.chars().all(|character| character == '-')
            {
                continue;
            }

            let mut title = field_at(&fields, columns.contract).unwrap_or_else(|| id.clone());
            if title.is_empty() {
                title = id.clone();
            }

            let status =
                normalize_story_status(&field_at(&fields, columns.status).unwrap_or_default());
            let unit = proof_from_cell(&field_at(&fields, columns.unit).unwrap_or_default());
            let integration =
                proof_from_cell(&field_at(&fields, columns.integration).unwrap_or_default());
            let e2e = proof_from_cell(&field_at(&fields, columns.e2e).unwrap_or_default());
            let platform =
                proof_from_cell(&field_at(&fields, columns.platform).unwrap_or_default());
            let evidence = columns
                .evidence
                .and_then(|index| evidence_from_fields(&fields, index));

            connection.execute(
                "INSERT INTO story (
                    id, title, risk_lane, contract_doc, status,
                    unit_proof, integration_proof, e2e_proof, platform_proof,
                    evidence, notes
                 ) VALUES (?1, ?2, 'high_risk', ?3, ?4, ?5, ?6, ?7, ?8, ?9,
                    'Imported from docs/TEST_MATRIX.md by harness import brownfield.'
                 )
                 ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    contract_doc=excluded.contract_doc,
                    status=excluded.status,
                    unit_proof=excluded.unit_proof,
                    integration_proof=excluded.integration_proof,
                    e2e_proof=excluded.e2e_proof,
                    platform_proof=excluded.platform_proof,
                    evidence=excluded.evidence,
                    notes=excluded.notes;",
                params![
                    id,
                    title,
                    field_at(&fields, columns.contract),
                    status,
                    unit,
                    integration,
                    e2e,
                    platform,
                    evidence,
                ],
            )?;
            story_count += 1;
        }

        Ok(story_count)
    }

    fn import_decisions(&self, connection: &Connection) -> Result<usize> {
        let decisions_dir = self.repo_root.join("docs/decisions");
        if !decisions_dir.is_dir() {
            return Err(HarnessInfraError::MissingBrownfieldPath(
                decisions_dir.display().to_string(),
            ));
        }

        let mut files = Vec::new();
        for entry in fs::read_dir(&decisions_dir)? {
            let entry = entry?;
            let path = entry.path();
            if path.extension().and_then(|value| value.to_str()) != Some("md") {
                continue;
            }
            let Some(file_name) = path.file_name().and_then(|value| value.to_str()) else {
                continue;
            };
            if is_decision_file_name(file_name) {
                files.push(path);
            }
        }
        files.sort();

        let mut decision_count = 0;
        for path in files {
            let content = fs::read_to_string(&path)?;
            let stem = path
                .file_stem()
                .and_then(|value| value.to_str())
                .unwrap_or_default()
                .to_owned();
            let title = content
                .lines()
                .next()
                .and_then(|line| line.strip_prefix("# "))
                .map(str::trim)
                .filter(|value| !value.is_empty())
                .unwrap_or(&stem)
                .to_owned();
            let status =
                normalize_decision_status(&markdown_section_first_value(&content, "Status"));
            let doc_path = format!(
                "docs/decisions/{}",
                path.file_name()
                    .and_then(|value| value.to_str())
                    .unwrap_or_default()
            );

            connection.execute(
                "INSERT INTO decision (id, title, status, doc_path, notes)
                 VALUES (?1, ?2, ?3, ?4,
                    'Imported from docs/decisions by harness import brownfield.'
                 )
                 ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    status=excluded.status,
                    doc_path=excluded.doc_path,
                    notes=excluded.notes;",
                params![stem, title, status, doc_path],
            )?;
            decision_count += 1;
        }

        Ok(decision_count)
    }

    fn import_backlog(&self, connection: &Connection) -> Result<usize> {
        let backlog_path = self.repo_root.join("docs/HARNESS_BACKLOG.md");
        if !backlog_path.exists() {
            return Ok(0);
        }

        let content = fs::read_to_string(backlog_path)?;
        let items = backlog_items(&content);
        let mut imported = 0;
        for item in items {
            if item.title.is_empty() || item.title == "Short name." {
                continue;
            }

            let risk = if item.risk.is_empty() {
                None
            } else {
                RiskLane::from_str(&item.risk)
                    .ok()
                    .map(|value| value.as_db_value().to_owned())
            };
            let status = normalize_backlog_status(&item.status);
            let discovered = empty_to_none(item.discovered_while);
            let pain = empty_to_none(item.current_pain);
            let suggestion = empty_to_none(item.suggested_improvement);

            connection.execute(
                "INSERT INTO backlog (
                    title, discovered_while, current_pain, suggested_improvement,
                    risk, status, notes
                 )
                 SELECT ?1, ?2, ?3, ?4, ?5, ?6,
                    'Imported from docs/HARNESS_BACKLOG.md by harness import brownfield.'
                 WHERE NOT EXISTS (
                    SELECT 1 FROM backlog WHERE title=?1
                 );",
                params![item.title, discovered, pain, suggestion, risk, status],
            )?;
            imported += 1;
        }

        Ok(imported)
    }
}

impl HarnessRepository for SqliteHarnessRepository {
    fn init(&self) -> Result<InitResult> {
        if self.db_path.exists() {
            let connection = self.open_existing()?;
            let current = Self::schema_version(&connection).unwrap_or(0);
            if current == 0 {
                self.apply_schema_v1(&connection)?;
                self.apply_pending_migrations(&connection, 1)?;
                return Ok(InitResult::MigratedExisting {
                    db_path: self.db_path.clone(),
                });
            }

            return Ok(InitResult::Existing {
                db_path: self.db_path.clone(),
                version: current,
            });
        }

        let connection = self.open_or_create()?;
        self.apply_schema_v1(&connection)?;
        self.apply_pending_migrations(&connection, 1)?;
        Ok(InitResult::Created {
            db_path: self.db_path.clone(),
        })
    }

    fn migrate(&self) -> Result<MigrateResult> {
        let connection = self.open_existing()?;
        let current_version = Self::schema_version(&connection).unwrap_or(0);
        let applied = self.apply_pending_migrations(&connection, current_version)?;

        Ok(MigrateResult {
            current_version,
            applied,
        })
    }

    fn import_brownfield(&self) -> Result<BrownfieldImportResult> {
        let connection = self.open_existing()?;
        let stories = self.import_matrix(&connection)?;
        let decisions = self.import_decisions(&connection)?;
        let backlog_items = self.import_backlog(&connection)?;

        Ok(BrownfieldImportResult {
            stories,
            decisions,
            backlog_items,
        })
    }

    fn record_intake(&self, input: IntakeInput) -> Result<i64> {
        let mut connection = self.open_existing()?;
        self.with_logged_write(&mut connection, |transaction| {
            let input_type = input.input_type.as_db_value().to_owned();
            let risk_lane = input.risk_lane.as_db_value().to_owned();
            let risk_flags = input.risk_flags.as_json_text();
            let affected_docs = input.affected_docs.as_json_text();
            transaction.execute(
                "INSERT INTO intake (
                    input_type, summary, risk_lane, risk_flags, affected_docs, story_id, notes
                 ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7);",
                params![
                    input_type,
                    input.summary,
                    risk_lane,
                    risk_flags,
                    affected_docs,
                    input.story_id,
                    input.notes,
                ],
            )?;

            let id = transaction.last_insert_rowid();
            Ok((
                id,
                vec![json!({
                    "op": "intake.add",
                    "version": 1,
                    "id": id,
                    "payload": {
                        "input_type": input_type,
                        "summary": input.summary,
                        "risk_lane": risk_lane,
                        "risk_flags": risk_flags,
                        "affected_docs": affected_docs,
                        "story_id": input.story_id,
                        "notes": input.notes,
                    },
                })],
            ))
        })
    }

    fn add_story(&self, input: StoryAddInput) -> Result<()> {
        let mut connection = self.open_existing()?;
        self.with_logged_write(&mut connection, |transaction| {
            let risk_lane = input.risk_lane.as_db_value().to_owned();
            transaction.execute(
                "INSERT INTO story (id, title, risk_lane, contract_doc, verify_command, notes)
                 VALUES (?1, ?2, ?3, ?4, ?5, ?6);",
                params![
                    input.id,
                    input.title,
                    risk_lane,
                    input.contract_doc,
                    input.verify_command,
                    input.notes,
                ],
            )?;
            Ok((
                (),
                vec![json!({
                    "op": "story.add",
                    "version": 1,
                    "id": input.id,
                    "payload": {
                        "title": input.title,
                        "risk_lane": risk_lane,
                        "contract_doc": input.contract_doc,
                        "verify_command": input.verify_command,
                        "notes": input.notes,
                    },
                })],
            ))
        })
    }

    fn update_story(&self, input: StoryUpdateInput) -> Result<()> {
        if input.status.is_none()
            && input.evidence.is_none()
            && input.unit.is_none()
            && input.integration.is_none()
            && input.e2e.is_none()
            && input.platform.is_none()
            && input.verify_command.is_none()
        {
            return Err(HarnessInfraError::EmptyStoryUpdate);
        }

        let mut connection = self.open_existing()?;
        self.with_logged_write(&mut connection, |transaction| {
            let unit = input.unit.map(|value| value.0);
            let integration = input.integration.map(|value| value.0);
            let e2e = input.e2e.map(|value| value.0);
            let platform = input.platform.map(|value| value.0);
            transaction.execute(
                "UPDATE story SET
                    status=COALESCE(?1, status),
                    evidence=COALESCE(?2, evidence),
                    unit_proof=COALESCE(?3, unit_proof),
                    integration_proof=COALESCE(?4, integration_proof),
                    e2e_proof=COALESCE(?5, e2e_proof),
                    platform_proof=COALESCE(?6, platform_proof),
                    verify_command=COALESCE(?7, verify_command)
                 WHERE id=?8;",
                params![
                    input.status,
                    input.evidence,
                    unit,
                    integration,
                    e2e,
                    platform,
                    input.verify_command,
                    input.id,
                ],
            )?;

            if transaction.changes() == 0 {
                return Err(HarnessInfraError::StoryNotFound(input.id));
            }
            Ok((
                (),
                vec![json!({
                    "op": "story.update",
                    "version": 1,
                    "id": input.id,
                    "payload": {
                        "status": input.status,
                        "evidence": input.evidence,
                        "unit_proof": unit,
                        "integration_proof": integration,
                        "e2e_proof": e2e,
                        "platform_proof": platform,
                        "verify_command": input.verify_command,
                    },
                })],
            ))
        })
    }

    fn add_story_dependency(&self, input: StoryDependencyInput) -> Result<bool> {
        if input.blocker == input.blocked {
            return Err(HarnessInfraError::StoryDependencySelf(input.blocker));
        }

        let mut connection = self.open_existing()?;
        self.with_logged_write(&mut connection, |transaction| {
            ensure_story_exists(transaction, &input.blocker)?;
            ensure_story_exists(transaction, &input.blocked)?;
            if dependency_path_exists(transaction, &input.blocked, &input.blocker)? {
                return Err(HarnessInfraError::StoryDependencyCycle(
                    input.blocker,
                    input.blocked,
                ));
            }
            let changed = transaction.execute(
                "INSERT INTO story_dependency (story_id, blocks_story_id) VALUES (?1, ?2)
                 ON CONFLICT(story_id, blocks_story_id) DO NOTHING;",
                params![input.blocker, input.blocked],
            )? > 0;
            let operations = if changed {
                vec![json!({
                    "op": "story.dependency.add",
                    "version": 1,
                    "id": input.blocker,
                    "payload": { "blocked": input.blocked },
                })]
            } else {
                Vec::new()
            };
            Ok((changed, operations))
        })
    }

    fn remove_story_dependency(&self, input: StoryDependencyInput) -> Result<bool> {
        let mut connection = self.open_existing()?;
        self.with_logged_write(&mut connection, |transaction| {
            let changed = transaction.execute(
                "DELETE FROM story_dependency WHERE story_id=?1 AND blocks_story_id=?2;",
                params![input.blocker, input.blocked],
            )? > 0;
            let operations = if changed {
                vec![json!({
                    "op": "story.dependency.remove",
                    "version": 1,
                    "id": input.blocker,
                    "payload": { "blocked": input.blocked },
                })]
            } else {
                Vec::new()
            };
            Ok((changed, operations))
        })
    }

    fn query_story_dependencies(&self, story: Option<&str>) -> Result<Vec<StoryDependencyRecord>> {
        let connection = self.open_existing()?;
        let mut statement = connection.prepare(
            "SELECT story_id, blocks_story_id FROM story_dependency
             WHERE (?1 IS NULL OR story_id=?1 OR blocks_story_id=?1)
             ORDER BY story_id, blocks_story_id;",
        )?;
        let rows = statement.query_map(params![story], |row| {
            Ok(StoryDependencyRecord {
                blocker: row.get(0)?,
                blocked: row.get(1)?,
            })
        })?;
        collect_rows(rows)
    }

    fn verify_story(&self, id: &str) -> Result<StoryVerifyResult> {
        let mut connection = self.open_existing()?;
        let verify_command = connection
            .query_row(
                "SELECT verify_command FROM story WHERE id=?1;",
                params![id],
                |row| row.get::<_, Option<String>>(0),
            )
            .optional()?
            .flatten()
            .filter(|value| !value.is_empty())
            .ok_or_else(|| HarnessInfraError::MissingStoryVerifyCommand(id.to_owned()))?;

        let (shell, flag) = verifier_shell();
        let output = Command::new(shell)
            .arg(flag)
            .arg(&verify_command)
            .current_dir(&self.repo_root)
            .output()?;
        let result = if output.status.success() {
            "pass"
        } else {
            "fail"
        }
        .to_owned();
        self.with_logged_write(&mut connection, |transaction| {
            transaction.execute(
                "UPDATE story
                 SET last_verified_at=datetime('now'), last_verified_result=?1
                 WHERE id=?2;",
                params![result, id],
            )?;
            Ok((
                (),
                vec![json!({
                    "op": "story.verify",
                    "version": 1,
                    "id": id,
                    "payload": {
                        "result": result,
                    },
                })],
            ))
        })?;

        Ok(StoryVerifyResult {
            command: verify_command,
            stdout: String::from_utf8_lossy(&output.stdout).into_owned(),
            stderr: String::from_utf8_lossy(&output.stderr).into_owned(),
            result,
        })
    }

    fn verify_all_stories(&self) -> Result<StoryVerifyAllResult> {
        let mut connection = self.open_existing()?;
        let mut statement =
            connection.prepare("SELECT id, title, verify_command FROM story ORDER BY id;")?;
        let story_rows = statement.query_map([], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, Option<String>>(2)?,
            ))
        })?;
        let stories = collect_rows(story_rows)?;
        drop(statement);
        let mut items = Vec::new();

        for (id, title, verify_command) in stories {
            let Some(command) = verify_command.filter(|value| !value.trim().is_empty()) else {
                items.push(StoryVerifyAllItem {
                    id,
                    title,
                    command: None,
                    result: "skipped".to_owned(),
                    stdout: String::new(),
                    stderr: String::new(),
                });
                continue;
            };

            let (shell, flag) = verifier_shell();
            let output = Command::new(shell)
                .arg(flag)
                .arg(&command)
                .current_dir(&self.repo_root)
                .output()?;
            let result = if output.status.success() {
                "pass"
            } else {
                "fail"
            }
            .to_owned();
            self.with_logged_write(&mut connection, |transaction| {
                transaction.execute(
                    "UPDATE story
                     SET last_verified_at=datetime('now'), last_verified_result=?1
                     WHERE id=?2;",
                    params![result, id],
                )?;
                Ok((
                    (),
                    vec![json!({
                        "op": "story.verify",
                        "version": 1,
                        "id": id,
                        "payload": {
                            "result": result,
                        },
                    })],
                ))
            })?;
            items.push(StoryVerifyAllItem {
                id,
                title,
                command: Some(command),
                result,
                stdout: String::from_utf8_lossy(&output.stdout).into_owned(),
                stderr: String::from_utf8_lossy(&output.stderr).into_owned(),
            });
        }

        Ok(StoryVerifyAllResult { items })
    }

    fn add_decision(&self, input: DecisionAddInput) -> Result<()> {
        let mut connection = self.open_existing()?;
        self.with_logged_write(&mut connection, |transaction| {
            transaction.execute(
                "INSERT INTO decision (id, title, status, doc_path, verify_command, predicted_impact, notes)
                 VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7);",
                params![
                    input.id,
                    input.title,
                    input.status,
                    input.doc_path,
                    input.verify_command,
                    input.predicted_impact,
                    input.notes,
                ],
            )?;
            Ok((
                (),
                vec![json!({
                    "op": "decision.add",
                    "version": 1,
                    "id": input.id,
                    "payload": {
                        "title": input.title,
                        "status": input.status,
                        "doc_path": input.doc_path,
                        "verify_command": input.verify_command,
                        "predicted_impact": input.predicted_impact,
                        "notes": input.notes,
                    },
                })],
            ))
        })
    }

    fn verify_decision(&self, id: &str) -> Result<DecisionVerifyResult> {
        let mut connection = self.open_existing()?;
        let verify_command = connection
            .query_row(
                "SELECT verify_command FROM decision WHERE id=?1;",
                params![id],
                |row| row.get::<_, Option<String>>(0),
            )
            .optional()?
            .flatten()
            .filter(|value| !value.is_empty())
            .ok_or_else(|| HarnessInfraError::MissingDecisionVerifyCommand(id.to_owned()))?;

        let (shell, flag) = verifier_shell();
        let status = Command::new(shell)
            .arg(flag)
            .arg(&verify_command)
            .current_dir(&self.repo_root)
            .status()?;
        let result = if status.success() { "pass" } else { "fail" }.to_owned();
        self.with_logged_write(&mut connection, |transaction| {
            transaction.execute(
                "UPDATE decision
                 SET last_verified_at=datetime('now'), last_verified_result=?1
                 WHERE id=?2;",
                params![result, id],
            )?;
            Ok((
                (),
                vec![json!({
                    "op": "decision.verify",
                    "version": 1,
                    "id": id,
                    "payload": {
                        "result": result,
                    },
                })],
            ))
        })?;

        Ok(DecisionVerifyResult {
            command: verify_command,
            result,
        })
    }

    fn add_backlog(&self, input: BacklogAddInput) -> Result<i64> {
        let mut connection = self.open_existing()?;
        self.with_logged_write(&mut connection, |transaction| {
            let risk = input.risk.map(|value| value.as_db_value().to_owned());
            transaction.execute(
                "INSERT INTO backlog (
                    title, discovered_while, current_pain, suggested_improvement,
                    risk, predicted_impact, notes
                 ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7);",
                params![
                    input.title,
                    input.discovered_while,
                    input.current_pain,
                    input.suggestion,
                    risk,
                    input.predicted_impact,
                    input.notes,
                ],
            )?;
            let id = transaction.last_insert_rowid();
            Ok((
                id,
                vec![json!({
                    "op": "backlog.add",
                    "version": 1,
                    "id": id,
                    "payload": {
                        "title": input.title,
                        "discovered_while": input.discovered_while,
                        "current_pain": input.current_pain,
                        "suggested_improvement": input.suggestion,
                        "risk": risk,
                        "predicted_impact": input.predicted_impact,
                        "notes": input.notes,
                    },
                })],
            ))
        })
    }

    fn close_backlog(&self, input: BacklogCloseInput) -> Result<()> {
        let mut connection = self.open_existing()?;
        self.with_logged_write(&mut connection, |transaction| {
            transaction.execute(
                "UPDATE backlog
                 SET status=?1, actual_outcome=?2, implemented_at=datetime('now')
                 WHERE id=?3;",
                params![input.status, input.actual_outcome, input.id],
            )?;

            if transaction.changes() == 0 {
                return Err(HarnessInfraError::BacklogNotFound(input.id));
            }
            Ok((
                (),
                vec![json!({
                    "op": "backlog.close",
                    "version": 1,
                    "id": input.id,
                    "payload": {
                        "status": input.status,
                        "actual_outcome": input.actual_outcome,
                    },
                })],
            ))
        })
    }

    fn register_tool(&self, input: ToolRegisterInput) -> Result<()> {
        validate_tool_description(&input.description)?;
        // Only exec-probed kinds are PATH-checked at register time. mcp/skill/http
        // are not on PATH by nature, so registering intent always succeeds; their
        // presence is resolved later by `tool check` via scan_target.
        let exec_probed = matches!(input.kind.as_str(), "cli" | "binary");
        if exec_probed && !input.force && !command_available(&self.repo_root, &input.command) {
            return Err(HarnessInfraError::ToolCommandNotFound(input.command));
        }

        let mut connection = self.open_existing()?;
        let existing = connection
            .query_row(
                "SELECT command FROM tool WHERE name=?1;",
                params![input.name],
                |row| row.get::<_, String>(0),
            )
            .optional()?;
        if let Some(command) = existing {
            return Err(HarnessInfraError::ToolAlreadyExists(input.name, command));
        }

        self.with_logged_write(&mut connection, |transaction| {
            let args_json = tool_args_json(&input.args);
            transaction.execute(
                "INSERT INTO tool
                    (name, provider, command, description, args, responsibility, since,
                     kind, capability, scan_target, status)
                 VALUES (?1, 'custom', ?2, ?3, ?4, ?5, 'registered', ?6, ?7, ?8, 'unknown');",
                params![
                    input.name,
                    input.command,
                    input.description,
                    args_json,
                    input.responsibility,
                    input.kind,
                    input.capability,
                    input.scan_target,
                ],
            )?;
            Ok((
                (),
                vec![json!({
                    "op": "tool.register",
                    "version": 1,
                    "id": input.name,
                    "payload": {
                        "command": input.command,
                        "description": input.description,
                        "args": args_json,
                        "responsibility": input.responsibility,
                        "kind": input.kind,
                        "capability": input.capability,
                        "scan_target": input.scan_target,
                    },
                })],
            ))
        })
    }

    fn remove_tool(&self, name: &str) -> Result<()> {
        let mut connection = self.open_existing()?;
        self.with_logged_write(&mut connection, |transaction| {
            transaction.execute("DELETE FROM tool WHERE name=?1;", params![name])?;
            if transaction.changes() == 0 {
                return Err(HarnessInfraError::ToolNotFound(name.to_owned()));
            }
            Ok((
                (),
                vec![json!({
                    "op": "tool.remove",
                    "version": 1,
                    "id": name,
                    "payload": {},
                })],
            ))
        })
    }

    fn check_tools(&self, name: Option<String>) -> Result<Vec<ToolCheckResult>> {
        let mut connection = self.open_existing()?;
        let mut statement = connection.prepare(
            "SELECT name, kind, command, scan_target, capability FROM tool
             WHERE (?1 IS NULL OR name = ?1)
             ORDER BY name;",
        )?;
        let rows = statement.query_map(params![name], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, String>(2)?,
                row.get::<_, Option<String>>(3)?,
                row.get::<_, Option<String>>(4)?,
            ))
        })?;
        let tools = collect_rows(rows)?;
        drop(statement);

        let mut results = Vec::with_capacity(tools.len());
        for (name, kind, command, scan_target, capability) in tools {
            let (status, detail) =
                scan_tool_status(&self.repo_root, &kind, &command, scan_target.as_deref());
            self.with_logged_write(&mut connection, |transaction| {
                transaction.execute(
                    "UPDATE tool SET status=?1, checked_at=datetime('now') WHERE name=?2;",
                    params![status, name],
                )?;
                Ok((
                    (),
                    vec![json!({
                        "op": "tool.check",
                        "version": 1,
                        "id": name,
                        "payload": {
                            "status": status,
                            "detail": detail,
                        },
                    })],
                ))
            })?;
            results.push(ToolCheckResult {
                name,
                kind,
                capability,
                status: status.to_owned(),
                detail,
            });
        }
        Ok(results)
    }

    fn add_intervention(&self, input: InterventionAddInput) -> Result<i64> {
        let mut connection = self.open_existing()?;
        self.with_logged_write(&mut connection, |transaction| {
            transaction.execute(
                "INSERT INTO intervention (trace_id, story_id, type, description, source, impact)
                 VALUES (?1, ?2, ?3, ?4, ?5, ?6);",
                params![
                    input.trace_id,
                    input.story_id,
                    input.intervention_type,
                    input.description,
                    input.source,
                    input.impact,
                ],
            )?;
            let id = transaction.last_insert_rowid();
            Ok((
                id,
                vec![json!({
                    "op": "intervention.add",
                    "version": 1,
                    "id": id,
                    "payload": {
                        "trace_id": input.trace_id,
                        "story_id": input.story_id,
                        "type": input.intervention_type,
                        "description": input.description,
                        "source": input.source,
                        "impact": input.impact,
                    },
                })],
            ))
        })
    }

    fn record_trace(&self, input: TraceInput) -> Result<i64> {
        let mut connection = self.open_existing()?;
        self.with_logged_write(&mut connection, |transaction| {
            let actions = input.actions.as_json_text();
            let files_read = input.files_read.as_json_text();
            let files_changed = input.files_changed.as_json_text();
            let decisions = input.decisions.as_json_text();
            let errors = input.errors.as_json_text();
            transaction.execute(
                "INSERT INTO trace (
                    task_summary, intake_id, story_id, agent,
                    actions_taken, files_read, files_changed, decisions_made, errors,
                    outcome, duration_seconds, token_estimate, harness_friction, notes
                 ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14);",
                params![
                    input.task_summary,
                    input.intake_id,
                    input.story_id,
                    input.agent,
                    actions,
                    files_read,
                    files_changed,
                    decisions,
                    errors,
                    input.outcome,
                    input.duration_seconds,
                    input.token_estimate,
                    input.friction,
                    input.notes,
                ],
            )?;
            let id = transaction.last_insert_rowid();
            Ok((
                id,
                vec![json!({
                    "op": "trace.add",
                    "version": 1,
                    "id": id,
                    "payload": {
                        "task_summary": input.task_summary,
                        "intake_id": input.intake_id,
                        "story_id": input.story_id,
                        "agent": input.agent,
                        "actions_taken": actions,
                        "files_read": files_read,
                        "files_changed": files_changed,
                        "decisions_made": decisions,
                        "errors": errors,
                        "outcome": input.outcome,
                        "duration_seconds": input.duration_seconds,
                        "token_estimate": input.token_estimate,
                        "harness_friction": input.friction,
                        "notes": input.notes,
                    },
                })],
            ))
        })
    }

    fn score_trace(&self, id: Option<i64>) -> Result<TraceScoreResult> {
        let connection = self.open_existing()?;
        let sql = match id {
            Some(_) => {
                "SELECT
                    trace.id,
                    trace.task_summary,
                    trace.intake_id,
                    intake.risk_lane,
                    trace.agent,
                    trace.actions_taken,
                    trace.files_read,
                    trace.files_changed,
                    trace.decisions_made,
                    trace.errors,
                    trace.outcome,
                    trace.duration_seconds,
                    trace.token_estimate,
                    trace.harness_friction,
                    trace.notes
                 FROM trace
                 LEFT JOIN intake ON intake.id = trace.intake_id
                 WHERE trace.id = ?1"
            }
            None => {
                "SELECT
                    trace.id,
                    trace.task_summary,
                    trace.intake_id,
                    intake.risk_lane,
                    trace.agent,
                    trace.actions_taken,
                    trace.files_read,
                    trace.files_changed,
                    trace.decisions_made,
                    trace.errors,
                    trace.outcome,
                    trace.duration_seconds,
                    trace.token_estimate,
                    trace.harness_friction,
                    trace.notes
                 FROM trace
                 LEFT JOIN intake ON intake.id = trace.intake_id
                 ORDER BY trace.id DESC
                 LIMIT 1"
            }
        };

        let source = if let Some(id) = id {
            connection
                .query_row(sql, params![id], trace_score_source_from_row)
                .optional()?
                .ok_or(HarnessInfraError::TraceNotFound(id))?
        } else {
            connection
                .query_row(sql, [], trace_score_source_from_row)
                .optional()?
                .ok_or(HarnessInfraError::NoTraces)?
        };

        Ok(score_trace(source))
    }

    fn score_context(&self, id: i64) -> Result<ContextScoreResult> {
        let connection = self.open_existing()?;
        let source = connection
            .query_row(
                "SELECT
                    trace.id,
                    intake.risk_lane,
                    trace.story_id,
                    trace.files_read,
                    trace.files_changed,
                    trace.outcome
                 FROM trace
                 LEFT JOIN intake ON intake.id = trace.intake_id
                 WHERE trace.id=?1;",
                params![id],
                |row| {
                    Ok(ContextScoreSource {
                        id: row.get(0)?,
                        risk_lane: row.get(1)?,
                        story_id: row.get(2)?,
                        files_read: row.get(3)?,
                        files_changed: row.get(4)?,
                        outcome: row.get(5)?,
                    })
                },
            )
            .optional()?
            .ok_or(HarnessInfraError::TraceNotFound(id))?;

        Ok(score_context(source))
    }

    fn story_verify_status(&self, id: &str) -> Result<StoryVerifyStatus> {
        let connection = self.open_existing()?;
        connection
            .query_row(
                "SELECT id, verify_command, last_verified_result FROM story WHERE id=?1;",
                params![id],
                |row| {
                    Ok(StoryVerifyStatus {
                        id: row.get(0)?,
                        verify_command: row.get(1)?,
                        last_verified_result: row.get(2)?,
                    })
                },
            )
            .optional()?
            .ok_or_else(|| HarnessInfraError::StoryNotFound(id.to_owned()))
    }

    fn query_matrix(&self) -> Result<Vec<StoryMatrixRecord>> {
        let connection = self.open_existing()?;
        let mut statement = connection.prepare(
            "SELECT id, title, status, unit_proof, integration_proof, e2e_proof, platform_proof, evidence
             FROM story ORDER BY id;",
        )?;

        let rows = statement.query_map([], |row| {
            Ok(StoryMatrixRecord {
                id: row.get(0)?,
                title: row.get(1)?,
                status: row.get(2)?,
                unit: row.get(3)?,
                integration: row.get(4)?,
                e2e: row.get(5)?,
                platform: row.get(6)?,
                evidence: row.get(7)?,
            })
        })?;

        collect_rows(rows)
    }

    fn query_backlog(&self, filter: BacklogFilter) -> Result<Vec<BacklogRecord>> {
        let connection = self.open_existing()?;
        let where_clause = match filter {
            BacklogFilter::All => "",
            BacklogFilter::Open => "WHERE status IN ('proposed', 'accepted')",
            BacklogFilter::Closed => "WHERE status IN ('implemented', 'rejected')",
        };
        let sql = format!(
            "SELECT id, title, status, risk, predicted_impact, actual_outcome
             FROM backlog {where_clause} ORDER BY status, id;"
        );
        let mut statement = connection.prepare(&sql)?;

        let rows = statement.query_map([], |row| {
            Ok(BacklogRecord {
                id: row.get(0)?,
                title: row.get(1)?,
                status: row.get(2)?,
                risk: row.get(3)?,
                predicted_impact: row.get(4)?,
                actual_outcome: row.get(5)?,
            })
        })?;

        collect_rows(rows)
    }

    fn query_decisions(&self) -> Result<Vec<DecisionRecord>> {
        let connection = self.open_existing()?;
        let mut statement = connection.prepare(
            "SELECT id, title, status, last_verified_at, last_verified_result
             FROM decision ORDER BY id;",
        )?;

        let rows = statement.query_map([], |row| {
            Ok(DecisionRecord {
                id: row.get(0)?,
                title: row.get(1)?,
                status: row.get(2)?,
                last_verified_at: row.get(3)?,
                last_verified_result: row.get(4)?,
            })
        })?;

        collect_rows(rows)
    }

    fn query_intakes(&self) -> Result<Vec<IntakeRecord>> {
        let connection = self.open_existing()?;
        let mut statement = connection.prepare(
            "SELECT id, created_at, input_type, risk_lane, summary
             FROM intake ORDER BY id DESC LIMIT 20;",
        )?;

        let rows = statement.query_map([], |row| {
            Ok(IntakeRecord {
                id: row.get(0)?,
                created_at: row.get(1)?,
                input_type: row.get(2)?,
                risk_lane: row.get(3)?,
                summary: row.get(4)?,
            })
        })?;

        collect_rows(rows)
    }

    fn query_traces(&self) -> Result<Vec<TraceRecord>> {
        let connection = self.open_existing()?;
        let mut statement = connection.prepare(
            "SELECT id, created_at, outcome, task_summary, harness_friction
             FROM trace ORDER BY id DESC LIMIT 20;",
        )?;

        let rows = statement.query_map([], |row| {
            Ok(TraceRecord {
                id: row.get(0)?,
                created_at: row.get(1)?,
                outcome: row.get(2)?,
                task_summary: row.get(3)?,
                harness_friction: row.get(4)?,
            })
        })?;

        collect_rows(rows)
    }

    fn query_friction(&self) -> Result<Vec<FrictionRecord>> {
        let connection = self.open_existing()?;
        let mut statement = connection.prepare(
            "SELECT
                trace.id,
                trace.created_at,
                intake.risk_lane,
                intake.input_type,
                trace.task_summary,
                trace.harness_friction
             FROM trace
             LEFT JOIN intake ON intake.id = trace.intake_id
             WHERE trace.harness_friction IS NOT NULL
             ORDER BY trace.id DESC;",
        )?;

        let rows = statement.query_map([], |row| {
            Ok(FrictionRecord {
                id: row.get(0)?,
                created_at: row.get(1)?,
                risk_lane: row.get(2)?,
                input_type: row.get(3)?,
                task_summary: row.get(4)?,
                harness_friction: row.get(5)?,
            })
        })?;

        collect_rows(rows)
    }

    fn query_tools(
        &self,
        responsibility: Option<String>,
        capability: Option<String>,
    ) -> Result<Vec<ToolEntry>> {
        let connection = self.open_existing()?;
        let mut tools = compiled_tool_registry();
        let mut statement = connection.prepare(
            "SELECT provider, name, command, description, args, responsibility, since,
                    kind, capability, scan_target, status, checked_at
             FROM tool ORDER BY name;",
        )?;
        let rows = statement.query_map([], |row| {
            Ok(ToolEntry {
                provider: row.get(0)?,
                name: row.get(1)?,
                command: row.get(2)?,
                description: row.get(3)?,
                args: parse_stored_tool_args(row.get::<_, Option<String>>(4)?.as_deref()),
                responsibility: row.get(5)?,
                source: "registered".to_owned(),
                since: row.get(6)?,
                kind: row.get(7)?,
                capability: row.get(8)?,
                scan_target: row.get(9)?,
                status: row.get(10)?,
                checked_at: row.get(11)?,
            })
        })?;
        tools.extend(collect_rows(rows)?);
        if let Some(responsibility) = responsibility {
            let normalized = normalize_token(&responsibility);
            tools.retain(|tool| normalize_token(&tool.responsibility) == normalized);
        }
        if let Some(capability) = capability {
            let normalized = normalize_token(&capability);
            tools.retain(|tool| {
                tool.capability
                    .as_deref()
                    .is_some_and(|value| normalize_token(value) == normalized)
            });
        }
        Ok(tools)
    }

    fn query_interventions(&self, filter: InterventionFilter) -> Result<Vec<InterventionRecord>> {
        let connection = self.open_existing()?;
        let mut statement = connection.prepare(
            "SELECT id, created_at, trace_id, story_id, type, description, source, impact
             FROM intervention
             WHERE (?1 IS NULL OR trace_id = ?1)
               AND (?2 IS NULL OR story_id = ?2)
               AND (?3 IS NULL OR type = ?3)
             ORDER BY id DESC;",
        )?;
        let rows = statement.query_map(
            params![filter.trace_id, filter.story_id, filter.intervention_type],
            |row| {
                Ok(InterventionRecord {
                    id: row.get(0)?,
                    created_at: row.get(1)?,
                    trace_id: row.get(2)?,
                    story_id: row.get(3)?,
                    intervention_type: row.get(4)?,
                    description: row.get(5)?,
                    source: row.get(6)?,
                    impact: row.get(7)?,
                })
            },
        )?;
        collect_rows(rows)
    }

    fn query_stats(&self) -> Result<HarnessStats> {
        let connection = self.open_existing()?;
        connection
            .query_row(
                "SELECT
                    (SELECT COUNT(*) FROM intake) AS intakes,
                    (SELECT COUNT(*) FROM story) AS stories,
                    (SELECT COUNT(*) FROM decision) AS decisions,
                    (SELECT COUNT(*) FROM backlog) AS backlog_items,
                    (SELECT COUNT(*) FROM trace) AS traces;",
                [],
                |row| {
                    Ok(HarnessStats {
                        intakes: row.get(0)?,
                        stories: row.get(1)?,
                        decisions: row.get(2)?,
                        backlog_items: row.get(3)?,
                        traces: row.get(4)?,
                    })
                },
            )
            .map_err(HarnessInfraError::from)
    }

    fn audit(&self) -> Result<AuditResult> {
        let connection = self.open_existing()?;
        let mut result = AuditResult {
            orphaned_stories: audit_findings(
                &connection,
                "SELECT story.id, story.title
                 FROM story
                 LEFT JOIN trace ON trace.story_id = story.id
                 WHERE story.status IN ('planned','in_progress') AND trace.id IS NULL
                 ORDER BY story.id;",
            )?,
            unverified_stories: audit_findings(
                &connection,
                "SELECT id, title FROM story
                 WHERE verify_command IS NOT NULL
                   AND TRIM(verify_command) <> ''
                   AND last_verified_result IS NULL
                   AND status <> 'retired'
                 ORDER BY id;",
            )?,
            unverified_decisions: audit_findings(
                &connection,
                "SELECT id, title FROM decision
                 WHERE verify_command IS NOT NULL
                   AND TRIM(verify_command) <> ''
                   AND last_verified_result IS NULL
                 ORDER BY id;",
            )?,
            backlog_without_outcomes: audit_findings(
                &connection,
                "SELECT CAST(id AS TEXT), title FROM backlog
                 WHERE predicted_impact IS NOT NULL
                   AND actual_outcome IS NULL
                   AND status='implemented'
                 ORDER BY id;",
            )?,
            stale_stories: audit_findings(
                &connection,
                "SELECT story.id, story.title
                 FROM story
                 JOIN trace ON trace.story_id = story.id
                 WHERE story.status <> 'implemented'
                 GROUP BY story.id, story.title
                 HAVING julianday('now') - julianday(MAX(trace.created_at)) > 30
                 ORDER BY story.id;",
            )?,
            broken_tools: Vec::new(),
        };

        let mut statement =
            connection.prepare("SELECT name, command, kind, status FROM tool ORDER BY name;")?;
        let rows = statement.query_map([], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, String>(2)?,
                row.get::<_, String>(3)?,
            ))
        })?;
        for (name, command, kind, status) in collect_rows(rows)? {
            // Exec-probed kinds are checked live against PATH. Scanned kinds
            // (mcp/skill/http) are only "broken" once a scan has positively
            // found them missing; an un-scanned `unknown` is not drift.
            let broken = match kind.as_str() {
                "cli" | "binary" => !command_available(&self.repo_root, &command),
                _ => status == "missing",
            };
            if broken {
                result.broken_tools.push(AuditFinding {
                    id: name,
                    title: command,
                });
            }
        }
        Ok(result)
    }

    fn propose(&self, commit: bool) -> Result<Vec<ImprovementProposal>> {
        let connection = self.open_existing()?;
        let audit = self.audit()?;
        let mut proposals = Vec::new();

        for (text, count) in repeated_friction(&connection)? {
            if validation_provider_friction_resolved(&connection, &text)? {
                continue;
            }
            proposals.push(ImprovementProposal {
                title: format!("Reduce repeated friction: {}", short_title(&text)),
                component: "Failure attribution".to_owned(),
                evidence: format!("{count} traces recorded similar friction: {text}"),
                predicted_impact: "Fewer repeated harness friction entries for similar tasks.".to_owned(),
                risk: "normal".to_owned(),
                suggested_action: "Update the relevant Harness docs, templates, or CLI guidance for this friction pattern.".to_owned(),
                validation_plan: "Review the next five related traces and compare friction frequency.".to_owned(),
                confidence: confidence_for_count(count),
                committed_backlog_id: None,
            });
        }

        for (key, count) in repeated_interventions(&connection)? {
            proposals.push(ImprovementProposal {
                title: format!("Address repeated intervention: {}", short_title(&key)),
                component: "Intervention recording".to_owned(),
                evidence: format!("{count} interventions share the pattern: {key}"),
                predicted_impact: "Fewer repeated human or review interventions for the same issue.".to_owned(),
                risk: "normal".to_owned(),
                suggested_action: "Clarify the relevant operating rule or validation gate that would have caught this earlier.".to_owned(),
                validation_plan: "Future interventions of this type should decrease after the rule change.".to_owned(),
                confidence: confidence_for_count(count),
                committed_backlog_id: None,
            });
        }

        for (category, count) in [
            (
                "orphaned planned or in-progress stories",
                audit.orphaned_stories.len(),
            ),
            ("unverified story commands", audit.unverified_stories.len()),
            (
                "unverified decision commands",
                audit.unverified_decisions.len(),
            ),
            (
                "implemented backlog items without outcomes",
                audit.backlog_without_outcomes.len(),
            ),
            ("stale unfinished stories", audit.stale_stories.len()),
            ("broken registered tools", audit.broken_tools.len()),
        ] {
            if count > 0 {
                proposals.push(ImprovementProposal {
                    title: format!("Clean up {category}"),
                    component: "Entropy auditing".to_owned(),
                    evidence: format!("Audit found {count} {category}."),
                    predicted_impact: "Lower entropy score and stronger completion evidence.".to_owned(),
                    risk: "tiny".to_owned(),
                    suggested_action: "Resolve the listed audit findings or record why they are intentionally retained.".to_owned(),
                    validation_plan: "Run harness-cli audit and confirm the category count decreases.".to_owned(),
                    confidence: "low".to_owned(),
                    committed_backlog_id: None,
                });
            }
        }

        if commit {
            for proposal in &mut proposals {
                connection.execute(
                    "INSERT INTO backlog (
                        title, discovered_while, current_pain, suggested_improvement,
                        risk, predicted_impact, notes
                     ) VALUES (?1, 'harness-cli propose', ?2, ?3, ?4, ?5, ?6);",
                    params![
                        proposal.title,
                        proposal.evidence,
                        proposal.suggested_action,
                        normalize_token(&proposal.risk),
                        proposal.predicted_impact,
                        format!(
                            "component: {}; confidence: {}; validation: {}",
                            proposal.component, proposal.confidence, proposal.validation_plan
                        ),
                    ],
                )?;
                proposal.committed_backlog_id = Some(connection.last_insert_rowid());
            }
        }

        Ok(proposals)
    }

    fn apply_changeset(&self, path: &Path) -> Result<ChangesetApplyResult> {
        let content = fs::read_to_string(path)?;
        let mut operations = Vec::new();
        for (index, line) in content.lines().enumerate() {
            if line.trim().is_empty() {
                continue;
            }
            let value = serde_json::from_str::<Value>(line).map_err(|error| {
                HarnessInfraError::InvalidChangeset(format!(
                    "{} line {} is not valid JSON: {error}",
                    path.display(),
                    index + 1
                ))
            })?;
            operations.push(value);
        }

        let header = operations
            .first()
            .filter(|value| value.get("op").and_then(Value::as_str) == Some("changeset.header"))
            .ok_or_else(|| {
                HarnessInfraError::InvalidChangeset(
                    "first operation must be changeset.header".to_owned(),
                )
            })?;
        let id = required_string(header, "run_id")?;

        self.migrate()?;
        let mut connection = self.open_existing()?;
        let already_applied = connection
            .query_row(
                "SELECT 1 FROM changeset_applied WHERE id=?1;",
                params![id],
                |_| Ok(()),
            )
            .optional()?
            .is_some();
        if already_applied {
            return Ok(ChangesetApplyResult {
                id,
                applied: false,
                operations: 0,
            });
        }

        let transaction = connection.transaction()?;
        let mut context = ChangesetApplyContext::default();
        let mut applied_operations = 0usize;
        for operation in operations.iter().skip(1) {
            apply_changeset_operation(&transaction, operation, &mut context)?;
            applied_operations += 1;
        }
        transaction.execute(
            "INSERT INTO changeset_applied (id, path) VALUES (?1, ?2);",
            params![id, path.display().to_string()],
        )?;
        transaction.commit()?;

        Ok(ChangesetApplyResult {
            id,
            applied: true,
            operations: applied_operations,
        })
    }

    fn rebuild_db(&self, changeset_dir: &Path) -> Result<DbRebuildResult> {
        if self.db_path.exists() {
            return Err(HarnessInfraError::RebuildDatabaseExists(
                self.db_path.display().to_string(),
            ));
        }

        self.init()?;

        let mut changesets = Vec::new();
        if changeset_dir.exists() {
            for entry in fs::read_dir(changeset_dir)? {
                let entry = entry?;
                let path = entry.path();
                let is_changeset = path
                    .file_name()
                    .and_then(|value| value.to_str())
                    .is_some_and(|value| value.ends_with(".changeset.jsonl"));
                if is_changeset {
                    changesets.push(path);
                }
            }
        }
        changesets.sort();

        let mut applied_count = 0usize;
        let mut operation_count = 0usize;
        for changeset in changesets {
            let result = self.apply_changeset(&changeset)?;
            if result.applied {
                applied_count += 1;
                operation_count += result.operations;
            }
        }

        Ok(DbRebuildResult {
            db_path: self.db_path.clone(),
            changesets: applied_count,
            operations: operation_count,
        })
    }

    fn query_sql(&self, sql: &str) -> Result<QueryTable> {
        let connection = self.open_existing()?;
        let mut statement = connection.prepare(sql)?;
        let headers = statement
            .column_names()
            .iter()
            .map(|value| value.to_string())
            .collect::<Vec<_>>();
        let column_count = statement.column_count();
        let rows = statement.query_map([], |row| {
            let mut values = Vec::new();
            for index in 0..column_count {
                values.push(sql_value_to_string(row.get_ref(index)?));
            }
            Ok(values)
        })?;

        Ok(QueryTable {
            headers,
            rows: collect_rows(rows)?,
        })
    }
}

impl From<HarnessContext> for SqliteHarnessRepository {
    fn from(context: HarnessContext) -> Self {
        Self::new(context.repo_root, context.db_path, context.schema_dir)
    }
}

#[derive(Debug)]
struct MatrixColumns {
    story: Option<usize>,
    contract: Option<usize>,
    unit: Option<usize>,
    integration: Option<usize>,
    e2e: Option<usize>,
    platform: Option<usize>,
    status: Option<usize>,
    evidence: Option<usize>,
}

#[derive(Debug, Default)]
struct BacklogMarkdownItem {
    title: String,
    discovered_while: String,
    current_pain: String,
    suggested_improvement: String,
    risk: String,
    status: String,
}

impl MatrixColumns {
    fn from_header(fields: &[String]) -> Self {
        let mut columns = Self {
            story: None,
            contract: None,
            unit: None,
            integration: None,
            e2e: None,
            platform: None,
            status: None,
            evidence: None,
        };

        for (index, field) in fields.iter().enumerate() {
            match normalize_token(field).as_str() {
                "story" => columns.story = Some(index),
                "contract" => columns.contract = Some(index),
                "unit" => columns.unit = Some(index),
                "integration" => columns.integration = Some(index),
                "e2e" => columns.e2e = Some(index),
                "platform" => columns.platform = Some(index),
                "status" => columns.status = Some(index),
                "evidence" => columns.evidence = Some(index),
                _ => {}
            }
        }

        columns
    }
}

fn collect_rows<T>(
    rows: rusqlite::MappedRows<'_, impl FnMut(&rusqlite::Row<'_>) -> rusqlite::Result<T>>,
) -> Result<Vec<T>> {
    rows.collect::<std::result::Result<Vec<_>, _>>()
        .map_err(HarnessInfraError::from)
}

fn trace_score_source_from_row(row: &rusqlite::Row<'_>) -> rusqlite::Result<TraceScoreSource> {
    Ok(TraceScoreSource {
        id: row.get(0)?,
        task_summary: row.get(1)?,
        intake_id: row.get(2)?,
        risk_lane: row.get(3)?,
        agent: row.get(4)?,
        actions_taken: row.get(5)?,
        files_read: row.get(6)?,
        files_changed: row.get(7)?,
        decisions_made: row.get(8)?,
        errors: row.get(9)?,
        outcome: row.get(10)?,
        duration_seconds: row.get(11)?,
        token_estimate: row.get(12)?,
        harness_friction: row.get(13)?,
        notes: row.get(14)?,
    })
}

fn markdown_table_fields(line: &str) -> Vec<String> {
    let trimmed = line.trim();
    let trimmed = trimmed.strip_prefix('|').unwrap_or(trimmed);
    let trimmed = trimmed.strip_suffix('|').unwrap_or(trimmed);
    trimmed
        .split('|')
        .map(|field| field.trim().to_owned())
        .collect()
}

fn field_at(fields: &[String], index: Option<usize>) -> Option<String> {
    index
        .and_then(|value| fields.get(value))
        .map(|value| value.trim().to_owned())
        .filter(|value| !value.is_empty())
}

fn evidence_from_fields(fields: &[String], start_index: usize) -> Option<String> {
    fields
        .get(start_index..)
        .map(|values| values.join(" | "))
        .map(|value| value.trim().to_owned())
        .filter(|value| !value.is_empty())
}

fn proof_from_cell(value: &str) -> i64 {
    match normalize_token(value).as_str() {
        ""
        | "no"
        | "none"
        | "n_a"
        | "na"
        | "planned"
        | "pending"
        | "blocked"
        | "not_attempted"
        | "not_operator_reviewed" => 0,
        token
            if token.starts_with("no_")
                || token.starts_with("pending")
                || token.starts_with("blocked")
                || token.contains("pending")
                || token.contains("blocked")
                || token.contains("not_attempted")
                || token.contains("not_operator_reviewed") =>
        {
            0
        }
        _ => 1,
    }
}

fn normalize_story_status(value: &str) -> String {
    match normalize_token(value).as_str() {
        "planned" => "planned",
        "in_progress" => "in_progress",
        "implemented" => "implemented",
        "changed" => "changed",
        "retired" => "retired",
        _ => "planned",
    }
    .to_owned()
}

fn normalize_decision_status(value: &str) -> String {
    let token = normalize_token(value);
    match token.as_str() {
        "proposed" => "proposed",
        "accepted" => "accepted",
        "superseded" => "superseded",
        "rejected" => "rejected",
        token if token.starts_with("superseded_") => "superseded",
        _ => "accepted",
    }
    .to_owned()
}

fn normalize_backlog_status(value: &str) -> String {
    match normalize_token(value).as_str() {
        "proposed" => "proposed",
        "accepted" => "accepted",
        "implemented" => "implemented",
        "rejected" => "rejected",
        _ => "proposed",
    }
    .to_owned()
}

fn markdown_section_first_value(content: &str, heading: &str) -> String {
    let target = format!("## {heading}");
    let mut found = false;
    for line in content.lines() {
        let trimmed = line.trim();
        if found && !trimmed.is_empty() {
            return trimmed.to_owned();
        }
        if trimmed == target {
            found = true;
        }
    }
    String::new()
}

fn backlog_items(content: &str) -> Vec<BacklogMarkdownItem> {
    let mut in_items = false;
    let mut current_heading = String::new();
    let mut current = BacklogMarkdownItem::default();
    let mut items = Vec::new();

    for line in content.lines() {
        let trimmed = line.trim();
        if trimmed == "## Items" {
            in_items = true;
            current_heading.clear();
            continue;
        }
        if !in_items {
            continue;
        }

        if let Some(heading) = trimmed.strip_prefix("### ") {
            let normalized = normalize_token(heading);
            if normalized == "title" && !current.title.is_empty() {
                items.push(current);
                current = BacklogMarkdownItem::default();
            }
            current_heading = normalized;
            continue;
        }

        if trimmed.is_empty() || current_heading.is_empty() {
            continue;
        }

        let target = match current_heading.as_str() {
            "title" => &mut current.title,
            "discovered_while" => &mut current.discovered_while,
            "current_pain" => &mut current.current_pain,
            "suggested_improvement" => &mut current.suggested_improvement,
            "risk" => &mut current.risk,
            "status" => &mut current.status,
            _ => continue,
        };
        if target.is_empty() {
            *target = trimmed.to_owned();
        }
    }

    if !current.title.is_empty() {
        items.push(current);
    }
    items
}

fn empty_to_none(value: String) -> Option<String> {
    if value.is_empty() {
        None
    } else {
        Some(value)
    }
}

fn command_available(repo_root: &Path, command: &str) -> bool {
    let first = command.split_whitespace().next().unwrap_or(command);
    if first.is_empty() {
        return false;
    }
    let candidate = Path::new(first);
    if candidate.is_absolute() {
        return candidate.exists();
    }
    if first.contains('/') || first.contains('\\') {
        return repo_root.join(first).exists();
    }
    env::var_os("PATH")
        .is_some_and(|path| env::split_paths(&path).any(|dir| dir.join(first).exists()))
}

/// Kind-aware presence probe. Returns `(status, detail)` where status is one of
/// `present` / `missing` / `unknown`. It never fails: an absent extension is a
/// fact to report, not an error to raise.
fn scan_tool_status(
    repo_root: &Path,
    kind: &str,
    command: &str,
    scan_target: Option<&str>,
) -> (&'static str, String) {
    match kind {
        "cli" | "binary" => {
            if command_available(repo_root, command) {
                ("present", command.to_owned())
            } else {
                ("missing", command.to_owned())
            }
        }
        "mcp" | "skill" => match scan_target.map(str::trim).filter(|t| !t.is_empty()) {
            Some(target) => {
                if scan_target_resolves(repo_root, target) {
                    ("present", target.to_owned())
                } else {
                    ("missing", target.to_owned())
                }
            }
            None => (
                "unknown",
                "no scan target; agent confirms availability".to_owned(),
            ),
        },
        "http" => match scan_target.map(str::trim).filter(|t| !t.is_empty()) {
            Some(target) => {
                if http_reachable(target) || scan_target_resolves(repo_root, target) {
                    ("present", target.to_owned())
                } else {
                    ("missing", target.to_owned())
                }
            }
            None => ("unknown", "no scan target".to_owned()),
        },
        _ => ("unknown", String::new()),
    }
}

/// Resolve a declarative scan target as a filesystem path: `~` expands to HOME,
/// absolute paths are tested directly, relative paths are tested against the
/// repo root.
fn scan_target_resolves(repo_root: &Path, target: &str) -> bool {
    let expanded = expand_home(target);
    let path = Path::new(&expanded);
    if path.is_absolute() {
        path.exists()
    } else {
        repo_root.join(&expanded).exists()
    }
}

fn expand_home(target: &str) -> String {
    if let Some(rest) = target.strip_prefix("~/") {
        if let Some(home) = env::var_os("HOME") {
            return format!("{}/{}", home.to_string_lossy(), rest);
        }
    }
    target.to_owned()
}

/// Best-effort TCP reachability for `http`/`https` scan targets. Any failure
/// (parse, DNS, timeout, refused) is reported as not reachable rather than an
/// error, so a down endpoint degrades the capability instead of breaking intake.
fn http_reachable(target: &str) -> bool {
    use std::net::{TcpStream, ToSocketAddrs};
    use std::time::Duration;

    let (default_port, rest) = if let Some(rest) = target.strip_prefix("https://") {
        (443u16, rest)
    } else if let Some(rest) = target.strip_prefix("http://") {
        (80u16, rest)
    } else {
        return false;
    };

    let authority = rest.split('/').next().unwrap_or("");
    if authority.is_empty() {
        return false;
    }
    let (host, port) = match authority.rsplit_once(':') {
        Some((host, port)) => (host, port.parse::<u16>().unwrap_or(default_port)),
        None => (authority, default_port),
    };

    let Ok(addresses) = (host, port).to_socket_addrs() else {
        return false;
    };
    addresses
        .into_iter()
        .any(|address| TcpStream::connect_timeout(&address, Duration::from_secs(2)).is_ok())
}

fn tool_args_json(args: &[ToolArgSpec]) -> Option<String> {
    if args.is_empty() {
        return None;
    }
    Some(format!(
        "[{}]",
        args.iter()
            .map(|arg| {
                format!(
                    "{{\"name\":\"{}\",\"type\":\"{}\",\"required\":{},\"help\":\"{}\"}}",
                    escape_json(&arg.name),
                    escape_json(&arg.arg_type),
                    arg.required,
                    escape_json(arg.help.as_deref().unwrap_or(""))
                )
            })
            .collect::<Vec<_>>()
            .join(",")
    ))
}

fn parse_stored_tool_args(value: Option<&str>) -> Vec<ToolArgSpec> {
    let Some(value) = value else {
        return Vec::new();
    };
    if !value.contains("\"name\"") {
        return Vec::new();
    }
    value
        .trim()
        .trim_start_matches('[')
        .trim_end_matches(']')
        .split("},{")
        .filter_map(|raw| {
            let item = raw.trim_matches('{').trim_matches('}');
            let name = json_object_value(item, "name")?;
            let arg_type = json_object_value(item, "type").unwrap_or_else(|| "string".to_owned());
            let required = json_object_value(item, "required")
                .map(|value| value == "true")
                .unwrap_or(false);
            let help = json_object_value(item, "help").filter(|value| !value.is_empty());
            Some(ToolArgSpec {
                name,
                arg_type,
                required,
                help,
            })
        })
        .collect()
}

fn json_object_value(raw: &str, key: &str) -> Option<String> {
    let target = format!("\"{key}\":");
    let start = raw.find(&target)? + target.len();
    let rest = &raw[start..];
    if let Some(rest) = rest.strip_prefix('"') {
        let end = rest.find('"')?;
        Some(rest[..end].to_owned())
    } else {
        Some(rest.split(',').next().unwrap_or_default().trim().to_owned())
    }
}

fn escape_json(value: &str) -> String {
    value
        .replace('\\', "\\\\")
        .replace('"', "\\\"")
        .replace('\n', "\\n")
}

fn audit_findings(connection: &Connection, sql: &str) -> Result<Vec<AuditFinding>> {
    let mut statement = connection.prepare(sql)?;
    let rows = statement.query_map([], |row| {
        Ok(AuditFinding {
            id: row.get(0)?,
            title: row.get(1)?,
        })
    })?;
    collect_rows(rows)
}

fn repeated_friction(connection: &Connection) -> Result<Vec<(String, usize)>> {
    let mut statement = connection.prepare(
        "SELECT harness_friction FROM trace
         WHERE harness_friction IS NOT NULL
           AND TRIM(harness_friction) <> ''
           AND LOWER(TRIM(harness_friction)) <> 'none';",
    )?;
    let rows = statement.query_map([], |row| row.get::<_, String>(0))?;
    let values = collect_rows(rows)?;
    Ok(repeated_values(values))
}

fn validation_provider_friction_resolved(connection: &Connection, text: &str) -> Result<bool> {
    let normalized = normalize_token(text);
    if !normalized.contains("tool_registry_lacks_entries_for_local_validation_capabilities") {
        return Ok(false);
    }

    for capability in [
        "build-verification",
        "browser-e2e",
        "coverage",
        "design-validation",
        "platform-smoke",
    ] {
        if !has_present_provider(connection, capability)? {
            return Ok(false);
        }
    }
    Ok(true)
}

fn has_present_provider(connection: &Connection, capability: &str) -> Result<bool> {
    let count: i64 = connection.query_row(
        "SELECT COUNT(*) FROM tool WHERE capability=?1 AND status='present';",
        params![capability],
        |row| row.get(0),
    )?;
    Ok(count > 0)
}

fn repeated_interventions(connection: &Connection) -> Result<Vec<(String, usize)>> {
    let mut statement = connection.prepare(
        "SELECT type || ': ' || description FROM intervention
         WHERE TRIM(description) <> '';",
    )?;
    let rows = statement.query_map([], |row| row.get::<_, String>(0))?;
    let values = collect_rows(rows)?;
    Ok(repeated_values(values))
}

fn repeated_values(values: Vec<String>) -> Vec<(String, usize)> {
    let mut grouped: Vec<(String, String, usize)> = Vec::new();
    for value in values {
        let key = normalize_token(&value);
        if let Some(existing) = grouped.iter_mut().find(|item| item.0 == key) {
            existing.2 += 1;
        } else {
            grouped.push((key, value, 1));
        }
    }
    grouped
        .into_iter()
        .filter(|(_, _, count)| *count >= 2)
        .map(|(_, value, count)| (value, count))
        .collect()
}

fn confidence_for_count(count: usize) -> String {
    if count >= 3 {
        "high".to_owned()
    } else {
        "medium".to_owned()
    }
}

fn short_title(value: &str) -> String {
    let words = value
        .split_whitespace()
        .take(8)
        .collect::<Vec<_>>()
        .join(" ");
    if words.len() > 72 {
        format!("{}...", &words[..69])
    } else {
        words
    }
}

fn verifier_shell() -> (&'static str, &'static str) {
    if cfg!(windows) {
        ("cmd", "/C")
    } else {
        ("sh", "-c")
    }
}

fn is_decision_file_name(file_name: &str) -> bool {
    let Some((prefix, _)) = file_name.split_once('-') else {
        return false;
    };
    prefix.len() == 4 && prefix.chars().all(|character| character.is_ascii_digit())
}

fn sql_value_to_string(value: ValueRef<'_>) -> String {
    match value {
        ValueRef::Null => String::new(),
        ValueRef::Integer(value) => value.to_string(),
        ValueRef::Real(value) => value.to_string(),
        ValueRef::Text(value) => String::from_utf8_lossy(value).into_owned(),
        ValueRef::Blob(value) => format!("<{} bytes>", value.len()),
    }
}

fn rollback_changeset_append(append: &ChangesetAppend) -> Result<()> {
    let mut file = OpenOptions::new().write(true).open(&append.path)?;
    file.set_len(append.original_len)?;
    file.seek(SeekFrom::Start(append.original_len))?;
    file.sync_all()?;
    Ok(())
}

#[derive(Debug, Default)]
struct ChangesetApplyContext {
    intake_ids: std::collections::HashMap<i64, i64>,
    backlog_ids: std::collections::HashMap<i64, i64>,
    trace_ids: std::collections::HashMap<i64, i64>,
}

fn mapped_id(source_id: Option<i64>, ids: &std::collections::HashMap<i64, i64>) -> Option<i64> {
    source_id.map(|id| ids.get(&id).copied().unwrap_or(id))
}

fn apply_changeset_operation(
    transaction: &Transaction<'_>,
    operation: &Value,
    context: &mut ChangesetApplyContext,
) -> Result<()> {
    let op = required_string(operation, "op")?;
    let payload = operation.get("payload").unwrap_or(&Value::Null);
    match op.as_str() {
        "intake.add" => {
            let source_id = required_i64(operation, "id")?;
            transaction.execute(
            "INSERT INTO intake (
                input_type, summary, risk_lane, risk_flags, affected_docs, story_id, notes
             ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7);",
            params![
                required_string(payload, "input_type")?,
                required_string(payload, "summary")?,
                required_string(payload, "risk_lane")?,
                optional_string(payload, "risk_flags"),
                optional_string(payload, "affected_docs"),
                optional_string(payload, "story_id"),
                optional_string(payload, "notes"),
            ],
            )?;
            context
                .intake_ids
                .insert(source_id, transaction.last_insert_rowid());
            1
        }
        "story.add" => transaction.execute(
            "INSERT INTO story (id, title, risk_lane, contract_doc, verify_command, notes)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6);",
            params![
                required_string(operation, "id")?,
                required_string(payload, "title")?,
                required_string(payload, "risk_lane")?,
                optional_string(payload, "contract_doc"),
                optional_string(payload, "verify_command"),
                optional_string(payload, "notes"),
            ],
        )?,
        "story.update" => transaction.execute(
            "UPDATE story SET
                status=COALESCE(?1, status),
                evidence=COALESCE(?2, evidence),
                unit_proof=COALESCE(?3, unit_proof),
                integration_proof=COALESCE(?4, integration_proof),
                e2e_proof=COALESCE(?5, e2e_proof),
                platform_proof=COALESCE(?6, platform_proof),
                verify_command=COALESCE(?7, verify_command)
             WHERE id=?8;",
            params![
                optional_string(payload, "status"),
                optional_string(payload, "evidence"),
                optional_i64(payload, "unit_proof"),
                optional_i64(payload, "integration_proof"),
                optional_i64(payload, "e2e_proof"),
                optional_i64(payload, "platform_proof"),
                optional_string(payload, "verify_command"),
                required_string(operation, "id")?,
            ],
        )?,
        "story.dependency.add" => {
            let blocker = required_string(operation, "id")?;
            let blocked = required_string(payload, "blocked")?;
            if blocker == blocked {
                return Err(HarnessInfraError::StoryDependencySelf(blocker));
            }
            ensure_story_exists(transaction, &blocker)?;
            ensure_story_exists(transaction, &blocked)?;
            if dependency_path_exists(transaction, &blocked, &blocker)? {
                return Err(HarnessInfraError::StoryDependencyCycle(blocker, blocked));
            }
            transaction.execute(
                "INSERT INTO story_dependency (story_id, blocks_story_id) VALUES (?1, ?2)
                 ON CONFLICT(story_id, blocks_story_id) DO NOTHING;",
                params![blocker, blocked],
            )?
        }
        "story.dependency.remove" => transaction.execute(
            "DELETE FROM story_dependency WHERE story_id=?1 AND blocks_story_id=?2;",
            params![
                required_string(operation, "id")?,
                required_string(payload, "blocked")?,
            ],
        )?,
        "story.verify" => transaction.execute(
            "UPDATE story
             SET last_verified_at=datetime('now'), last_verified_result=?1
             WHERE id=?2;",
            params![
                required_string(payload, "result")?,
                required_string(operation, "id")?,
            ],
        )?,
        "decision.add" => transaction.execute(
            "INSERT INTO decision (id, title, status, doc_path, verify_command, predicted_impact, notes)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7);",
            params![
                required_string(operation, "id")?,
                required_string(payload, "title")?,
                required_string(payload, "status")?,
                optional_string(payload, "doc_path"),
                optional_string(payload, "verify_command"),
                optional_string(payload, "predicted_impact"),
                optional_string(payload, "notes"),
            ],
        )?,
        "decision.verify" => transaction.execute(
            "UPDATE decision
             SET last_verified_at=datetime('now'), last_verified_result=?1
             WHERE id=?2;",
            params![
                required_string(payload, "result")?,
                required_string(operation, "id")?,
            ],
        )?,
        "backlog.add" => {
            let source_id = required_i64(operation, "id")?;
            transaction.execute(
            "INSERT INTO backlog (
                title, discovered_while, current_pain, suggested_improvement,
                risk, predicted_impact, notes
             ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7);",
            params![
                required_string(payload, "title")?,
                optional_string(payload, "discovered_while"),
                optional_string(payload, "current_pain"),
                optional_string(payload, "suggested_improvement"),
                optional_string(payload, "risk"),
                optional_string(payload, "predicted_impact"),
                optional_string(payload, "notes"),
            ],
            )?;
            context
                .backlog_ids
                .insert(source_id, transaction.last_insert_rowid());
            1
        }
        "backlog.close" => transaction.execute(
            "UPDATE backlog
             SET status=?1, actual_outcome=?2, implemented_at=datetime('now')
             WHERE id=?3;",
            params![
                required_string(payload, "status")?,
                optional_string(payload, "actual_outcome"),
                mapped_id(Some(required_i64(operation, "id")?), &context.backlog_ids),
            ],
        )?,
        "tool.register" => transaction.execute(
            "INSERT INTO tool
                (name, provider, command, description, args, responsibility, since,
                 kind, capability, scan_target, status)
             VALUES (?1, 'custom', ?2, ?3, ?4, ?5, 'registered', ?6, ?7, ?8, 'unknown');",
            params![
                required_string(operation, "id")?,
                required_string(payload, "command")?,
                required_string(payload, "description")?,
                optional_string(payload, "args"),
                required_string(payload, "responsibility")?,
                required_string(payload, "kind")?,
                optional_string(payload, "capability"),
                optional_string(payload, "scan_target"),
            ],
        )?,
        "tool.check" => transaction.execute(
            "UPDATE tool SET status=?1, checked_at=datetime('now') WHERE name=?2;",
            params![
                required_string(payload, "status")?,
                required_string(operation, "id")?,
            ],
        )?,
        "tool.remove" => transaction.execute(
            "DELETE FROM tool WHERE name=?1;",
            params![required_string(operation, "id")?],
        )?,
        "intervention.add" => transaction.execute(
            "INSERT INTO intervention (trace_id, story_id, type, description, source, impact)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6);",
            params![
                mapped_id(optional_i64(payload, "trace_id"), &context.trace_ids),
                optional_string(payload, "story_id"),
                required_string(payload, "type")?,
                required_string(payload, "description")?,
                required_string(payload, "source")?,
                optional_string(payload, "impact"),
            ],
        )?,
        "trace.add" => {
            let source_id = required_i64(operation, "id")?;
            transaction.execute(
            "INSERT INTO trace (
                task_summary, intake_id, story_id, agent,
                actions_taken, files_read, files_changed, decisions_made, errors,
                outcome, duration_seconds, token_estimate, harness_friction, notes
             ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14);",
            params![
                required_string(payload, "task_summary")?,
                mapped_id(optional_i64(payload, "intake_id"), &context.intake_ids),
                optional_string(payload, "story_id"),
                optional_string(payload, "agent"),
                optional_string(payload, "actions_taken"),
                optional_string(payload, "files_read"),
                optional_string(payload, "files_changed"),
                optional_string(payload, "decisions_made"),
                optional_string(payload, "errors"),
                optional_string(payload, "outcome"),
                optional_i64(payload, "duration_seconds"),
                optional_i64(payload, "token_estimate"),
                optional_string(payload, "harness_friction"),
                optional_string(payload, "notes"),
            ],
            )?;
            context
                .trace_ids
                .insert(source_id, transaction.last_insert_rowid());
            1
        }
        _ => return Err(HarnessInfraError::UnsupportedChangesetOp(op)),
    };
    Ok(())
}

fn ensure_story_exists(transaction: &Transaction<'_>, id: &str) -> Result<()> {
    let exists = transaction
        .query_row("SELECT 1 FROM story WHERE id=?1;", params![id], |_| Ok(()))
        .optional()?
        .is_some();
    if exists {
        Ok(())
    } else {
        Err(HarnessInfraError::StoryNotFound(id.to_owned()))
    }
}

fn dependency_path_exists(transaction: &Transaction<'_>, from: &str, to: &str) -> Result<bool> {
    transaction
        .query_row(
            "WITH RECURSIVE reachable(id) AS (
                SELECT blocks_story_id FROM story_dependency WHERE story_id=?1
                UNION
                SELECT dependency.blocks_story_id
                FROM story_dependency AS dependency
                JOIN reachable ON dependency.story_id=reachable.id
             )
             SELECT 1 FROM reachable WHERE id=?2 LIMIT 1;",
            params![from, to],
            |_| Ok(()),
        )
        .optional()
        .map(|value| value.is_some())
        .map_err(HarnessInfraError::from)
}

fn required_string(value: &Value, field: &str) -> Result<String> {
    value
        .get(field)
        .and_then(Value::as_str)
        .map(ToOwned::to_owned)
        .ok_or_else(|| HarnessInfraError::InvalidChangeset(format!("missing string field {field}")))
}

fn optional_string(value: &Value, field: &str) -> Option<String> {
    value
        .get(field)
        .and_then(Value::as_str)
        .map(ToOwned::to_owned)
}

fn required_i64(value: &Value, field: &str) -> Result<i64> {
    value.get(field).and_then(Value::as_i64).ok_or_else(|| {
        HarnessInfraError::InvalidChangeset(format!("missing integer field {field}"))
    })
}

fn optional_i64(value: &Value, field: &str) -> Option<i64> {
    value.get(field).and_then(Value::as_i64)
}

#[cfg(test)]
mod tests {
    use tempfile::TempDir;

    use super::*;
    use crate::application::{
        BacklogAddInput, BacklogCloseInput, DecisionAddInput, IntakeInput, InterventionAddInput,
        InterventionFilter, StoryAddInput, StoryDependencyInput, StoryUpdateInput,
        ToolRegisterInput, TraceInput,
    };
    use crate::domain::{BacklogFilter, BoolFlag, CsvList, InputType, RiskLane, TraceQualityTier};

    fn test_repository() -> (TempDir, SqliteHarnessRepository) {
        let temp_dir = tempfile::tempdir().unwrap();
        let repo_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .ancestors()
            .nth(2)
            .unwrap()
            .to_path_buf();
        let repository = SqliteHarnessRepository::new(
            repo_root.clone(),
            temp_dir.path().join("harness.db"),
            repo_root.join("scripts/schema"),
        );
        (temp_dir, repository)
    }

    fn isolated_test_repository() -> (TempDir, SqliteHarnessRepository) {
        let temp_dir = tempfile::tempdir().unwrap();
        let repo_root = temp_dir.path().join("repo");
        fs::create_dir_all(&repo_root).unwrap();
        let schema_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .ancestors()
            .nth(2)
            .unwrap()
            .to_path_buf();
        let repository = SqliteHarnessRepository::new(
            repo_root.clone(),
            repo_root.join("harness.db"),
            schema_root.join("scripts/schema"),
        );
        (temp_dir, repository)
    }

    fn story_columns(connection: &Connection) -> Vec<String> {
        let mut statement = connection.prepare("PRAGMA table_info(story);").unwrap();
        let rows = statement
            .query_map([], |row| row.get::<_, String>(1))
            .unwrap();
        rows.collect::<std::result::Result<Vec<_>, _>>().unwrap()
    }

    #[test]
    fn init_creates_database_and_schema() {
        let (_temp_dir, repository) = test_repository();

        let result = repository.init().unwrap();

        assert!(matches!(result, InitResult::Created { .. }));
        assert_eq!(repository.query_stats().unwrap().intakes, 0);
        let connection = repository.open_existing().unwrap();
        let schema_version = SqliteHarnessRepository::schema_version(&connection).unwrap();
        assert_eq!(schema_version, 8);
        let story_columns = story_columns(&connection);
        assert!(story_columns.contains(&"verify_command".to_owned()));
        assert!(story_columns.contains(&"last_verified_at".to_owned()));
        assert!(story_columns.contains(&"last_verified_result".to_owned()));
        let dependency_table_exists = connection
            .query_row(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='story_dependency';",
                [],
                |_| Ok(()),
            )
            .is_ok();
        assert!(dependency_table_exists);
        let hierarchy_table_exists = connection
            .query_row(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='story_hierarchy';",
                [],
                |_| Ok(()),
            )
            .is_ok();
        assert!(hierarchy_table_exists);
    }

    #[test]
    fn logged_write_appends_header_and_semantic_operation() {
        let (_temp_dir, repository) = isolated_test_repository();
        repository.init().unwrap();
        let mut connection = repository.open_existing().unwrap();

        repository
            .with_logged_write_for_run(&mut connection, Some("run_test"), |transaction| {
                transaction
                    .execute(
                        "INSERT INTO intake (input_type, summary, risk_lane)
                         VALUES ('harness_improvement', 'Logged write test', 'normal');",
                        [],
                    )
                    .unwrap();
                let id = transaction.last_insert_rowid();
                Ok((
                    id,
                    vec![json!({
                        "op": "intake.add",
                        "version": 1,
                        "id": id,
                        "payload": {
                            "summary": "Logged write test",
                        },
                    })],
                ))
            })
            .unwrap();

        let changeset = fs::read_to_string(repository.changeset_path("run_test")).unwrap();
        let lines = changeset.lines().collect::<Vec<_>>();
        assert_eq!(lines.len(), 2);
        let header: Value = serde_json::from_str(lines[0]).unwrap();
        assert_eq!(header["op"], "changeset.header");
        assert_eq!(header["run_id"], "run_test");
        assert_eq!(header["base_schema_version"], 8);
        let operation: Value = serde_json::from_str(lines[1]).unwrap();
        assert_eq!(operation["op"], "intake.add");
        assert_eq!(operation["payload"]["summary"], "Logged write test");

        let count = connection
            .query_row("SELECT COUNT(*) FROM intake;", [], |row| {
                row.get::<_, i64>(0)
            })
            .unwrap();
        assert_eq!(count, 1);
    }

    #[test]
    fn story_dependency_command_validates_mutation_and_query_contract() {
        let (_temp_dir, repository) = isolated_test_repository();
        repository.init().unwrap();
        for id in ["US-A", "US-B", "US-C"] {
            repository
                .add_story(StoryAddInput {
                    id: id.to_owned(),
                    title: id.to_owned(),
                    risk_lane: RiskLane::Normal,
                    contract_doc: None,
                    verify_command: None,
                    notes: None,
                })
                .unwrap();
        }

        assert!(repository
            .add_story_dependency(StoryDependencyInput {
                blocker: "US-A".to_owned(),
                blocked: "US-B".to_owned(),
            })
            .unwrap());
        assert!(!repository
            .add_story_dependency(StoryDependencyInput {
                blocker: "US-A".to_owned(),
                blocked: "US-B".to_owned(),
            })
            .unwrap());
        assert!(matches!(
            repository.add_story_dependency(StoryDependencyInput {
                blocker: "US-MISSING".to_owned(),
                blocked: "US-B".to_owned(),
            }),
            Err(HarnessInfraError::StoryNotFound(id)) if id == "US-MISSING"
        ));
        assert!(matches!(
            repository.add_story_dependency(StoryDependencyInput {
                blocker: "US-A".to_owned(),
                blocked: "US-A".to_owned(),
            }),
            Err(HarnessInfraError::StoryDependencySelf(id)) if id == "US-A"
        ));
        assert!(repository
            .add_story_dependency(StoryDependencyInput {
                blocker: "US-B".to_owned(),
                blocked: "US-C".to_owned(),
            })
            .unwrap());
        assert!(matches!(
            repository.add_story_dependency(StoryDependencyInput {
                blocker: "US-C".to_owned(),
                blocked: "US-A".to_owned(),
            }),
            Err(HarnessInfraError::StoryDependencyCycle(blocker, blocked))
                if blocker == "US-C" && blocked == "US-A"
        ));

        assert_eq!(
            repository.query_story_dependencies(None).unwrap(),
            vec![
                StoryDependencyRecord {
                    blocker: "US-A".to_owned(),
                    blocked: "US-B".to_owned(),
                },
                StoryDependencyRecord {
                    blocker: "US-B".to_owned(),
                    blocked: "US-C".to_owned(),
                },
            ]
        );
        assert!(repository
            .remove_story_dependency(StoryDependencyInput {
                blocker: "US-A".to_owned(),
                blocked: "US-B".to_owned(),
            })
            .unwrap());
        assert!(!repository
            .remove_story_dependency(StoryDependencyInput {
                blocker: "US-A".to_owned(),
                blocked: "US-B".to_owned(),
            })
            .unwrap());
    }

    #[test]
    fn story_dependency_changeset_replays_idempotently() {
        let (temp_dir, repository) = isolated_test_repository();
        repository.init().unwrap();
        let changeset_path = temp_dir.path().join("dependency.changeset.jsonl");
        fs::write(
            &changeset_path,
            r#"{"op":"changeset.header","version":1,"run_id":"run_dependency","base_schema_version":8}
{"op":"story.add","version":1,"id":"US-A","payload":{"title":"A","risk_lane":"normal","contract_doc":null,"verify_command":null,"notes":null}}
{"op":"story.add","version":1,"id":"US-B","payload":{"title":"B","risk_lane":"normal","contract_doc":null,"verify_command":null,"notes":null}}
{"op":"story.dependency.add","version":1,"id":"US-A","payload":{"blocked":"US-B"}}
{"op":"story.dependency.remove","version":1,"id":"US-A","payload":{"blocked":"US-B"}}
{"op":"story.dependency.add","version":1,"id":"US-A","payload":{"blocked":"US-B"}}
"#,
        )
        .unwrap();

        assert!(repository.apply_changeset(&changeset_path).unwrap().applied);
        assert!(!repository.apply_changeset(&changeset_path).unwrap().applied);
        assert_eq!(
            repository.query_story_dependencies(None).unwrap(),
            vec![StoryDependencyRecord {
                blocker: "US-A".to_owned(),
                blocked: "US-B".to_owned(),
            }]
        );
    }

    #[test]
    fn failed_logged_write_rolls_back_without_changeset() {
        let (_temp_dir, repository) = isolated_test_repository();
        repository.init().unwrap();
        let mut connection = repository.open_existing().unwrap();

        let result: Result<i64> = repository.with_logged_write_for_run(
            &mut connection,
            Some("run_fail"),
            |transaction| {
                transaction
                    .execute(
                        "INSERT INTO intake (input_type, summary, risk_lane)
                         VALUES ('harness_improvement', 'Failed write test', 'normal');",
                        [],
                    )
                    .unwrap();
                Err(HarnessInfraError::StoryNotFound("US-NOPE".to_owned()))
            },
        );

        assert!(result.is_err());
        assert!(!repository.changeset_path("run_fail").exists());
        let count = connection
            .query_row("SELECT COUNT(*) FROM intake;", [], |row| {
                row.get::<_, i64>(0)
            })
            .unwrap();
        assert_eq!(count, 0);
    }

    #[test]
    fn apply_changeset_replays_operations_once() {
        let (temp_dir, repository) = isolated_test_repository();
        repository.init().unwrap();
        let changeset_path = temp_dir.path().join("fixture.changeset.jsonl");
        fs::write(
            &changeset_path,
            r#"{"op":"changeset.header","version":1,"run_id":"run_apply","base_schema_version":6}
{"op":"intake.add","version":1,"id":10,"payload":{"input_type":"harness_improvement","summary":"Apply changeset intake","risk_lane":"normal","risk_flags":null,"affected_docs":null,"story_id":null,"notes":null}}
{"op":"story.add","version":1,"id":"US-APPLY","payload":{"title":"Apply changeset story","risk_lane":"normal","contract_doc":null,"verify_command":null,"notes":null}}
{"op":"story.update","version":1,"id":"US-APPLY","payload":{"status":"implemented","evidence":"applied","unit_proof":1,"integration_proof":null,"e2e_proof":null,"platform_proof":null,"verify_command":null}}
"#,
        )
        .unwrap();

        let first = repository.apply_changeset(&changeset_path).unwrap();
        assert!(first.applied);
        assert_eq!(first.id, "run_apply");
        assert_eq!(first.operations, 3);
        let second = repository.apply_changeset(&changeset_path).unwrap();
        assert!(!second.applied);
        assert_eq!(second.operations, 0);

        let connection = repository.open_existing().unwrap();
        let status = connection
            .query_row("SELECT status FROM story WHERE id='US-APPLY';", [], |row| {
                row.get::<_, String>(0)
            })
            .unwrap();
        assert_eq!(status, "implemented");
        let applied = connection
            .query_row(
                "SELECT COUNT(*) FROM changeset_applied WHERE id='run_apply';",
                [],
                |row| row.get::<_, i64>(0),
            )
            .unwrap();
        assert_eq!(applied, 1);
    }

    #[test]
    fn apply_changeset_migrates_existing_database_before_idempotency_check() {
        let (temp_dir, repository) = isolated_test_repository();
        let connection = repository.open_or_create().unwrap();
        repository.apply_schema_v1(&connection).unwrap();
        for file in [
            "002-story-verify.sql",
            "003-tool-registry.sql",
            "004-intervention.sql",
            "005-tool-extensions.sql",
        ] {
            let sql = fs::read_to_string(repository.schema_dir.join(file)).unwrap();
            connection.execute_batch(&sql).unwrap();
        }
        assert_eq!(
            SqliteHarnessRepository::schema_version(&connection).unwrap(),
            5
        );
        drop(connection);

        let changeset_path = temp_dir.path().join("fixture.changeset.jsonl");
        fs::write(
            &changeset_path,
            r#"{"op":"changeset.header","version":1,"run_id":"run_migrated_apply","base_schema_version":6}
{"op":"story.add","version":1,"id":"US-MIGRATED-APPLY","payload":{"title":"Migrated apply story","risk_lane":"normal","contract_doc":null,"verify_command":null,"notes":null}}
"#,
        )
        .unwrap();

        let result = repository.apply_changeset(&changeset_path).unwrap();

        assert!(result.applied);
        assert_eq!(result.operations, 1);
        let connection = repository.open_existing().unwrap();
        assert_eq!(
            SqliteHarnessRepository::schema_version(&connection).unwrap(),
            8
        );
        let applied = connection
            .query_row(
                "SELECT COUNT(*) FROM changeset_applied WHERE id='run_migrated_apply';",
                [],
                |row| row.get::<_, i64>(0),
            )
            .unwrap();
        assert_eq!(applied, 1);
    }

    #[test]
    fn apply_changesets_remaps_local_numeric_ids() {
        let (temp_dir, repository) = isolated_test_repository();
        repository.init().unwrap();

        for (run_id, summary) in [
            ("run_worktree_a", "First worktree trace"),
            ("run_worktree_b", "Second worktree trace"),
        ] {
            fs::write(
                temp_dir.path().join(format!("{run_id}.changeset.jsonl")),
                format!(
                    r#"{{"op":"changeset.header","version":1,"run_id":"{run_id}","base_schema_version":8}}
{{"op":"intake.add","version":1,"id":1,"payload":{{"input_type":"change_request","summary":"{summary} intake","risk_lane":"normal","risk_flags":null,"affected_docs":null,"story_id":null,"notes":null}}}}
{{"op":"trace.add","version":1,"id":1,"payload":{{"task_summary":"{summary}","intake_id":1,"story_id":null,"agent":"Codex","actions_taken":null,"files_read":null,"files_changed":null,"decisions_made":null,"errors":null,"outcome":"completed","duration_seconds":null,"token_estimate":null,"harness_friction":null,"notes":null}}}}
"#
                ),
            )
            .unwrap();

            let result = repository
                .apply_changeset(&temp_dir.path().join(format!("{run_id}.changeset.jsonl")))
                .unwrap();
            assert!(result.applied);
            assert_eq!(result.operations, 2);
        }

        let connection = repository.open_existing().unwrap();
        let counts = connection
            .query_row(
                "SELECT
                    (SELECT COUNT(*) FROM intake),
                    (SELECT COUNT(*) FROM trace),
                    (SELECT COUNT(DISTINCT intake_id) FROM trace)
                 ;",
                [],
                |row| {
                    Ok((
                        row.get::<_, i64>(0)?,
                        row.get::<_, i64>(1)?,
                        row.get::<_, i64>(2)?,
                    ))
                },
            )
            .unwrap();
        assert_eq!(counts, (2, 2, 2));
    }

    #[test]
    fn rebuild_db_creates_fresh_database_from_changesets() {
        let (temp_dir, repository) = isolated_test_repository();
        let changeset_dir = temp_dir.path().join("changesets");
        fs::create_dir_all(&changeset_dir).unwrap();
        fs::write(
            changeset_dir.join("001.changeset.jsonl"),
            r#"{"op":"changeset.header","version":1,"run_id":"run_rebuild","base_schema_version":6}
{"op":"story.add","version":1,"id":"US-REBUILD","payload":{"title":"Rebuild story","risk_lane":"normal","contract_doc":null,"verify_command":null,"notes":null}}
{"op":"story.update","version":1,"id":"US-REBUILD","payload":{"status":"implemented","evidence":"rebuilt","unit_proof":1,"integration_proof":1,"e2e_proof":null,"platform_proof":null,"verify_command":null}}
"#,
        )
        .unwrap();

        let result = repository.rebuild_db(&changeset_dir).unwrap();
        assert_eq!(result.changesets, 1);
        assert_eq!(result.operations, 2);

        let connection = repository.open_existing().unwrap();
        let evidence = connection
            .query_row(
                "SELECT evidence FROM story WHERE id='US-REBUILD';",
                [],
                |row| row.get::<_, String>(0),
            )
            .unwrap();
        assert_eq!(evidence, "rebuilt");
    }

    #[test]
    fn rebuild_db_refuses_existing_database() {
        let (temp_dir, repository) = isolated_test_repository();
        repository.init().unwrap();
        let result = repository.rebuild_db(temp_dir.path());

        assert!(matches!(
            result,
            Err(HarnessInfraError::RebuildDatabaseExists(_))
        ));
    }

    #[test]
    fn migrate_applies_story_verify_columns_to_existing_database() {
        let (_temp_dir, repository) = test_repository();
        let connection = repository.open_or_create().unwrap();
        repository.apply_schema_v1(&connection).unwrap();
        drop(connection);

        let result = repository.migrate().unwrap();

        assert_eq!(result.current_version, 1);
        assert_eq!(result.applied, vec![2, 3, 4, 5, 6, 7, 8]);
        let connection = repository.open_existing().unwrap();
        assert_eq!(
            SqliteHarnessRepository::schema_version(&connection).unwrap(),
            8
        );
        let story_columns = story_columns(&connection);
        assert!(story_columns.contains(&"verify_command".to_owned()));
        assert!(story_columns.contains(&"last_verified_at".to_owned()));
        assert!(story_columns.contains(&"last_verified_result".to_owned()));
    }

    #[test]
    fn migration_005_backfills_kind_from_command_prefix() {
        let (_temp_dir, repository) = test_repository();
        let schema_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .ancestors()
            .nth(2)
            .unwrap()
            .join("scripts/schema");

        // Build a pre-kind (v4) database: v1 base plus migrations 002-004 only.
        let connection = repository.open_or_create().unwrap();
        repository.apply_schema_v1(&connection).unwrap();
        for file in [
            "002-story-verify.sql",
            "003-tool-registry.sql",
            "004-intervention.sql",
        ] {
            let sql = std::fs::read_to_string(schema_dir.join(file)).unwrap();
            connection.execute_batch(&sql).unwrap();
        }
        assert_eq!(
            SqliteHarnessRepository::schema_version(&connection).unwrap(),
            4
        );

        // Insert tools the old way (no kind column existed yet).
        for (name, command) in [
            ("mcp-example", "mcp:example-server"),
            ("skill-example", "skill:example-skill"),
            ("cli-example", "./deploy.sh"),
        ] {
            connection
                .execute(
                    "INSERT INTO tool (name, command, description, responsibility)
                     VALUES (?1, ?2, 'pre-kind registered tool example', 'Verification');",
                    params![name, command],
                )
                .unwrap();
        }
        drop(connection);

        // Upgrade: migration 005 must infer kind from the command prefix.
        assert_eq!(repository.migrate().unwrap().applied, vec![5, 6, 7, 8]);
        let connection = repository.open_existing().unwrap();
        let kind_of = |name: &str| -> String {
            connection
                .query_row(
                    "SELECT kind FROM tool WHERE name=?1;",
                    params![name],
                    |row| row.get::<_, String>(0),
                )
                .unwrap()
        };
        assert_eq!(kind_of("mcp-example"), "mcp");
        assert_eq!(kind_of("skill-example"), "skill");
        assert_eq!(kind_of("cli-example"), "cli");
    }

    #[test]
    fn records_and_queries_intake() {
        let (_temp_dir, repository) = test_repository();
        repository.init().unwrap();

        let id = repository
            .record_intake(IntakeInput {
                input_type: InputType::HarnessImprovement,
                summary: "Port one CLI slice".to_owned(),
                risk_lane: RiskLane::HighRisk,
                risk_flags: CsvList::from_optional(Some("public contracts".to_owned())),
                affected_docs: CsvList::from_optional(None),
                story_id: Some("US-002".to_owned()),
                notes: None,
            })
            .unwrap();

        let intakes = repository.query_intakes().unwrap();
        assert_eq!(id, 1);
        assert_eq!(intakes[0].summary, "Port one CLI slice");
        assert_eq!(intakes[0].input_type, "harness_improvement");
        assert_eq!(intakes[0].risk_lane, "high_risk");

        let connection = repository.open_existing().unwrap();
        let missing_lists_are_null: (bool, bool) = connection
            .query_row(
                "SELECT risk_flags IS NULL, affected_docs IS NULL FROM intake WHERE id=?1;",
                params![id],
                |row| Ok((row.get(0)?, row.get(1)?)),
            )
            .unwrap();
        assert_eq!(missing_lists_are_null, (false, true));
    }

    #[test]
    fn decision_verify_runs_from_repo_root() {
        let temp_dir = tempfile::tempdir().unwrap();
        let repo_root = temp_dir.path().join("repo");
        fs::create_dir_all(&repo_root).unwrap();
        let schema_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .ancestors()
            .nth(2)
            .unwrap()
            .to_path_buf()
            .join("scripts/schema");
        let repository = SqliteHarnessRepository::new(
            repo_root.clone(),
            temp_dir.path().join("harness.db"),
            schema_root,
        );
        repository.init().unwrap();

        let pwd_output = repo_root.join("verify-pwd.txt");
        let verify_command = if cfg!(windows) {
            "cd > verify-pwd.txt".to_owned()
        } else {
            "pwd > verify-pwd.txt".to_owned()
        };
        repository
            .add_decision(DecisionAddInput {
                id: "0001-test".to_owned(),
                title: "Verify from root".to_owned(),
                status: "accepted".to_owned(),
                doc_path: None,
                verify_command: Some(verify_command),
                predicted_impact: None,
                notes: None,
            })
            .unwrap();

        let result = repository.verify_decision("0001-test").unwrap();

        assert_eq!(result.result, "pass");
        assert_eq!(
            fs::canonicalize(fs::read_to_string(pwd_output).unwrap().trim()).unwrap(),
            fs::canonicalize(repo_root).unwrap()
        );
    }

    #[test]
    fn story_add_update_and_verify_status_store_verify_command() {
        let (_temp_dir, repository) = test_repository();
        repository.init().unwrap();

        repository
            .add_story(StoryAddInput {
                id: "US-VERIFY".to_owned(),
                title: "Verify command story".to_owned(),
                risk_lane: RiskLane::Normal,
                contract_doc: None,
                verify_command: Some("echo ok".to_owned()),
                notes: None,
            })
            .unwrap();
        assert_eq!(
            repository
                .story_verify_status("US-VERIFY")
                .unwrap()
                .verify_command
                .as_deref(),
            Some("echo ok")
        );

        repository
            .update_story(StoryUpdateInput {
                id: "US-VERIFY".to_owned(),
                status: None,
                evidence: None,
                unit: None,
                integration: None,
                e2e: None,
                platform: None,
                verify_command: Some("npm test".to_owned()),
            })
            .unwrap();

        assert_eq!(
            repository
                .story_verify_status("US-VERIFY")
                .unwrap()
                .verify_command
                .as_deref(),
            Some("npm test")
        );
    }

    #[test]
    fn story_verify_records_pass_fail_and_missing_command() {
        let temp_dir = tempfile::tempdir().unwrap();
        let repo_root = temp_dir.path().join("repo");
        fs::create_dir_all(&repo_root).unwrap();
        let schema_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .ancestors()
            .nth(2)
            .unwrap()
            .to_path_buf()
            .join("scripts/schema");
        let repository = SqliteHarnessRepository::new(
            repo_root.clone(),
            temp_dir.path().join("harness.db"),
            schema_root,
        );
        repository.init().unwrap();

        let pwd_output = repo_root.join("story-verify-pwd.txt");
        let verify_command = if cfg!(windows) {
            "cd > story-verify-pwd.txt".to_owned()
        } else {
            "pwd > story-verify-pwd.txt".to_owned()
        };
        repository
            .add_story(StoryAddInput {
                id: "US-PASS".to_owned(),
                title: "Passing story".to_owned(),
                risk_lane: RiskLane::Normal,
                contract_doc: None,
                verify_command: Some(verify_command),
                notes: None,
            })
            .unwrap();
        let pass = repository.verify_story("US-PASS").unwrap();
        assert_eq!(pass.result, "pass");
        assert_eq!(
            fs::canonicalize(fs::read_to_string(pwd_output).unwrap().trim()).unwrap(),
            fs::canonicalize(repo_root).unwrap()
        );
        assert_eq!(
            repository
                .story_verify_status("US-PASS")
                .unwrap()
                .last_verified_result
                .as_deref(),
            Some("pass")
        );

        repository
            .add_story(StoryAddInput {
                id: "US-FAIL".to_owned(),
                title: "Failing story".to_owned(),
                risk_lane: RiskLane::Normal,
                contract_doc: None,
                verify_command: Some("exit 1".to_owned()),
                notes: None,
            })
            .unwrap();
        let fail = repository.verify_story("US-FAIL").unwrap();
        assert_eq!(fail.result, "fail");
        assert_eq!(
            repository
                .story_verify_status("US-FAIL")
                .unwrap()
                .last_verified_result
                .as_deref(),
            Some("fail")
        );

        repository
            .add_story(StoryAddInput {
                id: "US-MISSING".to_owned(),
                title: "Missing command story".to_owned(),
                risk_lane: RiskLane::Normal,
                contract_doc: None,
                verify_command: None,
                notes: None,
            })
            .unwrap();
        assert!(matches!(
            repository.verify_story("US-MISSING"),
            Err(HarnessInfraError::MissingStoryVerifyCommand(id)) if id == "US-MISSING"
        ));
    }

    #[test]
    fn story_verify_all_reports_pass_fail_and_skipped() {
        let (_temp_dir, repository) = test_repository();
        repository.init().unwrap();
        for (id, command) in [
            ("US-PASS", Some("exit 0")),
            ("US-FAIL", Some("exit 1")),
            ("US-SKIP", None),
        ] {
            repository
                .add_story(StoryAddInput {
                    id: id.to_owned(),
                    title: id.to_owned(),
                    risk_lane: RiskLane::Normal,
                    contract_doc: None,
                    verify_command: command.map(str::to_owned),
                    notes: None,
                })
                .unwrap();
        }

        let result = repository.verify_all_stories().unwrap();

        assert_eq!(result.passed(), 1);
        assert_eq!(result.failed(), 1);
        assert_eq!(result.skipped(), 1);
        assert_eq!(
            repository
                .story_verify_status("US-PASS")
                .unwrap()
                .last_verified_result
                .as_deref(),
            Some("pass")
        );
        assert_eq!(
            repository
                .story_verify_status("US-FAIL")
                .unwrap()
                .last_verified_result
                .as_deref(),
            Some("fail")
        );
    }

    #[test]
    fn tool_registry_register_query_and_remove_work() {
        let (_temp_dir, repository) = test_repository();
        repository.init().unwrap();

        repository
            .register_tool(ToolRegisterInput {
                name: "deploy-check".to_owned(),
                command: "definitely-missing-tool".to_owned(),
                description: "Verify deploy health before release".to_owned(),
                responsibility: "Verification".to_owned(),
                args: Vec::new(),
                force: true,
                kind: "cli".to_owned(),
                capability: Some("deploy-verification".to_owned()),
                scan_target: None,
            })
            .unwrap();
        assert!(matches!(
            repository.register_tool(ToolRegisterInput {
                name: "deploy-check".to_owned(),
                command: "definitely-missing-tool".to_owned(),
                description: "Verify deploy health before release".to_owned(),
                responsibility: "Verification".to_owned(),
                args: Vec::new(),
                force: true,
                kind: "cli".to_owned(),
                capability: Some("deploy-verification".to_owned()),
                scan_target: None,
            }),
            Err(HarnessInfraError::ToolAlreadyExists(_, _))
        ));

        let verification_tools = repository
            .query_tools(Some("Verification".to_owned()), None)
            .unwrap();
        assert!(verification_tools
            .iter()
            .any(|tool| tool.name == "deploy-check" && tool.source == "registered"));

        // Capability lookup returns the registered provider.
        let by_capability = repository
            .query_tools(None, Some("deploy-verification".to_owned()))
            .unwrap();
        assert!(by_capability.iter().any(|tool| tool.name == "deploy-check"));

        repository.remove_tool("deploy-check").unwrap();
        assert!(!repository
            .query_tools(None, None)
            .unwrap()
            .iter()
            .any(|tool| tool.name == "deploy-check"));
    }

    #[test]
    fn tool_check_scans_and_persists_status_per_kind() {
        let (temp_dir, repository) = test_repository();
        repository.init().unwrap();

        // Absolute scan targets keep the test hermetic: test_repository's
        // repo_root points at the real project, so relative targets would
        // resolve against the checkout rather than the temp dir.
        let present_target = temp_dir.path().join("skill-present");
        std::fs::create_dir_all(&present_target).unwrap();
        let missing_target = temp_dir.path().join("mcp-missing");

        // An mcp tool whose scan target does not exist -> missing.
        repository
            .register_tool(ToolRegisterInput {
                name: "mcp-example".to_owned(),
                command: "mcp:example-server".to_owned(),
                description: "Example MCP-backed provider".to_owned(),
                responsibility: "Verification".to_owned(),
                args: Vec::new(),
                force: false,
                kind: "mcp".to_owned(),
                capability: Some("impact-analysis".to_owned()),
                scan_target: Some(missing_target.to_string_lossy().into_owned()),
            })
            .unwrap();

        // A skill tool whose scan target exists -> present.
        repository
            .register_tool(ToolRegisterInput {
                name: "skill-example".to_owned(),
                command: "skill:example-skill".to_owned(),
                description: "Example skill-backed provider".to_owned(),
                responsibility: "Verification".to_owned(),
                args: Vec::new(),
                force: false,
                kind: "skill".to_owned(),
                capability: Some("impact-analysis".to_owned()),
                scan_target: Some(present_target.to_string_lossy().into_owned()),
            })
            .unwrap();

        let results = repository.check_tools(None).unwrap();
        let mcp_tool = results.iter().find(|r| r.name == "mcp-example").unwrap();
        let skill_tool = results.iter().find(|r| r.name == "skill-example").unwrap();
        assert_eq!(mcp_tool.status, "missing");
        assert_eq!(skill_tool.status, "present");

        // Status is persisted, not just returned.
        let stored = repository
            .query_tools(None, Some("impact-analysis".to_owned()))
            .unwrap();
        assert_eq!(stored.len(), 2);
        assert!(stored
            .iter()
            .all(|tool| tool.checked_at.as_deref().is_some_and(|v| !v.is_empty())));
        assert_eq!(
            stored
                .iter()
                .find(|t| t.name == "skill-example")
                .unwrap()
                .status,
            "present"
        );
    }

    #[test]
    fn interventions_can_be_added_and_filtered() {
        let (_temp_dir, repository) = test_repository();
        repository.init().unwrap();
        repository
            .add_story(StoryAddInput {
                id: "US-I".to_owned(),
                title: "Intervention story".to_owned(),
                risk_lane: RiskLane::Normal,
                contract_doc: None,
                verify_command: None,
                notes: None,
            })
            .unwrap();
        let trace_id = repository
            .record_trace(TraceInput {
                task_summary: "Trace for intervention".to_owned(),
                intake_id: None,
                story_id: Some("US-I".to_owned()),
                agent: Some("codex".to_owned()),
                outcome: Some("completed".to_owned()),
                duration_seconds: None,
                token_estimate: None,
                friction: Some("none".to_owned()),
                notes: None,
                actions: CsvList::from_optional(None),
                files_read: CsvList::from_optional(None),
                files_changed: CsvList::from_optional(None),
                decisions: CsvList::from_optional(None),
                errors: CsvList::from_optional(None),
            })
            .unwrap();
        repository
            .add_intervention(InterventionAddInput {
                trace_id: Some(trace_id),
                story_id: Some("US-I".to_owned()),
                intervention_type: "correction".to_owned(),
                description: "Use error handling instead of unwrap".to_owned(),
                source: "human".to_owned(),
                impact: Some("Reduced panic risk".to_owned()),
            })
            .unwrap();

        assert_eq!(
            repository
                .query_interventions(InterventionFilter {
                    trace_id: Some(trace_id),
                    story_id: None,
                    intervention_type: None,
                })
                .unwrap()
                .len(),
            1
        );
        assert_eq!(
            repository
                .query_interventions(InterventionFilter {
                    trace_id: None,
                    story_id: Some("US-I".to_owned()),
                    intervention_type: Some("override".to_owned()),
                })
                .unwrap()
                .len(),
            0
        );
    }

    #[test]
    fn audit_detects_drift_and_propose_can_commit_backlog_items() {
        let (_temp_dir, repository) = test_repository();
        repository.init().unwrap();
        repository
            .add_story(StoryAddInput {
                id: "US-AUDIT".to_owned(),
                title: "Audit story".to_owned(),
                risk_lane: RiskLane::Normal,
                contract_doc: None,
                verify_command: Some("exit 0".to_owned()),
                notes: None,
            })
            .unwrap();
        repository
            .update_story(StoryUpdateInput {
                id: "US-AUDIT".to_owned(),
                status: Some("in_progress".to_owned()),
                evidence: None,
                unit: None,
                integration: None,
                e2e: None,
                platform: None,
                verify_command: None,
            })
            .unwrap();
        repository
            .add_story(StoryAddInput {
                id: "US-RETIRED".to_owned(),
                title: "Retired audit story".to_owned(),
                risk_lane: RiskLane::Normal,
                contract_doc: None,
                verify_command: Some("exit 0".to_owned()),
                notes: None,
            })
            .unwrap();
        repository
            .update_story(StoryUpdateInput {
                id: "US-RETIRED".to_owned(),
                status: Some("retired".to_owned()),
                evidence: None,
                unit: None,
                integration: None,
                e2e: None,
                platform: None,
                verify_command: None,
            })
            .unwrap();
        repository
            .add_backlog(BacklogAddInput {
                title: "Implemented without outcome".to_owned(),
                discovered_while: None,
                current_pain: None,
                suggestion: None,
                risk: Some(RiskLane::Tiny),
                predicted_impact: Some("Expected improvement".to_owned()),
                notes: None,
            })
            .unwrap();
        repository
            .close_backlog(BacklogCloseInput {
                id: 1,
                status: "implemented".to_owned(),
                actual_outcome: None,
            })
            .unwrap();
        repository
            .register_tool(ToolRegisterInput {
                name: "missing-tool".to_owned(),
                command: "definitely-missing-tool".to_owned(),
                description: "Missing command for audit coverage".to_owned(),
                responsibility: "Verification".to_owned(),
                args: Vec::new(),
                force: true,
                kind: "cli".to_owned(),
                capability: None,
                scan_target: None,
            })
            .unwrap();
        for _ in 0..2 {
            repository
                .record_trace(TraceInput {
                    task_summary: "Repeated friction trace".to_owned(),
                    intake_id: None,
                    story_id: None,
                    agent: Some("codex".to_owned()),
                    outcome: Some("completed".to_owned()),
                    duration_seconds: None,
                    token_estimate: None,
                    friction: Some("Context rules missed schema decision".to_owned()),
                    notes: None,
                    actions: CsvList::from_optional(Some("read".to_owned())),
                    files_read: CsvList::from_optional(Some("docs/HARNESS.md".to_owned())),
                    files_changed: CsvList::from_optional(Some(
                        "scripts/schema/003-tool-registry.sql".to_owned(),
                    )),
                    decisions: CsvList::from_optional(None),
                    errors: CsvList::from_optional(None),
                })
                .unwrap();
        }

        let audit = repository.audit().unwrap();
        assert_eq!(audit.orphaned_stories.len(), 1);
        assert_eq!(audit.unverified_stories.len(), 1);
        assert_eq!(audit.backlog_without_outcomes.len(), 1);
        assert_eq!(audit.broken_tools.len(), 1);
        assert!(audit.entropy_score() > 0);

        let proposals = repository.propose(true).unwrap();
        assert!(proposals.iter().any(|proposal| proposal
            .evidence
            .contains("Context rules missed schema decision")));
        assert!(proposals
            .iter()
            .all(|proposal| proposal.committed_backlog_id.is_some()));
        assert!(repository.query_backlog(BacklogFilter::Open).unwrap().len() >= 1);
    }

    #[test]
    fn propose_suppresses_resolved_validation_provider_friction() {
        let (_temp_dir, repository) = test_repository();
        repository.init().unwrap();

        for _ in 0..2 {
            repository
                .record_trace(TraceInput {
                    task_summary: "Validation provider friction trace".to_owned(),
                    intake_id: None,
                    story_id: None,
                    agent: Some("codex".to_owned()),
                    outcome: Some("completed".to_owned()),
                    duration_seconds: None,
                    token_estimate: None,
                    friction: Some(
                        "Tool registry lacks entries for local validation capabilities".to_owned(),
                    ),
                    notes: None,
                    actions: CsvList::from_optional(Some("query tools".to_owned())),
                    files_read: CsvList::from_optional(Some("docs/TOOL_REGISTRY.md".to_owned())),
                    files_changed: CsvList::from_optional(Some("harness.db".to_owned())),
                    decisions: CsvList::from_optional(None),
                    errors: CsvList::from_optional(None),
                })
                .unwrap();
        }

        let executable = std::env::current_exe()
            .unwrap()
            .to_string_lossy()
            .into_owned();
        for (name, capability) in [
            ("build-provider", "build-verification"),
            ("browser-provider", "browser-e2e"),
            ("coverage-provider", "coverage"),
            ("design-provider", "design-validation"),
            ("platform-provider", "platform-smoke"),
        ] {
            repository
                .register_tool(ToolRegisterInput {
                    name: name.to_owned(),
                    command: executable.clone(),
                    description: format!("{capability} test provider for proposal suppression"),
                    responsibility: "Verification".to_owned(),
                    args: Vec::new(),
                    force: false,
                    kind: "cli".to_owned(),
                    capability: Some(capability.to_owned()),
                    scan_target: None,
                })
                .unwrap();
        }
        repository.check_tools(None).unwrap();

        let proposals = repository.propose(false).unwrap();
        assert!(proposals.iter().all(|proposal| !proposal
            .title
            .contains("Tool registry lacks entries for local validation capabilities")));
    }

    #[test]
    fn story_backlog_trace_and_queries_work() {
        let (_temp_dir, repository) = test_repository();
        repository.init().unwrap();

        repository
            .add_story(StoryAddInput {
                id: "US-T".to_owned(),
                title: "Test story".to_owned(),
                risk_lane: RiskLane::Normal,
                contract_doc: None,
                verify_command: None,
                notes: None,
            })
            .unwrap();
        repository
            .update_story(StoryUpdateInput {
                id: "US-T".to_owned(),
                status: Some("implemented".to_owned()),
                evidence: Some("unit test".to_owned()),
                unit: Some(BoolFlag(1)),
                integration: None,
                e2e: None,
                platform: None,
                verify_command: None,
            })
            .unwrap();
        assert_eq!(repository.query_matrix().unwrap()[0].unit, 1);

        let backlog_id = repository
            .add_backlog(BacklogAddInput {
                title: "Improve CLI".to_owned(),
                discovered_while: None,
                current_pain: Some("manual SQL".to_owned()),
                suggestion: None,
                risk: Some(RiskLane::HighRisk),
                predicted_impact: None,
                notes: None,
            })
            .unwrap();
        repository
            .close_backlog(BacklogCloseInput {
                id: backlog_id,
                status: "implemented".to_owned(),
                actual_outcome: Some("done".to_owned()),
            })
            .unwrap();
        assert_eq!(
            repository.query_backlog(BacklogFilter::All).unwrap()[0]
                .actual_outcome
                .as_deref(),
            Some("done")
        );

        let trace_id = repository
            .record_trace(TraceInput {
                task_summary: "Test trace".to_owned(),
                intake_id: None,
                story_id: Some("US-T".to_owned()),
                agent: Some("test".to_owned()),
                outcome: Some("completed".to_owned()),
                duration_seconds: None,
                token_estimate: None,
                friction: Some("none".to_owned()),
                notes: None,
                actions: CsvList::from_optional(Some("one,two".to_owned())),
                files_read: CsvList::from_optional(None),
                files_changed: CsvList::from_optional(None),
                decisions: CsvList::from_optional(None),
                errors: CsvList::from_optional(None),
            })
            .unwrap();
        assert_eq!(trace_id, 1);
        assert_eq!(
            repository.query_traces().unwrap()[0].task_summary,
            "Test trace"
        );
        assert_eq!(
            repository.query_friction().unwrap()[0].harness_friction,
            "none"
        );
    }

    #[test]
    fn friction_query_includes_intake_context_and_filters_null_friction() {
        let (_temp_dir, repository) = test_repository();
        repository.init().unwrap();
        let intake_id = repository
            .record_intake(IntakeInput {
                input_type: InputType::ChangeRequest,
                summary: "Friction query context".to_owned(),
                risk_lane: RiskLane::Normal,
                risk_flags: CsvList::from_optional(None),
                affected_docs: CsvList::from_optional(None),
                story_id: None,
                notes: None,
            })
            .unwrap();
        repository
            .record_trace(TraceInput {
                task_summary: "Trace without friction".to_owned(),
                intake_id: Some(intake_id),
                story_id: None,
                agent: Some("codex".to_owned()),
                outcome: Some("completed".to_owned()),
                duration_seconds: None,
                token_estimate: None,
                friction: None,
                notes: None,
                actions: CsvList::from_optional(None),
                files_read: CsvList::from_optional(None),
                files_changed: CsvList::from_optional(None),
                decisions: CsvList::from_optional(None),
                errors: CsvList::from_optional(None),
            })
            .unwrap();
        repository
            .record_trace(TraceInput {
                task_summary: "Trace with linked friction".to_owned(),
                intake_id: Some(intake_id),
                story_id: None,
                agent: Some("codex".to_owned()),
                outcome: Some("completed".to_owned()),
                duration_seconds: None,
                token_estimate: None,
                friction: Some("Linked friction".to_owned()),
                notes: None,
                actions: CsvList::from_optional(None),
                files_read: CsvList::from_optional(None),
                files_changed: CsvList::from_optional(None),
                decisions: CsvList::from_optional(None),
                errors: CsvList::from_optional(None),
            })
            .unwrap();
        repository
            .record_trace(TraceInput {
                task_summary: "Trace with unlinked friction".to_owned(),
                intake_id: None,
                story_id: None,
                agent: Some("codex".to_owned()),
                outcome: Some("completed".to_owned()),
                duration_seconds: None,
                token_estimate: None,
                friction: Some("Unlinked friction".to_owned()),
                notes: None,
                actions: CsvList::from_optional(None),
                files_read: CsvList::from_optional(None),
                files_changed: CsvList::from_optional(None),
                decisions: CsvList::from_optional(None),
                errors: CsvList::from_optional(None),
            })
            .unwrap();

        let friction = repository.query_friction().unwrap();

        assert_eq!(friction.len(), 2);
        assert_eq!(friction[0].risk_lane, None);
        assert_eq!(friction[0].input_type, None);
        assert_eq!(friction[1].risk_lane.as_deref(), Some("normal"));
        assert_eq!(friction[1].input_type.as_deref(), Some("change_request"));
    }

    #[test]
    fn import_brownfield_seeds_markdown_state_idempotently() {
        let temp_dir = tempfile::tempdir().unwrap();
        let repo_root = temp_dir.path().join("repo");
        fs::create_dir_all(repo_root.join("docs/decisions")).unwrap();
        fs::write(
            repo_root.join("docs/TEST_MATRIX.md"),
            r#"# Test Matrix

| Story | Contract | Unit | Integration | E2E | Platform | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| US-010 | docs/product/tasks.md | yes | pending | no | mac smoke | implemented | cargo test |
"#,
        )
        .unwrap();
        fs::write(
            repo_root.join("docs/decisions/0007-test-decision.md"),
            r#"# Test Decision

## Status

Accepted
"#,
        )
        .unwrap();
        fs::write(
            repo_root.join("docs/HARNESS_BACKLOG.md"),
            r#"# Harness Backlog

## Items

### Title

Import existing docs

### Discovered While

Testing brownfield import

### Current Pain

Existing Harness v0 repos have markdown truth.

### Suggested Improvement

Seed the durable database.

### Risk

normal

### Status

accepted

### Title

Keep installer checksum

### Discovered While

Testing release install

### Current Pain

Downloads need verification.

### Suggested Improvement

Verify sha256 files.

### Risk

high-risk

### Status

implemented
"#,
        )
        .unwrap();

        let source_repo_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .ancestors()
            .nth(2)
            .unwrap()
            .to_path_buf();
        let repository = SqliteHarnessRepository::new(
            repo_root.clone(),
            temp_dir.path().join("harness.db"),
            source_repo_root.join("scripts/schema"),
        );
        repository.init().unwrap();

        let first = repository.import_brownfield().unwrap();
        let second = repository.import_brownfield().unwrap();

        assert_eq!(
            first,
            BrownfieldImportResult {
                stories: 1,
                decisions: 1,
                backlog_items: 2,
            }
        );
        assert_eq!(second.backlog_items, 2);

        let matrix = repository.query_matrix().unwrap();
        assert_eq!(matrix[0].id, "US-010");
        assert_eq!(matrix[0].title, "docs/product/tasks.md");
        assert_eq!(matrix[0].status, "implemented");
        assert_eq!(matrix[0].unit, 1);
        assert_eq!(matrix[0].integration, 0);
        assert_eq!(matrix[0].platform, 1);

        let decisions = repository.query_decisions().unwrap();
        assert_eq!(decisions[0].id, "0007-test-decision");
        assert_eq!(decisions[0].status, "accepted");

        let backlog = repository.query_backlog(BacklogFilter::All).unwrap();
        assert_eq!(backlog.len(), 2);
        assert!(backlog
            .iter()
            .any(|item| item.title == "Import existing docs"
                && item.status == "accepted"
                && item.risk.as_deref() == Some("normal")));
        assert!(backlog
            .iter()
            .any(|item| item.title == "Keep installer checksum"
                && item.status == "implemented"
                && item.risk.as_deref() == Some("high_risk")));
    }

    #[test]
    fn filters_open_and_closed_backlog_items() {
        let (_temp_dir, repository) = test_repository();
        repository.init().unwrap();

        let proposed_id = repository
            .add_backlog(BacklogAddInput {
                title: "Proposed item".to_owned(),
                discovered_while: None,
                current_pain: None,
                suggestion: None,
                risk: Some(RiskLane::Tiny),
                predicted_impact: Some("Should improve trace review.".to_owned()),
                notes: None,
            })
            .unwrap();
        let implemented_id = repository
            .add_backlog(BacklogAddInput {
                title: "Implemented item".to_owned(),
                discovered_while: None,
                current_pain: None,
                suggestion: None,
                risk: Some(RiskLane::Normal),
                predicted_impact: Some("Should reduce missing proof.".to_owned()),
                notes: None,
            })
            .unwrap();
        repository
            .close_backlog(BacklogCloseInput {
                id: implemented_id,
                status: "implemented".to_owned(),
                actual_outcome: Some("Proof gaps were found earlier.".to_owned()),
            })
            .unwrap();

        let all = repository.query_backlog(BacklogFilter::All).unwrap();
        let open = repository.query_backlog(BacklogFilter::Open).unwrap();
        let closed = repository.query_backlog(BacklogFilter::Closed).unwrap();

        assert_eq!(all.len(), 2);
        assert_eq!(open.len(), 1);
        assert_eq!(open[0].id, proposed_id);
        assert_eq!(closed.len(), 1);
        assert_eq!(closed[0].id, implemented_id);
        assert_eq!(
            closed[0].actual_outcome.as_deref(),
            Some("Proof gaps were found earlier.")
        );
    }

    #[test]
    fn scores_latest_and_specific_trace_with_lane_lookup() {
        let (_temp_dir, repository) = test_repository();
        repository.init().unwrap();
        let intake_id = repository
            .record_intake(IntakeInput {
                input_type: InputType::HarnessImprovement,
                summary: "High risk trace quality test".to_owned(),
                risk_lane: RiskLane::HighRisk,
                risk_flags: CsvList::from_optional(None),
                affected_docs: CsvList::from_optional(None),
                story_id: None,
                notes: None,
            })
            .unwrap();
        let first_trace = repository
            .record_trace(TraceInput {
                task_summary: "Minimal trace test".to_owned(),
                intake_id: None,
                story_id: None,
                agent: None,
                outcome: Some("completed".to_owned()),
                duration_seconds: None,
                token_estimate: None,
                friction: None,
                notes: None,
                actions: CsvList::from_optional(None),
                files_read: CsvList::from_optional(None),
                files_changed: CsvList::from_optional(None),
                decisions: CsvList::from_optional(None),
                errors: CsvList::from_optional(None),
            })
            .unwrap();
        repository
            .record_trace(TraceInput {
                task_summary: "Standard trace linked to high risk intake".to_owned(),
                intake_id: Some(intake_id),
                story_id: None,
                agent: Some("codex".to_owned()),
                outcome: Some("completed".to_owned()),
                duration_seconds: None,
                token_estimate: None,
                friction: Some("none".to_owned()),
                notes: None,
                actions: CsvList::from_optional(Some("read,patched".to_owned())),
                files_read: CsvList::from_optional(Some("PHASE3.md".to_owned())),
                files_changed: CsvList::from_optional(Some(
                    "crates/harness-cli/src/domain.rs".to_owned(),
                )),
                decisions: CsvList::from_optional(None),
                errors: CsvList::from_optional(None),
            })
            .unwrap();

        let latest = repository.score_trace(None).unwrap();
        assert_eq!(latest.achieved, TraceQualityTier::Standard);
        assert_eq!(latest.required, Some(TraceQualityTier::Detailed));
        assert!(!latest.meets_requirement);
        assert!(latest
            .missing_detailed
            .iter()
            .any(|field| field.starts_with("decisions_made")));

        let specific = repository.score_trace(Some(first_trace)).unwrap();
        assert_eq!(specific.trace_id, first_trace);
        assert_eq!(specific.achieved, TraceQualityTier::Minimal);
        assert_eq!(specific.required, None);
        assert!(specific.meets_requirement);
    }
}
