// Investigation-keyed API operations, kept separate from api/incidents.ts
// on purpose (Sprint 17 design decision): remediation is scoped to an
// Investigation ID, not an Incident ID — a different resource than
// everything in incidents.ts operates on.

import { apiGet, apiPost } from "./client";
import type { RemediationResponse } from "../types/api";

// GET /investigations/{id}/remediations -> RemediationResponse[].
// Remediations are immutable snapshots (Day 11), same pattern as
// Investigation — re-running creates a new row rather than updating one,
// hence a list. Component layer picks which one to show.
export function getRemediations(investigationId: string): Promise<RemediationResponse[]> {
  return apiGet<RemediationResponse[]>(`/investigations/${investigationId}/remediations`);
}

// POST /investigations/{id}/remediate -> RemediationResponse. No request
// body (verified against the real backend's OpenAPI spec before writing
// this — not inferred).
export function requestRemediation(investigationId: string): Promise<RemediationResponse> {
  return apiPost<RemediationResponse>(`/investigations/${investigationId}/remediate`);
}
