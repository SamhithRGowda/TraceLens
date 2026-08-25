// Purely presentational — renders whatever evidence array it's given.
// No fetching. Deliberately does NOT render `payload` or any content
// field, because EvidenceResponse doesn't return one (the backend's
// evidence content endpoint doesn't exist yet — see project handoff,
// known limitation). Showing type/timestamp/id is honest about what
// data is actually available right now, rather than faking content.
//
// UI-polish pass: the one readable thing the frontend *does* already have
// is the Trace Library manifest's per-event `preview` string, which
// TraceLibrary has always rendered. It's now passed in here too, so
// evidence on an incident reads the same as it did in the library instead
// of being a column of bare UUIDs. Evidence that didn't come from the
// library has no preview and falls back to the id, as before.
//
// The section heading lives in StageSection now, not here.

import type { EvidenceResponse } from "../types/api";
import { badgeNeutral, cardMuted, idText } from "./ui";

interface EvidenceListProps {
  evidence: EvidenceResponse[];
  // evidence id -> human-readable preview. Missing keys are expected.
  previews: Record<string, string>;
}

// evidence_type -> label. Plain lookup, same reasoning as
// IncidentHeader's STATUS_STYLES: EvidenceType is a closed, stable set.
const TYPE_LABELS: Record<EvidenceResponse["evidence_type"], string> = {
  llm_call: "LLM Call",
  tool_call: "Tool Call",
};

export default function EvidenceList({ evidence, previews }: EvidenceListProps) {
  if (evidence.length === 0) {
    return (
      <div className={`${cardMuted} px-4 py-3`}>
        <p className="text-sm text-slate-500">
          No evidence attached yet. Creating an incident from a Trace Library scenario attaches its
          events automatically.
        </p>
      </div>
    );
  }

  // A trace is a sequence, so render it as one. The API doesn't promise an
  // order, and reading the steps out of order makes a contradiction between
  // two of them much harder to spot.
  const ordered = [...evidence].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
  );

  return (
    <ul className="divide-y divide-slate-800 overflow-hidden rounded-lg border border-slate-800">
      {ordered.map((item, index) => {
        const preview = previews[item.id];
        return (
          <li key={item.id} className="flex items-start gap-3 bg-slate-900/40 px-3 py-2.5">
            <span className="w-4 shrink-0 pt-0.5 text-right font-mono text-xs text-slate-600">
              {index + 1}
            </span>
            <span className={`${badgeNeutral} mt-0.5`}>{TYPE_LABELS[item.evidence_type]}</span>
            <div className="min-w-0 flex-1">
              {preview ? (
                <>
                  <p className="text-xs leading-relaxed text-slate-300">{preview}</p>
                  <p className={`mt-0.5 truncate ${idText}`}>{item.id}</p>
                </>
              ) : (
                <p className={`truncate ${idText} text-xs`}>{item.id}</p>
              )}
            </div>
            <span className="shrink-0 pt-0.5 text-xs text-slate-500">
              {new Date(item.timestamp).toLocaleTimeString()}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
