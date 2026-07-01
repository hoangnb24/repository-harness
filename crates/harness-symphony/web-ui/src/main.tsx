import React from "react";
import ReactDOM from "react-dom/client";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Circle,
  Clock3,
  GitBranch,
  GitPullRequestArrow,
  Loader2,
  Play,
  RefreshCw,
  Search,
  ShieldAlert,
  X
} from "lucide-react";
import { Badge } from "./components/ui/badge";
import { Button } from "./components/ui/button";
import { Card } from "./components/ui/card";
import { Input } from "./components/ui/input";
import { Separator } from "./components/ui/separator";
import { cn } from "./lib/utils";
import { formatRunLog } from "./run-log";
import "./styles.css";

type BoardState =
  | "Ready"
  | "Blocked"
  | "In Progress"
  | "Review"
  | "Needs Attention"
  | "Done";

type BoardItem = {
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
};

type BoardResponse = {
  items: BoardItem[];
};

type AgentOverall = "ready" | "needs-setup" | "not-installed" | "unknown";

type AgentStatus = {
  adapter: string;
  active: boolean;
  binary_present: boolean;
  binary_detail: string;
  auth_ready: boolean;
  auth_detail: string;
  overall: AgentOverall;
  next: string | null;
};

type AgentsResponse = {
  agents: AgentStatus[];
};

type RunEvent = unknown;

type EventsResponse = {
  run_id: string;
  events: RunEvent[];
};

type ReviewResponse = {
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
};

type SyncResponse = {
  run_id: string;
  applied: boolean;
};

type PrMergedResponse = {
  run_id: string;
  pr_status: string;
};

type ConfettiBurst = {
  id: number;
  x: number;
  y: number;
};

const states: BoardState[] = [
  "Ready",
  "Blocked",
  "In Progress",
  "Review",
  "Needs Attention",
  "Done"
];

const stateIcon = {
  Ready: Circle,
  Blocked: ShieldAlert,
  "In Progress": Loader2,
  Review: GitPullRequestArrow,
  "Needs Attention": AlertTriangle,
  Done: CheckCircle2
};

const stateTone = {
  Ready: "ready",
  Blocked: "blocked",
  "In Progress": "progress",
  Review: "review",
  "Needs Attention": "attention",
  Done: "done"
} as const;

const agentOverallLabel = {
  ready: "Ready",
  "needs-setup": "Needs setup",
  "not-installed": "Not installed",
  unknown: "Unknown"
} as const;

const agentDot = {
  ready: "bg-emerald-500",
  "needs-setup": "bg-amber-500",
  "not-installed": "bg-zinc-400",
  unknown: "bg-zinc-300"
} as const;

