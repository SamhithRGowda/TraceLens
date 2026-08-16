// Purely presentational — takes an incident, renders it. No fetching,
// no mutation, no routing. Wired up with real data in IncidentDetail
// (a later step); for now it just needs to render whatever it's given.

import type { IncidentWithEvidenceResponse } from "../types/api";

interface IncidentHeaderProps {
  incident: IncidentWithEvidenceResponse;
}

// Status -> badge color. A plain lookup object, not a switch statement,
// because this is a closed, stable set (IncidentStatus has exactly three
// values) and a lookup keeps the JSX below free of conditional branching.
const STATUS_STYLES: Record<IncidentWithEvidenceResponse["status"], string> = {
  open: "bg-red-500/15 text-red-400 border-red-500/30",
  investigating: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  resolved: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
};

export default function IncidentHeader({ incident }: IncidentHeaderProps) {
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
    </header>
  );
}
