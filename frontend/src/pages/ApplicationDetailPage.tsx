/**
 * ApplicationDetailPage — the full decision workspace.
 * Per UI_UX_DESIGN.md §3.2: scroll top-to-bottom in underwriter's reasoning order:
 *   Header → VerificationStrip → Score Breakdown → Recommendation →
 *   Fairness & Challenger → Counterfactual → DecisionActionBar (sticky)
 */
import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { api } from "../api/client";
import type { DecisionRecord } from "../api/client";

import StatusPill        from "../components/StatusPill";
import VerificationStrip from "../components/VerificationStrip";
import ScoreBar          from "../components/ScoreBar";
import CompositeScoreGauge from "../components/CompositeScoreGauge";
import ClauseCitationChip  from "../components/ClauseCitationChip";
import FairnessCard      from "../components/FairnessCard";
import ChallengerCard    from "../components/ChallengerCard";
import DecisionActionBar from "../components/DecisionActionBar";
import NoticeEditor      from "../components/NoticeEditor";

// Side-drawer for policy clause detail
function ClauseDrawer({ clauseId, clauses, onClose }: {
  clauseId: string | null;
  clauses: DecisionRecord["score_breakdown"]["clause_citations"];
  onClose: () => void;
}) {
  const clause = clauseId ? clauses.find((c) => c.clause_id === clauseId) : null;
  if (!clause) return null;

  return (
    <div
      className="fixed inset-y-0 right-0 z-40 w-80 bg-[#FAF8F3] border-l border-[#D6D0C4] shadow-xl
                 flex flex-col overflow-y-auto"
      role="complementary"
      aria-label={`Policy clause ${clause.clause_id}`}
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#D6D0C4]">
        <span className="font-mono text-sm font-semibold text-[#C48A2A]">{clause.clause_id}</span>
        <button
          onClick={onClose}
          className="text-[#8A8072] hover:text-[#12213A] focus:outline-none focus:ring-1 focus:ring-[#C48A2A] rounded-sm"
          aria-label="Close clause drawer"
        >
          ✕
        </button>
      </div>
      <div className="px-4 py-4 text-sm leading-relaxed">
        <div className="text-xs text-[#8A8072] uppercase tracking-wide mb-2 capitalize">
          Factor: {clause.factor.replace(/_/g, " ")}
        </div>
        <p className="text-[#12213A]">{clause.clause_text}</p>
      </div>
    </div>
  );
}

