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
//
// UI-polish pass: hierarchy only. The diagnosis now reads
// category -> confidence -> explanation -> citations, top to bottom, with
// the category as the headline rather than one pill among equals. Cited
// evidence gains the same manifest previews EvidenceList uses. Every
// citation still renders, including the unmatched-id fallback below —
// nothing is filtered, reordered away, or summarised.

import type { EvidenceResponse, InvestigationResponse } from "../types/api";
import { badgeNeutral, card, cardMuted, idText } from "./ui";

interface InvestigationPanelProps {
  investigations: InvestigationResponse[];
  evidence: EvidenceResponse[];
  // evidence id -> human-readable preview. Missing keys are expected.
  previews: Record<string, string>;
}

const TYPE_LABELS: Record<EvidenceResponse["evidence_type"], string> = {
  llm_call: "LLM Call",
  tool_call: "Tool Call",
};

// Exported so IncidentDetail (Sprint 17) can determine which investigation
// the "Get Remediation" action should target — same selection rule used
// here to decide what to display, reused rather than duplicated.
export function pickMostRecentInvestigation(
  investigations: InvestigationResponse[],
): InvestigationResponse | null {
  if (investigations.length === 0) return null;
  return [...investigations].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  )[0];
}

export default function InvestigationPanel({
  investigations,
  evidence,
  previews,
}: InvestigationPanelProps) {
  const investigation = pickMostRecentInvestigation(investigations);

  if (!investigation) {
    return (
      <div className={`${cardMuted} px-4 py-3`}>
        <p className="text-sm text-slate-500">
          No diagnosis yet. Run an investigation to classify this incident against the taxonomy and
          get a cited root-cause explanation.
        </p>
      </div>
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
  const earlierCount = investigations.length - 1;

  return (
    <div className={`${card} divide-y divide-slate-800`}>
      {/* Headline: what this incident is, and how sure the model is. */}
      <div className="flex items-start justify-between gap-6 p-4">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
            Category
          </p>
          <p className="mt-1 text-lg font-semibold capitalize leading-tight text-violet-300">
            {investigation.category.replace(/_/g, " ")}
          </p>
        </div>
        <div className="w-32 shrink-0">
          <div className="flex items-baseline justify-end gap-1">
            <span className="text-lg font-semibold text-slate-100">{confidencePct}%</span>
            <span className="text-[11px] text-slate-500">confidence</span>
          </div>
          {/* A bar makes "83%" comparable at a glance across runs, which a
              bare number doesn't. Width is data, not decoration. */}
          <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-slate-800">
            <div className="h-full rounded-full bg-violet-400/70" style={{ width: `${confidencePct}%` }} />
          </div>
        </div>
      </div>

      <div className="p-4">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Diagnosis</p>
        <p className="mt-1.5 text-sm leading-relaxed text-slate-200">{investigation.explanation}</p>
      </div>

      <div className="p-4">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
          Cited Evidence <span className="text-slate-600">({citedItems.length})</span>
        </p>
        <ul className="mt-2 space-y-1.5">
          {citedItems.map(({ id, match }) => {
            const preview = previews[id];
            return (
              <li
                key={id}
                className="flex items-start gap-3 rounded border border-slate-800 px-3 py-2"
              >
                {match ? (
                  <span className={`${badgeNeutral} mt-0.5`}>{TYPE_LABELS[match.evidence_type]}</span>
                ) : (
                  <span className="mt-0.5 shrink-0 rounded border border-red-500/30 bg-red-500/10 px-2 py-0.5 text-[11px] font-medium text-red-400">
                    not found
                  </span>
                )}
                <div className="min-w-0 flex-1">
                  {preview ? (
                    <>
                      <p className="text-xs leading-relaxed text-slate-300">{preview}</p>
                      <p className={`mt-0.5 truncate ${idText}`}>{id}</p>
                    </>
                  ) : (
                    <p className={`truncate ${idText} text-xs`}>{id}</p>
                  )}
                </div>
                {match && (
                  <span className="shrink-0 pt-0.5 text-xs text-slate-500">
                    {new Date(match.timestamp).toLocaleTimeString()}
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-2.5 text-[11px] text-slate-500">
        <span>
          Model <span className="text-slate-400">{investigation.model}</span>
        </span>
        <span>Taxonomy v{investigation.taxonomy_version}</span>
        <span>{new Date(investigation.created_at).toLocaleString()}</span>
        {/* Re-running Investigate used to silently replace what was on
            screen even though every prior snapshot is still held in state.
            At least say how many there are. */}
        {earlierCount > 0 && (
          <span className="text-slate-600">
            {earlierCount} earlier {earlierCount === 1 ? "run" : "runs"} retained
          </span>
        )}
      </div>
    </div>
  );
}
