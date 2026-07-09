import React from "react";
import { CheckCircle2, ClipboardList, Lightbulb, ShieldCheck } from "lucide-react";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Card } from "../../components/ui/card";
import { cn } from "../../lib/utils";
import type { GuidedIntakeDraft } from "./types";

type DraftAnswers = {
  audience: string;
  outcome: string;
  nonGoals: string;
  validation: string;
};

const questions = [
  {
    key: "audience",
    label: "Who benefits from this work?",
    helper: "Name the operator or reviewer. This keeps the story grounded in a real workflow."
  },
  {
    key: "outcome",
    label: "What should be true when this succeeds?",
    helper: "Write the acceptance shape, not the implementation."
  },
  {
    key: "nonGoals",
    label: "What should stay out of scope?",
    helper: "State what the story must not change so Symphony can stay bounded."
  },
  {
    key: "validation",
    label: "What proof should show it worked?",
    helper: "Use a command, screenshot, API result, or review artifact."
  }
] as const;

type GuidedIntakePanelProps = {
  creating: boolean;
  error: string | null;
  onCreate: (draft: GuidedIntakeDraft) => Promise<void>;
};

export function GuidedIntakePanel({ creating, error, onCreate }: GuidedIntakePanelProps) {
  const [idea, setIdea] = React.useState("");
  const [activeIndex, setActiveIndex] = React.useState(0);
  const [answers, setAnswers] = React.useState<DraftAnswers>({
    audience: "",
    outcome: "",
    nonGoals: "",
    validation: ""
  });
  const activeQuestion = questions[activeIndex];
  const activeAnswer = answers[activeQuestion.key];
  const completedCount = Object.values(answers).filter((value) => value.trim().length > 0).length;
  const draft = React.useMemo(
    () => ({
      idea: idea.trim(),
      audience: answers.audience.trim(),
      outcome: answers.outcome.trim(),
      non_goals: answers.nonGoals.trim(),
      validation: answers.validation.trim()
    }),
    [answers, idea]
  );
  const canCreate = draft.idea.length > 0 && draft.outcome.length > 0 && draft.validation.length > 0;

  function updateAnswer(value: string) {
    setAnswers((current) => ({ ...current, [activeQuestion.key]: value }));
  }

  return (
    <section className="grid gap-3 xl:grid-cols-[minmax(0,0.95fr)_minmax(360px,0.65fr)]" aria-label="Guided Intake">
      <Card className="min-w-0 rounded-lg p-4">
        <div className="flex flex-col gap-3 border-b border-border pb-4 md:flex-row md:items-start md:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="grid size-9 place-items-center rounded-md border border-blue-200 bg-blue-50 text-blue-800">
                <ClipboardList className="size-4" />
              </span>
              <Badge tone="info">Guarded create</Badge>
              <Badge tone="neutral">{completedCount}/4 answered</Badge>
            </div>
            <h2 className="mt-3 text-2xl font-semibold leading-tight">Guided Intake</h2>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">
              Turn a rough idea into a Harness-ready story draft, then create a durable story when the scope and proof are clear.
            </p>
          </div>
          <div className="rounded-md border border-border bg-muted/60 px-3 py-2 text-xs leading-5 text-muted-foreground">
            Explicit create writes intake and story records. It never starts Symphony.
          </div>
        </div>

        <div className="mt-4 grid gap-4">
          <label className="grid gap-2">
            <span className="text-sm font-semibold">Rough idea</span>
            <textarea
              aria-label="Rough idea"
              value={idea}
              onChange={(event) => setIdea(event.target.value)}
              placeholder="Example: Make review evidence easier to scan"
              className="min-h-28 resize-y rounded-sm border border-input bg-background px-3 py-2 text-sm leading-6 text-foreground shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </label>

          <div className="rounded-md border border-border bg-muted/45 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="text-xs font-semibold text-muted-foreground">Question {activeIndex + 1} of {questions.length}</p>
                <label htmlFor="guided-intake-answer" className="mt-1 block text-sm font-semibold">
                  {activeQuestion.label}
                </label>
              </div>
              <div className="flex gap-1">
                {questions.map((question, index) => (
                  <button
                    key={question.key}
                    type="button"
                    onClick={() => setActiveIndex(index)}
                    aria-label={`Go to intake question ${index + 1}`}
                    className={cn(
                      "size-7 rounded-sm border text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                      index === activeIndex
                        ? "border-primary bg-primary text-primary-foreground"
                        : answers[question.key].trim().length > 0
                          ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                          : "border-border bg-background text-muted-foreground"
                    )}
                  >
                    {index + 1}
                  </button>
                ))}
              </div>
            </div>
            <p className="mt-2 text-xs leading-5 text-muted-foreground">{activeQuestion.helper}</p>
            <textarea
              id="guided-intake-answer"
              aria-label={activeQuestion.label}
              value={activeAnswer}
              onChange={(event) => updateAnswer(event.target.value)}
              className="mt-3 min-h-24 w-full resize-y rounded-sm border border-input bg-background px-3 py-2 text-sm leading-6 text-foreground shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              placeholder="Type the answer that should appear in the story draft"
            />
            <div className="mt-3 flex flex-wrap gap-2">
              <Button
                type="button"
                variant="outline"
                disabled={activeIndex === 0}
                onClick={() => setActiveIndex((index) => Math.max(0, index - 1))}
              >
                Previous question
              </Button>
              <Button
                type="button"
                onClick={() => setActiveIndex((index) => Math.min(questions.length - 1, index + 1))}
                disabled={activeIndex === questions.length - 1}
              >
                Next question
              </Button>
            </div>
          </div>
        </div>
      </Card>

      <DraftPreview
        idea={idea}
        answers={answers}
        canCreate={canCreate}
        creating={creating}
        error={error}
        onCreate={() => onCreate(draft)}
      />
    </section>
  );
}

