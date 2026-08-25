// One consistent frame for every stage of the workflow: step number,
// title, one-line hint, and a slot for that stage's single action.
//
// Before this, each panel rendered its own `<h2 className="text-sm
// font-medium text-slate-300">` and the stage's action button lived
// wherever it happened to be wired up — so Create Incident, Investigate,
// Get Remediation and Resolve all sat at different visual weights in
// different places. Panels now render content only; this owns the chrome.

import type { ReactNode } from "react";

interface StageSectionProps {
  step: number;
  title: string;
  // Short explanation of what this stage does. Also the place to state
  // when something happens automatically.
  hint?: string;
  // Completed — shows a tick instead of the step number.
  done?: boolean;
  // Not yet reachable. Dims the whole section and marks it inert to
  // assistive tech, so an unreachable stage still communicates that it
  // exists and what will unlock it (via `hint`).
  pending?: boolean;
  // This stage's action, right-aligned in the header row.
  action?: ReactNode;
  children: ReactNode;
}

export default function StageSection({
  step,
  title,
  hint,
  done = false,
  pending = false,
  action,
  children,
}: StageSectionProps) {
  return (
    <section aria-current={!done && !pending ? "step" : undefined} className={pending ? "opacity-50" : undefined}>
      <div className="mb-2 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-200">
            <span
              aria-hidden="true"
              className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[11px] font-semibold ${
                done
                  ? "border-emerald-500/40 bg-emerald-500/15 text-emerald-300"
                  : pending
                    ? "border-slate-800 bg-slate-900 text-slate-600"
                    : "border-slate-700 bg-slate-800 text-slate-300"
              }`}
            >
              {done ? "✓" : step}
            </span>
            {title}
          </h2>
          {hint && <p className="mt-1 pl-7 text-xs leading-relaxed text-slate-500">{hint}</p>}
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </div>

      <div className="pl-7">{children}</div>
    </section>
  );
}
