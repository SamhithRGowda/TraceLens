// Minimal fetch wrapper. Deliberately generic — no incident/investigation-
// specific logic here. That belongs in api/incidents.ts (next step).
//
// Base URL is a plain constant, not an env var, on purpose: this is a
// single-developer MVP talking to a single local backend. An env-based
// config is a real need later (deploy target changes), not now.

const API_BASE_URL = "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

// Thin GET helper. Only GET exists right now because Milestone 1 is
// read-only — no POST/PATCH helpers until the ActionBar milestone.
export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);

  if (!response.ok) {
    // Try to surface the backend's own error detail (FastAPI returns
    // {"detail": "..."} on HTTPException) rather than a generic message.
    let detail = response.statusText;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") {
        detail = body.detail;
      }
    } catch {
      // Response body wasn't JSON — fall back to statusText above.
    }
    throw new ApiError(response.status, detail);
  }

  return response.json() as Promise<T>;
}

// POST helper for Sprint 16's write actions (create incident, link
// evidence, correlate, investigate). `body` is optional because
// correlate/investigate take no request body per the backend's OpenAPI
// schema — Content-Type is only sent when there's actually a body.
export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    // Same error-detail-extraction as apiGet, kept identical on purpose.
    let detail = response.statusText;
    try {
      const responseBody = await response.json();
      if (typeof responseBody?.detail === "string") {
        detail = responseBody.detail;
      }
    } catch {
      // Response body wasn't JSON — fall back to statusText above.
    }
    throw new ApiError(response.status, detail);
  }

  return response.json() as Promise<T>;
}
