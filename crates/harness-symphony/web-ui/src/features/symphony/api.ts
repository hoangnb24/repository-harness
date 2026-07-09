import type {
  BoardItem,
  BoardResponse,
  BoardState,
  CreatedStoryResponse,
  EventsResponse,
  FailureSummary,
  GuidedIntakeDraft,
  PrMergedResponse,
  PrRetryResponse,
  RecoveryAction,
  ReviewResponse,
  SyncResponse
} from "./types";

const boardStates: BoardState[] = ["Ready", "Blocked", "In Progress", "Review", "Needs Attention", "Done"];

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function fetchBoard(options?: { signal?: AbortSignal }): Promise<BoardResponse> {
  const response = await fetch("/api/board", { signal: options?.signal });
  return readJson(response, parseBoardResponse, "Board request failed");
}

export async function fetchEvents(runId: string, options?: { signal?: AbortSignal }): Promise<EventsResponse> {
  const response = await fetch(`/api/runs/${encodeURIComponent(runId)}/events`, { signal: options?.signal });
  return readJson(response, parseEventsResponse, "Events request failed");
}

export async function fetchReview(runId: string, options?: { signal?: AbortSignal }): Promise<ReviewResponse> {
  const response = await fetch(`/api/runs/${encodeURIComponent(runId)}/review`, { signal: options?.signal });
  return readJson(response, parseReviewResponse, "Review request failed");
}

export async function postStartTask(storyId: string): Promise<void> {
  const response = await fetch(`/api/tasks/${encodeURIComponent(storyId)}/start`, { method: "POST" });
  await readEmptyOrJson(response, "Start failed");
}

export async function postRetireTask(storyId: string): Promise<void> {
  const response = await fetch(`/api/tasks/${encodeURIComponent(storyId)}/retire`, { method: "POST" });
  await readEmptyOrJson(response, "Delete failed");
}

export async function postRecoverTask(action: RecoveryAction): Promise<void> {
  const response = await fetch(action.endpoint, { method: "POST" });
  await readEmptyOrJson(response, "Recovery failed");
}

export async function postSyncRun(runId: string): Promise<SyncResponse> {
  const response = await fetch(`/api/runs/${encodeURIComponent(runId)}/sync`, { method: "POST" });
  return readJson(response, parseSyncResponse, "Sync failed");
}

export async function postMarkPrMerged(runId: string): Promise<PrMergedResponse> {
  const response = await fetch(`/api/runs/${encodeURIComponent(runId)}/pr-merged`, { method: "POST" });
  return readJson(response, parsePrMergedResponse, "Merge update failed");
}

export async function postRetryPr(action: RecoveryAction): Promise<PrRetryResponse> {
  const response = await fetch(action.endpoint, { method: "POST" });
  return readJson(response, parsePrRetryResponse, "PR retry failed");
}

export async function postCreateGuidedIntake(draft: GuidedIntakeDraft): Promise<CreatedStoryResponse> {
  const response = await fetch("/api/intake", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(draft)
  });
  return readJson(response, parseCreatedStoryResponse, "Create story failed");
}

async function readJson<T>(response: Response, parser: (value: unknown) => T, fallback: string): Promise<T> {
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(errorMessage(body) ?? `${fallback} (${response.status})`, response.status);
  }
  try {
    return parser(body);
  } catch (cause) {
    const detail = cause instanceof Error ? cause.message : "Malformed response";
    throw new ApiError(`${fallback}: ${detail}`, response.status);
  }
}

async function readEmptyOrJson(response: Response, fallback: string): Promise<void> {
  if (response.ok) {
    return;
  }
  const body = await response.json().catch(() => null);
  throw new ApiError(errorMessage(body) ?? `${fallback} (${response.status})`, response.status);
}

function errorMessage(value: unknown): string | null {
  return isRecord(value) && typeof value.error === "string" ? value.error : null;
}

function parseBoardResponse(value: unknown): BoardResponse {
  const record = expectRecord(value, "board response");
  return { items: expectArray(record.items, "items").map(parseBoardItem) };
}

function parseBoardItem(value: unknown): BoardItem {
  const record = expectRecord(value, "board item");
  return {
    id: expectString(record.id, "id"),
    title: expectString(record.title, "title"),
    board_state: expectBoardState(record.board_state),
    story_status: expectString(record.story_status, "story_status"),
    lane: expectString(record.lane, "lane"),
    verify: expectString(record.verify, "verify"),
    blockers: parseStringArray(record.blockers, "blockers"),
    unblocks: parseStringArray(record.unblocks, "unblocks"),
    parent_id: parseNullableString(record.parent_id, "parent_id"),
    children: parseStringArray(record.children, "children"),
    hierarchy_depth: typeof record.hierarchy_depth === "number" ? record.hierarchy_depth : 0,
    run_id: parseNullableString(record.run_id, "run_id"),
    active_run: parseNullableString(record.active_run, "active_run"),
    reason: expectString(record.reason, "reason"),
    failure_summary: parseNullable(record.failure_summary, parseFailureSummary),
    recovery_action: parseNullable(record.recovery_action, parseRecoveryAction)
  };
}

