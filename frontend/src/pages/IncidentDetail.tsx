// The container/page component. Owns state and fetch orchestration for
// both the read side (incident/investigation display) and, as of
// Sprint 16, the write side (create/link/correlate/investigate actions).
// IncidentHeader, EvidenceList, InvestigationPanel, and ActionBar stay
// presentational — they render what they're given and call the
// callbacks they're passed, nothing more.

import { useEffect, useState } from "react";
import {
  getIncident,
  getInvestigations,
  createIncident,
  linkEvidence,
  correlateIncident,
  investigateIncident,
  updateIncidentStatus,
} from "../api/incidents";
import { getRemediations, requestRemediation } from "../api/investigations";
import { ApiError } from "../api/client";
import type {
  IncidentStatus,
  IncidentWithEvidenceResponse,
  InvestigationResponse,
  RemediationResponse,
} from "../types/api";
import IncidentHeader from "../components/IncidentHeader";
import EvidenceList from "../components/EvidenceList";
import InvestigationPanel, { pickMostRecentInvestigation } from "../components/InvestigationPanel";
import RemediationPanel from "../components/RemediationPanel";
import ActionBar, { type ActionState } from "../components/ActionBar";

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

// Shared with all four action handlers below — same ApiError-vs-network
// distinction loadIncident already used, factored out so it isn't
// duplicated five times.
function extractErrorMessage(err: unknown): string {
  return err instanceof ApiError
    ? `${err.message} (status ${err.status})`
    : "Could not reach the backend. Is it running?";
}

// Sprint 17: remediation's own small state, separate from both LoadState
// (read side) and ActionBar's ActionState (create/link/correlate/
// investigate) — the "Get Remediation" trigger lives outside ActionBar,
// scoped to the displayed investigation rather than the whole incident,
// so it gets its own minimal state rather than being folded into either
// existing union.
type RemediationLoadState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "requesting" }
  | { status: "error"; message: string }
  | { status: "success"; remediations: RemediationResponse[] };

