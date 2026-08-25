// The pipeline stepper. Purely presentational: it renders the stage list
// it's handed and derives nothing itself — IncidentDetail owns the state
// that decides which stage is done/current/pending, same division of
// labour every other component here follows.
//
// This exists because the workflow used to be an undifferentiated vertical
// stack of same-weight sections, with nothing indicating that they were
// sequential steps of one process or which step you were on.

export type StageState = "done" | "current" | "pending";

export interface PipelineStage {
  label: string;
  state: StageState;
}

const DOT_STYLES: Record<StageState, string> = {
  done: "border-emerald-500/40 bg-emerald-500/15 text-emerald-300",
  current: "border-slate-300 bg-slate-100 text-slate-900",
  pending: "border-slate-800 bg-slate-900 text-slate-600",
};

const LABEL_STYLES: Record<StageState, string> = {
  done: "text-slate-400",
  current: "text-slate-100 font-medium",
  pending: "text-slate-600",
};

export default function PipelineStages({ stages }: { stages: PipelineStage[] }) {
  return (
    <nav aria-label="Workflow progress" className="flex items-center gap-1 overflow-x-auto pb-1">
      {stages.map((stage, index) => (
        <div key={stage.label} className="flex shrink-0 items-center gap-1">
          <div className="flex items-center gap-2 px-1">
            <span
              aria-hidden="true"
              className={`flex h-5 w-5 items-center justify-center rounded-full border text-[11px] font-semibold ${DOT_STYLES[stage.state]}`}
            >
              {/* A tick for completed stages, the step number otherwise —
                  the number stays useful as a "how far through am I" cue. */}
              {stage.state === "done" ? "✓" : index + 1}
            </span>
            <span className={`whitespace-nowrap text-xs ${LABEL_STYLES[stage.state]}`}>
              {stage.label}
              {stage.state === "current" && <span className="sr-only"> (current stage)</span>}
            </span>
          </div>

          {index < stages.length - 1 && (
            <span
              aria-hidden="true"
              className={`h-px w-6 ${stage.state === "done" ? "bg-emerald-500/30" : "bg-slate-800"}`}
            />
          )}
        </div>
      ))}
    </nav>
  );
}
