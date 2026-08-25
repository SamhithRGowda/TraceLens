// Shared class-string tokens for the incident workflow UI.
//
// These previously lived as local consts in ActionBar and were re-inlined
// by hand in IncidentDetail and IncidentHeader — four copies that had
// already drifted apart (different disabled opacities, and a focus style
// that removed the outline without replacing it). Centralised here so
// "primary vs secondary action" is a single decision rather than a
// per-file guess.
//
// Plain TS module rather than an @layer components block in index.css:
// nothing else in this project hand-writes CSS, and keeping it here means
// the tokens type-check alongside their consumers.

// Restores a visible keyboard focus indicator. The old inline styles used
// `focus:outline-none` with only a faint border change, which is close to
// invisible on the slate palette.
const focusRing =
  "focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950";

const disabled = "disabled:opacity-40 disabled:cursor-not-allowed";

// The single recommended next action. At most one enabled primary button
// should be on screen at a time — IncidentDetail decides which.
export const btnPrimary =
  `rounded-md bg-slate-100 px-4 py-2 text-sm font-medium text-slate-900 transition-colors hover:bg-white ${disabled} ${focusRing}`;

// Available and valid, but not the recommended next step.
export const btnSecondary =
  `rounded-md border border-slate-700 bg-slate-900 px-4 py-2 text-sm font-medium text-slate-300 transition-colors hover:bg-slate-800 hover:text-slate-100 ${disabled} ${focusRing}`;

// Small, low-emphasis controls: inline toggles, status changes, disclosures.
export const btnGhost =
  `rounded-md border border-slate-700 px-3 py-1 text-xs font-medium text-slate-300 transition-colors hover:bg-slate-800 hover:text-slate-100 ${disabled} ${focusRing}`;

// Text-only affordance, for "Edit details"-style disclosures where even a
// bordered button would compete with the stage's real action.
export const btnLink =
  `rounded text-xs font-medium text-slate-400 underline decoration-slate-700 underline-offset-2 transition-colors hover:text-slate-200 ${disabled} ${focusRing}`;

export const input =
  `w-full rounded-md border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-slate-500 focus-visible:border-slate-500`;

// The standard content surface. Used by every stage body so panels stop
// each inventing their own border/background pairing.
export const card = "rounded-lg border border-slate-800 bg-slate-900/40";

// A quieter surface for "nothing here yet" states, so an empty stage reads
// as pending rather than as a failure.
export const cardMuted = "rounded-lg border border-dashed border-slate-800 bg-slate-900/20";

// Monospace UUIDs and ids — always secondary to human-readable text.
export const idText = "font-mono text-[11px] text-slate-600";

export const badgeNeutral =
  "shrink-0 rounded border border-slate-700 bg-slate-800/60 px-2 py-0.5 text-[11px] font-medium text-slate-300";
