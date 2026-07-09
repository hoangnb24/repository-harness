import React from "react";
import ReactDOM from "react-dom/client";
import {
  Activity,
  AlertTriangle,
  PanelTop,
  RefreshCw,
  Search
} from "lucide-react";
import { Button } from "./components/ui/button";
import { Card } from "./components/ui/card";
import { Input } from "./components/ui/input";
import {
  fetchBoard,
  postCreateGuidedIntake,
  postMarkPrMerged,
  postRecoverTask,
  postRetireTask,
  postRetryPr,
  postStartTask,
  postSyncRun
} from "./features/symphony/api";
import { BoardGrid, SummaryStrip } from "./features/symphony/board";
import { ConfettiBurstHost, TaskDetail, TaskDetailOverlay } from "./features/symphony/detail";
import { GuidedIntakePanel } from "./features/symphony/intake";
import { states } from "./features/symphony/constants";
import { ControllerSidebar } from "./features/symphony/sidebar";
import type {
  BoardItem,
  BoardState,
  GuidedIntakeDraft,
  PrMergedResponse,
  PrRetryResponse,
  RecoveryAction
} from "./features/symphony/types";
import { cn } from "./lib/utils";
import "./styles.css";

type ConfettiBurst = {
  id: number;
  x: number;
  y: number;
};

type AppView = "board" | "intake";

