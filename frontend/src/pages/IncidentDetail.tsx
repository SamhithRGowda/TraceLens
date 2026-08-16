// The one container/page component for Milestone 1. Owns state and
// fetch orchestration; everything else (IncidentHeader, EvidenceList,
// InvestigationPanel) stays presentational, per the plan. No routing —
// the incident ID is just a text input, submitted manually. No writes —
// only getIncident/getInvestigations from the existing API layer.

import { useEffect, useState } from "react";
import { getIncident, getInvestigations } from "../api/incidents";
import { ApiError } from "../api/client";
import type { IncidentWithEvidenceResponse, InvestigationResponse } from "../types/api";
import IncidentHeader from "../components/IncidentHeader";
import EvidenceList from "../components/EvidenceList";
import InvestigationPanel from "../components/InvestigationPanel";

const DEFAULT_INCIDENT_ID = "cffefe5b-7b72-49f9-a995-9e929d4d2486";

// Three explicit states rather than a couple of loose booleans — makes
// "what should render right now" unambiguous (no accidental moment
// where both an old result and a loading spinner could show at once).
type LoadState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | {
      status: "success";
      incident: IncidentWithEvidenceResponse;
      investigations: InvestigationResponse[];
    };

export default function IncidentDetail() {
  const [incidentIdInput, setIncidentIdInput] = useState(DEFAULT_INCIDENT_ID);
  const [state, setState] = useState<LoadState>({ status: "idle" });

  async function loadIncident(id: string) {
    const trimmedId = id.trim();
    if (!trimmedId) {
      setState({ status: "error", message: "Enter an incident ID." });
      return;
    }

    setState({ status: "loading" });

    try {
      // Two independent GETs. Run them together rather than sequentially —
      // neither depends on the other's result, so there's no reason to
      // wait on one before starting the next.
      const [incident, investigations] = await Promise.all([
        getIncident(trimmedId),
        getInvestigations(trimmedId),
      ]);
      setState({ status: "success", incident, investigations });
    } catch (err) {
      const message =
        err instanceof ApiError
          ? `${err.message} (status ${err.status})`
          : "Could not reach the backend. Is it running?";
      setState({ status: "error", message });
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    loadIncident(incidentIdInput);
  }

  // Load the verified demo incident on first mount, so opening the app
  // shows the real workflow immediately rather than an empty idle state.
  // Still fully re-triggerable via the input above for any other ID.
  useEffect(() => {
    loadIncident(DEFAULT_INCIDENT_ID);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="max-w-3xl mx-auto px-6 py-10">
        <form onSubmit={handleSubmit} className="flex gap-2 mb-8">
          <input
            type="text"
            value={incidentIdInput}
            onChange={(e) => setIncidentIdInput(e.target.value)}
            placeholder="Incident ID"
            className="flex-1 rounded-md border border-slate-800 bg-slate-900 px-3 py-2 text-sm font-mono text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-slate-600"
          />
          <button
            type="submit"
            disabled={state.status === "loading"}
            className="rounded-md bg-slate-100 px-4 py-2 text-sm font-medium text-slate-900 hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {state.status === "loading" ? "Loading…" : "Load Incident"}
          </button>
        </form>

        {state.status === "idle" && (
          <p className="text-sm text-slate-500">Enter an incident ID above to load it.</p>
        )}

        {state.status === "loading" && (
          <p className="text-sm text-slate-500">Loading incident…</p>
        )}

        {state.status === "error" && (
          <div className="rounded-md border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {state.message}
          </div>
        )}

        {state.status === "success" && (
          <div className="space-y-8">
            <IncidentHeader incident={state.incident} />
            <EvidenceList evidence={state.incident.evidence} />
            <InvestigationPanel
              investigations={state.investigations}
              evidence={state.incident.evidence}
            />
          </div>
        )}
      </div>
    </div>
  );
}
