/**
 * App.tsx — root routing shell for the Credit Decisioning Agent UI.
 * Design: slim vertical nav (Queue · Audit), paper background, ledger aesthetic.
 */
import { BrowserRouter, Routes, Route, NavLink, Navigate } from "react-router-dom";

import CaseQueuePage          from "./pages/CaseQueuePage";
import ApplicationDetailPage  from "./pages/ApplicationDetailPage";
import AuditTracePage          from "./pages/AuditTracePage";

const NAV_LINK_BASE =
  "flex items-center gap-2 px-3 py-2 text-xs font-medium uppercase tracking-wider rounded-sm transition-colors";
const NAV_LINK_ACTIVE  = "bg-[#12213A] text-[#FAF8F3]";
const NAV_LINK_IDLE    = "text-[#8A8072] hover:text-[#12213A] hover:bg-[#F2EFE8]";

function NavItem({ to, label, icon }: { to: string; label: string; icon: React.ReactNode }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) => `${NAV_LINK_BASE} ${isActive ? NAV_LINK_ACTIVE : NAV_LINK_IDLE}`}
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

        {/* ── Slim vertical nav ──────────────────────────────────────── */}
        <nav
          className="w-40 flex-shrink-0 border-r border-[#D6D0C4] pt-6 px-3 flex flex-col gap-1"
          aria-label="Primary navigation"
        >
          {/* Logo / wordmark */}
          <div className="px-3 mb-6">
            <span className="font-serif text-base font-bold text-[#12213A] leading-tight">
              Credit<br/>Agent
            </span>
            <div className="text-2xs text-[#8A8072] mt-0.5">Decisioning</div>
          </div>

          <NavItem
            to="/"
            label="Queue"
            icon={
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                <rect x="1" y="1" width="12" height="2" rx="1" fill="currentColor"/>
                <rect x="1" y="6" width="8" height="2" rx="1" fill="currentColor"/>
                <rect x="1" y="11" width="10" height="2" rx="1" fill="currentColor"/>
              </svg>
            }
          />

          <NavItem
            to="/audit"
            label="Audit"
            icon={
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                <path d="M7 1V7L10 9" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                <circle cx="7" cy="7" r="6" stroke="currentColor" strokeWidth="1.4"/>
              </svg>
            }
          />
        </nav>

        {/* ── Main content ──────────────────────────────────────────── */}
        <main className="flex-1 min-w-0 overflow-y-auto" id="main-content">
          <Routes>
            <Route path="/"                                   element={<CaseQueuePage />} />
            <Route path="/applications/:id"                   element={<ApplicationDetailPage />} />
            <Route path="/applications/:id/trace"             element={<AuditTracePage />} />
            <Route path="/audit"                              element={<AuditTracePage />} />
            {/* Catch-all redirect */}
            <Route path="*"                                   element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
