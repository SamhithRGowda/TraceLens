// Purely presentational, plus local expand/collapse UI state. No
// fetching — reads the static manifest passed in as a prop. This is a
// curated demo/evaluation catalog for the current version of TraceLens,
// not automatic production incident detection — see the note in
// IncidentDetail where this is rendered.
//
// Nothing here hints at a scenario's expected category: the manifest type
// has no field for it (see types/traceLibrary.ts), and the grouping and
// labelling below are deliberately outcome-neutral.

import { useState } from "react";
import type { TraceLibraryScenario } from "../types/traceLibrary";
import { btnGhost, btnPrimary, btnSecondary, cardMuted } from "./ui";

interface TraceLibraryProps {
  scenarios: TraceLibraryScenario[];
  selectedId: string | null;
  onSelect: (scenario: TraceLibraryScenario) => void;
  // Once an incident has been created from a scenario, the full list stops
  // being the point of the page — it collapses to a one-line summary with
  // an explicit way back.
  collapsed?: boolean;
}

export default function TraceLibrary({
  scenarios,
  selectedId,
  onSelect,
  collapsed = false,
}: TraceLibraryProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);

  const selected = scenarios.find((s) => s.id === selectedId) ?? null;

  if (scenarios.length === 0) {
    return (
      <div className={`${cardMuted} px-4 py-3`}>
        <p className="text-sm text-slate-500">
          No scenarios seeded yet. Run{" "}
          <code className="text-slate-400">demo/seed_trace_library.py</code> to populate the library.
        </p>
      </div>
    );
  }

  // Collapsed: the selection is already made and acted on. Show what was
  // chosen, not the catalogue.
  if (collapsed && selected && !showAll) {
    return (
      <div className={`flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-800 bg-slate-900/40 px-4 py-3`}>
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-slate-200">{selected.title}</p>
          <p className="truncate text-xs text-slate-500">
            {selected.domain} · {selected.events.length} events
          </p>
        </div>
        <button type="button" onClick={() => setShowAll(true)} className={`${btnGhost} shrink-0`}>
          Change trace
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {collapsed && (
        <div className="flex justify-end">
          <button type="button" onClick={() => setShowAll(false)} className={btnGhost}>
            Done
          </button>
        </div>
      )}

      <ul className="max-h-[26rem] space-y-2 overflow-y-auto pr-1">
        {scenarios.map((scenario) => {
          const isSelected = scenario.id === selectedId;
          const isExpanded = scenario.id === expandedId;
          return (
            <li
              key={scenario.id}
              className={`rounded-lg border p-3 transition-colors ${
                isSelected
                  ? "border-slate-400 bg-slate-800/50 ring-1 ring-slate-400/40"
                  : "border-slate-800 bg-slate-900/30 hover:border-slate-700"
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="truncate text-sm font-medium text-slate-200">{scenario.title}</h3>
                    {isSelected && (
                      <span className="shrink-0 rounded-full border border-slate-400/40 bg-slate-100/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-200">
                        Selected
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-500">
                    {scenario.domain} · {scenario.events.length} events
                  </p>
                  <p className="mt-1 text-sm italic text-slate-400">"{scenario.user_request}"</p>
                </div>
                <div className="flex shrink-0 gap-2">
                  <button
                    type="button"
                    onClick={() => setExpandedId(isExpanded ? null : scenario.id)}
                    className={btnGhost}
                  >
                    {isExpanded ? "Hide events" : "Inspect events"}
                  </button>
                  {/* Labelled for what it does. It previously read
                      "Investigate This Trace", which investigated nothing —
                      it selects the trace and prefills the incident form;
                      Investigate is two stages later. */}
                  <button
                    type="button"
                    onClick={() => onSelect(scenario)}
                    disabled={isSelected}
                    className={`${isSelected ? btnSecondary : btnPrimary} px-3 py-1 text-xs`}
                  >
                    {isSelected ? "Selected" : "Use This Trace"}
                  </button>
                </div>
              </div>

              {isExpanded && (
                <ul className="mt-3 space-y-1.5 border-t border-slate-800 pt-3">
                  {scenario.events.map((event, index) => (
                    <li key={event.evidence_id} className="flex items-start gap-3 text-xs">
                      <span className="w-4 shrink-0 text-right font-mono text-slate-600">
                        {index + 1}
                      </span>
                      <span className="shrink-0 rounded border border-slate-700 bg-slate-800/60 px-2 py-0.5 text-[11px] font-medium text-slate-300">
                        {event.type === "llm_call" ? "LLM Call" : "Tool Call"}
                      </span>
                      <span className="leading-relaxed text-slate-400">{event.preview}</span>
                    </li>
                  ))}
                </ul>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
