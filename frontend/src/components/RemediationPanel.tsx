// Purely presentational — renders remediations it's given. No fetching,
// no mutation. Mirrors InvestigationPanel's structure: remediations are
// immutable snapshots (Day 11), so this picks the most recent by
// created_at, same rule used for investigations.
//
// UI-polish pass: the empty state used to read "No remediation yet." in
// the same weight as real content, which scanned as something having gone
// wrong. It's now an explicitly pending state, and it distinguishes
// "nothing requested yet" from "request in flight" — previously both
// rendered identically, because IncidentDetail passes `[]` for every
// non-success state.

import type { RemediationResponse } from "../types/api";
import { card, cardMuted } from "./ui";

interface RemediationPanelProps {
  remediations: RemediationResponse[];
  // "loading" — checking for an existing remediation after an incident load.
  // "generating" — an LLM remediation request is in flight, which takes
  // seconds, so it gets its own wording rather than a generic spinner.
  pending: "none" | "loading" | "generating";
  // False before any investigation exists, when remediation has nothing to
  // target. The stage still renders, so the pipeline doesn't appear to end
  // at Investigation.
  isAvailable: boolean;
}

function pickMostRecentRemediation(remediations: RemediationResponse[]): RemediationResponse | null {
  if (remediations.length === 0) return null;
  return [...remediations].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  )[0];
}

export default function RemediationPanel({
  remediations,
  pending,
  isAvailable,
}: RemediationPanelProps) {
  const remediation = pickMostRecentRemediation(remediations);

  if (pending !== "none" && !remediation) {
    return (
      <div className={`${cardMuted} px-4 py-3`}>
        <p className="text-sm text-slate-400">
          {pending === "generating"
            ? "Generating a recommended fix from the diagnosis…"
            : "Checking for an existing remediation…"}
        </p>
      </div>
    );
  }

  if (!remediation) {
    return (
      <div className={`${cardMuted} px-4 py-3`}>
        <p className="text-sm text-slate-500">
          {isAvailable
            ? "Ready when you are — generate a recommended fix from the diagnosis above."
            : "Unlocks once an investigation has produced a diagnosis."}
        </p>
      </div>
    );
  }

  return (
    <div className={`${card} divide-y divide-slate-800`}>
      <div className="p-4">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
          Recommended Fix
        </p>
        <p className="mt-1.5 text-sm leading-relaxed text-slate-100">{remediation.recommended_fix}</p>
      </div>

      <div className="p-4">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Rationale</p>
        <p className="mt-1.5 text-sm leading-relaxed text-slate-300">{remediation.rationale}</p>
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-2.5 text-[11px] text-slate-500">
        <span>
          Model <span className="text-slate-400">{remediation.model}</span>
        </span>
        <span>{new Date(remediation.created_at).toLocaleString()}</span>
        {/* The backend is explicit that this output is advisory; the UI was
            not. Copy only — nothing about how remediation is generated. */}
        <span className="text-slate-600">Advisory — review before applying</span>
        {pending === "generating" && <span className="text-slate-400">Regenerating…</span>}
      </div>
    </div>
  );
}
