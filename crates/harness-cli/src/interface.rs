use std::env;
use std::path::PathBuf;
use std::str::FromStr;

use clap::{Args, Parser, Subcommand};
use thiserror::Error;

use crate::application::{
    BacklogAddInput, BacklogCloseInput, BrownfieldImportResult, ChangesetApplyResult,
    DbRebuildResult, DecisionAddInput, HarnessContext, HarnessService, InitResult, IntakeInput,
    InterventionAddInput, InterventionFilter, MigrateResult, QueryTable, StoryAddInput,
    StoryBacklogLinkInput, StoryDependencyInput, StoryUpdateInput, ToolRegisterInput, TraceInput,
};
use crate::domain::{
    normalize_capability, parse_optional_integer, parse_tool_args, proof_display,
    validate_responsibility, validate_tool_kind, BacklogFilter, BacklogRecord, BoolFlag,
    ContextScoreResult, CsvList, DecisionRecord, FrictionRecord, HarnessStats, ImprovementProposal,
    InputType, IntakeRecord, InterventionRecord, RiskLane, StoryMatrixRecord, StoryVerifyAllResult,
    ToolEntry, TraceQualityTier, TraceRecord, TraceScoreResult, RISK_LANE_HELP,
};
use crate::infrastructure::{ProposalDecision, ProposalResult, ToolCheckResult};

#[derive(Parser, Debug)]
#[command(name = "harness-cli")]
#[command(about = "durable layer for the project harness", long_about = None)]
#[command(version)]
pub struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand, Debug)]
enum Command {
    /// Create the harness database if it does not already exist.
    Init,
    /// Apply schema migrations.
    Migrate,
    /// Seed or refresh the database from existing markdown state.
    Import(ImportArgs),
    /// Record a feature intake classification.
    Intake(IntakeArgs),
    /// Add or update a story.
    Story(StoryArgs),
    /// Add a decision or run its verification.
    Decision(DecisionArgs),
    /// Add or close a backlog item.
    Backlog(BacklogArgs),
    /// Register or remove external tools.
    Tool(ToolArgs),
    /// Record a human, review, CI, or agent intervention.
    Intervention(InterventionArgs),
    /// Record an agent execution trace.
    Trace(TraceArgs),
    /// Score a trace against the trace quality tiers.
    ScoreTrace(ScoreTraceArgs),
    /// Score trace context reads against CONTEXT_RULES.md.
    ScoreContext { trace_id: String },
    /// Run drift audit and entropy score.
    Audit(AuditArgs),
    /// Generate improvement proposals from observed patterns.
    Propose(ProposeArgs),
    /// Manage harness database changesets.
    Db(DbArgs),
    /// Query harness data.
    Query(QueryArgs),
}

#[derive(Args, Debug)]
struct AuditArgs {
    /// Explicitly persist audit evidence episode transitions.
    #[arg(long)]
    record_evidence: bool,
}

#[derive(Args, Debug)]
#[command(after_help = RISK_LANE_HELP)]
struct IntakeArgs {
    #[arg(long = "type")]
    input_type: String,
    #[arg(long)]
    summary: String,
    #[arg(long, value_name = "tiny|normal|high-risk")]
    lane: String,
    #[arg(long)]
    flags: Option<String>,
    #[arg(long)]
    docs: Option<String>,
    #[arg(long)]
    story: Option<String>,
    #[arg(long)]
    notes: Option<String>,
}

#[derive(Args, Debug)]
struct ImportArgs {
    #[command(subcommand)]
    source: ImportSource,
}

#[derive(Subcommand, Debug)]
enum ImportSource {
    /// Import TEST_MATRIX, decisions, and backlog markdown.
    Brownfield,
}

#[derive(Args, Debug)]
struct StoryArgs {
    #[command(subcommand)]
    action: StoryAction,
}

#[derive(Subcommand, Debug)]
enum StoryAction {
    #[command(after_help = RISK_LANE_HELP)]
    Add(StoryAddArgs),
    #[command(
        after_help = "Proof flags use numeric booleans: --unit 1 --integration 1 --e2e 0 --platform 0. Do not use yes/no."
    )]
    Update(StoryUpdateArgs),
    /// Add or remove a dependency edge where blocker -> blocked.
    Dependency(StoryDependencyArgs),
    /// Link a story to a stable Harness backlog occurrence.
    Backlog(StoryBacklogArgs),
    #[command(
        after_help = "story verify only accepts the story id. Configure proof with story add/update --verify, then record proof flags with story update."
    )]
    Verify {
        /// Story id to verify.
        id: String,
    },
    /// Run fresh proof and atomically mark a completion-eligible story implemented.
    Complete {
        /// Story id to complete.
        id: String,
    },
    /// Verify every story, skipping stories without verify_command.
    VerifyAll,
}

#[derive(Args, Debug)]
struct StoryDependencyArgs {
    #[command(subcommand)]
    action: StoryDependencyAction,
}

#[derive(Subcommand, Debug)]
enum StoryDependencyAction {
    /// Add a cycle-safe dependency edge.
    Add(StoryDependencyMutationArgs),
    /// Remove a dependency edge; a missing edge is unchanged.
    Remove(StoryDependencyMutationArgs),
}

#[derive(Args, Debug)]
struct StoryBacklogArgs {
    #[command(subcommand)]
    action: StoryBacklogAction,
}

#[derive(Subcommand, Debug)]
enum StoryBacklogAction {
    Link(StoryBacklogLinkArgs),
    Unlink(StoryBacklogUnlinkArgs),
    List(StoryBacklogListArgs),
}

#[derive(Args, Debug)]
struct StoryBacklogLinkArgs {
    #[arg(long)]
    story: String,
    #[arg(long)]
    backlog: String,
    #[arg(long, value_parser = ["resolves", "references"])]
    relationship: String,
}

#[derive(Args, Debug)]
struct StoryBacklogUnlinkArgs {
    #[arg(long)]
    story: String,
    #[arg(long)]
    backlog: String,
}

#[derive(Args, Debug)]
struct StoryBacklogListArgs {
    #[arg(long)]
    story: Option<String>,
    #[arg(long)]
    backlog: Option<String>,
}

#[derive(Args, Debug)]
struct StoryDependencyMutationArgs {
    /// The story that must complete first.
    #[arg(long)]
    blocker: String,
    /// The story blocked by --blocker.
    #[arg(long)]
    blocked: String,
}

#[derive(Args, Debug)]
struct StoryAddArgs {
    #[arg(long)]
    id: String,
    #[arg(long)]
    title: String,
    #[arg(long, value_name = "tiny|normal|high-risk")]
    lane: String,
    #[arg(long)]
    contract: Option<String>,
    #[arg(long)]
    verify: Option<String>,
    #[arg(long)]
    notes: Option<String>,
}

