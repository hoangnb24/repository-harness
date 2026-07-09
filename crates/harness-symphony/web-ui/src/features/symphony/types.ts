export type BoardState =
  | "Ready"
  | "Blocked"
  | "In Progress"
  | "Review"
  | "Needs Attention"
  | "Done";

export type FailureSummary = {
  category: string;
  reason: string;
  latest_event: string | null;
  latest_error: string | null;
  run_id: string;
  evidence_artifacts: string[];
  next_action: string;
};

export type RecoveryAction = {
  kind: "execution_retry" | "pr_retry";
  label: string;
  endpoint: string;
  confirmation: string;
};

export type BoardItem = {
  id: string;
  title: string;
  board_state: BoardState;
  story_status: string;
  lane: string;
  verify: string;
  blockers: string[];
  unblocks: string[];
  parent_id: string | null;
  children: string[];
  hierarchy_depth: number;
  run_id: string | null;
  active_run: string | null;
  reason: string;
  failure_summary: FailureSummary | null;
  recovery_action: RecoveryAction | null;
};

export type BoardResponse = {
  items: BoardItem[];
};

export type GuidedIntakeDraft = {
  idea: string;
  audience: string;
  outcome: string;
  non_goals: string;
  validation: string;
};

export type CreatedStoryResponse = {
  story_id: string;
  title: string;
  status: string;
};

export type RunEvent = unknown;

export type EventsResponse = {
  run_id: string;
  events: RunEvent[];
};

export type ReviewResponse = {
  run_id: string;
  story_id: string;
  status: string;
  outcome: string | null;
  summary: string | null;
  result: unknown | null;
  validation: unknown | null;
  changed_files: string[];
  changeset_preview: string | null;
  pr_url: string | null;
  pr_status: string;
  artifact_paths: string[];
  events: RunEvent[];
  suggested_next_action: string;
  failure_summary: FailureSummary | null;
  recovery_action: RecoveryAction | null;
};

export type SyncResponse = {
  run_id: string;
  applied: boolean;
};

export type PrMergedResponse = {
  run_id: string;
  pr_status: string;
};

export type PrRetryResponse = {
  run_id: string;
  pr_status: string;
  pr_url: string | null;
};
