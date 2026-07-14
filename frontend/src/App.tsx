/**
 * App.tsx — root routing shell.
 * Professional enterprise SaaS layout: dark sidebar + white content area.
 */
import { BrowserRouter, Routes, Route, NavLink, Navigate } from "react-router-dom";

import CaseQueuePage         from "./pages/CaseQueuePage";
import ApplicationDetailPage from "./pages/ApplicationDetailPage";
import AuditTracePage        from "./pages/AuditTracePage";

// ── Icons ──────────────────────────────────────────────────────────────────
function QueueIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <rect x="1.5" y="2.5" width="13" height="2" rx="0.75" fill="currentColor" opacity="0.9"/>
      <rect x="1.5" y="7" width="9" height="2" rx="0.75" fill="currentColor" opacity="0.9"/>
      <rect x="1.5" y="11.5" width="11" height="2" rx="0.75" fill="currentColor" opacity="0.9"/>
    </svg>
  );
}

function AuditIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <circle cx="8" cy="8" r="6.25" stroke="currentColor" strokeWidth="1.5"/>
      <path d="M8 4.5V8L10.5 9.75" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}

// ── Nav item ──────────────────────────────────────────────────────────────
function NavItem({
  to,
  label,
  icon,
  end,
}: {
  to: string;
  label: string;
  icon: React.ReactNode;
  end?: boolean;
}) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `flex items-center gap-2.5 px-3 py-2 rounded-md text-sm font-medium transition-colors duration-100 ${
          isActive
            ? "bg-blue-700 text-white"
            : "text-slate-400 hover:text-white hover:bg-slate-800"
        }`
      }
      aria-label={label}
    >
      {icon}
      <span>{label}</span>
    </NavLink>
  );
}

// ── App shell ─────────────────────────────────────────────────────────────
export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex bg-slate-50">

        {/* ── Sidebar ──────────────────────────────────────────────────── */}
        <aside
          className="w-56 flex-shrink-0 flex flex-col bg-slate-900"
          style={{ minHeight: "100vh" }}
          aria-label="Primary navigation"
        >
          {/* Brand */}
          <div className="px-5 pt-5 pb-4 border-b border-slate-800">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-md bg-blue-600 flex items-center justify-center flex-shrink-0">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                  <path d="M7 1.5L12.5 7L7 12.5L1.5 7L7 1.5Z" fill="white"/>
                </svg>
              </div>
              <div>
                <div className="text-sm font-semibold text-white leading-tight tracking-tight">
                  Credit Agent
                </div>
                <div className="text-[10px] text-slate-500 leading-none mt-0.5 uppercase tracking-wider">
                  Decisioning
                </div>
              </div>
            </div>
          </div>

          {/* Nav section */}
          <div className="flex-1 px-3 py-4">
            <p className="px-3 mb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-600">
              Workspace
            </p>
            <nav className="space-y-0.5">
              <NavItem to="/"      label="Case Queue"  icon={<QueueIcon />} end />
              <NavItem to="/audit" label="Audit Trace" icon={<AuditIcon />} />
            </nav>
          </div>

          {/* Footer */}
          <div className="px-5 py-4 border-t border-slate-800">
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-green-500 flex-shrink-0" />
              <span className="text-[11px] text-slate-500">Human-gated pipeline</span>
            </div>
          </div>
        </aside>

        {/* ── Main content ─────────────────────────────────────────────── */}
        <main className="flex-1 min-w-0 overflow-y-auto" id="main-content">
          <Routes>
            <Route path="/"                        element={<CaseQueuePage />} />
            <Route path="/applications/:id"        element={<ApplicationDetailPage />} />
            <Route path="/applications/:id/trace"  element={<AuditTracePage />} />
            <Route path="/audit"                   element={<AuditTracePage />} />
            <Route path="*"                        element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