function App() {
  const [items, setItems] = React.useState<BoardItem[]>([]);
  const [agents, setAgents] = React.useState<AgentStatus[]>([]);
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [confettiBursts, setConfettiBursts] = React.useState<ConfettiBurst[]>([]);
  const [query, setQuery] = React.useState("");
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [startingId, setStartingId] = React.useState<string | null>(null);
  const [syncingRunId, setSyncingRunId] = React.useState<string | null>(null);
  const [markingMergedRunId, setMarkingMergedRunId] = React.useState<string | null>(null);
  const confettiBurstIdRef = React.useRef(0);
  const prefersReducedMotion = usePrefersReducedMotion();

  const loadAgents = React.useCallback(async () => {
    try {
      const response = await fetch("/api/agents");
      if (!response.ok) {
        throw new Error(`Agents request failed (${response.status})`);
      }
      const data = (await response.json()) as AgentsResponse;
      setAgents(Array.isArray(data.agents) ? data.agents : []);
    } catch {
      // Keep the app usable when agent status is unavailable; render a degraded strip.
      setAgents([]);
    }
  }, []);

  const loadBoard = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/board");
      if (!response.ok) {
        throw new Error(`Board request failed (${response.status})`);
      }
      const data = (await response.json()) as BoardResponse;
      setItems(data.items);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Board request failed");
    } finally {
      setLoading(false);
      void loadAgents();
    }
  }, [loadAgents]);

  React.useEffect(() => {
    void loadBoard();
  }, [loadBoard]);

  React.useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setSelectedId(null);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const filtered = React.useMemo(() => {
    const value = query.trim().toLowerCase();
    return items.filter(
      (item) =>
        value.length === 0 ||
        item.id.toLowerCase().includes(value) ||
        item.title.toLowerCase().includes(value)
    );
  }, [items, query]);
  const selected = selectedId ? items.find((item) => item.id === selectedId) ?? null : null;
  const counts = React.useMemo(
    () =>
      Object.fromEntries(states.map((state) => [state, items.filter((item) => item.board_state === state).length])) as
        Record<BoardState, number>,
    [items]
  );
  const activeRun = items.find((item) => item.active_run);

  const clearConfettiBurst = React.useCallback((id: number) => {
    setConfettiBursts((current) => current.filter((burst) => burst.id !== id));
  }, []);

  const closeSelectedTask = React.useCallback(
    (origin?: HTMLElement) => {
      if (origin && !prefersReducedMotion) {
        const rect = origin.getBoundingClientRect();
        const burst: ConfettiBurst = {
          id: (confettiBurstIdRef.current += 1),
          x: rect.left + rect.width / 2,
          y: rect.top + rect.height / 2
        };
        setConfettiBursts((current) => [...current.slice(-2), burst]);
      }
      setSelectedId(null);
    },
    [prefersReducedMotion]
  );

  const startTask = React.useCallback(
    async (storyId: string) => {
      setStartingId(storyId);
      setError(null);
      try {
        const response = await fetch(`/api/tasks/${encodeURIComponent(storyId)}/start`, {
          method: "POST"
        });
        if (!response.ok) {
          const body = (await response.json().catch(() => null)) as { error?: string } | null;
          throw new Error(body?.error ?? `Start failed (${response.status})`);
        }
        await loadBoard();
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : "Start failed");
      } finally {
        setStartingId(null);
      }
    },
    [loadBoard]
  );

  const syncRun = React.useCallback(
    async (runId: string) => {
      setSyncingRunId(runId);
      setError(null);
      try {
        const response = await fetch(`/api/runs/${encodeURIComponent(runId)}/sync`, {
          method: "POST"
        });
        if (!response.ok) {
          const body = (await response.json().catch(() => null)) as { error?: string } | null;
          throw new Error(body?.error ?? `Sync failed (${response.status})`);
        }
        const result = (await response.json()) as SyncResponse;
        if (!result.applied) {
          setError("No new changeset was applied for that run.");
        }
        await loadBoard();
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : "Sync failed");
      } finally {
        setSyncingRunId(null);
      }
    },
    [loadBoard]
  );

  const markPrMerged = React.useCallback(
    async (runId: string) => {
      setMarkingMergedRunId(runId);
      setError(null);
      try {
        const response = await fetch(`/api/runs/${encodeURIComponent(runId)}/pr-merged`, {
          method: "POST"
        });
        if (!response.ok) {
          const body = (await response.json().catch(() => null)) as { error?: string } | null;
          throw new Error(body?.error ?? `Merge update failed (${response.status})`);
        }
        (await response.json()) as PrMergedResponse;
        await loadBoard();
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : "Merge update failed");
      } finally {
        setMarkingMergedRunId(null);
      }
    },
    [loadBoard]
  );

  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="mx-auto grid w-full max-w-[1720px] grid-cols-1 gap-4 p-3 md:p-4 lg:grid-cols-[224px_minmax(0,1fr)] xl:p-6">
        <ControllerSidebar counts={counts} items={items} selectedId={selected?.id ?? null} onSelect={setSelectedId} />

        <div className="flex min-w-0 flex-col gap-3">
          <header className="flex flex-col gap-3 border-b border-border pb-3 xl:flex-row xl:items-end xl:justify-between">
            <div>
              <h1 className="text-[40px] font-semibold leading-none tracking-tight max-md:text-[28px]">
                Symphony work board
              </h1>
              <p className="mt-2 max-w-3xl text-base font-medium leading-6 text-muted-foreground">
                Kanban, blockers, and run logs in one focused view.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <label className="relative block w-full sm:w-72">
                <Search className="pointer-events-none absolute left-3 top-2.5 size-4 text-muted-foreground" />
                <Input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  className="pl-9"
                  placeholder="Find task"
                />
              </label>
              <Button variant="outline" onClick={() => void loadBoard()} disabled={loading}>
                <RefreshCw data-icon="inline-start" className={cn(loading && "animate-spin")} />
                Refresh
              </Button>
            </div>
          </header>

          <AgentsStrip agents={agents} />

          <SummaryStrip activeRun={activeRun} counts={counts} />

          {error ? (
            <Card className="flex items-center gap-3 border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
              <AlertTriangle className="size-4 shrink-0" />
              {error}
            </Card>
          ) : null}

          <section
            id="board"
            className="grid min-h-[calc(100dvh-220px)] grid-cols-1 gap-3"
          >
            <BoardGrid items={filtered} selectedId={selected?.id ?? null} onSelect={setSelectedId} />
          </section>

          <ConfettiBurstHost bursts={confettiBursts} onBurstDone={clearConfettiBurst} />

          {selected ? (
            <TaskDetailOverlay onClose={() => setSelectedId(null)}>
              <TaskDetail
                item={selected}
                startingId={startingId}
                syncingRunId={syncingRunId}
                markingMergedRunId={markingMergedRunId}
                onClose={closeSelectedTask}
                onStart={startTask}
                onSync={syncRun}
                onMarkPrMerged={markPrMerged}
              />
            </TaskDetailOverlay>
          ) : null}

          <p className="text-xs leading-5 text-muted-foreground">
            Source: local Symphony API responses for board state, run events, review artifacts, PR status, and sync state.
          </p>
        </div>
      </div>
    </main>
  );
}

