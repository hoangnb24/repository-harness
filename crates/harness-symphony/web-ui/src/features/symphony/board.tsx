import { AlertTriangle, GitPullRequestArrow, PlayCircle, Radio, ShieldAlert } from "lucide-react";
import { Badge } from "../../components/ui/badge";
import { Card } from "../../components/ui/card";
import { cn } from "../../lib/utils";
import { columnId, stateIcon, states } from "./constants";
import { StatusBadge, toneForState } from "./status-badge";
import type { BoardItem, BoardState } from "./types";

export function SummaryStrip({
  activeRun,
  counts,
  className
}: {
  activeRun: BoardItem | undefined;
  counts: Record<BoardState, number>;
  className?: string;
}) {
  const metrics = [
    {
      label: "Active run",
      value: activeRun?.id ?? "none",
      detail: activeRun?.active_run ? `${activeRun.active_run} is the only task allowed in progress.` : "No active Symphony run.",
      icon: Radio,
      className: activeRun?.active_run ? "border-blue-200 bg-blue-50 text-blue-950" : "border-border bg-card"
    },
    {
      label: "Safe to start",
      value: `${counts.Ready} ready`,
      detail: "Ready tasks have no incomplete blockers.",
      icon: PlayCircle,
      className: "border-emerald-200 bg-emerald-50 text-emerald-950"
    },
    {
      label: "Avoid for now",
      value: `${counts.Blocked} blocked`,
      detail: "Blocked work explains its missing dependency before action.",
      icon: ShieldAlert,
      className: "border-zinc-300 bg-zinc-100 text-zinc-950"
    },
    {
      label: "Needs decision",
      value: `${counts.Review} review`,
      detail: "Merge PR first, then approve local sync.",
      icon: GitPullRequestArrow,
      className: "border-violet-200 bg-violet-50 text-violet-950"
    }
  ];

  return (
    <section
      aria-label="Command status rail"
      className={cn("scrollbar-none flex gap-2 overflow-x-auto md:grid md:grid-cols-2 md:overflow-visible xl:grid-cols-[1.2fr_.9fr_.9fr_1fr]", className)}
    >
      {metrics.map((metric) => {
        const Icon = metric.icon;
        return (
        <Card key={metric.label} className={cn("min-w-[210px] rounded-md p-3 md:min-w-0", metric.className)}>
          <div className="flex items-start gap-3">
            <span className="grid size-8 shrink-0 place-items-center rounded-md border border-current/15 bg-white/50">
              <Icon className="size-4" />
            </span>
            <div className="min-w-0">
              <span className="text-xs font-semibold text-current/70">{metric.label}</span>
              <strong className="mt-0.5 block truncate text-xl leading-tight">{metric.value}</strong>
              <p className="mt-1 text-xs leading-5 text-current/70">{metric.detail}</p>
            </div>
          </div>
        </Card>
        );
      })}
    </section>
  );
}