#[derive(Args, Debug)]
struct StoryUpdateArgs {
    #[arg(long)]
    id: String,
    #[arg(long)]
    status: Option<String>,
    #[arg(long)]
    evidence: Option<String>,
    #[arg(long, value_name = "0|1")]
    unit: Option<String>,
    #[arg(long, value_name = "0|1")]
    integration: Option<String>,
    #[arg(long, value_name = "0|1")]
    e2e: Option<String>,
    #[arg(long, value_name = "0|1")]
    platform: Option<String>,
    #[arg(long)]
    verify: Option<String>,
}

#[derive(Args, Debug)]
struct DecisionArgs {
    #[command(subcommand)]
    action: DecisionAction,
}

#[derive(Subcommand, Debug)]
enum DecisionAction {
    Add(DecisionAddArgs),
    Verify { id: String },
}

#[derive(Args, Debug)]
struct DecisionAddArgs {
    #[arg(long)]
    id: String,
    #[arg(long)]
    title: String,
    #[arg(long, default_value = "accepted")]
    status: String,
    #[arg(long)]
    doc: Option<String>,
    #[arg(long)]
    verify: Option<String>,
    #[arg(long)]
    predicted: Option<String>,
    #[arg(long)]
    notes: Option<String>,
}

#[derive(Args, Debug)]
struct BacklogArgs {
    #[command(subcommand)]
    action: BacklogAction,
}

#[derive(Subcommand, Debug)]
enum BacklogAction {
    #[command(after_help = RISK_LANE_HELP)]
    Add(BacklogAddArgs),
    Close(BacklogCloseArgs),
}

#[derive(Args, Debug)]
struct BacklogAddArgs {
    #[arg(long)]
    title: String,
    #[arg(long = "while")]
    discovered_while: Option<String>,
    #[arg(long)]
    pain: Option<String>,
    #[arg(long)]
    suggestion: Option<String>,
    #[arg(long, value_name = "tiny|normal|high-risk")]
    risk: Option<String>,
    #[arg(long)]
    predicted: Option<String>,
    #[arg(long)]
    notes: Option<String>,
}

#[derive(Args, Debug)]
struct BacklogCloseArgs {
    #[arg(long)]
    id: String,
    #[arg(long, default_value = "implemented")]
    status: String,
    #[arg(long)]
    outcome: Option<String>,
}

#[derive(Args, Debug)]
struct ToolArgs {
    #[command(subcommand)]
    action: ToolAction,
}

#[derive(Subcommand, Debug)]
enum ToolAction {
    Register(ToolRegisterArgs),
    /// Scan registered tools and persist present/missing/unknown status.
    Check(ToolCheckArgs),
    Remove {
        #[arg(long)]
        name: String,
    },
}

#[derive(Args, Debug)]
struct ToolRegisterArgs {
    #[arg(long)]
    name: String,
    #[arg(long)]
    command: String,
    #[arg(long)]
    description: String,
    #[arg(long)]
    responsibility: String,
    #[arg(long)]
    args: Option<String>,
    #[arg(long)]
    force: bool,
    /// How the tool is reached and probed: cli, binary, mcp, skill, http.
    #[arg(long, default_value = "cli")]
    kind: String,
    /// Workflow purpose a step looks the tool up by (kebab-case).
    #[arg(long)]
    capability: Option<String>,
    /// Declarative path/URL `tool check` resolves to decide presence.
    #[arg(long)]
    scan: Option<String>,
}

#[derive(Args, Debug)]
struct ToolCheckArgs {
    /// Check one tool by name; omit to check every registered tool.
    #[arg(long)]
    name: Option<String>,
    #[arg(long)]
    json: bool,
}

#[derive(Args, Debug)]
struct InterventionArgs {
    #[command(subcommand)]
    action: InterventionAction,
}

#[derive(Subcommand, Debug)]
enum InterventionAction {
    Add(InterventionAddArgs),
}

#[derive(Args, Debug)]
struct InterventionAddArgs {
    #[arg(long)]
    trace: Option<String>,
    #[arg(long)]
    story: Option<String>,
    #[arg(long = "type")]
    intervention_type: String,
    #[arg(long)]
    description: String,
    #[arg(long)]
    source: String,
    #[arg(long)]
    impact: Option<String>,
}

#[derive(Args, Debug)]
struct TraceArgs {
    #[arg(long)]
    summary: String,
    #[arg(long)]
    intake: Option<String>,
    #[arg(long)]
    story: Option<String>,
    #[arg(long)]
    agent: Option<String>,
    #[arg(long)]
    outcome: Option<String>,
    #[arg(long)]
    duration: Option<String>,
    #[arg(long)]
    tokens: Option<String>,
    #[arg(long)]
    friction: Option<String>,
    #[arg(long)]
    actions: Option<String>,
    #[arg(long = "read")]
    files_read: Option<String>,
    #[arg(long = "changed")]
    files_changed: Option<String>,
    #[arg(long)]
    decisions: Option<String>,
    #[arg(long)]
    errors: Option<String>,
    #[arg(long)]
    notes: Option<String>,
}

#[derive(Args, Debug)]
struct ScoreTraceArgs {
    /// Score a specific trace id. Defaults to the latest trace.
    #[arg(long)]
    id: Option<String>,
}

#[derive(Args, Debug)]
struct ProposeArgs {
    /// Removed bulk writer. Select one key with --accept or --reject instead.
    #[arg(long)]
    commit: bool,
    #[arg(long, conflicts_with = "reject")]
    accept: Option<String>,
    #[arg(long, conflicts_with = "accept")]
    reject: Option<String>,
    #[arg(long)]
    outcome_manual: bool,
    #[arg(long)]
    outcome_due: Option<String>,
    #[arg(long)]
    outcome_after_traces: Option<String>,
    #[arg(long)]
    reason: Option<String>,
}

#[derive(Args, Debug)]
struct DbArgs {
    #[command(subcommand)]
    action: DbAction,
}

#[derive(Subcommand, Debug)]
enum DbAction {
    Changeset(ChangesetArgs),
    /// Rebuild a fresh harness database from committed changesets.
    Rebuild {
        #[arg(long = "from")]
        from: PathBuf,
    },
}

#[derive(Args, Debug)]
struct ChangesetArgs {
    #[command(subcommand)]
    action: ChangesetAction,
}

#[derive(Subcommand, Debug)]
enum ChangesetAction {
    /// Apply one semantic changeset file idempotently.
    Apply { path: PathBuf },
}

#[derive(Args, Debug)]
struct QueryArgs {
    #[command(subcommand)]
    view: QueryView,
}

#[derive(Args, Debug)]
struct MatrixQueryArgs {
    /// Render proof flags as CLI input values, 1 and 0, instead of yes and no.
    #[arg(long)]
    numeric: bool,
}

#[derive(Args, Debug)]
struct BacklogQueryArgs {
    /// Show only proposed and accepted backlog items.
    #[arg(long, conflicts_with = "closed")]
    open: bool,
    /// Show only implemented and rejected backlog items.
    #[arg(long)]
    closed: bool,
    /// Also render relationships for one backlog occurrence.
    #[arg(long)]
    id: Option<String>,
}