function usePrefersReducedMotion() {
  const [prefersReducedMotion, setPrefersReducedMotion] = React.useState(() =>
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );

  React.useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    function syncPreference() {
      setPrefersReducedMotion(mediaQuery.matches);
    }

    syncPreference();
    mediaQuery.addEventListener("change", syncPreference);
    return () => mediaQuery.removeEventListener("change", syncPreference);
  }, []);

  return prefersReducedMotion;
}

function SidebarDependencyGraph({
  items,
  selectedId,
  onSelect
}: {
  items: BoardItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const graphItems = items.filter((item) => item.blockers.length > 0 || item.unblocks.length > 0);
  const edgeCount = graphItems.reduce((sum, item) => sum + item.blockers.length, 0);

  return (
    <section className="mt-2 hidden border-t border-border/70 pt-3 lg:block" aria-label="Dependency graph sidebar">
      <div className="flex items-center justify-between gap-2 px-2">
        <div className="flex items-center gap-2">
          <GitBranch className="size-4 text-muted-foreground" />
          <h2 className="text-sm font-bold">Dependency graph</h2>
        </div>
        <span className="font-mono text-xs text-muted-foreground">{edgeCount}</span>
      </div>
      <div className="mt-3 grid max-h-[34vh] gap-2 overflow-auto pr-1" aria-label="Dependency edges">
        {graphItems.length > 0 ? (
          graphItems.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelect(item.id)}
              className={cn(
                "w-full rounded-md border border-border bg-background p-2 text-left transition hover:border-primary hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                item.id === selectedId && "border-primary bg-accent"
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <strong className="font-mono text-xs">{item.id}</strong>
                <Badge tone={stateTone[item.board_state]}>{item.board_state}</Badge>
              </div>
              <p className="mt-1 line-clamp-2 text-xs font-semibold leading-5">{item.title}</p>
              <div className="mt-2 grid gap-1 text-xs leading-5 text-muted-foreground">
                {item.blockers.length > 0 ? (
                  <GraphLine left={item.blockers.join(", ")} right={item.id} />
                ) : null}
                {item.unblocks.length > 0 ? (
                  <GraphLine left={item.id} right={item.unblocks.join(", ")} />
                ) : null}
              </div>
            </button>
          ))
        ) : (
          <div className="rounded-md border border-dashed border-border bg-background p-3 text-xs leading-5 text-muted-foreground">
            No dependency edges on the current board.
          </div>
        )}
      </div>
    </section>
  );
}

function GraphLine({ left, right }: { left: string; right: string }) {
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_16px_minmax(0,1fr)] items-center gap-1">
      <span className="truncate font-mono">{left}</span>
      <ArrowRight className="size-3 justify-self-center" />
      <span className="truncate font-mono">{right}</span>
    </div>
  );
}

