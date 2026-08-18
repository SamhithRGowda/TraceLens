// Presentational, with one addition as of Sprint 18: the three status
// buttons. Still no fetching — onChangeStatus is a callback owned by
// IncidentDetail, same pattern ActionBar/RemediationPanel's trigger use.

import type { IncidentStatus, IncidentWithEvidenceResponse } from "../types/api";

interface IncidentHeaderProps {
  incident: IncidentWithEvidenceResponse;
  onChangeStatus: (status: IncidentStatus) => void;
  isChangingStatus: boolean;
}

// Status -> badge color. A plain lookup object, not a switch statement,
// because this is a closed, stable set (IncidentStatus has exactly three
// values) and a lookup keeps the JSX below free of conditional branching.
const STATUS_STYLES: Record<IncidentWithEvidenceResponse["status"], string> = {
  open: "bg-red-500/15 text-red-400 border-red-500/30",
  investigating: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  resolved: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
};

// Fixed, ordered set matching the backend's closed IncidentStatus enum —
// same three buttons every time, not derived from anything dynamic.
const STATUS_OPTIONS: IncidentStatus[] = ["open", "investigating", "resolved"];

export default function IncidentHeader({
  incident,
  onChangeStatus,
  isChangingStatus,
}: IncidentHeaderProps) {
  return (
    <header className="border-b border-slate-800 pb-4 mb-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">{incident.title}</h1>
          {incident.description && (
            <p className="mt-1 text-sm text-slate-400">{incident.description}</p>
          )}
        </div>

        <span
          className={`shrink-0 rounded-full border px-3 py-1 text-xs font-medium capitalize ${STATUS_STYLES[incident.status]}`}
        >
          {incident.status}
        </span>
      </div>

      <dl className="mt-3 flex gap-6 text-xs text-slate-500">
        <div>
          <dt className="inline">Category: </dt>
          <dd className="inline text-slate-300">{incident.category ?? "—"}</dd>
        </div>
        <div>
          <dt className="inline">Created: </dt>
          <dd className="inline text-slate-300">
            {new Date(incident.created_at).toLocaleString()}
          </dd>
        </div>
      </dl>

      <div className="mt-3 flex gap-2">
        {STATUS_OPTIONS.map((status) => {
          // Disabling the current status's own button is what keeps a
          // natural click from ever triggering the backend's no-op
          // rejection (Day 12: same-status transitions are rejected).
          const isCurrent = status === incident.status;
          return (
            <button
              key={status}
              type="button"
              onClick={() => onChangeStatus(status)}
              disabled={isCurrent || isChangingStatus}
              className="rounded-md border border-slate-700 px-3 py-1 text-xs font-medium capitalize text-slate-300 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {status}
            </button>
          );
        })}
      </div>
    </header>
  );
}
