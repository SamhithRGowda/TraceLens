// Sprint 16: the write side of the incident workflow. Owns its own form
// input state (title/description/project name, evidence-ID text) but
// not incident data itself, and never calls api/incidents.ts directly —
// IncidentDetail owns all fetching/refetching, per the Sprint 16 plan.
// This component only invokes the callbacks it's given.

import { useState } from "react";

export type ActionState =
  | { status: "idle" }
  | { status: "creating" | "linking" | "correlating" | "investigating" }
  | { status: "error"; message: string };

interface ActionBarProps {
  // Whether an incident is currently loaded. Link/Correlate/Investigate
  // need an existing incident; Create Incident does not.
  hasLoadedIncident: boolean;

  onCreateIncident: (data: {
    projectName: string;
    title: string;
    description: string;
  }) => Promise<void>;
  onLinkEvidence: (evidenceIds: string[]) => Promise<void>;
  onCorrelate: () => Promise<void>;
  onInvestigate: () => Promise<void>;

  actionState: ActionState;
}

// Small shared styling helpers, matching the existing input/button
// classes already used in IncidentDetail's ID-input form — kept local
// rather than extracted, since this is the only other place they're used.
const inputClasses =
  "w-full rounded-md border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-slate-600";
const buttonClasses =
  "rounded-md bg-slate-100 px-4 py-2 text-sm font-medium text-slate-900 hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed";

export default function ActionBar({
  hasLoadedIncident,
  onCreateIncident,
  onLinkEvidence,
  onCorrelate,
  onInvestigate,
  actionState,
}: ActionBarProps) {
  const [projectName, setProjectName] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [evidenceIdsText, setEvidenceIdsText] = useState("");

  const isBusy = actionState.status !== "idle" && actionState.status !== "error";

  function handleCreateSubmit(e: React.FormEvent) {
    e.preventDefault();
    onCreateIncident({ projectName, title, description });
  }

  function handleLinkSubmit(e: React.FormEvent) {
    e.preventDefault();
    // Split on commas and/or whitespace/newlines, drop empty entries —
    // accommodates pasting IDs from the documented psql query output in
    // whatever separator form they land in.
    const ids = evidenceIdsText
      .split(/[\s,]+/)
      .map((id) => id.trim())
      .filter((id) => id.length > 0);
    if (ids.length > 0) {
      onLinkEvidence(ids);
    }
  }

  return (
    <section className="border border-slate-800 rounded-lg bg-slate-900/40 p-4 space-y-6">
      <div>
        <h2 className="text-sm font-medium text-slate-300 mb-2">Create Incident</h2>
        <form onSubmit={handleCreateSubmit} className="space-y-2">
          <input
            type="text"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            placeholder="Project name"
            className={inputClasses}
            required
          />
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Title"
            className={inputClasses}
            required
          />
          <input
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Description (optional)"
            className={inputClasses}
          />
          <button type="submit" disabled={isBusy} className={buttonClasses}>
            {actionState.status === "creating" ? "Creating…" : "Create Incident"}
          </button>
        </form>
      </div>

      <div className={hasLoadedIncident ? undefined : "opacity-50 pointer-events-none"}>
        <h2 className="text-sm font-medium text-slate-300 mb-2">Link Evidence</h2>
        <form onSubmit={handleLinkSubmit} className="space-y-2">
          <textarea
            value={evidenceIdsText}
            onChange={(e) => setEvidenceIdsText(e.target.value)}
            placeholder="Evidence IDs (comma or newline separated)"
            rows={3}
            className={inputClasses}
            disabled={!hasLoadedIncident}
          />
          <button
            type="submit"
            disabled={isBusy || !hasLoadedIncident}
            className={buttonClasses}
          >
            {actionState.status === "linking" ? "Linking…" : "Link Evidence"}
          </button>
        </form>
      </div>

      <div className={hasLoadedIncident ? undefined : "opacity-50 pointer-events-none"}>
        <h2 className="text-sm font-medium text-slate-300 mb-2">Pipeline Actions</h2>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => onCorrelate()}
            disabled={isBusy || !hasLoadedIncident}
            className={buttonClasses}
          >
            {actionState.status === "correlating" ? "Correlating…" : "Correlate"}
          </button>
          <button
            type="button"
            onClick={() => onInvestigate()}
            disabled={isBusy || !hasLoadedIncident}
            className={buttonClasses}
          >
            {actionState.status === "investigating" ? "Investigating…" : "Investigate"}
          </button>
        </div>
      </div>

      {actionState.status === "error" && (
        <div className="rounded-md border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {actionState.message}
        </div>
      )}
    </section>
  );
}
