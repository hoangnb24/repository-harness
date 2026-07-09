import { ArrowRight, GitBranch } from "lucide-react";
import type * as React from "react";
import { cn } from "../../lib/utils";
import { columnId } from "./constants";
import { StatusBadge } from "./status-badge";
import type { BoardItem, BoardState } from "./types";

export function ControllerSidebar({
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
      className="flex min-h-0 flex-col rounded-lg border border-border bg-background p-3 lg:sticky lg:top-4 lg:min-h-[calc(100vh-40px)]"
    >
      <div className="mb-3 rounded-md border border-border bg-muted/55 p-2.5">
        <div className="flex items-center gap-2 text-sm font-bold">
        <span className="grid size-7 place-items-center rounded-sm border border-border bg-background font-mono text-xs">
          S
        </span>
          <span>Symphony</span>
        </div>
        <p className="mt-2 text-xs leading-5 text-muted-foreground">
          Local run control for the current repository.
        </p>
      </div>

      <nav aria-label="Primary" className="scrollbar-none flex gap-1 overflow-x-auto border-t border-border/70 py-2 lg:flex-col lg:overflow-visible">
        <SidebarLabel>Workspace</SidebarLabel>
        <SidebarItem active href="#board" label="Work board" count={String(Object.values(counts).reduce((sum, count) => sum + count, 0))} />
        <details className="min-w-56 rounded-sm lg:min-w-0">
          <summary className="flex min-h-9 cursor-pointer list-none items-center justify-between rounded-sm px-2 text-sm font-semibold text-muted-foreground hover:bg-muted hover:text-foreground">
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
        <SidebarItem href="#logs" label="Run logs" count="live" />
      </nav>

      <nav aria-label="Status" className="scrollbar-none mt-2 flex gap-1 overflow-x-auto border-t border-border/70 py-2 lg:flex-col lg:overflow-visible">
        <SidebarLabel>Status</SidebarLabel>
        <SidebarItem href={`#${columnId("Ready")}`} label="Ready" count={String(counts.Ready)} />
        <SidebarItem href={`#${columnId("Blocked")}`} label="Blocked" count={String(counts.Blocked)} />
        <SidebarItem href={`#${columnId("Review")}`} label="Review" count={String(counts.Review)} />
      </nav>

      <SidebarDependencyGraph items={items} selectedId={selectedId} onSelect={onSelect} />
    </aside>
  );
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
                "w-full rounded-md border border-border bg-muted/45 p-2 text-left transition hover:border-primary hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                item.id === selectedId && "border-primary bg-accent"
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <strong className="font-mono text-xs">{item.id}</strong>
                <StatusBadge state={item.board_state} />
              </div>
              <p className="mt-1 line-clamp-2 text-xs font-semibold leading-5">{item.title}</p>
              <div className="mt-2 grid gap-1 text-xs leading-5 text-muted-foreground">
                {item.blockers.length > 0 ? <GraphLine left={item.blockers.join(", ")} right={item.id} /> : null}
                {item.unblocks.length > 0 ? <GraphLine left={item.id} right={item.unblocks.join(", ")} /> : null}
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

function SidebarLabel({ children }: { children: React.ReactNode }) {
  return <p className="hidden px-2 py-2 text-xs font-semibold text-muted-foreground lg:block">{children}</p>;
}

function SidebarItem({
  label,
  count,
  href,
  active = false
}: {
  label: string;
  count: string;
  href: string;
  active?: boolean;
}) {
  return (
    <a
      href={href}
      aria-current={active ? "page" : undefined}
      className={cn(
        "flex min-h-9 min-w-max items-center justify-between gap-3 rounded-sm px-2 text-sm font-semibold text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring lg:min-w-0",
        active && "bg-muted text-foreground"
      )}
    >
      <span>{label}</span>
      <span className="font-mono text-xs text-muted-foreground">{count}</span>
    </a>
  );
}
