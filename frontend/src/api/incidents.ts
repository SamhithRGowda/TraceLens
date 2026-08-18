// Endpoint-specific functions. Two GETs (read-only IncidentDetail
// screen) plus, as of Sprint 16, four POSTs for the incident action
// workflow (create / link evidence / correlate / investigate). No
// status-transition or remediation functions — out of Sprint 16 scope.

import { apiGet, apiPost } from "./client";
import type {
  EvidenceLinkRequest,
  IncidentCreate,
  IncidentResponse,
  IncidentWithEvidenceResponse,
  InvestigationResponse,
} from "../types/api";

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

// --- Sprint 16 additions: write actions -----------------------------------
// Each of these returns the backend's real response type, but callers in
// this project deliberately don't use the returned value to update local
// state — IncidentDetail re-fetches via getIncident/getInvestigations
// after every successful mutation instead (see Sprint 16 plan, section 6).
// Typed accurately anyway, since under-typing a real response would be
// its own kind of inaccuracy.

// POST /incidents -> IncidentResponse (no evidence array — see
// IncidentResponse's comment in types/api.ts for why this isn't
// IncidentWithEvidenceResponse).
export function createIncident(data: IncidentCreate): Promise<IncidentResponse> {
  return apiPost<IncidentResponse>("/incidents", data);
}

// POST /incidents/{id}/evidence -> IncidentWithEvidenceResponse.
export function linkEvidence(
  incidentId: string,
  evidenceIds: string[],
): Promise<IncidentWithEvidenceResponse> {
  const body: EvidenceLinkRequest = { evidence_ids: evidenceIds };
  return apiPost<IncidentWithEvidenceResponse>(`/incidents/${incidentId}/evidence`, body);
}

// POST /incidents/{id}/correlate -> IncidentWithEvidenceResponse. No
// request body.
export function correlateIncident(incidentId: string): Promise<IncidentWithEvidenceResponse> {
  return apiPost<IncidentWithEvidenceResponse>(`/incidents/${incidentId}/correlate`);
}

// POST /incidents/{id}/investigate -> InvestigationResponse. No request
// body.
export function investigateIncident(incidentId: string): Promise<InvestigationResponse> {
  return apiPost<InvestigationResponse>(`/incidents/${incidentId}/investigate`);
}
