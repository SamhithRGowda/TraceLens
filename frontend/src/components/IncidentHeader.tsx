// Purely presentational. Identity of the incident being viewed: title,
// description, status, and timestamps.
//
// UI-polish pass: the three status buttons moved out to ResolutionPanel
// (stage 6) so status *display* and status *control* stop sitting side by
// side encoding the same value. Also dropped the `Category` field — it read
// `incident.category ?? "—"`, and that column is never populated, so it
// rendered a permanently blank row next to the title. The real category
// comes from the most recent Investigation and is shown by
// InvestigationPanel, which is where it's actually derived.

import type { IncidentWithEvidenceResponse } from "../types/api";
import { idText } from "./ui";

interface IncidentHeaderProps {
  incident: IncidentWithEvidenceResponse;
  // A mutation's re-fetch is in flight. Shown as a quiet inline chip rather
  // than unmounting the incident body, which is what used to happen on
  // every single action (see IncidentDetail.loadIncident).
  isRefreshing: boolean;
}

// Status -> badge color. A plain lookup object, not a switch statement,
// because this is a closed, stable set (IncidentStatus has exactly three
// values) and a lookup keeps the JSX below free of conditional branching.
const STATUS_STYLES: Record<IncidentWithEvidenceResponse["status"], string> = {
  open: "bg-red-500/15 text-red-300 border-red-500/40",
  investigating: "bg-amber-500/15 text-amber-300 border-amber-500/40",
  resolved: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
};

// A distinct glyph per status, so the three states are told apart by shape
// as well as by colour.
const STATUS_GLYPHS: Record<IncidentWithEvidenceResponse["status"], string> = {
  open: "●",
  investigating: "◐",
  resolved: "✓",
};

export default function IncidentHeader({ incident, isRefreshing }: IncidentHeaderProps) {
  return (
    <header className="border-b border-slate-800 pb-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-xl font-semibold leading-tight text-slate-100">{incident.title}</h1>
          {incident.description && (
            <p className="mt-1.5 text-sm leading-relaxed text-slate-400">{incident.description}</p>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {isRefreshing && <span className="text-xs text-slate-500">Refreshing…</span>}
          <span
            className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold capitalize ${STATUS_STYLES[incident.status]}`}
          >
            <span aria-hidden="true">{STATUS_GLYPHS[incident.status]}</span>
            {incident.status}
          </span>
        </div>
      </div>

      <dl className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-slate-500">
        <div>
          <dt className="inline">Created </dt>
          <dd className="inline text-slate-400">
            {new Date(incident.created_at).toLocaleString()}
          </dd>
        </div>
        {/* resolved_at has always been on the response type but was never
            rendered, so the terminal state of the workflow had no visible
            completion marker. */}
        {incident.resolved_at && (
          <div>
            <dt className="inline">Resolved </dt>
            <dd className="inline text-emerald-400/90">
              {new Date(incident.resolved_at).toLocaleString()}
            </dd>
          </div>
        )}
        <div>
          <dt className="sr-only">Incident ID</dt>
          <dd className={idText}>{incident.id}</dd>
        </div>
      </dl>
    </header>
  );
}
