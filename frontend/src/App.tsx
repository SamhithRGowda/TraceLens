// Renders the real Milestone 1 workflow. The scaffold placeholder is
// gone now that there's an actual page to render.
//
// UI-polish pass: owns the page chrome (background, product header) so
// IncidentDetail is just the workflow. Previously the app opened directly
// on a bare UUID text field with no indication of what the product was.
import IncidentDetail from "./pages/IncidentDetail";

export default function App() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 antialiased">
      <header className="border-b border-slate-800 bg-slate-950/80">
        <div className="mx-auto flex max-w-4xl items-baseline justify-between gap-4 px-6 py-4">
          <div className="flex items-baseline gap-2.5">
            <span className="text-sm font-semibold tracking-tight text-slate-100">TraceLens</span>
            <span className="text-xs text-slate-500">Agent failure investigation</span>
          </div>
          <span className="text-xs text-slate-600">Milestone 1</span>
        </div>
      </header>

      <main>
        <IncidentDetail />
      </main>
    </div>
  );
}