function App() {
  const [items, setItems] = React.useState<BoardItem[]>([]);
  const [view, setView] = React.useState<AppView>("board");
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [confettiBursts, setConfettiBursts] = React.useState<ConfettiBurst[]>([]);
  const [query, setQuery] = React.useState("");
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [startingId, setStartingId] = React.useState<string | null>(null);
  const [deletingId, setDeletingId] = React.useState<string | null>(null);
  const [recoveringId, setRecoveringId] = React.useState<string | null>(null);
  const [syncingRunId, setSyncingRunId] = React.useState<string | null>(null);
  const [markingMergedRunId, setMarkingMergedRunId] = React.useState<string | null>(null);
  const [retryingPrRunId, setRetryingPrRunId] = React.useState<string | null>(null);
  const [creatingStory, setCreatingStory] = React.useState(false);
  const [intakeError, setIntakeError] = React.useState<string | null>(null);
  const confettiBurstIdRef = React.useRef(0);
  const boardRequestIdRef = React.useRef(0);
  const selectedOpenerRef = React.useRef<HTMLElement | null>(null);
  const prefersReducedMotion = usePrefersReducedMotion();

  const loadBoard = React.useCallback(async (options?: { silent?: boolean }) => {
    const requestId = (boardRequestIdRef.current += 1);
    if (!options?.silent) {
      setLoading(true);
    }
    if (!options?.silent) {
      setError(null);
    }
    try {
      const data = await fetchBoard();
      if (requestId !== boardRequestIdRef.current) {
        return;
      }
      setItems(data.items);
    } catch (cause) {
      if (requestId === boardRequestIdRef.current && !options?.silent) {
        setError(cause instanceof Error ? cause.message : "Board request failed");
      }
    } finally {
      if (requestId === boardRequestIdRef.current && !options?.silent) {
        setLoading(false);
      }
    }
  }, []);

  React.useEffect(() => {
    void loadBoard();
  }, [loadBoard]);

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
  const selectTask = React.useCallback((id: string) => {
    selectedOpenerRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setSelectedId(id);
  }, []);

  React.useEffect(() => {
    if (!activeRun?.active_run) {
      return;
    }
    const timer = window.setInterval(() => {
      void loadBoard({ silent: true });
    }, 1500);
    return () => window.clearInterval(timer);
  }, [activeRun?.active_run, loadBoard]);

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
        await postStartTask(storyId);
        await loadBoard();
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : "Start failed");
      } finally {
        setStartingId(null);
      }
    },
    [loadBoard]
  );

  const runTaskFromBoard = React.useCallback(
    async (item: BoardItem) => {
      if (!window.confirm(`Run ${item.id} with Codex? This starts Symphony and allows Codex to edit the repository.`)) {
        return;
      }
      await startTask(item.id);
    },
    [startTask]
  );

  const retireTask = React.useCallback(
    async (item: BoardItem) => {
      if (!window.confirm(`Retire ${item.id} ${item.title}? This removes it from active Ready work without deleting history.`)) {
        return;
      }
      setDeletingId(item.id);
      setError(null);
      try {
        await postRetireTask(item.id);
        setSelectedId(null);
        await loadBoard();
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : "Delete failed");
      } finally {
        setDeletingId(null);
      }
    },
    [loadBoard]
  );

  const recoverTask = React.useCallback(
    async (storyId: string, action: RecoveryAction) => {
      if (!window.confirm(action.confirmation)) {
        return;
      }
      setRecoveringId(storyId);
      setError(null);
      try {
        await postRecoverTask(action);
        await loadBoard();
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : "Recovery failed");
      } finally {
        setRecoveringId(null);
      }
    },
    [loadBoard]
  );

  const syncRun = React.useCallback(
    async (runId: string) => {
      setSyncingRunId(runId);
      setError(null);
      try {
        const result = await postSyncRun(runId);
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
    async (runId: string): Promise<PrMergedResponse> => {
      setMarkingMergedRunId(runId);
      setError(null);
      try {
        const result = await postMarkPrMerged(runId);
        await loadBoard();
        return result;
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : "Merge update failed");
        throw cause;
      } finally {
        setMarkingMergedRunId(null);
      }
    },
    [loadBoard]
  );

  const retryPr = React.useCallback(
    async (runId: string, action: RecoveryAction): Promise<PrRetryResponse> => {
      if (!window.confirm(action.confirmation)) {
        throw new Error("PR retry cancelled");
      }
      setRetryingPrRunId(runId);
      setError(null);
      try {
        const result = await postRetryPr(action);
        await loadBoard();
        return result;
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : "PR retry failed");
        throw cause;
      } finally {
        setRetryingPrRunId(null);
      }
    },
    [loadBoard]
  );

  const createGuidedStory = React.useCallback(
    async (draft: GuidedIntakeDraft) => {
      if (!window.confirm("Create a durable Harness story from this guided intake? This writes intake and story records but does not start Symphony.")) {
        return;
      }
      setCreatingStory(true);
      setIntakeError(null);
      try {
        const story = await postCreateGuidedIntake(draft);
        await loadBoard();
        setQuery(story.story_id);
        setView("board");
      } catch (cause) {
        setIntakeError(cause instanceof Error ? cause.message : "Create story failed");
      } finally {
        setCreatingStory(false);
      }
    },
    [loadBoard]
  );

  function switchView(nextView: AppView) {
    setView(nextView);
    if (nextView === "intake") {
      setSelectedId(null);
    }
  }

  return (
    <main className="min-h-screen bg-muted/45 text-foreground">
      <div className="mx-auto grid w-full max-w-[1760px] grid-cols-1 gap-3 p-3 md:p-4 lg:grid-cols-[240px_minmax(0,1fr)] xl:p-5">
        <ControllerSidebar counts={counts} items={items} selectedId={selected?.id ?? null} onSelect={selectTask} />

        <div className="flex min-w-0 flex-col gap-3">
          <header className="rounded-lg border border-border bg-background p-3">
            <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2 text-xs font-semibold text-muted-foreground">
                  <span className="inline-flex min-h-7 items-center gap-2 rounded-full border border-border bg-muted px-2.5">
                    <PanelTop className="size-3.5" />
                    Local operations surface
                  </span>
                  <span className="inline-flex min-h-7 items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 text-emerald-800">
                    <Activity className={cn("size-3.5", activeRun?.active_run && "motion-safe:animate-pulse")} />
                    {activeRun?.active_run ? "Run active" : "No active run"}
                  </span>
                </div>
                <h1 className="mt-2 text-2xl font-semibold leading-tight tracking-normal md:text-[32px]">
                  Symphony Command Center
                </h1>
                <p className="mt-1 max-w-3xl text-sm font-medium leading-6 text-muted-foreground">
                  Start safe work, watch the active run, review evidence, and sync accepted changes from one local controller.
                </p>
                <div role="tablist" aria-label="Command Center views" className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    role="tab"
                    aria-selected={view === "board"}
                    className={cn(
                      "min-h-9 rounded-sm border px-3 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                      view === "board" ? "border-primary bg-primary text-primary-foreground" : "border-border bg-muted text-muted-foreground hover:text-foreground"
                    )}
                    onClick={() => switchView("board")}
                  >
                    Work Board
                  </button>
                  <button
                    type="button"
                    role="tab"
                    aria-selected={view === "intake"}
                    className={cn(
                      "min-h-9 rounded-sm border px-3 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                      view === "intake" ? "border-primary bg-primary text-primary-foreground" : "border-border bg-muted text-muted-foreground hover:text-foreground"
                    )}
                    onClick={() => switchView("intake")}
                  >
                    Guided Intake
                  </button>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2 xl:justify-end">
                <label className="relative block w-full sm:w-80">
                  <span className="sr-only">Find task</span>
                  <Search className="pointer-events-none absolute left-3 top-2.5 size-4 text-muted-foreground" />
                  <Input
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    className="h-10 bg-muted/60 pl-9"
                    placeholder="Find task or story ID"
                    aria-label="Find task"
                  />
                </label>
                <Button variant="outline" onClick={() => void loadBoard()} disabled={loading} className="h-10 bg-background">
                  <RefreshCw data-icon="inline-start" className={cn(loading && "motion-safe:animate-spin")} />
                  Refresh
                </Button>
              </div>
            </div>
          </header>

          {view === "board" ? <SummaryStrip activeRun={activeRun} counts={counts} className="order-1 md:order-none" /> : null}

          {view === "board" && error ? (
            <Card role="alert" className="order-1 flex items-center gap-3 border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive md:order-none">
              <AlertTriangle className="size-4 shrink-0" />
              {error}
            </Card>
          ) : null}

          {view === "board" ? (
            <section
              id="board"
              aria-busy={loading}
              className="command-board-surface order-2 grid min-h-[calc(100dvh-232px)] grid-cols-1 gap-3 rounded-lg border border-border bg-background p-2 md:order-none"
            >
              <div className="sr-only" role="status" aria-live="polite">
                {loading
                  ? "Loading Symphony board."
                  : activeRun?.active_run
                    ? `Active run ${activeRun.active_run} is updating.`
                    : "Symphony board loaded."}
              </div>
              <BoardGrid
                items={filtered}
                selectedId={selected?.id ?? null}
                activeRunId={activeRun?.active_run ?? null}
                startingId={startingId}
                onSelect={selectTask}
                onRun={runTaskFromBoard}
              />
            </section>
          ) : (
            <GuidedIntakePanel creating={creatingStory} error={intakeError} onCreate={createGuidedStory} />
          )}

          <ConfettiBurstHost bursts={confettiBursts} onBurstDone={clearConfettiBurst} />

          {selected ? (
            <TaskDetailOverlay restoreFocusElement={selectedOpenerRef.current} onClose={() => setSelectedId(null)}>
              <TaskDetail
                item={selected}
                startingId={startingId}
                deletingId={deletingId}
                recoveringId={recoveringId}
                syncingRunId={syncingRunId}
                markingMergedRunId={markingMergedRunId}
                retryingPrRunId={retryingPrRunId}
                onClose={closeSelectedTask}
                onStart={startTask}
                onRetire={retireTask}
                onRecover={recoverTask}
                onSync={syncRun}
                onMarkPrMerged={markPrMerged}
                onRetryPr={retryPr}
              />
            </TaskDetailOverlay>
          ) : null}

          <p className="order-4 text-xs leading-5 text-muted-foreground md:order-none">
            {view === "board"
              ? "Source: local Symphony API responses for board state, run events, review artifacts, PR status, and sync state."
              : "Source: local draft state until explicit create writes Harness intake and story records."}
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

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
