/**
 * App.tsx — root routing shell for the Credit Decisioning Agent UI.
 * Professional ledger-aesthetic layout with slim sidebar navigation.
 */
import { BrowserRouter, Routes, Route, NavLink, Navigate } from "react-router-dom";

import CaseQueuePage          from "./pages/CaseQueuePage";
import ApplicationDetailPage  from "./pages/ApplicationDetailPage";
import AuditTracePage          from "./pages/AuditTracePage";

function QueueIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 15 15" fill="none" aria-hidden="true">
      <rect x="1" y="2" width="13" height="2" rx="1" fill="currentColor"/>
      <rect x="1" y="6.5" width="9" height="2" rx="1" fill="currentColor"/>
      <rect x="1" y="11" width="11" height="2" rx="1" fill="currentColor"/>
    </svg>
  );
}

function AuditIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 15 15" fill="none" aria-hidden="true">
      <circle cx="7.5" cy="7.5" r="6.5" stroke="currentColor" strokeWidth="1.5"/>
      <path d="M7.5 4V7.5L10 9.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}

function NavItem({ to, label, icon, end }: { to: string; label: string; icon: React.ReactNode; end?: boolean }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `flex items-center gap-2.5 px-3 py-2 rounded text-xs font-medium tracking-wide transition-all duration-150 ${
          isActive
            ? "bg-[#12213A] text-[#FAF8F3] shadow-sm"
            : "text-[#8A8072] hover:text-[#12213A] hover:bg-[#F2EFE8]"
        }`
      }
      aria-label={label}
    >
      {icon}
      <span>{label}</span>
    </NavLink>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex bg-[#FAF8F3]">

        {/* ── Sidebar navigation ─────────────────────────────────────── */}
        <aside
          className="w-48 flex-shrink-0 flex flex-col border-r border-[#D6D0C4] bg-[#FAF8F3]"
          aria-label="Primary navigation"
        >
          {/* Branding */}
          <div className="px-5 pt-6 pb-5 border-b border-[#D6D0C4]">
            <div className="flex items-center gap-2 mb-1">
              {/* Lozenge icon */}
              <div className="w-6 h-6 rounded bg-[#12213A] flex items-center justify-center flex-shrink-0">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                  <path d="M6 1L11 6L6 11L1 6L6 1Z" fill="#FAF8F3"/>
                </svg>
              </div>
              <span className="font-serif text-sm font-bold text-[#12213A] leading-tight">
                Credit Agent
              </span>
            </div>
            <div className="text-[10px] text-[#8A8072] pl-8 tracking-wide uppercase">
              Decisioning
            </div>
          </div>

          {/* Nav links */}
          <nav className="flex-1 px-3 py-4 space-y-1">
            <NavItem to="/" label="Case Queue" icon={<QueueIcon />} end />
            <NavItem to="/audit" label="Audit Trace" icon={<AuditIcon />} />
          </nav>

          {/* Footer */}
          <div className="px-5 py-4 border-t border-[#D6D0C4]">
            <div className="text-[10px] text-[#8A8072]/60 leading-relaxed">
              Human-gated<br/>credit decisioning
            </div>
          </div>
        </aside>

        {/* ── Main content ──────────────────────────────────────────── */}
        <main className="flex-1 min-w-0 overflow-y-auto" id="main-content">
          <Routes>
            <Route path="/"                               element={<CaseQueuePage />} />
            <Route path="/applications/:id"               element={<ApplicationDetailPage />} />
            <Route path="/applications/:id/trace"         element={<AuditTracePage />} />
            <Route path="/audit"                          element={<AuditTracePage />} />
            {/* Catch-all */}
            <Route path="*"                               element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