function DraftPreview({
  idea,
  answers,
  canCreate,
  creating,
  error,
  onCreate
}: {
  idea: string;
  answers: DraftAnswers;
  canCreate: boolean;
  creating: boolean;
  error: string | null;
  onCreate: () => Promise<void>;
}) {
  const normalizedIdea = idea.trim() || "Untitled intake idea";
  const validation = answers.validation.trim() || "Recommended: Playwright UI check plus build verification.";

  return (
    <Card role="region" aria-label="Draft story preview" className="min-w-0 rounded-lg p-4">
      <div className="flex items-start gap-3">
        <span className="grid size-9 shrink-0 place-items-center rounded-md border border-emerald-200 bg-emerald-50 text-emerald-800">
          <Lightbulb className="size-4" />
        </span>
        <div className="min-w-0">
          <p className="text-xs font-semibold text-muted-foreground">Preview</p>
          <h3 className="bounded-text mt-1 text-xl font-semibold leading-tight">{normalizedIdea}</h3>
        </div>
      </div>

      <div className="mt-4 grid gap-3 text-sm leading-6">
        <PreviewRow label="Audience" value={answers.audience || "Not answered yet"} />
        <PreviewRow label="Outcome" value={answers.outcome || "Not answered yet"} />
        <PreviewRow label="Non-goals" value={answers.nonGoals || "Not answered yet"} />
        <PreviewRow label="Validation" value={validation} />
      </div>

      <div className="mt-4 rounded-md border border-border bg-muted/55 p-3">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <ShieldCheck className="size-4 text-emerald-700" />
          Normal lane
        </div>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">
          This create path writes intake and story records only. Dependencies, execution, PR, and sync stay untouched.
        </p>
      </div>

      {error ? (
        <div role="alert" className="mt-4 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-xs leading-5 text-destructive">
          {error}
        </div>
      ) : null}

      <div className="mt-4 flex flex-col gap-2 rounded-md border border-border p-3">
        <Button type="button" onClick={() => void onCreate()} disabled={!canCreate || creating}>
          <CheckCircle2 />
          {creating ? "Creating story" : "Create story"}
        </Button>
        <p className="text-xs leading-5 text-muted-foreground">
          Requires rough idea, outcome, and validation proof. Creation writes Harness records only; execution stays manual.
        </p>
      </div>
    </Card>
  );
}

function PreviewRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-background p-3">
      <p className="text-xs font-semibold text-muted-foreground">{label}</p>
      <p className="bounded-text mt-1 font-medium">{value}</p>
    </div>
  );
}
