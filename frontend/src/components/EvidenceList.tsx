// Purely presentational — renders whatever evidence array it's given.
// No fetching. Deliberately does NOT render `payload` or any content
// field, because EvidenceResponse doesn't return one (the backend's
// evidence content endpoint doesn't exist yet — see project handoff,
// known limitation). Showing type/timestamp/id is honest about what
// data is actually available right now, rather than faking content.

import type { EvidenceResponse } from "../types/api";

interface EvidenceListProps {
  evidence: EvidenceResponse[];
}

// evidence_type -> label. Plain lookup, same reasoning as
// IncidentHeader's STATUS_STYLES: EvidenceType is a closed, stable set.
const TYPE_LABELS: Record<EvidenceResponse["evidence_type"], string> = {
  llm_call: "LLM Call",
  tool_call: "Tool Call",
};

export default function EvidenceList({ evidence }: EvidenceListProps) {
  if (evidence.length === 0) {
    return (
      <section>
        <h2 className="text-sm font-medium text-slate-300 mb-2">Evidence</h2>
        <p className="text-sm text-slate-500">No evidence linked to this incident yet.</p>
      </section>
    );
  }

  return (
    <section>
      <h2 className="text-sm font-medium text-slate-300 mb-2">
        Evidence <span className="text-slate-500">({evidence.length})</span>
      </h2>

      <ul className="divide-y divide-slate-800 border border-slate-800 rounded-lg overflow-hidden">
        {evidence.map((item) => (
          <li key={item.id} className="flex items-center justify-between gap-4 px-3 py-2 bg-slate-900/40">
            <div className="flex items-center gap-3 min-w-0">
              <span className="shrink-0 rounded border border-slate-700 px-2 py-0.5 text-[11px] font-medium text-slate-300">
                {TYPE_LABELS[item.evidence_type]}
              </span>
              <span className="truncate text-xs text-slate-500 font-mono">{item.id}</span>
            </div>
            <span className="shrink-0 text-xs text-slate-500">
              {new Date(item.timestamp).toLocaleString()}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
