/**
 * App.tsx — Reviewer / Underwriter dashboard shell.
 */
import { BrowserRouter, Routes, Route, NavLink, Navigate } from "react-router-dom";
import DashboardPage         from "./pages/DashboardPage";
import QueuePage             from "./pages/QueuePage";
import ApplicationDetailPage from "./pages/ApplicationDetailPage";

// ── Icons ─────────────────────────────────────────────────────────────────

function DashboardIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <rect x="1.5" y="1.5" width="5.5" height="5.5" rx="1" fill="currentColor" opacity="0.9"/>
      <rect x="9"   y="1.5" width="5.5" height="5.5" rx="1" fill="currentColor" opacity="0.9"/>
      <rect x="1.5" y="9"   width="5.5" height="5.5" rx="1" fill="currentColor" opacity="0.9"/>
      <rect x="9"   y="9"   width="5.5" height="5.5" rx="1" fill="currentColor" opacity="0.9"/>
    </svg>
  );
}

function QueueIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <rect x="1.5" y="2.5"  width="13" height="2" rx="0.75" fill="currentColor" opacity="0.9"/>
      <rect x="1.5" y="7"    width="9"  height="2" rx="0.75" fill="currentColor" opacity="0.9"/>
      <rect x="1.5" y="11.5" width="11" height="2" rx="0.75" fill="currentColor" opacity="0.9"/>
    </svg>
  );
}

function NavItem({
  to, label, icon, end, badge,
}: {
  to: string; label: string; icon: React.ReactNode; end?: boolean; badge?: number;
}) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-100 group ${
          isActive
            ? "bg-blue-600 text-white shadow-sm"
            : "text-slate-400 hover:text-white hover:bg-slate-800"
        }`
      }
    >
      {icon}
      <span className="flex-1">{label}</span>
      {badge != null && badge > 0 && (
        <span className="text-[10px] font-bold bg-amber-500 text-white rounded-full px-1.5 py-0.5 leading-none">
          {badge}
        </span>
      )}
    </NavLink>
  );
}

// ── App ───────────────────────────────────────────────────────────────────

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex bg-slate-100">

        {/* ── Sidebar ─────────────────────────────────────────────────── */}
        <aside
          className="w-60 flex-shrink-0 flex flex-col bg-slate-900 border-r border-slate-800"
          style={{ minHeight: "100vh" }}
          aria-label="Primary navigation"
        >
          {/* Brand */}
          <div className="px-5 pt-6 pb-5 border-b border-slate-800">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center flex-shrink-0 shadow-lg">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                  <path d="M8 1.5L14 8L8 14.5L2 8L8 1.5Z" fill="white"/>
                </svg>
              </div>
              <div>
                <div className="text-sm font-bold text-white leading-tight tracking-tight">Credit Agent</div>
                <div className="text-[10px] text-blue-400 leading-none mt-0.5 font-medium">Reviewer Dashboard</div>
              </div>
            </div>
          </div>

          {/* Main nav */}
          <div className="flex-1 px-3 py-5 space-y-6">
            <div>
              <p className="px-3 mb-2 text-[10px] font-bold uppercase tracking-widest text-slate-600">Overview</p>
              <nav className="space-y-1">
                <NavItem to="/"      label="Dashboard"  icon={<DashboardIcon />} end />
                <NavItem to="/queue" label="Case Queue" icon={<QueueIcon />} />
              </nav>
            </div>

            {/* Pipeline info */}
            <div className="mx-1 p-3 bg-slate-800/60 rounded-lg border border-slate-700/50">
              <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-2">Pipeline</p>
              <div className="space-y-1.5">
                {["Verify Docs", "Extract (LLM)", "Score (Python)", "Recommend (LLM)", "Human Gate"].map((step, i) => (
                  <div key={step} className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded-full bg-blue-900 border border-blue-700 flex items-center justify-center flex-shrink-0">
                      <span className="text-[8px] text-blue-400 font-bold">{i + 1}</span>
                    </div>
                    <span className="text-[11px] text-slate-400">{step}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="px-4 py-4 border-t border-slate-800 space-y-2">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-green-400 flex-shrink-0 animate-pulse" />
              <span className="text-[11px] text-slate-500">Human-gated · no auto-decisions</span>
            </div>
            <div className="text-[10px] text-slate-700">Policy v1.2 · Fairness checks active</div>
          </div>
        </aside>

        {/* ── Main content ────────────────────────────────────────────── */}
        <main className="flex-1 min-w-0 overflow-y-auto bg-slate-50" id="main-content">
          {/* Top bar */}
          <div className="sticky top-0 z-20 bg-white border-b border-slate-200 px-8 py-3 flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <span className="font-semibold text-slate-700">Credit Decisioning Agent</span>
              <span className="text-slate-300">/</span>
              <span>Underwriter Review</span>
            </div>
            <div className="flex items-center gap-3">
              <a
                href="http://localhost:8000/docs"
                target="_blank"
                rel="noreferrer"
                className="text-xs text-slate-400 hover:text-blue-600 transition-colors flex items-center gap-1"
              >
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                  <circle cx="6" cy="6" r="5" stroke="currentColor" strokeWidth="1.2"/>
                  <path d="M6 4V6.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
                  <circle cx="6" cy="8.5" r="0.5" fill="currentColor"/>
                </svg>
                API Docs
              </a>
              <div className="flex items-center gap-1.5 text-xs text-slate-400">
                <div className="w-1.5 h-1.5 rounded-full bg-green-400" />
                Backend connected
              </div>
            </div>
          </div>

          <Routes>
            <Route path="/"                  element={<DashboardPage />} />
            <Route path="/queue"             element={<QueuePage />} />
            <Route path="/applications/:id"  element={<ApplicationDetailPage />} />
            <Route path="*"                  element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
