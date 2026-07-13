/**
 * ApplicationDetailPage — the full decision workspace.
 * Scroll order: Header → VerificationStrip → Score Breakdown → Recommendation →
 *   Fairness & Challenger → Counterfactual → Adverse Action → DecisionActionBar (sticky)
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

// ── Section wrapper ────────────────────────────────────────────────────────
function Section({ id, label, children }: { id: string; label: string; children: React.ReactNode }) {
  return (
    <section className="bg-white border border-[#D6D0C4] rounded overflow-hidden" aria-labelledby={id}>
      <div className="px-5 py-3 border-b border-[#D6D0C4] bg-[#FAF8F3]">
        <h2 id={id} className="text-[10px] font-semibold uppercase tracking-widest text-[#8A8072]">
          {label}
        </h2>
      </div>
      <div className="px-5 py-4">{children}</div>
    </section>
  );
}

// ── Side-drawer for policy clause detail ──────────────────────────────────
function ClauseDrawer({ clauseId, clauses, onClose }: {
  clauseId: string | null;
  clauses: DecisionRecord["score_breakdown"]["clause_citations"];
  onClose: () => void;
}) {
  const clause = clauseId ? clauses.find((c) => c.clause_id === clauseId) : null;
  if (!clause) return null;

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-30 bg-[#12213A]/20" onClick={onClose} aria-hidden="true" />
      {/* Drawer */}
      <aside
        className="fixed inset-y-0 right-0 z-40 w-80 bg-[#FAF8F3] border-l border-[#D6D0C4] shadow-2xl flex flex-col"
        aria-label={`Policy clause ${clause.clause_id}`}
        role="complementary"
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#D6D0C4]">
          <div>
            <span className="font-mono text-sm font-bold text-[#C48A2A]">{clause.clause_id}</span>
            <div className="text-[10px] text-[#8A8072] mt-0.5 uppercase tracking-wide capitalize">
              {clause.factor.replace(/_/g, " ")}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-[#8A8072] hover:text-[#12213A] focus:outline-none focus:ring-1 focus:ring-[#C48A2A] rounded"
            aria-label="Close clause drawer"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path d="M4 4L12 12M12 4L4 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </button>
        </div>
        <div className="px-5 py-5 flex-1 overflow-y-auto">
          <p className="text-sm leading-relaxed text-[#12213A]">{clause.clause_text}</p>
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

  // ── Loading ──────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-12">
        <div className="h-6 w-48 bg-[#D6D0C4] rounded animate-pulse mb-4" />
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 bg-[#F2EFE8] rounded animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  // ── Error ────────────────────────────────────────────────────────────
  if (error || !record) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-16 text-center">
        <div className="text-4xl mb-4 opacity-20">◈</div>
        <div className="text-sm font-medium text-[#8C3B2E] mb-2" role="alert">
          {error ?? "Application not found."}
        </div>
        <button
          onClick={() => navigate("/")}
          className="text-sm text-[#C48A2A] hover:underline focus:outline-none focus:underline"
        >
          ← Back to queue
        </button>
      </div>
    );
  }

  const sb = record.score_breakdown;

  // ── Counterfactual hint ──────────────────────────────────────────────
  function counterfactualHint(): string {
    if (sb.band === "approve") return "Score is already in the approve band — no further action required.";
    const composite = Math.round(sb.composite_score * 100);
    if (sb.band === "refer") {
      const gap = 75 - composite;
      return gap > 0
        ? `Composite score needs to rise by ${gap} points (${composite} → 75) to reach APPROVE.`
        : "Score is at the approve threshold — minor improvement would clear it.";
    }
    const gap = 65 - composite;
    return `Composite score needs to rise by ${gap} points (${composite} → 65) to reach REFER.`;
  }

  // Band colour helper
  const bandColor = sb.band === "approve" ? "#3A6B4C" : sb.band === "refer" ? "#C48A2A" : "#8C3B2E";

  // ── Render ───────────────────────────────────────────────────────────
  return (
    <>
      <div className="max-w-3xl mx-auto px-6 py-6 pb-32">

        {/* Back nav */}
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-xs text-[#8A8072] hover:text-[#12213A] mb-5 transition-colors group"
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true" className="group-hover:-translate-x-0.5 transition-transform">
            <path d="M8 2L4 6L8 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Queue
        </Link>

        {/* ── 1. Header ────────────────────────────────────────────────── */}
        <div className="flex flex-wrap items-start justify-between gap-4 mb-5">
          <div>
            <h1 className="font-serif text-2xl font-bold text-[#12213A] leading-tight">
              {record.application_id}
            </h1>
            <div className="text-xs text-[#8A8072] mt-1 tabular-nums">
              Submitted {new Date(record.created_at).toLocaleString()}
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[10px] font-mono text-[#8A8072] border border-[#D6D0C4] px-2 py-1 rounded bg-white">
              {record.policy_version}
            </span>
            <StatusPill value={record.status} />
          </div>
        </div>

        {/* ── 2. Verification Strip ──────────────────────────────────────── */}
        <div className="mb-4">
          <VerificationStrip
            missingDocs={record.missing_docs}
            consistencyFlags={record.consistency_flags}
          />
        </div>

        {/* ── 3. Score Breakdown ─────────────────────────────────────────── */}
        <div className="mb-4">
          <Section id="score-heading" label="Score Breakdown">
            <CompositeScoreGauge composite={sb.composite_score} band={sb.band} />

            <div className="border-t border-[#D6D0C4] mt-2 pt-4 space-y-0.5">
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

            <div className="mt-3 pt-3 border-t border-[#D6D0C4] text-xs text-[#8A8072] tabular-nums">
              DTI ratio:{" "}
              <span className="font-semibold text-[#12213A]">{(sb.dti_ratio * 100).toFixed(1)}%</span>
              {sb.dti_ratio > 0.43 && (
                <span className="ml-2 text-[#8C3B2E]">· above acceptable threshold</span>
              )}
            </div>
          </Section>
        </div>

        {/* ── 4. Agent Recommendation ───────────────────────────────────── */}
        <div className="mb-4">
          <Section id="rec-heading" label="Agent Recommendation">
            <div className="flex items-center gap-4 mb-4">
              <div
                className="px-4 py-2 rounded font-serif text-xl font-bold capitalize"
                style={{ color: bandColor, background: `${bandColor}14` }}
              >
                {record.agent_recommendation}
              </div>
              <div className="text-sm text-[#8A8072] tabular-nums">
                Composite score:{" "}
                <span className="font-semibold text-[#12213A]">
                  {Math.round(sb.composite_score * 100)}/100
                </span>
              </div>
            </div>
            <p className="text-sm leading-relaxed text-[#12213A] mb-4">
              {record.rationale}
            </p>
            {sb.clause_citations.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-3 border-t border-[#D6D0C4]">
                <span className="text-[10px] text-[#8A8072] uppercase tracking-wide self-center mr-1">Clauses:</span>
                {sb.clause_citations.map((c) => (
                  <ClauseCitationChip key={c.clause_id} citation={c} />
                ))}
              </div>
            )}
          </Section>
        </div>

        {/* ── 5. Fairness & Challenger ───────────────────────────────────── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
          <FairnessCard check={record.fairness_check} />
          <ChallengerCard result={record.challenger_result} />
        </div>

        {/* ── 6. Counterfactual ─────────────────────────────────────────── */}
        <div className="mb-4">
          <Section id="cf-heading" label="What would change this">
            <p className="text-sm text-[#8A8072] leading-relaxed">{counterfactualHint()}</p>
          </Section>
        </div>

        {/* ── 7. Adverse Action Notice (DECLINE only) ───────────────────── */}
        {(record.agent_recommendation === "decline" || record.adverse_action_draft) && (
          <div className="mb-4">
            <NoticeEditor record={record} />
          </div>
        )}

        {/* ── Audit trail link ──────────────────────────────────────────── */}
        <div className="text-right pt-1">
          <Link
            to={`/applications/${record.application_id}/trace`}
            className="text-xs text-[#C48A2A] hover:underline focus:outline-none focus:underline inline-flex items-center gap-1"
          >
            View full pipeline trace
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
              <path d="M2 5H8M6 3L8 5L6 7" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </Link>
        </div>
      </div>

      {/* ── Sticky decision bar ────────────────────────────────────────── */}
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