function ControllerSidebar({
  counts,
  items,
  selectedId,
  onSelect
}: {
  counts: Record<BoardState, number>;
  items: BoardItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const blockedItems = items.filter((item) => item.board_state === "Blocked");

  return (
    <aside
      aria-label="Workspace navigation"
      className="flex min-h-0 flex-col rounded-lg border border-border bg-muted p-3 lg:sticky lg:top-4 lg:min-h-[calc(100vh-48px)]"
    >
      <div className="mb-3 flex items-center gap-2 p-2 text-sm font-bold">
        <span className="grid size-6 place-items-center rounded-sm border border-border bg-background font-mono text-xs">
          S
        </span>
        <span>Symphony</span>
      </div>

      <nav aria-label="Primary" className="flex gap-1 overflow-x-auto border-t border-border/70 py-2 lg:flex-col lg:overflow-visible">
        <SidebarLabel>Workspace</SidebarLabel>
        <SidebarItem active label="Work board" count={String(Object.values(counts).reduce((sum, count) => sum + count, 0))} />
        <details className="min-w-56 rounded-sm lg:min-w-0">
          <summary className="flex min-h-9 cursor-pointer list-none items-center justify-between rounded-sm px-2 text-sm font-semibold text-muted-foreground hover:bg-background hover:text-foreground">
            <span>Dependencies</span>
            <span className="font-mono text-xs text-muted-foreground">{blockedItems.length}</span>
          </summary>
          <div className="grid gap-1 px-2 pb-2 pt-1">
            {blockedItems.length > 0 ? (
              blockedItems.slice(0, 4).map((item) => (
                <div key={item.id} className="flex justify-between gap-2 text-xs leading-5 text-muted-foreground">
                  <span className="font-mono">{item.id}</span>
                  <span className="truncate">{item.reason}</span>
                </div>
              ))
            ) : (
              <span className="text-xs text-muted-foreground">No blocked work</span>
            )}
          </div>
        </details>
        <SidebarItem label="Run logs" count="live" />
      </nav>

      <nav aria-label="Status" className="mt-2 flex gap-1 overflow-x-auto border-t border-border/70 py-2 lg:flex-col lg:overflow-visible">
        <SidebarLabel>Status</SidebarLabel>
        <SidebarItem label="Ready" count={String(counts.Ready)} />
        <SidebarItem label="Blocked" count={String(counts.Blocked)} />
        <SidebarItem label="Review" count={String(counts.Review)} />
      </nav>

      <SidebarDependencyGraph items={items} selectedId={selectedId} onSelect={onSelect} />
    </aside>
  );
}

function SidebarLabel({ children }: { children: React.ReactNode }) {
  return <p className="hidden px-2 py-2 text-xs font-bold uppercase tracking-widest text-muted-foreground lg:block">{children}</p>;
}

function SidebarItem({ label, count, active = false }: { label: string; count: string; active?: boolean }) {
  return (
    <a
      href="#board"
      className={cn(
        "flex min-h-9 min-w-max items-center justify-between gap-3 rounded-sm px-2 text-sm font-semibold text-muted-foreground hover:bg-background hover:text-foreground lg:min-w-0",
        active && "bg-background text-foreground"
      )}
    >
      <span>{label}</span>
      <span className="font-mono text-xs text-muted-foreground">{count}</span>
    </a>
  );
}

function AgentsStrip({ agents }: { agents: AgentStatus[] }) {
  return (
    <section
      aria-label="Agent readiness"
      className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs text-muted-foreground"
    >
      <span className="font-semibold uppercase tracking-widest">Agents</span>
      {agents.length > 0 ? (
        agents.map((agent) => <AgentPill key={agent.adapter} agent={agent} />)
      ) : (
        <span>Agent status unavailable.</span>
      )}
    </section>
  );
}

function AgentPill({ agent }: { agent: AgentStatus }) {
  const label = agentOverallLabel[agent.overall] ?? agent.overall;
  const dot = agentDot[agent.overall] ?? "bg-zinc-300";
  const hint = agent.next ?? agent.auth_detail;

  return (
    <span
      data-testid={`agent-card-${agent.adapter}`}
      title={hint ? `${agent.binary_detail} — ${hint}` : agent.binary_detail}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5",
        agent.active ? "border-primary/40 bg-accent" : "border-transparent"
      )}
    >
      <span className={cn("size-1.5 shrink-0 rounded-full", dot)} aria-hidden />
      <span className="font-mono font-medium text-foreground/90">{agent.adapter}</span>
      {agent.active ? (
        <span className="text-[10px] font-semibold uppercase tracking-wide text-primary">active</span>
      ) : null}
      <span className="text-muted-foreground">{label}</span>
    </span>
  );
}