function parseFailureSummary(value: unknown): FailureSummary {
  const record = expectRecord(value, "failure_summary");
  return {
    category: expectString(record.category, "category"),
    reason: expectString(record.reason, "reason"),
    latest_event: parseNullableString(record.latest_event, "latest_event"),
    latest_error: parseNullableString(record.latest_error, "latest_error"),
    run_id: expectString(record.run_id, "run_id"),
    evidence_artifacts: parseStringArray(record.evidence_artifacts, "evidence_artifacts"),
    next_action: expectString(record.next_action, "next_action")
  };
}

function parseRecoveryAction(value: unknown): RecoveryAction {
  const record = expectRecord(value, "recovery_action");
  const kind = expectString(record.kind, "kind");
  if (kind !== "execution_retry" && kind !== "pr_retry") {
    throw new Error("recovery_action.kind is invalid");
  }
  return {
    kind,
    label: expectString(record.label, "label"),
    endpoint: expectString(record.endpoint, "endpoint"),
    confirmation: expectString(record.confirmation, "confirmation")
  };
}

function parseEventsResponse(value: unknown): EventsResponse {
  const record = expectRecord(value, "events response");
  return {
    run_id: expectString(record.run_id, "run_id"),
    events: expectArray(record.events, "events")
  };
}

function parseReviewResponse(value: unknown): ReviewResponse {
  const record = expectRecord(value, "review response");
  return {
    run_id: expectString(record.run_id, "run_id"),
    story_id: expectString(record.story_id, "story_id"),
    status: expectString(record.status, "status"),
    outcome: parseNullableString(record.outcome, "outcome"),
    summary: parseNullableString(record.summary, "summary"),
    result: record.result ?? null,
    validation: record.validation ?? null,
    changed_files: parseStringArray(record.changed_files, "changed_files"),
    changeset_preview: parseNullableString(record.changeset_preview, "changeset_preview"),
    pr_url: parseNullableString(record.pr_url, "pr_url"),
    pr_status: expectString(record.pr_status, "pr_status"),
    artifact_paths: parseStringArray(record.artifact_paths, "artifact_paths"),
    events: expectArray(record.events, "events"),
    suggested_next_action: expectString(record.suggested_next_action, "suggested_next_action"),
    failure_summary: parseNullable(record.failure_summary, parseFailureSummary),
    recovery_action: parseNullable(record.recovery_action, parseRecoveryAction)
  };
}

function parseSyncResponse(value: unknown): SyncResponse {
  const record = expectRecord(value, "sync response");
  return { run_id: expectString(record.run_id, "run_id"), applied: Boolean(record.applied) };
}

function parsePrMergedResponse(value: unknown): PrMergedResponse {
  const record = expectRecord(value, "pr merged response");
  return { run_id: expectString(record.run_id, "run_id"), pr_status: expectString(record.pr_status, "pr_status") };
}

function parsePrRetryResponse(value: unknown): PrRetryResponse {
  const record = expectRecord(value, "pr retry response");
  return {
    run_id: expectString(record.run_id, "run_id"),
    pr_status: expectString(record.pr_status, "pr_status"),
    pr_url: parseNullableString(record.pr_url, "pr_url")
  };
}

function parseCreatedStoryResponse(value: unknown): CreatedStoryResponse {
  const record = expectRecord(value, "created story response");
  return {
    story_id: expectString(record.story_id, "story_id"),
    title: expectString(record.title, "title"),
    status: expectString(record.status, "status")
  };
}

function parseNullable<T>(value: unknown, parser: (value: unknown) => T): T | null {
  return value === null || value === undefined ? null : parser(value);
}

function parseNullableString(value: unknown, field: string): string | null {
  if (value === null || value === undefined) {
    return null;
  }
  return expectString(value, field);
}

function parseStringArray(value: unknown, field: string): string[] {
  return expectArray(value, field).map((entry, index) => expectString(entry, `${field}[${index}]`));
}

function expectBoardState(value: unknown): BoardState {
  const found = expectString(value, "board_state");
  if (!boardStates.includes(found as BoardState)) {
    throw new Error(`board_state is invalid: ${found}`);
  }
  return found as BoardState;
}

function expectString(value: unknown, field: string): string {
  if (typeof value !== "string") {
    throw new Error(`${field} must be a string`);
  }
  return value;
}

function expectArray(value: unknown, field: string): unknown[] {
  if (!Array.isArray(value)) {
    throw new Error(`${field} must be an array`);
  }
  return value;
}

function expectRecord(value: unknown, field: string): Record<string, unknown> {
  if (!isRecord(value)) {
    throw new Error(`${field} must be an object`);
  }
  return value;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
