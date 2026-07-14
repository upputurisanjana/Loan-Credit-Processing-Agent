/**
 * ApplicationDetailPage — the full underwriter decision workspace.
 */
import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { api } from "../api/client";
import type { DecisionRecord } from "../api/client";

import StatusPill          from "../components/StatusPill";
import VerificationStrip   from "../components/VerificationStrip";
import ScoreBar            from "../components/ScoreBar";
import CompositeScoreGauge from "../components/CompositeScoreGauge";
import ClauseCitationChip  from "../components/ClauseCitationChip";
import FairnessCard        from "../components/FairnessCard";
import ChallengerCard      from "../components/ChallengerCard";
import DecisionActionBar   from "../components/DecisionActionBar";
import NoticeEditor        from "../components/NoticeEditor";

// ── Section card ──────────────────────────────────────────────────────────
function Section({
  id,
  label,
  children,
  accent,
}: {
  id: string;
  label: string;
  children: React.ReactNode;
  accent?: "danger" | "warning";
}) {
  const headerCls = accent === "danger"
    ? "bg-red-50 border-b border-red-100"
    : accent === "warning"
    ? "bg-amber-50 border-b border-amber-100"
    : "border-b border-slate-100 bg-slate-50/50";

  const titleCls = accent === "danger"
    ? "text-red-600"
    : accent === "warning"
    ? "text-amber-700"
    : "text-slate-500";

  return (
    <section
      className="bg-white border border-slate-200 rounded-lg shadow-card overflow-hidden"
      aria-labelledby={id}
    >
      <div className={`px-5 py-3 ${headerCls}`}>
        <h2 id={id} className={`text-xs font-semibold uppercase tracking-wider ${titleCls}`}>
          {label}
        </h2>
      </div>
      <div className="px-5 py-4">{children}</div>
    </section>
  );
}

// ── Policy clause side-drawer ─────────────────────────────────────────────
function ClauseDrawer({
  clauseId,
  clauses,
  onClose,
}: {
  clauseId: string | null;
  clauses: DecisionRecord["score_breakdown"]["clause_citations"];
  onClose: () => void;
}) {
  const clause = clauseId ? clauses.find((c) => c.clause_id === clauseId) : null;
  if (!clause) return null;

  return (
    <>
      <div
        className="fixed inset-0 z-30 bg-slate-900/30 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />
      <aside
        className="fixed inset-y-0 right-0 z-40 w-80 bg-white border-l border-slate-200 shadow-2xl flex flex-col"
        aria-label={`Policy clause ${clause.clause_id}`}
        role="complementary"
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
          <div>
            <span className="font-mono text-sm font-bold text-blue-700">{clause.clause_id}</span>
            <div className="text-xs text-slate-400 mt-0.5 capitalize">
              {clause.factor.replace(/_/g, " ")}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
            aria-label="Close clause drawer"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path d="M4 4L12 12M12 4L4 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </button>
        </div>
        <div className="px-5 py-5 flex-1 overflow-y-auto">
          <p className="text-sm leading-relaxed text-slate-700">{clause.clause_text}</p>
        </div>
      </aside>
    </>
  );
}

