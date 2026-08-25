// Sprint 16: the write side of the incident workflow. Owns its own form
// input state (title/description/project name, evidence-ID text) but
// not incident data itself, and never calls api/incidents.ts directly —
// IncidentDetail owns all fetching/refetching, per the Sprint 16 plan.
// This component only invokes the callbacks it's given.
//
// UI-polish pass: this is now the *Create Incident* stage only. Investigate
// moved out to its own stage (rendered in IncidentDetail's StageSection
// action slot) so the four pipeline actions each sit in the stage they
// belong to instead of two of them sharing a generic "Pipeline Actions"
// box. Errors moved out to the single page-level ErrorBanner.

import { useEffect, useState } from "react";
import { btnGhost, btnLink, btnPrimary, btnSecondary, card, cardMuted, idText, input } from "./ui";

export type ActionState =
  | { status: "idle" }
  | { status: "creating" | "linking" | "correlating" | "investigating" }
  // `action` names what failed, so the page-level ErrorBanner can label it
  // without having to guess from the message text.
  | { status: "error"; action: string; message: string };

// Sprint 19 (final polish): when a Trace Library scenario is selected,
// IncidentDetail passes its prefill fields and known evidence here,
// instead of the user typing anything.
export interface ActionBarPrefill {
  scenarioId: string; // used to detect a new selection and re-apply prefill
  projectName: string;
  title: string;
  description: string;
}

export interface ScenarioEvidenceItem {
  id: string;
  type: "llm_call" | "tool_call";
  preview: string;
}

interface ActionBarProps {
  // Whether an incident is currently loaded. Only the manual
  // link/correlate controls need one; Create Incident does not.
  hasLoadedIncident: boolean;

  onCreateIncident: (data: {
    projectName: string;
    title: string;
    description: string;
  }) => Promise<void>;
  onLinkEvidence: (evidenceIds: string[]) => Promise<void>;
  onCorrelate: () => Promise<void>;

  actionState: ActionState;

  // True when Create Incident is the recommended next action, so it gets
  // primary weight and everything else on the page stays secondary.
  isNextAction: boolean;

  // Trace Library integration. Both optional — with neither set,
  // ActionBar behaves exactly as it did before this scenario existed
  // (manual project/title/description entry, manual evidence-ID
  // textarea) — nothing is removed, only added-to.
  prefill?: ActionBarPrefill;
  scenarioEvidence?: ScenarioEvidenceItem[];
}

