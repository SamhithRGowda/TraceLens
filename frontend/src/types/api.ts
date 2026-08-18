// Hand-written types mirroring the backend's OpenAPI schemas exactly
// (verified against /openapi.json — see project handoff, Day 13).
// Only the shapes Milestone 1 actually consumes are included here.
// No speculative fields, no fields from endpoints we haven't wired up yet.

export type IncidentStatus = "open" | "investigating" | "resolved";

export type EvidenceType = "llm_call" | "tool_call";

// What GET /incidents/{id}/investigations returns (list), and what
// each item looks like. Investigations are immutable snapshots, so
// this type has no "updated_at" — only "created_at".
export interface InvestigationResponse {
  id: string;
  incident_id: string;
  category: string;
  confidence: number;
  explanation: string;
  cited_evidence_ids: string[];
  taxonomy_version: number;
  model: string;
  created_at: string; // ISO 8601 date-time
}

// What each item in IncidentWithEvidenceResponse.evidence looks like.
// Note: this does NOT include `payload` — the backend's EvidenceResponse
// schema doesn't return it. EvidenceList can show type/timestamp/id,
// not the actual LLM/tool content, until that's added server-side.
export interface EvidenceResponse {
  id: string;
  trace_id: string;
  evidence_type: EvidenceType;
  timestamp: string; // ISO 8601 date-time
  created_at: string; // ISO 8601 date-time
}

// What GET /incidents/{id} actually returns (confirmed via backend
// grep: response_model=IncidentWithEvidenceResponse), not the plainer
// IncidentResponse. Evidence comes bundled in the same call.
export interface IncidentWithEvidenceResponse {
  id: string;
  project_id: string;
  title: string;
  description: string | null;
  status: IncidentStatus;
  category: string | null;
  created_at: string; // ISO 8601 date-time
  updated_at: string; // ISO 8601 date-time
  resolved_at: string | null;
  evidence: EvidenceResponse[];
}

// --- Sprint 16 additions: write-action request/response shapes -----------

// Request body for POST /incidents.
export interface IncidentCreate {
  project_name: string;
  title: string;
  description?: string | null;
}

// Request body for POST /incidents/{id}/evidence.
export interface EvidenceLinkRequest {
  evidence_ids: string[];
}

// What POST /incidents actually returns — the plain shape, with no
// `evidence` array. Distinct from IncidentWithEvidenceResponse, which
// only GET /incidents/{id} returns. Mixing these up would silently
// break anything that expects `.evidence` on a freshly created incident.
export interface IncidentResponse {
  id: string;
  project_id: string;
  title: string;
  description: string | null;
  status: IncidentStatus;
  category: string | null;
  created_at: string; // ISO 8601 date-time
  updated_at: string; // ISO 8601 date-time
  resolved_at: string | null;
}
