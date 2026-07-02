import * as React from "react";
import { cn } from "../../lib/utils";

type BadgeTone = "neutral" | "ready" | "blocked" | "progress" | "review" | "attention" | "done";

const tones: Record<BadgeTone, string> = {
  neutral: "border-border bg-muted text-muted-foreground",
  ready: "border-emerald-200 bg-emerald-50 text-emerald-800",
  blocked: "border-zinc-300 bg-zinc-100 text-zinc-700",
  progress: "border-blue-200 bg-blue-50 text-blue-800",
  review: "border-violet-200 bg-violet-50 text-violet-800",
  attention: "border-red-200 bg-red-50 text-red-800",
  done: "border-teal-200 bg-teal-50 text-teal-800"
};

export function Badge({
  className,
  tone = "neutral",
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { tone?: BadgeTone }) {
  return (
    <span
      className={cn(
        "inline-flex h-6 items-center rounded-md border px-2 text-xs font-medium",
        tones[tone],
        className
      )}
      {...props}
    />
  );
}