#[derive(Subcommand, Debug)]
enum QueryView {
    /// Test matrix.
    Matrix(MatrixQueryArgs),
    /// Story dependency edges, optionally filtered to one story.
    Dependencies(DependenciesQueryArgs),
    /// Harness improvement proposals.
    Backlog(BacklogQueryArgs),
    /// Decision records.
    Decisions,
    /// Recent intake classifications.
    Intakes,
    /// Recent traces.
    Traces,
    /// Traces with harness friction.
    Friction,
    /// Machine-readable and registered tool manifest.
    Tools(ToolsQueryArgs),
    /// Intervention records.
    Interventions(InterventionsQueryArgs),
    /// Summary counts.
    Stats,
    /// Run arbitrary SQL.
    Sql { query: Vec<String> },
}

#[derive(Args, Debug)]
struct DependenciesQueryArgs {
    /// Show edges where this story is either the blocker or blocked story.
    #[arg(long)]
    story: Option<String>,
}

#[derive(Args, Debug)]
struct ToolsQueryArgs {
    #[arg(long)]
    json: bool,
    #[arg(long)]
    summary: bool,
    #[arg(long)]
    responsibility: Option<String>,
    /// Filter to tools that provide this capability.
    #[arg(long)]
    capability: Option<String>,
    /// Filter to tools with this scanned status: present, missing, unknown.
    #[arg(long)]
    status: Option<String>,
}

#[derive(Args, Debug)]
struct InterventionsQueryArgs {
    #[arg(long)]
    trace: Option<String>,
    #[arg(long)]
    story: Option<String>,
    #[arg(long = "type")]
    intervention_type: Option<String>,
}

