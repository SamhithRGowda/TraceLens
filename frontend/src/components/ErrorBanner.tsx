// A single error surface for the whole page.
//
// There used to be four byte-identical red boxes in four different
// positions (incident load, create/link/correlate/investigate, status
// change, remediation), and none of them said which action had failed —
// so the same-looking box meant something different depending on where it
// appeared. This renders in one predictable place and always names the
// action.

import { btnGhost } from "./ui";

interface ErrorBannerProps {
  // What failed, e.g. "Investigation". Rendered as the label so the banner
  // is unambiguous regardless of which action produced it.
  action: string;
  message: string;
  onDismiss: () => void;
}

export default function ErrorBanner({ action, message, onDismiss }: ErrorBannerProps) {
  return (
    <div
      role="alert"
      className="flex items-start justify-between gap-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3"
    >
      <div className="min-w-0">
        <p className="text-sm font-medium text-red-300">{action} failed</p>
        <p className="mt-0.5 text-sm leading-relaxed text-red-400/90">{message}</p>
      </div>
      <button type="button" onClick={onDismiss} className={`${btnGhost} shrink-0 border-red-500/30 text-red-300 hover:bg-red-500/10 hover:text-red-200`}>
        Dismiss
      </button>
    </div>
  );
}