export default function ApplicationDetailPage() {
  const { id }    = useParams<{ id: string }>();
  const navigate  = useNavigate();

  const [record, setRecord]       = useState<DecisionRecord | null>(null);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState<string | null>(null);
  const [activeClause, setClause] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getApplication(id);
      setRecord(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load application.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { void load(); }, [load]);

  // ── Loading skeleton ─────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-8 py-8">
        <div className="skeleton h-6 w-40 mb-5" />
        <div className="skeleton h-8 w-64 mb-8" />
        <div className="space-y-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="skeleton h-28 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  // ── Error ────────────────────────────────────────────────────────────
  if (error || !record) {
    return (
      <div className="max-w-3xl mx-auto px-8 py-20 text-center">
        <div className="text-4xl mb-4 opacity-10">⚠</div>
        <p className="text-sm font-medium text-red-600 mb-3" role="alert">
          {error ?? "Application not found."}
        </p>
        <button
          onClick={() => navigate("/")}
          className="text-sm text-blue-600 hover:underline"
        >
          ← Back to queue
        </button>
      </div>
    );
  }

  const sb = record.score_breakdown;

  function counterfactualHint(): string {
    if (sb.band === "approve") return "Score is already in the approve band — no further action required.";
    const composite = Math.round(sb.composite_score * 100);
    if (sb.band === "refer") {
      const gap = 75 - composite;
      return gap > 0
        ? `Composite score needs to rise by ${gap} points (${composite} → 75) to reach APPROVE.`
        : "Score is at the approve threshold — a minor improvement would clear it.";
    }
    const gap = 65 - composite;
    return `Composite score needs to rise by ${gap} points (${composite} → 65) to reach REFER.`;
  }

  return (
    <>
      <div className="max-w-3xl mx-auto px-8 py-6 pb-32">

        {/* Back link */}
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 mb-5 transition-colors group"
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"
               className="group-hover:-translate-x-0.5 transition-transform">
            <path d="M8 2L4 6L8 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Case Queue
        </Link>

        {/* ── 1. Header ─────────────────────────────────────────────── */}
        <div className="flex flex-wrap items-start justify-between gap-4 mb-5">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900 tracking-tight leading-tight">
              {record.application_id}
            </h1>
            <p className="text-xs text-slate-400 mt-1 tabular-nums">
              Submitted {new Date(record.created_at).toLocaleString()}
            </p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-mono text-slate-400 bg-slate-100 border border-slate-200 px-2 py-1 rounded-md">
              {record.policy_version}
            </span>
            <StatusPill value={record.status} />
          </div>
        </div>

        {/* ── 2. Verification ───────────────────────────────────────── */}
        <div className="mb-4">
          <VerificationStrip
            missingDocs={record.missing_docs}
            consistencyFlags={record.consistency_flags}
          />
        </div>

        {/* ── 3. Score Breakdown ────────────────────────────────────── */}
        <div className="mb-4">
          <Section id="score-heading" label="Score Breakdown">
            <CompositeScoreGauge composite={sb.composite_score} band={sb.band} />
            <div className="border-t border-slate-100 mt-3 pt-4 space-y-1">
              <ScoreBar
                label="Debt-to-Income"
                subscore={sb.dti_subscore}
                weight={sb.weights["dti"] ?? 0.4}
                clauseId={sb.clause_citations.find((c) => c.factor === "dti_ratio" || c.factor === "dti")?.clause_id}
                onViewClause={setClause}
              />
              <ScoreBar
                label="Credit History"
                subscore={sb.credit_history_subscore}
                weight={sb.weights["credit_history"] ?? 0.35}
                clauseId={sb.clause_citations.find((c) => c.factor === "credit_history")?.clause_id}
                onViewClause={setClause}
              />
              <ScoreBar
                label="Income Stability"
                subscore={sb.income_stability_subscore}
                weight={sb.weights["income_stability"] ?? 0.25}
                clauseId={sb.clause_citations.find((c) => c.factor === "income_stability")?.clause_id}
                onViewClause={setClause}
              />
            </div>
            <div className="mt-3 pt-3 border-t border-slate-100 text-xs text-slate-500 tabular-nums">
              DTI ratio:{" "}
              <span className="font-semibold text-slate-700">{(sb.dti_ratio * 100).toFixed(1)}%</span>
              {sb.dti_ratio > 0.43 && (
                <span className="ml-2 text-red-500">· above 43% acceptable threshold</span>
              )}
            </div>
          </Section>
        </div>

        {/* ── 4. Agent Recommendation ───────────────────────────────── */}
        <div className="mb-4">
          <Section id="rec-heading" label="Agent Recommendation">
            <div className="flex items-center gap-4 mb-4">
              <StatusPill value={record.agent_recommendation} />
              <span className="text-sm text-slate-500 tabular-nums">
                Composite score:{" "}
                <span className="font-semibold text-slate-900">
                  {Math.round(sb.composite_score * 100)}/100
                </span>
              </span>
            </div>
            <p className="text-sm leading-relaxed text-slate-700 mb-4">
              {record.rationale}
            </p>
            {sb.clause_citations.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-3 border-t border-slate-100">
                <span className="text-xs text-slate-400 self-center mr-1">Policy clauses:</span>
                {sb.clause_citations.map((c) => (
                  <ClauseCitationChip key={c.clause_id} citation={c} />
                ))}
              </div>
            )}
          </Section>
        </div>

        {/* ── 5. Fairness & Challenger ──────────────────────────────── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
          <FairnessCard check={record.fairness_check} />
          <ChallengerCard result={record.challenger_result} />
        </div>

        {/* ── 6. Counterfactual ─────────────────────────────────────── */}
        <div className="mb-4">
          <Section id="cf-heading" label="What would change this">
            <p className="text-sm text-slate-500 leading-relaxed">{counterfactualHint()}</p>
          </Section>
        </div>

        {/* ── 7. Adverse Action Notice ──────────────────────────────── */}
        {(record.agent_recommendation === "decline" || record.adverse_action_draft) && (
          <div className="mb-4">
            <NoticeEditor record={record} />
          </div>
        )}

        {/* Audit trail link */}
        <div className="text-right pt-1">
          <Link
            to={`/applications/${record.application_id}/trace`}
            className="text-xs text-blue-600 hover:underline inline-flex items-center gap-1"
          >
            View full pipeline trace
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
              <path d="M2 5H8M6 3L8 5L6 7" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </Link>
        </div>
      </div>

      {/* Sticky decision bar */}
      <DecisionActionBar record={record} onDecisionMade={setRecord} />

      {/* Policy clause drawer */}
      <ClauseDrawer
        clauseId={activeClause}
        clauses={sb.clause_citations}
        onClose={() => setClause(null)}
      />
    </>
  );
}
