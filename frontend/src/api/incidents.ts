// Endpoint-specific functions for Milestone 1. Only the two GETs the
// read-only IncidentDetail screen needs — no create/link/correlate/
// investigate/status functions yet (those belong to the ActionBar
// milestone, which is explicitly deferred).

import { apiGet } from "./client";
import type { IncidentWithEvidenceResponse, InvestigationResponse } from "../types/api";

// GET /incidents/{id} -> IncidentWithEvidenceResponse (confirmed via
// backend grep: response_model=IncidentWithEvidenceResponse). Evidence
// is bundled in this same response, so no separate evidence fetch.
export function getIncident(incidentId: string): Promise<IncidentWithEvidenceResponse> {
  return apiGet<IncidentWithEvidenceResponse>(`/incidents/${incidentId}`);
}

// GET /incidents/{id}/investigations -> InvestigationResponse[]. This is
// a list because investigations are immutable snapshots — re-running an
// investigation creates a new row rather than updating an old one. The
// component layer decides how to pick/display from this list (e.g. most
// recent by created_at); this function just returns what the backend gives.
export function getInvestigations(incidentId: string): Promise<InvestigationResponse[]> {
  return apiGet<InvestigationResponse[]>(`/incidents/${incidentId}/investigations`);
}