#[derive(Debug, Error)]
pub enum InterfaceError {
    #[error("{0}")]
    InvalidArgument(String),
    #[error("{0}")]
    ParseHarnessValue(#[from] crate::domain::ParseHarnessValueError),
    #[error("{0}")]
    ToolValidation(#[from] crate::domain::ToolValidationError),
    #[error("{0}")]
    Infrastructure(#[from] crate::infrastructure::HarnessInfraError),
    #[error("could not determine current directory: {0}")]
    CurrentDir(std::io::Error),
    #[error("query sql requires a SQL statement")]
    EmptySql,
}

pub fn run(cli: Cli) -> Result<(), InterfaceError> {
    let service = HarnessService::new(resolve_context()?);

    match cli.command {
        Command::Init => print_init_result(service.init()?),
        Command::Migrate => print_migrate_result(service.migrate()?),
        Command::Import(args) => match args.source {
            ImportSource::Brownfield => {
                print_brownfield_import_result(service.import_brownfield()?)
            }
        },
        Command::Intake(args) => {
            let id = service.record_intake(IntakeInput {
                input_type: InputType::from_str(&args.input_type)?,
                summary: args.summary,
                risk_lane: RiskLane::from_str(&args.lane)?,
                risk_flags: CsvList::from_optional(args.flags),
                affected_docs: CsvList::from_optional(args.docs),
                story_id: args.story,
                notes: args.notes,
            })?;
            println!("Intake #{id} recorded.");
        }
        Command::Story(args) => match args.action {
            StoryAction::Add(args) => {
                service.add_story(StoryAddInput {
                    id: args.id.clone(),
                    title: args.title,
                    risk_lane: RiskLane::from_str(&args.lane)?,
                    contract_doc: args.contract,
                    verify_command: args.verify,
                    notes: args.notes,
                })?;
                println!("Story {} added.", args.id);
            }
            StoryAction::Update(args) => {
                service.update_story(StoryUpdateInput {
                    id: args.id.clone(),
                    status: args.status,
                    evidence: args.evidence,
                    unit: parse_optional_bool("story update: --unit", args.unit)?,
                    integration: parse_optional_bool(
                        "story update: --integration",
                        args.integration,
                    )?,
                    e2e: parse_optional_bool("story update: --e2e", args.e2e)?,
                    platform: parse_optional_bool("story update: --platform", args.platform)?,
                    verify_command: args.verify,
                })?;
                println!("Story {} updated.", args.id);
            }
            StoryAction::Dependency(args) => match args.action {
                StoryDependencyAction::Add(args) => {
                    let changed = service.add_story_dependency(StoryDependencyInput {
                        blocker: args.blocker.clone(),
                        blocked: args.blocked.clone(),
                    })?;
                    println!(
                        "Story dependency {} -> {} {}.",
                        args.blocker,
                        args.blocked,
                        if changed { "added" } else { "unchanged" }
                    );
                }
                StoryDependencyAction::Remove(args) => {
                    let changed = service.remove_story_dependency(StoryDependencyInput {
                        blocker: args.blocker.clone(),
                        blocked: args.blocked.clone(),
                    })?;
                    println!(
                        "Story dependency {} -> {} {}.",
                        args.blocker,
                        args.blocked,
                        if changed { "removed" } else { "unchanged" }
                    );
                }
            },
            StoryAction::Backlog(args) => match args.action {
                StoryBacklogAction::Link(args) => {
                    let backlog_id = parse_optional_integer(
                        "story backlog link: --backlog",
                        Some(args.backlog),
                    )?
                    .expect("value provided");
                    let changed = service.link_story_backlog(StoryBacklogLinkInput {
                        story_id: args.story.clone(),
                        backlog_id,
                        relationship: args.relationship.clone(),
                    })?;
                    println!(
                        "Story backlog link {} -> #{} ({}) {}.",
                        args.story,
                        backlog_id,
                        args.relationship,
                        if changed { "updated" } else { "unchanged" }
                    );
                }
                StoryBacklogAction::Unlink(args) => {
                    let backlog_id = parse_optional_integer(
                        "story backlog unlink: --backlog",
                        Some(args.backlog),
                    )?
                    .expect("value provided");
                    let changed = service.unlink_story_backlog(&args.story, backlog_id)?;
                    println!(
                        "Story backlog link {} -> #{} {}.",
                        args.story,
                        backlog_id,
                        if changed { "removed" } else { "unchanged" }
                    );
                }
                StoryBacklogAction::List(args) => {
                    let backlog_id =
                        parse_optional_integer("story backlog list: --backlog", args.backlog)?;
                    print_story_backlog_links(
                        &service.query_story_backlog_links(args.story.as_deref(), backlog_id)?,
                    );
                }
            },
            StoryAction::Verify { id } => {
                let result = service.verify_story(&id)?;
                println!("Running: {}", result.command);
                print!("{}", result.stdout);
                print!("{}", result.stderr);
                println!("Story {id} verification: {}", result.result);
                if result.result == "fail" {
                    std::process::exit(1);
                }
            }
            StoryAction::Complete { id } => {
                let result = service.complete_story(&id)?;
                println!("Running: {}", result.command);
                print!("{}", result.stdout);
                print!("{}", result.stderr);
                if let Some(intake_uid) = &result.intake_uid {
                    println!("Completion intake: {intake_uid}");
                }
                if let Some(trace_uid) = &result.implementation_trace_uid {
                    println!("Implementation trace: {trace_uid}");
                }
                println!(
                    "Story {id} completion: {}; closed backlog: {}; already closed: {}; references: {}",
                    result.result,
                    result
                        .closed_backlog_ids
                        .iter()
                        .map(ToString::to_string)
                        .collect::<Vec<_>>()
                        .join(", "),
                    result
                        .already_closed_backlog_ids
                        .iter()
                        .map(ToString::to_string)
                        .collect::<Vec<_>>()
                        .join(", "),
                    result
                        .referenced_backlog_ids
                        .iter()
                        .map(ToString::to_string)
                        .collect::<Vec<_>>()
                        .join(", ")
                );
                if result.result == "fail" {
                    std::process::exit(1);
                }
            }
            StoryAction::VerifyAll => {
                let result = service.verify_all_stories()?;
                print_story_verify_all(&result);
                if result.failed() > 0 {
                    std::process::exit(1);
                }
            }
        },
        Command::Decision(args) => match args.action {
            DecisionAction::Add(args) => {
                service.add_decision(DecisionAddInput {
                    id: args.id.clone(),
                    title: args.title,
                    status: args.status,
                    doc_path: args.doc,
                    verify_command: args.verify,
                    predicted_impact: args.predicted,
                    notes: args.notes,
                })?;
                println!("Decision {} added.", args.id);
            }
            DecisionAction::Verify { id } => {
                let result = service.verify_decision(&id)?;
                println!("Running: {}", result.command);
                println!("Decision {id} verification: {}", result.result);
                if result.result == "fail" {
                    std::process::exit(1);
                }
            }
        },
        Command::Backlog(args) => match args.action {
            BacklogAction::Add(args) => {
                let id = service.add_backlog(BacklogAddInput {
                    title: args.title,
                    discovered_while: args.discovered_while,
                    current_pain: args.pain,
                    suggestion: args.suggestion,
                    risk: args
                        .risk
                        .map(|value| RiskLane::from_str(&value))
                        .transpose()?,
                    predicted_impact: args.predicted,
                    notes: args.notes,
                })?;
                println!("Backlog #{id} added.");
            }
            BacklogAction::Close(args) => {
                let id = parse_optional_integer("backlog close: --id", Some(args.id))?
                    .expect("value provided");
                let status = args.status;
                service.close_backlog(BacklogCloseInput {
                    id,
                    status: status.clone(),
                    actual_outcome: args.outcome,
                })?;
                println!("Backlog #{id} closed as {status}.");
            }
        },
        Command::Tool(args) => match args.action {
            ToolAction::Register(args) => {
                let kind = validate_tool_kind(&args.kind)?;
                let capability = args
                    .capability
                    .as_deref()
                    .map(normalize_capability)
                    .transpose()?;
                service.register_tool(ToolRegisterInput {
                    name: args.name.clone(),
                    command: args.command,
                    description: args.description,
                    responsibility: validate_responsibility(&args.responsibility)?,
                    args: parse_tool_args(args.args)?,
                    force: args.force,
                    kind,
                    capability,
                    scan_target: args.scan,
                })?;
                println!("Tool {} registered.", args.name);
            }
            ToolAction::Check(args) => {
                let results = service.check_tools(args.name)?;
                if args.json {
                    print_tool_check_json(&results);
                } else {
                    print_tool_check_summary(&results);
                }
            }
            ToolAction::Remove { name } => {
                service.remove_tool(&name)?;
                println!("Tool {name} removed.");
            }
        },
        Command::Intervention(args) => match args.action {
            InterventionAction::Add(args) => {
                let id = service.add_intervention(InterventionAddInput {
                    trace_id: parse_optional_integer("intervention add: --trace", args.trace)?,
                    story_id: args.story,
                    intervention_type: args.intervention_type,
                    description: args.description,
                    source: args.source,
                    impact: args.impact,
                })?;
                println!("Intervention #{id} recorded.");
            }
        },
        Command::Trace(args) => {
            let story_id = args.story.clone();
            let id = service.record_trace(TraceInput {
                task_summary: args.summary,
                intake_id: parse_optional_integer("trace: --intake", args.intake)?,
                story_id: args.story,
                agent: args.agent,
                outcome: args.outcome,
                duration_seconds: parse_optional_integer("trace: --duration", args.duration)?,
                token_estimate: parse_optional_integer("trace: --tokens", args.tokens)?,
                friction: args.friction,
                notes: args.notes,
                actions: CsvList::from_optional(args.actions),
                files_read: CsvList::from_optional(args.files_read),
                files_changed: CsvList::from_optional(args.files_changed),
                decisions: CsvList::from_optional(args.decisions),
                errors: CsvList::from_optional(args.errors),
            })?;
            println!("Trace #{id} recorded.");
            let result = service.score_trace(Some(id))?;
            print_trace_score(&result, false);
            println!("Reminder: Record any human corrections with: harness-cli intervention add");
            if let Some(story_id) = story_id {
                print_story_verify_warning(&service, &story_id)?;
            }
        }
        Command::ScoreTrace(args) => {
            let id = parse_optional_integer("score-trace: --id", args.id)?;
            let result = service.score_trace(id)?;
            print_trace_score(&result, id.is_none());
            if !result.meets_requirement {
                std::process::exit(1);
            }
        }
        Command::ScoreContext { trace_id } => {
            let id = parse_optional_integer("score-context: trace-id", Some(trace_id))?
                .expect("value provided");
            print_context_score(&service.score_context(id)?);
        }
        Command::Audit(args) => {
            let result = if args.record_evidence {
                service.audit_record_evidence()?
            } else {
                service.audit()?
            };
            print_audit(&result)
        }
        Command::Propose(args) => {
            if args.commit {
                eprintln!("use propose --accept <proposal-key> or propose --reject <proposal-key>");
                std::process::exit(2);
            }
            let decision = match (args.accept, args.reject) {
                (None, None) => {
                    if args.outcome_manual
                        || args.outcome_due.is_some()
                        || args.outcome_after_traces.is_some()
                        || args.reason.is_some()
                    {
                        return Err(InterfaceError::InvalidArgument(
                            "propose decision flags require --accept or --reject".to_owned(),
                        ));
                    }
                    ProposalDecision::Preview
                }
                (Some(key), None) => {
                    let schedules = usize::from(args.outcome_manual)
                        + usize::from(args.outcome_due.is_some())
                        + usize::from(args.outcome_after_traces.is_some());
                    if schedules != 1 || args.reason.is_some() {
                        return Err(InterfaceError::InvalidArgument(
                            "propose --accept requires exactly one outcome schedule".to_owned(),
                        ));
                    }
                    let schedule = if args.outcome_manual {
                        "manual".to_owned()
                    } else if let Some(value) = args.outcome_due {
                        format!("due:{value}")
                    } else {
                        format!("traces:{}", args.outcome_after_traces.unwrap_or_default())
                    };
                    ProposalDecision::Accept { key, schedule }
                }
                (None, Some(key)) => {
                    if args.outcome_manual
                        || args.outcome_due.is_some()
                        || args.outcome_after_traces.is_some()
                    {
                        return Err(InterfaceError::InvalidArgument(
                            "propose --reject does not accept an outcome schedule".to_owned(),
                        ));
                    }
                    ProposalDecision::Reject {
                        key,
                        reason: args.reason.ok_or_else(|| {
                            InterfaceError::InvalidArgument(
                                "propose --reject requires --reason".to_owned(),
                            )
                        })?,
                    }
                }
                _ => unreachable!(),
            };
            print_proposal_result(&service.propose(decision)?)
        }
        Command::Db(args) => match args.action {
            DbAction::Changeset(args) => match args.action {
                ChangesetAction::Apply { path } => {
                    print_changeset_apply_result(service.apply_changeset(&path)?)
                }
            },
            DbAction::Rebuild { from } => print_db_rebuild_result(service.rebuild_db(&from)?),
        },
        Command::Query(args) => match args.view {
            QueryView::Matrix(args) => print_matrix(&service.query_matrix()?, args.numeric),
            QueryView::Dependencies(args) => {
                print_dependencies(&service.query_story_dependencies(args.story.as_deref())?)
            }
            QueryView::Backlog(args) => {
                let filter = backlog_filter(&args);
                let id = parse_optional_integer("query backlog: --id", args.id)?;
                if let Some(id) = id {
                    print_query_table(&service.query_sql(&format!(
                        "SELECT backlog.id, backlog.uid, backlog.status, backlog.proposal_key, backlog.predecessor_uid, backlog.resolution_evidence, (SELECT story_id FROM story_backlog_link WHERE backlog_uid=backlog.uid AND relationship='resolves') AS resolver, COALESCE((SELECT group_concat(story_id, ', ') FROM story_backlog_link WHERE backlog_uid=backlog.uid AND relationship='references'), '') AS reference_stories FROM backlog WHERE backlog.id={id};"
                    ))?);
                } else {
                    print_backlog(&service.query_backlog(filter)?);
                }
            }
            QueryView::Decisions => print_decisions(&service.query_decisions()?),
            QueryView::Intakes => print_intakes(&service.query_intakes()?),
            QueryView::Traces => print_traces(&service.query_traces()?),
            QueryView::Friction => print_friction(&service.query_friction()?),
            QueryView::Tools(args) => {
                let responsibility = args
                    .responsibility
                    .map(|value| validate_responsibility(&value))
                    .transpose()?;
                let capability = args
                    .capability
                    .as_deref()
                    .map(normalize_capability)
                    .transpose()?;
                let mut tools = service.query_tools(responsibility, capability)?;
                if let Some(status) = args.status.as_deref() {
                    let normalized = status.trim().to_lowercase();
                    tools.retain(|tool| tool.status == normalized);
                }
                if args.json {
                    print_tools_json(&tools);
                } else {
                    print_tools_summary(&tools);
                }
            }
            QueryView::Interventions(args) => {
                let trace_id = parse_optional_integer("query interventions: --trace", args.trace)?;
                print_interventions(&service.query_interventions(InterventionFilter {
                    trace_id,
                    story_id: args.story,
                    intervention_type: args.intervention_type,
                })?);
            }
            QueryView::Stats => print_stats(&service.query_stats()?),
            QueryView::Sql { query } => {
                if query.is_empty() {
                    return Err(InterfaceError::EmptySql);
                }
                print_query_table(&service.query_sql(&query.join(" "))?);
            }
        },
    }

    Ok(())
}

fn print_trace_score(result: &TraceScoreResult, latest: bool) {
    if latest {
        println!("Trace #{} (latest):", result.trace_id);
    } else {
        println!("Trace #{}:", result.trace_id);
    }
    println!(
        "  Tier achieved: {} ({}/3)",
        result.achieved.label(),
        result.achieved.score()
    );

    match (&result.risk_lane, result.required) {
        (Some(lane), Some(required)) => {
            println!(
                "  Lane: {} -> required tier: {} ({}/3)",
                lane,
                required.label(),
                required.score()
            );
            if result.meets_requirement {
                println!("  MEETS REQUIREMENT");
            } else {
                println!("  BELOW REQUIREMENT");
            }
        }
        _ => {
            println!("  Lane: unknown (no linked intake)");
        }
    }

    print_missing_fields(
        "minimal",
        TraceQualityTier::Minimal,
        &result.missing_minimal,
    );
    print_missing_fields(
        "standard",
        TraceQualityTier::Standard,
        &result.missing_standard,
    );
    print_missing_fields(
        "detailed",
        TraceQualityTier::Detailed,
        &result.missing_detailed,
    );
}

fn print_story_verify_all(result: &StoryVerifyAllResult) {
    for item in &result.items {
        match item.result.as_str() {
            "skipped" => println!("Story {}: skipped (no verify_command)", item.id),
            status => {
                println!("Story {}: {status}", item.id);
                if !item.stdout.is_empty() {
                    print!("{}", item.stdout);
                }
                if !item.stderr.is_empty() {
                    print!("{}", item.stderr);
                }
            }
        }
    }
    println!(
        "{} stories verified: {} passed, {} failed, {} skipped (no verify_command)",
        result.items.len(),
        result.passed(),
        result.failed(),
        result.skipped()
    );
}

fn print_context_score(result: &ContextScoreResult) {
    println!(
        "Trace #{} | Lane: {} | Phase: {}",
        result.trace_id, result.lane, result.phase
    );
    println!();
    let must_met = result.must.iter().filter(|item| item.met).count();
    println!("Must-read compliance: {must_met}/{}", result.must.len());
    for item in &result.must {
        println!(
            "  {} {} ({})",
            if item.met { "OK" } else { "MISSING" },
            item.label,
            item.target
        );
    }
    let should_met = result.should.iter().filter(|item| item.met).count();
    println!(
        "Should-read compliance: {should_met}/{}",
        result.should.len()
    );
    for item in &result.should {
        println!(
            "  {} {} ({})",
            if item.met { "OK" } else { "MISSING" },
            item.label,
            item.target
        );
    }
    println!("Over-reading: {} item(s)", result.over_read.len());
    for item in &result.over_read {
        println!("  - {item}");
    }
}

fn print_audit(result: &crate::domain::AuditResult) {
    println!("=== Harness Drift Audit ===");
    print_audit_category(
        "Orphaned stories (planned/in-progress, no traces)",
        &result.orphaned_stories,
    );
    print_audit_category("Unverified stories", &result.unverified_stories);
    print_audit_category("Unverified decisions", &result.unverified_decisions);
    print_audit_category(
        "Open backlog without outcomes",
        &result.backlog_without_outcomes,
    );
    print_audit_category("Stale stories", &result.stale_stories);
    print_audit_category("Broken tools", &result.broken_tools);
    println!(
        "Entropy score: {}/100 (lower is better)",
        result.entropy_score()
    );
}

fn print_audit_category(label: &str, findings: &[crate::domain::AuditFinding]) {
    println!();
    println!("{label}: {}", findings.len());
    for finding in findings {
        println!("  - {}: {}", finding.id, finding.title);
    }
}

fn print_proposals(proposals: &[ImprovementProposal]) {
    println!("=== Improvement Proposals ===");
    if proposals.is_empty() {
        println!("No proposals generated.");
        return;
    }
    for (index, proposal) in proposals.iter().enumerate() {
        println!();
        println!(
            "Proposal {} ({} confidence):",
            index + 1,
            proposal.confidence
        );
        println!("  Key: {}", proposal.key);
        println!("  Lifecycle: {}", proposal.lifecycle_state);
        println!("  Title: {}", proposal.title);
        println!("  Component: {}", proposal.component);
        println!("  Evidence: {}", proposal.evidence);
        println!("  Predicted impact: {}", proposal.predicted_impact);
        println!("  Risk: {}", proposal.risk);
        println!("  Suggested action: {}", proposal.suggested_action);
        println!("  Validation: {}", proposal.validation_plan);
        if let Some(id) = proposal.committed_backlog_id {
            println!("  Created backlog item #{id}");
        }
    }
    println!();
    println!(
        "{} proposals generated. Use --accept <proposal-key> or --reject <proposal-key> to make one explicit decision.",
        proposals.len()
    );
}

fn print_proposal_result(result: &ProposalResult) {
    print_proposals(&result.proposals);
    if let Some(message) = &result.message {
        println!("{message}");
    }
}

fn print_changeset_apply_result(result: ChangesetApplyResult) {
    if result.applied {
        println!(
            "Changeset {} applied ({} operation(s)).",
            result.id, result.operations
        );
    } else {
        println!("Changeset {} already applied; skipped.", result.id);
    }
}

fn print_db_rebuild_result(result: DbRebuildResult) {
    println!("Rebuilt database at {}", result.db_path.display());
    println!(
        "Applied {} changeset(s), {} operation(s).",
        result.changesets, result.operations
    );
}

fn print_story_verify_warning(
    service: &HarnessService,
    story_id: &str,
) -> Result<(), InterfaceError> {
    let status = service.story_verify_status(story_id)?;
    let has_command = status
        .verify_command
        .as_deref()
        .map(str::trim)
        .is_some_and(|value| !value.is_empty());
    if has_command && status.last_verified_result.as_deref() != Some("pass") {
        println!();
        println!(
            "Warning: Story {} has verify_command but verification has not passed.",
            status.id
        );
        println!("Run: harness-cli story verify {}", status.id);
    }
    Ok(())
}

fn print_missing_fields(label: &str, tier: TraceQualityTier, fields: &[String]) {
    if fields.is_empty() {
        return;
    }
    println!();
    println!("  Missing for {label}:");
    for field in fields {
        println!("    - {field}");
    }
    if tier == TraceQualityTier::Detailed {
        println!();
    }
}

fn backlog_filter(args: &BacklogQueryArgs) -> BacklogFilter {
    if args.open {
        BacklogFilter::Open
    } else if args.closed {
        BacklogFilter::Closed
    } else {
        BacklogFilter::All
    }
}

fn print_brownfield_import_result(result: BrownfieldImportResult) {
    println!("Brownfield import complete.");
    println!("Stories imported or updated: {}", result.stories);
    println!("Decisions imported or updated: {}", result.decisions);
    println!("Backlog items discovered: {}", result.backlog_items);
}

fn parse_optional_bool(
    label: &str,
    value: Option<String>,
) -> Result<Option<BoolFlag>, InterfaceError> {
    value
        .map(|inner| BoolFlag::parse(label, &inner))
        .transpose()
        .map_err(InterfaceError::from)
}

fn print_init_result(result: InitResult) {
    match result {
        InitResult::Created { db_path } => {
            println!("Creating harness database at {}", db_path.display());
            println!("Schema applied.");
        }
        InitResult::Existing { db_path, version } => {
            println!("Database already exists at {}", db_path.display());
            println!("Current schema version: {version}");
        }
        InitResult::MigratedExisting { db_path } => {
            println!("Database already exists at {}", db_path.display());
            println!("No schema version found. Applying schema.");
            println!("Schema applied.");
        }
    }
}

fn print_migrate_result(result: MigrateResult) {
    println!("Current schema version: {}", result.current_version);
    if result.applied.is_empty() {
        println!("Already up to date.");
    } else {
        for version in &result.applied {
            println!("Applying migration {version}...");
        }
        println!("Applied {} migration(s).", result.applied.len());
    }
}

fn resolve_context() -> Result<HarnessContext, InterfaceError> {
    let repo_root = match env::var_os("HARNESS_REPO_ROOT") {
        Some(path) => PathBuf::from(path),
        None => env::current_dir().map_err(InterfaceError::CurrentDir)?,
    };
    let db_path = resolve_db_path(
        &repo_root,
        env::var_os("HARNESS_DB_PATH").map(PathBuf::from),
        env::var_os("HARNESS_DB").map(PathBuf::from),
    );

    let schema_dir = repo_root.join("scripts/schema");

    Ok(HarnessContext {
        repo_root,
        db_path,
        schema_dir,
    })
}

fn resolve_db_path(
    repo_root: &std::path::Path,
    harness_db_path: Option<PathBuf>,
    legacy_harness_db: Option<PathBuf>,
) -> PathBuf {
    harness_db_path
        .or(legacy_harness_db)
        .unwrap_or_else(|| repo_root.join("harness.db"))
}

fn print_matrix(records: &[StoryMatrixRecord], numeric: bool) {
    let rows = records
        .iter()
        .map(|record| {
            vec![
                record.id.clone(),
                record.title.clone(),
                record.status.clone(),
                proof_display(record.unit, numeric),
                proof_display(record.integration, numeric),
                proof_display(record.e2e, numeric),
                proof_display(record.platform, numeric),
                record.evidence.clone().unwrap_or_default(),
            ]
        })
        .collect::<Vec<_>>();
    print_table(
        &[
            "id", "title", "status", "unit", "integ", "e2e", "plat", "evidence",
        ],
        &rows,
    );
}

fn print_dependencies(records: &[crate::application::StoryDependencyRecord]) {
    let rows = records
        .iter()
        .map(|record| vec![record.blocker.clone(), record.blocked.clone()])
        .collect::<Vec<_>>();
    print_table(&["blocker", "blocked"], &rows);
}

fn print_story_backlog_links(records: &[crate::application::StoryBacklogLinkRecord]) {
    let rows = records
        .iter()
        .map(|record| {
            vec![
                record.story_id.clone(),
                record.backlog_id.to_string(),
                record.backlog_uid.clone(),
                record.relationship.clone(),
            ]
        })
        .collect::<Vec<_>>();
    print_table(&["story", "backlog", "backlog_uid", "relationship"], &rows);
}

fn print_backlog(records: &[BacklogRecord]) {
    let rows = records
        .iter()
        .map(|record| {
            vec![
                record.id.to_string(),
                record.title.clone(),
                record.status.clone(),
                record.risk.clone().unwrap_or_default(),
                record.predicted_impact.clone().unwrap_or_default(),
                record.actual_outcome.clone().unwrap_or_default(),
            ]
        })
        .collect::<Vec<_>>();
    print_table(
        &[
            "id",
            "title",
            "status",
            "risk",
            "predicted_impact",
            "actual_outcome",
        ],
        &rows,
    );
}

fn print_decisions(records: &[DecisionRecord]) {
    let rows = records
        .iter()
        .map(|record| {
            vec![
                record.id.clone(),
                record.title.clone(),
                record.status.clone(),
                record.last_verified_at.clone().unwrap_or_default(),
                record.last_verified_result.clone().unwrap_or_default(),
            ]
        })
        .collect::<Vec<_>>();
    print_table(
        &[
            "id",
            "title",
            "status",
            "last_verified_at",
            "last_verified_result",
        ],
        &rows,
    );
}

fn print_intakes(records: &[IntakeRecord]) {
    let rows = records
        .iter()
        .map(|record| {
            vec![
                record.id.to_string(),
                record.created_at.clone(),
                record.input_type.clone(),
                record.risk_lane.clone(),
                record.summary.clone(),
            ]
        })
        .collect::<Vec<_>>();

    print_table(
        &["id", "created_at", "input_type", "risk_lane", "summary"],
        &rows,
    );
}

fn print_traces(records: &[TraceRecord]) {
    let rows = records
        .iter()
        .map(|record| {
            vec![
                record.id.to_string(),
                record.created_at.clone(),
                record.outcome.clone().unwrap_or_default(),
                record.task_summary.clone(),
                record.harness_friction.clone().unwrap_or_default(),
            ]
        })
        .collect::<Vec<_>>();
    print_table(
        &[
            "id",
            "created_at",
            "outcome",
            "task_summary",
            "harness_friction",
        ],
        &rows,
    );
}

fn print_friction(records: &[FrictionRecord]) {
    let rows = records
        .iter()
        .map(|record| {
            vec![
                record.id.to_string(),
                record.created_at.clone(),
                record.risk_lane.clone().unwrap_or_else(|| "-".to_owned()),
                record.input_type.clone().unwrap_or_else(|| "-".to_owned()),
                record.task_summary.clone(),
                record.harness_friction.clone(),
            ]
        })
        .collect::<Vec<_>>();
    print_table(
        &[
            "id",
            "created_at",
            "risk_lane",
            "input_type",
            "task_summary",
            "harness_friction",
        ],
        &rows,
    );
}

fn print_tools_summary(records: &[ToolEntry]) {
    let rows = records
        .iter()
        .map(|record| {
            vec![
                record.name.clone(),
                record.kind.clone(),
                record.capability.clone().unwrap_or_else(|| "-".to_owned()),
                record.responsibility.clone(),
                record.status.clone(),
                record.source.clone(),
            ]
        })
        .collect::<Vec<_>>();
    print_table(
        &[
            "name",
            "kind",
            "capability",
            "responsibility",
            "status",
            "source",
        ],
        &rows,
    );
}

fn print_tools_json(records: &[ToolEntry]) {
    println!("[");
    for (index, record) in records.iter().enumerate() {
        let comma = if index + 1 == records.len() { "" } else { "," };
        println!("  {{");
        println!("    \"provider\": \"{}\",", json_escape(&record.provider));
        println!("    \"name\": \"{}\",", json_escape(&record.name));
        println!("    \"command\": \"{}\",", json_escape(&record.command));
        println!(
            "    \"description\": \"{}\",",
            json_escape(&record.description)
        );
        println!("    \"args\": [");
        for (arg_index, arg) in record.args.iter().enumerate() {
            let arg_comma = if arg_index + 1 == record.args.len() {
                ""
            } else {
                ","
            };
            println!(
                "      {{\"name\":\"{}\",\"type\":\"{}\",\"required\":{},\"help\":\"{}\"}}{}",
                json_escape(&arg.name),
                json_escape(&arg.arg_type),
                arg.required,
                json_escape(arg.help.as_deref().unwrap_or("")),
                arg_comma
            );
        }
        println!("    ],");
        println!(
            "    \"responsibility\": \"{}\",",
            json_escape(&record.responsibility)
        );
        println!("    \"source\": \"{}\",", json_escape(&record.source));
        println!("    \"since\": \"{}\",", json_escape(&record.since));
        println!("    \"kind\": \"{}\",", json_escape(&record.kind));
        println!(
            "    \"capability\": {},",
            json_optional(record.capability.as_deref())
        );
        println!(
            "    \"scan_target\": {},",
            json_optional(record.scan_target.as_deref())
        );
        println!("    \"status\": \"{}\",", json_escape(&record.status));
        println!(
            "    \"checked_at\": {}",
            json_optional(record.checked_at.as_deref())
        );
        println!("  }}{comma}");
    }
    println!("]");
}

fn print_tool_check_summary(records: &[ToolCheckResult]) {
    let rows = records
        .iter()
        .map(|record| {
            vec![
                record.name.clone(),
                record.kind.clone(),
                record.capability.clone().unwrap_or_else(|| "-".to_owned()),
                record.status.clone(),
                record.detail.clone(),
            ]
        })
        .collect::<Vec<_>>();
    print_table(&["name", "kind", "capability", "status", "detail"], &rows);
}

fn print_tool_check_json(records: &[ToolCheckResult]) {
    println!("[");
    for (index, record) in records.iter().enumerate() {
        let comma = if index + 1 == records.len() { "" } else { "," };
        println!("  {{");
        println!("    \"name\": \"{}\",", json_escape(&record.name));
        println!("    \"kind\": \"{}\",", json_escape(&record.kind));
        println!(
            "    \"capability\": {},",
            json_optional(record.capability.as_deref())
        );
        println!("    \"status\": \"{}\",", json_escape(&record.status));
        println!("    \"detail\": \"{}\"", json_escape(&record.detail));
        println!("  }}{comma}");
    }
    println!("]");
}

fn json_optional(value: Option<&str>) -> String {
    match value {
        Some(value) => format!("\"{}\"", json_escape(value)),
        None => "null".to_owned(),
    }
}

fn print_interventions(records: &[InterventionRecord]) {
    let rows = records
        .iter()
        .map(|record| {
            vec![
                record.id.to_string(),
                record.created_at.clone(),
                record
                    .trace_id
                    .map(|value| value.to_string())
                    .unwrap_or_default(),
                record.story_id.clone().unwrap_or_default(),
                record.intervention_type.clone(),
                record.source.clone(),
                record.description.clone(),
                record.impact.clone().unwrap_or_default(),
            ]
        })
        .collect::<Vec<_>>();
    print_table(
        &[
            "id",
            "created_at",
            "trace",
            "story",
            "type",
            "source",
            "description",
            "impact",
        ],
        &rows,
    );
}

fn json_escape(value: &str) -> String {
    value
        .replace('\\', "\\\\")
        .replace('"', "\\\"")
        .replace('\n', "\\n")
}

fn print_stats(stats: &HarnessStats) {
    println!("=== Harness Stats ===");
    print_table(
        &["intakes", "stories", "decisions", "backlog_items", "traces"],
        &[vec![
            stats.intakes.to_string(),
            stats.stories.to_string(),
            stats.decisions.to_string(),
            stats.backlog_items.to_string(),
            stats.traces.to_string(),
        ]],
    );
}

fn print_query_table(table: &QueryTable) {
    let headers = table.headers.iter().map(String::as_str).collect::<Vec<_>>();
    print_table(&headers, &table.rows);
}

fn print_table(headers: &[&str], rows: &[Vec<String>]) {
    let widths = headers
        .iter()
        .enumerate()
        .map(|(index, header)| {
            rows.iter()
                .filter_map(|row| row.get(index))
                .map(String::len)
                .chain(std::iter::once(header.len()))
                .max()
                .unwrap_or(header.len())
        })
        .collect::<Vec<_>>();

    print_row(
        &headers
            .iter()
            .map(|value| value.to_string())
            .collect::<Vec<_>>(),
        &widths,
    );
    print_row(
        &widths
            .iter()
            .map(|width| "-".repeat(*width))
            .collect::<Vec<_>>(),
        &widths,
    );
    for row in rows {
        print_row(row, &widths);
    }
}

fn print_row(values: &[String], widths: &[usize]) {
    for (index, width) in widths.iter().enumerate() {
        if index > 0 {
            print!("  ");
        }
        let value = values.get(index).map(String::as_str).unwrap_or("");
        print!("{value:<width$}");
    }
    println!();
}

#[cfg(test)]
mod tests {
    use super::*;
    use clap::{CommandFactory, Parser};
    use std::path::Path;

    #[test]
    fn cli_definition_is_valid() {
        Cli::command().debug_assert();
    }

    #[test]
    fn story_dependency_command_parses_typed_edges() {
        let cli = Cli::try_parse_from([
            "harness-cli",
            "story",
            "dependency",
            "add",
            "--blocker",
            "US-073",
            "--blocked",
            "US-074",
        ])
        .unwrap();
        assert!(matches!(
            cli.command,
            Command::Story(StoryArgs {
                action: StoryAction::Dependency(StoryDependencyArgs {
                    action: StoryDependencyAction::Add(StoryDependencyMutationArgs { blocker, blocked })
                })
            }) if blocker == "US-073" && blocked == "US-074"
        ));

        let cli = Cli::try_parse_from([
            "harness-cli",
            "story",
            "dependency",
            "remove",
            "--blocker",
            "US-073",
            "--blocked",
            "US-074",
        ])
        .unwrap();
        assert!(matches!(
            cli.command,
            Command::Story(StoryArgs {
                action: StoryAction::Dependency(StoryDependencyArgs {
                    action: StoryDependencyAction::Remove(StoryDependencyMutationArgs { blocker, blocked })
                })
            }) if blocker == "US-073" && blocked == "US-074"
        ));

        let cli =
            Cli::try_parse_from(["harness-cli", "query", "dependencies", "--story", "US-074"])
                .unwrap();
        assert!(matches!(
            cli.command,
            Command::Query(QueryArgs {
                view: QueryView::Dependencies(DependenciesQueryArgs { story: Some(story) })
            }) if story == "US-074"
        ));
    }

    #[test]
    fn harness_db_path_overrides_legacy_harness_db() {
        let db_path = resolve_db_path(
            Path::new("/repo"),
            Some(PathBuf::from("/isolated/harness.db")),
            Some(PathBuf::from("/legacy/harness.db")),
        );

        assert_eq!(db_path, PathBuf::from("/isolated/harness.db"));
    }

    #[test]
    fn legacy_harness_db_remains_fallback() {
        let db_path = resolve_db_path(
            Path::new("/repo"),
            None,
            Some(PathBuf::from("/legacy/harness.db")),
        );

        assert_eq!(db_path, PathBuf::from("/legacy/harness.db"));
    }

    #[test]
    fn database_path_defaults_to_repo_root_harness_db() {
        let db_path = resolve_db_path(Path::new("/repo"), None, None);

        assert_eq!(db_path, PathBuf::from("/repo/harness.db"));
    }

    #[test]
    fn story_help_documents_proof_command_shape() {
        let mut command = Cli::command();
        let story = command.find_subcommand_mut("story").unwrap();

        let update_help = story
            .find_subcommand_mut("update")
            .unwrap()
            .render_long_help()
            .to_string();
        assert!(update_help.contains("--unit <0|1>"));
        assert!(update_help.contains("--integration <0|1>"));
        assert!(update_help.contains("Proof flags use numeric booleans"));

        let verify_help = story
            .find_subcommand_mut("verify")
            .unwrap()
            .render_long_help()
            .to_string();
        assert!(verify_help.contains("story verify only accepts the story id"));
        assert!(verify_help.contains("Configure proof with story add/update --verify"));
    }

    #[test]
    fn command_help_documents_lane_values_and_version() {
        let mut command = Cli::command();
        assert!(command.render_long_help().to_string().contains("--version"));

        let intake_help = command
            .find_subcommand_mut("intake")
            .unwrap()
            .render_long_help()
            .to_string();
        assert!(intake_help.contains("--lane <tiny|normal|high-risk>"));
        assert!(intake_help.contains("Use tiny instead of low"));

        let story_add_help = command
            .find_subcommand_mut("story")
            .unwrap()
            .find_subcommand_mut("add")
            .unwrap()
            .render_long_help()
            .to_string();
        assert!(story_add_help.contains("--lane <tiny|normal|high-risk>"));

        let backlog_add_help = command
            .find_subcommand_mut("backlog")
            .unwrap()
            .find_subcommand_mut("add")
            .unwrap()
            .render_long_help()
            .to_string();
        assert!(backlog_add_help.contains("--risk <tiny|normal|high-risk>"));
        assert!(backlog_add_help.contains("Accepted lanes"));

        let matrix_help = command
            .find_subcommand_mut("query")
            .unwrap()
            .find_subcommand_mut("matrix")
            .unwrap()
            .render_long_help()
            .to_string();
        assert!(matrix_help.contains("--numeric"));
    }
}