export function BoardGrid({
  items,
  selectedId,
  onSelect
}: {
  items: BoardItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="min-h-0 min-w-0 overflow-x-auto">
      <div className="grid h-[calc(100dvh-244px)] min-h-[410px] min-w-[1120px] grid-cols-[repeat(6,minmax(176px,1fr))] items-stretch gap-2.5 max-sm:h-auto max-sm:min-h-0 max-sm:min-w-0 max-sm:grid-cols-1">
        {states.map((state) => {
          const stateItems = items.filter((item) => item.board_state === state);
          const Icon = stateIcon[state];
          return (
            <section
              key={state}
              id={columnId(state)}
              aria-label={`${state} column`}
              className={cn(
                "flex h-full min-h-0 flex-col overflow-hidden rounded-md border bg-muted/45 max-sm:h-[min(520px,calc(100dvh-180px))] max-sm:min-h-[320px]",
                columnChrome[state]
              )}
            >
              <div className="flex min-h-12 items-center justify-between gap-2 border-b border-border/80 bg-background px-3">
                <div className="flex items-center gap-2">
                  <span className={cn("grid size-6 place-items-center rounded-md border", columnIcon[state])}>
                    <Icon className={cn("size-3.5", state === "In Progress" && "motion-safe:animate-spin")} />
                  </span>
                  <h2 className="text-sm font-bold">{state}</h2>
                </div>
                <StatusBadge state={state}>{stateItems.length}</StatusBadge>
              </div>
              <div aria-label={`${state} tasks`} className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto p-2">
                {stateItems.map((item) => (
                  <TaskCard key={item.id} item={item} selected={item.id === selectedId} onSelect={onSelect} />
                ))}
                {stateItems.length === 0 ? (
                  <div className="flex min-h-24 items-center justify-center rounded-md border border-dashed border-border bg-background/65 px-3 text-center text-xs text-muted-foreground">
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
        "group block min-h-[136px] w-full min-w-0 shrink-0 overflow-hidden rounded-md border bg-background p-3 text-left transition-colors hover:border-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        cardChrome[item.board_state],
        selected && "border-primary ring-2 ring-ring/25",
        blocked && "bg-zinc-100",
        attention && "bg-red-50",
        done && "opacity-80"
      )}
      data-testid="task-card"
    >
      <div className="flex min-w-0 items-center justify-between gap-2">
        <span className="flex min-w-0 items-center gap-1.5 truncate font-mono text-xs font-bold text-muted-foreground">
          <span className={cn("size-2 shrink-0 rounded-full", stateDot[item.board_state])} />
          <span className="min-w-0 truncate">{item.id}</span>
        </span>
        <Badge className="max-w-[58%] shrink-0 truncate" tone={item.verify === "configured" ? toneForState(item.board_state) : "neutral"}>
          {item.board_state === "In Progress" ? "active" : item.verify}
        </Badge>
      </div>
      <h3 className="bounded-text mt-2 line-clamp-3 text-sm font-bold leading-5">{item.title}</h3>
      <p className="bounded-text mt-2 line-clamp-2 text-xs leading-5 text-muted-foreground">{item.reason}</p>
      {item.failure_summary ? (
        <div className="mt-2 flex min-w-0 items-start gap-2 overflow-hidden rounded-sm border border-destructive/20 bg-destructive/10 px-2 py-1 text-xs font-semibold text-destructive">
          <AlertTriangle className="size-3 shrink-0" />
          <span className="bounded-text line-clamp-2 min-w-0">{item.failure_summary.category}</span>
        </div>
      ) : null}
      <div className="mt-3 flex min-w-0 flex-wrap gap-1 border-t border-border/70 pt-2">
        <span className="max-w-full truncate rounded-full border border-border bg-background/80 px-2 py-0.5 text-xs font-semibold text-muted-foreground">
          {item.board_state === "Ready" ? "Start" : item.board_state === "Blocked" ? "Start disabled" : item.lane}
        </span>
        <span className="max-w-full truncate rounded-full border border-border bg-background/80 px-2 py-0.5 text-xs font-semibold text-muted-foreground">
          {item.blockers.length > 0 ? `${item.blockers.length} blockers` : item.run_id ?? "No run"}
        </span>
      </div>
    </button>
  );
}

const columnChrome: Record<BoardState, string> = {
  Ready: "border-emerald-200/80",
  Blocked: "border-zinc-300",
  "In Progress": "border-blue-200/80",
  Review: "border-violet-200/80",
  "Needs Attention": "border-red-200/80",
  Done: "border-teal-200/80"
};

const columnIcon: Record<BoardState, string> = {
  Ready: "border-emerald-200 bg-emerald-50 text-emerald-800",
  Blocked: "border-zinc-300 bg-zinc-100 text-zinc-700",
  "In Progress": "border-blue-200 bg-blue-50 text-blue-800",
  Review: "border-violet-200 bg-violet-50 text-violet-800",
  "Needs Attention": "border-red-200 bg-red-50 text-red-800",
  Done: "border-teal-200 bg-teal-50 text-teal-800"
};

const cardChrome: Record<BoardState, string> = {
  Ready: "border-emerald-200 hover:bg-emerald-50/45",
  Blocked: "border-zinc-300",
  "In Progress": "border-blue-200 hover:bg-blue-50/45",
  Review: "border-violet-200 hover:bg-violet-50/45",
  "Needs Attention": "border-red-200",
  Done: "border-teal-200 hover:bg-teal-50/45"
};

const stateDot: Record<BoardState, string> = {
  Ready: "bg-emerald-500",
  Blocked: "bg-zinc-500",
  "In Progress": "bg-blue-500",
  Review: "bg-violet-500",
  "Needs Attention": "bg-red-500",
  Done: "bg-teal-500"
};