export default function IncidentDetail() {
  const [incidentIdInput, setIncidentIdInput] = useState(DEFAULT_INCIDENT_ID);
  const [state, setState] = useState<LoadState>({ status: "idle" });
  const [actionState, setActionState] = useState<ActionState>({ status: "idle" });
  const [remediationState, setRemediationState] = useState<RemediationLoadState>({ status: "idle" });
  const [statusActionState, setStatusActionState] = useState<
    { status: "idle" } | { status: "changing" } | { status: "error"; message: string }
  >({ status: "idle" });

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
      setState({ status: "error", message: extractErrorMessage(err) });
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

  // --- Sprint 17: remediation ---------------------------------------------

  async function loadRemediations(investigationId: string) {
    setRemediationState({ status: "loading" });
    try {
      const remediations = await getRemediations(investigationId);
      setRemediationState({ status: "success", remediations });
    } catch (err) {
      setRemediationState({ status: "error", message: extractErrorMessage(err) });
    }
  }

  // Whenever the incident finishes loading and there's a most-recent
  // investigation to show, also load whatever remediations already exist
  // for it — same mirroring relationship investigations already have to
  // the incident load. If there's no investigation yet, remediation has
  // nothing to target, so state stays idle.
  useEffect(() => {
    if (state.status !== "success") return;
    const investigation = pickMostRecentInvestigation(state.investigations);
    if (investigation) {
      loadRemediations(investigation.id);
    } else {
      setRemediationState({ status: "idle" });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state]);

  async function handleGetRemediation() {
    if (state.status !== "success") return;
    const investigation = pickMostRecentInvestigation(state.investigations);
    if (!investigation) return;

    setRemediationState({ status: "requesting" });
    try {
      await requestRemediation(investigation.id);
      await loadRemediations(investigation.id);
    } catch (err) {
      setRemediationState({ status: "error", message: extractErrorMessage(err) });
    }
  }

  // --- Sprint 16: write actions ------------------------------------------
  // Each follows the same shape: set an in-flight actionState, call the
  // corresponding api/incidents.ts function, then re-fetch via the
  // existing loadIncident() rather than merging the mutation's own
  // response into local state (per the Sprint 16 plan, section 6).

  async function handleCreateIncident(data: {
    projectName: string;
    title: string;
    description: string;
  }) {
    setActionState({ status: "creating" });
    try {
      const created = await createIncident({
        project_name: data.projectName,
        title: data.title,
        description: data.description || null,
      });
      setIncidentIdInput(created.id);
      await loadIncident(created.id);
      setActionState({ status: "idle" });
    } catch (err) {
      setActionState({ status: "error", message: extractErrorMessage(err) });
    }
  }

  async function handleLinkEvidence(evidenceIds: string[]) {
    setActionState({ status: "linking" });
    try {
      await linkEvidence(incidentIdInput, evidenceIds);
      await loadIncident(incidentIdInput);
      setActionState({ status: "idle" });
    } catch (err) {
      setActionState({ status: "error", message: extractErrorMessage(err) });
    }
  }

  async function handleCorrelate() {
    setActionState({ status: "correlating" });
    try {
      await correlateIncident(incidentIdInput);
      await loadIncident(incidentIdInput);
      setActionState({ status: "idle" });
    } catch (err) {
      setActionState({ status: "error", message: extractErrorMessage(err) });
    }
  }

  async function handleInvestigate() {
    setActionState({ status: "investigating" });
    try {
      await investigateIncident(incidentIdInput);
      await loadIncident(incidentIdInput);
      setActionState({ status: "idle" });
    } catch (err) {
      setActionState({ status: "error", message: extractErrorMessage(err) });
    }
  }

  // --- Sprint 18: status update --------------------------------------------
  // Same shape as every other action handler: set an in-flight state,
  // call the API function, then re-fetch via loadIncident() so the badge
  // and disabled button reflect the backend's actual, confirmed state —
  // never optimistically assumed from the request that was sent.

  async function handleChangeStatus(status: IncidentStatus) {
    setStatusActionState({ status: "changing" });
    try {
      await updateIncidentStatus(incidentIdInput, status);
      await loadIncident(incidentIdInput);
      setStatusActionState({ status: "idle" });
    } catch (err) {
      setStatusActionState({ status: "error", message: extractErrorMessage(err) });
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        <form onSubmit={handleSubmit} className="flex gap-2">
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

        <ActionBar
          hasLoadedIncident={state.status === "success"}
          onCreateIncident={handleCreateIncident}
          onLinkEvidence={handleLinkEvidence}
          onCorrelate={handleCorrelate}
          onInvestigate={handleInvestigate}
          actionState={actionState}
        />

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
            <IncidentHeader
              incident={state.incident}
              onChangeStatus={handleChangeStatus}
              isChangingStatus={statusActionState.status === "changing"}
            />

            {statusActionState.status === "error" && (
              <div className="rounded-md border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
                {statusActionState.message}
              </div>
            )}

            <EvidenceList evidence={state.incident.evidence} />
            <InvestigationPanel
              investigations={state.investigations}
              evidence={state.incident.evidence}
            />

            {pickMostRecentInvestigation(state.investigations) && (
              <div className="space-y-3">
                <button
                  type="button"
                  onClick={handleGetRemediation}
                  disabled={remediationState.status === "requesting"}
                  className="rounded-md bg-slate-100 px-4 py-2 text-sm font-medium text-slate-900 hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {remediationState.status === "requesting" ? "Requesting…" : "Get Remediation"}
                </button>

                {remediationState.status === "error" && (
                  <div className="rounded-md border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
                    {remediationState.message}
                  </div>
                )}

                <RemediationPanel
                  remediations={
                    remediationState.status === "success" ? remediationState.remediations : []
                  }
                />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
