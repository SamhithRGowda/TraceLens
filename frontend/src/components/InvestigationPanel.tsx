// Purely presentational — renders investigations + evidence it's given.
// No fetching, no mutation.
//
// Investigations are immutable snapshots (Day 10 decision): re-running
// creates a new row rather than updating an old one. GET /investigations
// therefore returns a list. This component's one piece of "logic" is
// picking which one to show — most recent by created_at — everything
// else is pure rendering. That selection lives here, not in the API
// layer, per the api/incidents.ts comment: the API layer returns what
// the backend gives; components decide how to use it.

import type { EvidenceResponse, InvestigationResponse } from "../types/api";

interface InvestigationPanelProps {
  investigations: InvestigationResponse[];
  evidence: EvidenceResponse[];
}

const TYPE_LABELS: Record<EvidenceResponse["evidence_type"], string> = {
  llm_call: "LLM Call",
  tool_call: "Tool Call",
};

function mostRecent(investigations: InvestigationResponse[]): InvestigationResponse | null {
  if (investigations.length === 0) return null;
  return [...investigations].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  )[0];
}

export default function InvestigationPanel({ investigations, evidence }: InvestigationPanelProps) {
  const investigation = mostRecent(investigations);

  if (!investigation) {
    return (
      <section>
        <h2 className="text-sm font-medium text-slate-300 mb-2">Investigation</h2>
        <p className="text-sm text-slate-500">
          No investigation yet. Run one from this incident to see a root-cause conclusion here.
        </p>
      </section>
    );
  }

  // Cross-reference: for each cited evidence id, find the matching
  // evidence item so we can show its type/timestamp, not just a bare
  // UUID. If a cited id isn't in the evidence list (shouldn't happen,
  // but the two come from separate endpoints/calls), say so plainly
  // rather than silently dropping it — a citation the UI can't verify
  // is worth surfacing, given the whole product thesis is "evidence
  // backs the conclusion."
  const citedItems = investigation.cited_evidence_ids.map((id) => ({
    id,
    match: evidence.find((e) => e.id === id) ?? null,
  }));

  const confidencePct = Math.round(investigation.confidence * 100);

  return (
    <section>
      <h2 className="text-sm font-medium text-slate-300 mb-2">Investigation</h2>

      <div className="border border-slate-800 rounded-lg bg-slate-900/40 p-4 space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <span className="inline-block rounded-full border border-violet-500/30 bg-violet-500/15 px-3 py-1 text-xs font-medium capitalize text-violet-300">
              {investigation.category}
            </span>
          </div>
          <div className="text-right shrink-0">
            <div className="text-lg font-semibold text-slate-100">{confidencePct}%</div>
            <div className="text-xs text-slate-500">confidence</div>
          </div>
        </div>

        <p className="text-sm text-slate-300 leading-relaxed">{investigation.explanation}</p>

        <div>
          <h3 className="text-xs font-medium text-slate-400 mb-1.5">
            Cited Evidence ({citedItems.length})
          </h3>
          <ul className="space-y-1.5">
            {citedItems.map(({ id, match }) => (
              <li
                key={id}
                className="flex items-center justify-between gap-4 rounded border border-slate-800 px-3 py-1.5"
              >
                <div className="flex items-center gap-3 min-w-0">
                  {match ? (
                    <span className="shrink-0 rounded border border-slate-700 px-2 py-0.5 text-[11px] font-medium text-slate-300">
                      {TYPE_LABELS[match.evidence_type]}
                    </span>
                  ) : (
                    <span className="shrink-0 rounded border border-red-500/30 bg-red-500/10 px-2 py-0.5 text-[11px] font-medium text-red-400">
                      not found
                    </span>
                  )}
                  <span className="truncate text-xs text-slate-500 font-mono">{id}</span>
                </div>
                {match && (
                  <span className="shrink-0 text-xs text-slate-500">
                    {new Date(match.timestamp).toLocaleString()}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>

        <div className="flex gap-4 text-xs text-slate-500 pt-1 border-t border-slate-800">
          <span>Model: <span className="text-slate-400">{investigation.model}</span></span>
          <span>Taxonomy v{investigation.taxonomy_version}</span>
          <span>{new Date(investigation.created_at).toLocaleString()}</span>
        </div>
      </div>
    </section>
  );
}