export default function ActionBar({
  hasLoadedIncident,
  onCreateIncident,
  onLinkEvidence,
  onCorrelate,
  actionState,
  isNextAction,
  prefill,
  scenarioEvidence,
}: ActionBarProps) {
  const [projectName, setProjectName] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [evidenceIdsText, setEvidenceIdsText] = useState("");
  const [isEditingDetails, setIsEditingDetails] = useState(false);

  const isBusy = actionState.status !== "idle" && actionState.status !== "error";

  // A selected Trace Library scenario brings its own evidence set, which
  // Create Incident links and correlates in one call. On that path there is
  // no manual Link Evidence or Correlate UI at all — selecting the trace
  // already determined the evidence, so a button for it would only imply
  // there's a decision left to make. Both controls stay for hand-assembled
  // incidents (no scenario selected).
  const hasScenarioEvidence = scenarioEvidence !== undefined && scenarioEvidence.length > 0;

  // Apply prefill whenever a *new* scenario is selected (keyed on
  // scenarioId, not the field values themselves, so the user can still
  // freely edit the prefilled fields without them snapping back on
  // every render). Fields remain fully editable after this — selecting
  // a scenario fills the form, it doesn't lock it.
  useEffect(() => {
    if (!prefill) return;
    setProjectName(prefill.projectName);
    setTitle(prefill.title);
    setDescription(prefill.description);
    setIsEditingDetails(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prefill?.scenarioId]);

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

  const createButton = (
    <button
      type="submit"
      disabled={isBusy}
      className={isNextAction ? btnPrimary : btnSecondary}
    >
      {actionState.status === "creating" ? "Creating…" : "Create Incident"}
    </button>
  );

  const detailFields = (
    <div className="space-y-2">
      <input
        type="text"
        value={projectName}
        onChange={(e) => setProjectName(e.target.value)}
        placeholder="Project name"
        className={input}
        required
      />
      <input
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Title"
        className={input}
        required
      />
      <input
        type="text"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="Description (optional)"
        className={input}
      />
    </div>
  );

  // --- Trace Library path -------------------------------------------------
  // Everything is already determined by the selection, so this reads as a
  // confirmation screen rather than a form: what will be created, what
  // evidence comes with it, one button.
  if (hasScenarioEvidence) {
    return (
      <form onSubmit={handleCreateSubmit} className={`${card} divide-y divide-slate-800`}>
        <div className="p-4">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <p className="text-sm font-medium text-slate-100">{title}</p>
              {description && (
                <p className="mt-1 text-xs leading-relaxed text-slate-400">{description}</p>
              )}
              <p className="mt-2 text-xs text-slate-500">
                Project <span className="text-slate-400">{projectName}</span>
              </p>
            </div>
            <button
              type="button"
              onClick={() => setIsEditingDetails((v) => !v)}
              className={`${btnLink} shrink-0`}
            >
              {isEditingDetails ? "Done editing" : "Edit details"}
            </button>
          </div>

          {isEditingDetails && <div className="mt-3">{detailFields}</div>}
        </div>

        <div className="p-4">
          <p className="text-xs text-slate-500">
            {scenarioEvidence.length} evidence events will be attached and correlated automatically.
          </p>
          <ul className="mt-2 space-y-1.5">
            {scenarioEvidence.map((item, index) => (
              <li key={item.id} className="flex items-start gap-3 text-xs">
                <span className="w-4 shrink-0 text-right font-mono text-slate-600">{index + 1}</span>
                <span className="shrink-0 rounded border border-slate-700 bg-slate-800/60 px-2 py-0.5 text-[11px] font-medium text-slate-300">
                  {item.type === "llm_call" ? "LLM Call" : "Tool Call"}
                </span>
                <span className="leading-relaxed text-slate-400">{item.preview}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="p-4">{createButton}</div>
      </form>
    );
  }

  // --- Manual path --------------------------------------------------------
  // Unchanged in capability: free-form details, then explicit Link Evidence
  // and Correlate steps, because here the evidence really is an open choice.
  return (
    <div className="space-y-4">
      <form onSubmit={handleCreateSubmit} className={`${card} space-y-3 p-4`}>
        {detailFields}
        {createButton}
      </form>

      <div className={`${hasLoadedIncident ? card : cardMuted} space-y-3 p-4`}>
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Link evidence manually
          </h3>
          <p className="mt-1 text-xs leading-relaxed text-slate-500">
            {hasLoadedIncident
              ? "For incidents assembled by hand from arbitrary evidence IDs. Correlate then expands outward from what's linked."
              : "Available once an incident is loaded. Not needed when you start from a Trace Library scenario."}
          </p>
        </div>

        <form onSubmit={handleLinkSubmit} className="space-y-2">
          <textarea
            value={evidenceIdsText}
            onChange={(e) => setEvidenceIdsText(e.target.value)}
            placeholder="Evidence IDs (comma or newline separated)"
            rows={3}
            className={`${input} ${idText} placeholder:font-sans placeholder:text-xs`}
            disabled={!hasLoadedIncident}
          />
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={isBusy || !hasLoadedIncident}
              className={btnGhost}
            >
              {actionState.status === "linking" ? "Linking…" : "Link Evidence"}
            </button>
            <button
              type="button"
              onClick={() => onCorrelate()}
              disabled={isBusy || !hasLoadedIncident}
              className={btnGhost}
            >
              {actionState.status === "correlating" ? "Correlating…" : "Correlate"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