function SummaryStrip({
  activeRun,
  counts
}: {
  activeRun: BoardItem | undefined;
  counts: Record<BoardState, number>;
}) {
  const metrics = [
    {
      label: "Active run",
      value: activeRun?.id ?? "none",
      detail: activeRun?.active_run ? `${activeRun.active_run} is the only task allowed in progress.` : "No active Symphony run."
    },
    {
      label: "Safe to start",
      value: `${counts.Ready} ready`,
      detail: "Ready tasks have no incomplete blockers."
    },
    {
      label: "Avoid for now",
      value: `${counts.Blocked} blocked`,
      detail: "Blocked work explains its missing dependency before action."
    },
    {
      label: "Needs decision",
      value: `${counts.Review} review`,
      detail: "Merge PR first, then approve local sync."
    }
  ];

  return (
    <section aria-label="Dashboard summary" className="grid gap-2 md:grid-cols-2 xl:grid-cols-[1.2fr_.9fr_.9fr_1fr]">
      {metrics.map((metric, index) => (
        <Card key={metric.label} className={cn("rounded-md p-3", index === 0 && "bg-muted")}>
          <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground">{metric.label}</span>
          <strong className="mt-1 block text-xl leading-tight">{metric.value}</strong>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">{metric.detail}</p>
        </Card>
      ))}
    </section>
  );
}

