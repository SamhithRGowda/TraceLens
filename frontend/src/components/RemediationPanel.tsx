// Purely presentational — renders remediations it's given. No fetching,
// no mutation. Mirrors InvestigationPanel's structure: remediations are
// immutable snapshots (Day 11), so this picks the most recent by
// created_at, same rule used for investigations.

import type { RemediationResponse } from "../types/api";

interface RemediationPanelProps {
  remediations: RemediationResponse[];
}

function pickMostRecentRemediation(remediations: RemediationResponse[]): RemediationResponse | null {
  if (remediations.length === 0) return null;
  return [...remediations].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  )[0];
}

export default function RemediationPanel({ remediations }: RemediationPanelProps) {
  const remediation = pickMostRecentRemediation(remediations);

  if (!remediation) {
    return (
      <section>
        <h2 className="text-sm font-medium text-slate-300 mb-2">Remediation</h2>
        <p className="text-sm text-slate-500">
          No remediation yet. Use "Get Remediation" above to request one for the current investigation.
        </p>
      </section>
    );
  }

  return (
    <section>
      <h2 className="text-sm font-medium text-slate-300 mb-2">Remediation</h2>

      <div className="border border-slate-800 rounded-lg bg-slate-900/40 p-4 space-y-4">
        <div>
          <h3 className="text-xs font-medium text-slate-400 mb-1">Recommended Fix</h3>
          <p className="text-sm text-slate-200 leading-relaxed">{remediation.recommended_fix}</p>
        </div>

        <div>
          <h3 className="text-xs font-medium text-slate-400 mb-1">Rationale</h3>
          <p className="text-sm text-slate-300 leading-relaxed">{remediation.rationale}</p>
        </div>

        <div className="flex gap-4 text-xs text-slate-500 pt-1 border-t border-slate-800">
          <span>Model: <span className="text-slate-400">{remediation.model}</span></span>
          <span>{new Date(remediation.created_at).toLocaleString()}</span>
        </div>
      </div>
    </section>
  );
}
