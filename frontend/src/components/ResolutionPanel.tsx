// Stage 6: resolution. Presentational — status transitions are performed
// by IncidentDetail via onChangeStatus.
//
// The status controls used to be three identical ghost buttons inside
// IncidentHeader, with the current status's button disabled. That made
// "Open", "Investigating" and "Resolved" look like three equally likely
// things to click, gave no indication that Resolved is the end of the
// workflow, and left the same three buttons sitting there after an
// incident was already resolved.
//
// Two rules here:
//   1. Only transitions that actually change something are offered. The
//      current status is never an option, which is also what keeps a click
//      from ever hitting the backend's no-op rejection.
//   2. Once resolved, the workflow is stated as complete and the only
//      remaining action is an explicit reopen.
//
// No automatic transitions: nothing here fires on investigate or remediate.
// A human still decides when something is resolved.

import type { IncidentStatus } from "../types/api";
import { btnGhost, btnPrimary, btnSecondary, card } from "./ui";

interface ResolutionPanelProps {
  status: IncidentStatus;
  resolvedAt: string | null;
  // Whether a diagnosis exists yet. Resolving without one is allowed, but
  // it isn't the recommended path, so it stays secondary-weight.
  hasInvestigation: boolean;
  // True when resolving is the recommended next action.
  isNextAction: boolean;
  isChangingStatus: boolean;
  onChangeStatus: (status: IncidentStatus) => void;
}

export default function ResolutionPanel({
  status,
  resolvedAt,
  hasInvestigation,
  isNextAction,
  isChangingStatus,
  onChangeStatus,
}: ResolutionPanelProps) {
  if (status === "resolved") {
    return (
      <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-sm font-medium text-emerald-300">Workflow complete</p>
            <p className="mt-1 text-xs leading-relaxed text-emerald-400/80">
              This incident is resolved
              {resolvedAt && <> on {new Date(resolvedAt).toLocaleString()}</>}. The investigation and
              remediation above are kept as an immutable record.
            </p>
          </div>
          <button
            type="button"
            onClick={() => onChangeStatus("investigating")}
            disabled={isChangingStatus}
            className={`${btnGhost} shrink-0 border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/10 hover:text-emerald-200`}
          >
            {isChangingStatus ? "Reopening…" : "Reopen"}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`${card} p-4`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs leading-relaxed text-slate-400">
          {hasInvestigation
            ? "Close this incident once you've acted on the remediation above."
            : "You can resolve at any point, but the diagnosis above is still empty."}
        </p>
        <div className="flex shrink-0 gap-2">
          {status === "open" && (
            <button
              type="button"
              onClick={() => onChangeStatus("investigating")}
              disabled={isChangingStatus}
              className={btnSecondary}
            >
              {isChangingStatus ? "Updating…" : "Mark Investigating"}
            </button>
          )}
          <button
            type="button"
            onClick={() => onChangeStatus("resolved")}
            disabled={isChangingStatus}
            className={isNextAction ? btnPrimary : btnSecondary}
          >
            {isChangingStatus ? "Updating…" : "Mark Resolved"}
          </button>
        </div>
      </div>
    </div>
  );
}