function BoardGrid({
  items,
  selectedId,
  onSelect
}: {
  items: BoardItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="min-h-0 min-w-0 overflow-x-auto pb-2">
      <div className="grid h-[calc(100dvh-220px)] min-h-[390px] min-w-[1120px] grid-cols-[repeat(6,minmax(176px,1fr))] items-stretch gap-3 max-sm:h-auto max-sm:min-h-0 max-sm:min-w-0 max-sm:grid-cols-1">
        {states.map((state) => {
          const stateItems = items.filter((item) => item.board_state === state);
          const Icon = stateIcon[state];
          return (
            <section
              key={state}
              aria-label={`${state} column`}
              className="flex h-full min-h-0 flex-col overflow-hidden rounded-lg border border-border bg-muted/60 max-sm:h-[min(520px,calc(100dvh-180px))] max-sm:min-h-[320px]"
            >
              <div className="flex min-h-12 items-center justify-between gap-2 border-b border-border bg-background px-3">
                <div className="flex items-center gap-2">
                  <Icon className={cn("size-4 text-muted-foreground", state === "In Progress" && "animate-spin")} />
                  <h2 className="text-sm font-bold">{state}</h2>
                </div>
                <Badge tone={stateTone[state]}>{stateItems.length}</Badge>
              </div>
              <div aria-label={`${state} tasks`} className="grid min-h-0 flex-1 content-start gap-2 overflow-y-auto p-2">
                {stateItems.map((item) => (
                  <TaskCard key={item.id} item={item} selected={item.id === selectedId} onSelect={onSelect} />
                ))}
                {stateItems.length === 0 ? (
                  <div className="flex min-h-24 items-center justify-center rounded-md border border-dashed border-border px-3 text-center text-xs text-muted-foreground">
                    No tasks
                  </div>
                ) : null}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}

function TaskCard({
  item,
  selected,
  onSelect
}: {
  item: BoardItem;
  selected: boolean;
  onSelect: (id: string) => void;
}) {
  const blocked = item.board_state === "Blocked";
  const attention = item.board_state === "Needs Attention";
  const done = item.board_state === "Done";

  return (
    <button
      onClick={() => onSelect(item.id)}
      className={cn(
        "block w-full rounded-md border border-border bg-background p-3 text-left shadow-sm transition hover:border-primary hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        selected && "border-primary shadow-md",
        blocked && "bg-warning/10",
        attention && "bg-destructive/10",
        done && "opacity-80"
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-xs font-bold text-muted-foreground">{item.id}</span>
        <Badge tone={item.verify === "configured" ? stateTone[item.board_state] : "neutral"}>
          {item.board_state === "In Progress" ? "active" : item.verify}
        </Badge>
      </div>
      <h3 className="mt-2 line-clamp-3 text-sm font-bold leading-5">{item.title}</h3>
      <p className="mt-2 line-clamp-2 text-xs leading-5 text-muted-foreground">{item.reason}</p>
      <div className="mt-3 flex flex-wrap gap-1 border-t border-border/70 pt-2">
        <span className="rounded-full border border-border bg-background px-2 py-0.5 text-xs font-semibold text-muted-foreground">
          {item.board_state === "Ready" ? "Start" : item.board_state === "Blocked" ? "Start disabled" : item.lane}
        </span>
        <span className="rounded-full border border-border bg-background px-2 py-0.5 text-xs font-semibold text-muted-foreground">
          {item.blockers.length > 0 ? `${item.blockers.length} blockers` : item.run_id ?? "No run"}
        </span>
      </div>
    </button>
  );
}

function TaskDetailOverlay({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-foreground/25 px-3 py-4 backdrop-blur-[2px] sm:px-5 lg:py-8"
      data-testid="task-detail-overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      {children}
    </div>
  );
}

const confettiPieces = [
  { x: -44, y: -34, color: "#f97316", rotation: "18deg" },
  { x: -28, y: 22, color: "#22c55e", rotation: "-30deg" },
  { x: -10, y: -50, color: "#0ea5e9", rotation: "42deg" },
  { x: 14, y: 28, color: "#eab308", rotation: "-18deg" },
  { x: 34, y: -36, color: "#ec4899", rotation: "28deg" },
  { x: 48, y: 12, color: "#6366f1", rotation: "-42deg" },
  { x: 4, y: -18, color: "#14b8a6", rotation: "12deg" },
  { x: 26, y: -4, color: "#ef4444", rotation: "36deg" }
] as const;

function ConfettiBurstHost({
  bursts,
  onBurstDone
}: {
  bursts: ConfettiBurst[];
  onBurstDone: (id: number) => void;
}) {
  React.useEffect(() => {
    const timers = bursts.map((burst) => window.setTimeout(() => onBurstDone(burst.id), 900));
    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, [bursts, onBurstDone]);

  if (bursts.length === 0) {
    return null;
  }

  return (
    <div aria-hidden="true" className="task-close-confetti-host" data-testid="task-close-confetti-host">
      {bursts.map((burst) => (
        <div
          key={burst.id}
          className="task-close-confetti-burst"
          data-testid="task-close-confetti"
          style={{ left: burst.x, top: burst.y }}
        >
          {confettiPieces.map((piece, index) => (
            <span
              key={`${piece.color}-${index}`}
              className="task-close-confetti-piece"
              style={
                {
                  "--confetti-x": `${piece.x}px`,
                  "--confetti-y": `${piece.y}px`,
                  "--confetti-r": piece.rotation,
                  backgroundColor: piece.color
                } as React.CSSProperties
              }
            />
          ))}
        </div>
      ))}
    </div>
  );
}

function TaskDetail({
  item,
  startingId,
  syncingRunId,
  markingMergedRunId,
  onClose,
  onStart,
  onSync,
  onMarkPrMerged
}: {
  item: BoardItem;
  startingId: string | null;
  syncingRunId: string | null;
  markingMergedRunId: string | null;
  onClose: (origin?: HTMLElement) => void;
  onStart: (storyId: string) => Promise<void>;
  onSync: (runId: string) => Promise<void>;
  onMarkPrMerged: (runId: string) => Promise<void>;
}) {
  const [events, setEvents] = React.useState<RunEvent[]>([]);
  const [review, setReview] = React.useState<ReviewResponse | null>(null);
  const dialogRef = React.useRef<HTMLElement>(null);

  React.useEffect(() => {
    dialogRef.current?.focus();
  }, [item.id]);

  React.useEffect(() => {
    let cancelled = false;
    let timer: number | undefined;

    async function loadEvents() {
      const runId = item.active_run ?? item.run_id;
      if (!runId) {
        setEvents([]);
        return;
      }
      try {
        const response = await fetch(`/api/runs/${encodeURIComponent(runId)}/events`);
        if (response.ok) {
          const data = (await response.json()) as EventsResponse;
          if (!cancelled) {
            setEvents(data.events);
          }
        }
      } finally {
        if (!cancelled) {
          timer = window.setTimeout(loadEvents, 2000);
        }
      }
    }

    void loadEvents();
    return () => {
      cancelled = true;
      if (timer) {
        window.clearTimeout(timer);
      }
    };
  }, [item.active_run, item.run_id]);

  React.useEffect(() => {
    let cancelled = false;
    const runId = item.run_id ?? item.active_run;
    if (!runId || !["Review", "Needs Attention", "Done"].includes(item.board_state)) {
      setReview(null);
      return;
    }
    const reviewRunId = runId;

    async function loadReview() {
      try {
        const response = await fetch(`/api/runs/${encodeURIComponent(reviewRunId)}/review`);
        if (response.ok) {
          const data = (await response.json()) as ReviewResponse;
          if (!cancelled) {
            setReview(data);
          }
        }
      } catch {
        if (!cancelled) {
          setReview(null);
        }
      }
    }

    void loadReview();
    return () => {
      cancelled = true;
    };
  }, [item.active_run, item.board_state, item.run_id]);

  const isReady = item.board_state === "Ready";
  const isStarting = startingId === item.id;

  return (
    <aside
      aria-label="Selected work detail"
      aria-modal="true"
      className="relative max-h-[calc(100dvh-2rem)] min-w-0 w-full max-w-4xl overflow-auto rounded-lg border border-border bg-background shadow-2xl outline-none"
      data-testid="task-detail-popup"
      ref={dialogRef}
      role="dialog"
      tabIndex={-1}
    >
      <Button
        type="button"
        variant="outline"
        size="icon"
        aria-label="Close selected work detail"
        className="sticky top-3 z-10 float-right m-3 bg-background shadow-sm"
        onClick={(event) => onClose(event.currentTarget)}
      >
        <X data-icon="inline-start" />
      </Button>

      <div className="border-b border-border p-4">
        <div className="flex items-center justify-between gap-3">
          <Badge tone={stateTone[item.board_state]}>{item.board_state}</Badge>
          <span className="font-mono text-xs font-bold text-muted-foreground">{item.id}</span>
        </div>
        <h2 className="mt-3 text-2xl font-semibold leading-tight tracking-tight">{item.title}</h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">{item.reason}</p>
        <div className="mt-4 grid grid-cols-2 gap-2">
          <Field label="Lane" value={item.lane} />
          <Field label="Proof" value={item.verify} />
          <Field label="Run" value={item.run_id ?? item.active_run ?? "none"} />
          <Field label="Children" value={item.children.length > 0 ? item.children.join(", ") : "none"} />
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button
            disabled={!isReady || isStarting}
            title={isReady ? "Start task" : "Blocked tasks cannot start"}
            onClick={() => void onStart(item.id)}
          >
            {isStarting ? <Loader2 data-icon="inline-start" className="animate-spin" /> : <Play data-icon="inline-start" />}
            {isReady ? "Start work" : item.board_state === "In Progress" ? "One run active" : "Start blocked"}
          </Button>
          <Button variant="secondary">
            <Clock3 data-icon="inline-start" />
            Open artifacts
          </Button>
        </div>
      </div>

      <div className="flex flex-col gap-4 border-b border-border p-4">
        <SectionTitle>Dependencies</SectionTitle>
        <ListBlock title="Blocked by" values={item.blockers} empty="No blockers" />
        <ListBlock title="Unblocks" values={item.unblocks} empty="No downstream work in this slice." />
        <HierarchyBlock item={item} />
      </div>

      {review ? (
        <div className="border-b border-border p-4">
          <ReviewPanel
            review={review}
            syncing={syncingRunId === review.run_id}
            markingMerged={markingMergedRunId === review.run_id}
            onSync={onSync}
            onMarkPrMerged={onMarkPrMerged}
          />
        </div>
      ) : null}

      {item.active_run || item.run_id ? <EventLog events={review?.events ?? events} /> : null}
    </aside>
  );
}

function HierarchyBlock({ item }: { item: BoardItem }) {
  return (
    <div className="flex flex-col gap-2">
      <SectionTitle>Hierarchy</SectionTitle>
      <div className="grid grid-cols-2 gap-2">
        <Field label="Parent" value={item.parent_id ?? "top level"} />
        <Field label="Depth" value={String(item.hierarchy_depth)} />
      </div>
      <ListBlock title="Child tasks" values={item.children} empty="No child tasks" />
    </div>
  );
}

function ReviewPanel({
  review,
  syncing,
  markingMerged,
  onSync,
  onMarkPrMerged
}: {
  review: ReviewResponse;
  syncing: boolean;
  markingMerged: boolean;
  onSync: (runId: string) => Promise<void>;
  onMarkPrMerged: (runId: string) => Promise<void>;
}) {
  const canMarkMerged = review.pr_status === "created" && review.pr_url !== null;
  const canSync = review.pr_status === "merged" && review.status === "completed";

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <SectionTitle>Review evidence</SectionTitle>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">{review.suggested_next_action}</p>
        </div>
        <Badge tone={review.pr_status === "created" ? "review" : "attention"}>{review.pr_status}</Badge>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <Field label="Outcome" value={review.outcome ?? "unknown"} />
        <Field label="Status" value={review.status} />
      </div>

      {review.pr_url ? (
        <a
          className="block break-all rounded-sm border border-border px-3 py-2 text-sm text-primary hover:bg-accent"
          href={review.pr_url}
          target="_blank"
          rel="noreferrer"
        >
          {review.pr_url}
        </a>
      ) : null}

      {review.summary ? <TextBlock title="Summary" text={review.summary} /> : null}
      {review.validation ? <TextBlock title="Validation" text={JSON.stringify(review.validation, null, 2)} /> : null}
      <ListBlock title="Changed files" values={review.changed_files} empty="No changed files listed" />
      {review.changeset_preview ? <TextBlock title="Changeset" text={review.changeset_preview} /> : null}
      <ListBlock title="Artifacts" values={review.artifact_paths} empty="No artifacts found" />

      <Separator />
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" disabled={!canMarkMerged || markingMerged} onClick={() => void onMarkPrMerged(review.run_id)}>
          {markingMerged ? (
            <Loader2 data-icon="inline-start" className="animate-spin" />
          ) : (
            <GitPullRequestArrow data-icon="inline-start" />
          )}
          Mark Merged
        </Button>
        <Button disabled={!canSync || syncing} onClick={() => void onSync(review.run_id)}>
          {syncing ? <Loader2 data-icon="inline-start" className="animate-spin" /> : <CheckCircle2 data-icon="inline-start" />}
          Approve Sync
        </Button>
      </div>
    </div>
  );
}

function TextBlock({ title, text }: { title: string; text: string }) {
  return (
    <div>
      <SectionTitle>{title}</SectionTitle>
      <pre className="mt-2 max-h-52 overflow-auto whitespace-pre-wrap rounded-md border border-border bg-muted p-3 text-xs leading-5">
        {text}
      </pre>
    </div>
  );
}

function EventLog({ events }: { events: RunEvent[] }) {
  const entries = formatRunLog(events).slice(-12);

  return (
    <div id="logs" className="flex flex-col gap-3 p-4">
      <div className="flex items-baseline justify-between gap-3">
        <SectionTitle>Run communication</SectionTitle>
        <p className="text-xs text-muted-foreground">Raw artifact: APP_SERVER_EVENTS.jsonl</p>
      </div>
      <div className="max-h-80 overflow-auto rounded-md border border-border bg-muted">
        {entries.length > 0 ? (
          entries.map((entry, index) => (
            <div
              key={`${entry.method ?? entry.title}-${index}`}
              className={cn(
                "grid min-h-12 grid-cols-[minmax(0,1fr)] gap-2 border-b border-border/70 px-3 py-3 text-sm last:border-b-0",
                entry.kind === "message" ? "bg-background" : "bg-muted"
              )}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={entry.kind === "message" ? "review" : entry.kind === "progress" ? "progress" : "neutral"}>
                    {entry.source}
                  </Badge>
                  <strong className="font-semibold">{entry.title}</strong>
                </div>
                {entry.timestamp ? <span className="text-xs text-muted-foreground">{entry.timestamp}</span> : null}
              </div>
              <p className="break-words text-sm leading-6 text-muted-foreground">{entry.message}</p>
            </div>
          ))
        ) : (
          <div className="flex min-h-12 items-center px-3 text-sm text-muted-foreground">No run communication yet</div>
        )}
      </div>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 break-words text-sm font-semibold">{value}</div>
    </div>
  );
}

function ListBlock({
  title,
  values,
  empty
}: {
  title: string;
  values: string[];
  empty: string;
}) {
  return (
    <div>
      <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">{title}</p>
      <div className="mt-2 flex min-h-8 flex-wrap gap-2">
        {values.length > 0 ? (
          values.map((value) => (
            <Badge key={value} tone="neutral">
              {value}
            </Badge>
          ))
        ) : (
          <span className="text-sm text-muted-foreground">{empty}</span>
        )}
      </div>
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h3 className="text-xl font-semibold leading-tight">{children}</h3>;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