export default function ApplicationDetailPage() {
  const { id }      = useParams<{ id: string }>();
  const navigate    = useNavigate();

  const [record, setRecord]         = useState<DecisionRecord | null>(null);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState<string | null>(null);
  const [activeClause, setClause]   = useState<string | null>(null);

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

  // ── Loading / error states ──────────────────────────────────────────────
  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center text-[#8A8072] text-sm">
        Loading application…
      </div>
    );
  }

  if (error || !record) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16">
        <div className="text-sm text-[#8C3B2E] mb-4" role="alert">{error ?? "Application not found."}</div>
        <button onClick={() => navigate("/")} className="text-sm text-[#C48A2A] underline hover:no-underline">
          ← Back to queue
        </button>
      </div>
    );
  }

  const sb = record.score_breakdown;

  // ── Counterfactual hint ─────────────────────────────────────────────────
  function counterfactualHint(): string {
    if (sb.band === "approve") return "Score is in the approve band.";
    const composite = Math.round(sb.composite_score * 100);
    if (sb.band === "refer") {
      const gap = 75 - composite;
      return `Composite score needs to rise by ${gap} points to reach APPROVE.`;
    }
    const gap = 65 - composite;
    return `Composite score needs to rise by ${gap} points to reach REFER.`;
  }

  // ── Render ──────────────────────────────────────────────────────────────
  return (
    <>
      <div className="max-w-3xl mx-auto px-4 py-6 pb-24">

        {/* Back nav */}
        <Link
          to="/"
          className="inline-flex items-center gap-1 text-xs text-[#8A8072] hover:text-[#12213A] mb-4 transition-colors"
        >
          ← Queue
        </Link>

        {/* ── 1. Header ─────────────────────────────────────────────────── */}
        <div className="flex flex-wrap items-start justify-between gap-3 mb-5">
          <div>
            <h1 className="font-serif text-2xl text-[#12213A]">{record.application_id}</h1>
            <div className="text-xs text-[#8A8072] mt-0.5" data-numeric>
              Submitted {new Date(record.created_at).toLocaleString()}
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-[#8A8072] border border-[#D6D0C4] px-2 py-0.5 rounded-sm font-mono">
              {record.policy_version}
            </span>
            <StatusPill value={record.status} />
          </div>
        </div>

        {/* ── 2. Verification Strip ─────────────────────────────────────── */}
        <div className="mb-5">
          <VerificationStrip
            missingDocs={record.missing_docs}
            consistencyFlags={record.consistency_flags}
          />
        </div>

        {/* ── 3. Score Breakdown ───────────────────────────────────────── */}
        <section className="ledger-card mb-5" aria-labelledby="score-heading">
          <h2 id="score-heading" className="section-label">Score Breakdown</h2>

          <CompositeScoreGauge composite={sb.composite_score} band={sb.band} />

          <div className="border-t border-[#D6D0C4] mt-2 pt-4 space-y-1">
            <ScoreBar
              label="Debt-to-Income Ratio"
              subscore={sb.dti_subscore}
              weight={sb.weights["dti"] ?? 0.4}
              clauseId={sb.clause_citations.find((c) => c.factor === "dti_ratio")?.clause_id}
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

          {/* DTI detail */}
          <div className="mt-3 text-xs text-[#8A8072] border-t border-[#D6D0C4] pt-2" data-numeric>
            DTI ratio: <span className="font-medium text-[#12213A]">{(sb.dti_ratio * 100).toFixed(1)}%</span>
          </div>
        </section>

        {/* ── 4. Recommendation Card ───────────────────────────────────── */}
        <section className="ledger-card mb-5" aria-labelledby="rec-heading">
          <h2 id="rec-heading" className="section-label">Agent Recommendation</h2>
          <div className="flex items-baseline gap-3 mb-3">
            <span className="font-serif text-3xl font-bold capitalize" style={{
              color: sb.band === "approve" ? "#3A6B4C" : sb.band === "refer" ? "#C48A2A" : "#8C3B2E"
            }}>
              {record.agent_recommendation}
            </span>
            <span className="text-xs text-[#8A8072]" data-numeric>
              score {Math.round(sb.composite_score * 100)}/100
            </span>
          </div>
          <p className="text-sm leading-relaxed text-[#12213A]">
            {record.rationale}
          </p>

          {/* Clause citations */}
          {sb.clause_citations.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {sb.clause_citations.map((c) => (
                <ClauseCitationChip key={c.clause_id} citation={c} />
              ))}
            </div>
          )}
        </section>

        {/* ── 5. Fairness & Challenger ─────────────────────────────────── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5">
          <FairnessCard check={record.fairness_check} />
          <ChallengerCard result={record.challenger_result} />
        </div>

        {/* ── 6. Counterfactual ────────────────────────────────────────── */}
        <section className="mb-5 px-4 py-3 border border-[#D6D0C4] rounded-sm bg-[#FAF8F3]"
                 aria-labelledby="cf-heading">
          <h2 id="cf-heading" className="section-label">What would change this</h2>
          <p className="text-sm text-[#8A8072]">{counterfactualHint()}</p>
        </section>

        {/* ── 7. Adverse Action Notice (DECLINE only) ──────────────────── */}
        {(record.agent_recommendation === "decline" || record.adverse_action_draft) && (
          <div className="mb-5">
            <NoticeEditor record={record} />
          </div>
        )}

        {/* Audit trail link */}
        <div className="text-xs text-[#8A8072] text-right">
          <Link
            to={`/applications/${record.application_id}/trace`}
            className="text-[#C48A2A] hover:underline focus:outline-none focus:underline"
          >
            View full audit trace →
          </Link>
        </div>
      </div>

      {/* ── 7. Sticky decision bar ───────────────────────────────────────── */}
      <DecisionActionBar record={record} onDecisionMade={setRecord} />

      {/* Policy clause side-drawer */}
      <ClauseDrawer
        clauseId={activeClause}
        clauses={sb.clause_citations}
        onClose={() => setClause(null)}
      />
    </>
  );
}
