/**
 * ApplicationDetailPage — reviewer workspace.
 * Shows applicant details, score breakdown, rationale, and a decision bar.
 */
import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { api } from "../api/client";
import type { DecisionRecord, Band } from "../api/client";

// ── Helpers ───────────────────────────────────────────────────────────────

function Section({ id, label, children, accent }: {
  id: string; label: string; children: React.ReactNode; accent?: "danger" | "warning" | "success";
}) {
  const hdr = accent === "danger"  ? "bg-red-50 border-b border-red-100"
            : accent === "warning" ? "bg-amber-50 border-b border-amber-100"
            : accent === "success" ? "bg-green-50 border-b border-green-100"
            : "border-b border-slate-100 bg-slate-50/50";
  const ttl = accent === "danger"  ? "text-red-600"
            : accent === "warning" ? "text-amber-700"
            : accent === "success" ? "text-green-700"
            : "text-slate-500";
  return (
    <section className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden" aria-labelledby={id}>
      <div className={`px-5 py-3 ${hdr}`}>
        <h2 id={id} className={`text-xs font-semibold uppercase tracking-wider ${ttl}`}>{label}</h2>
      </div>
      <div className="px-5 py-4">{children}</div>
    </section>
  );
}

function KV({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null;
  return (
    <div className="flex gap-3 py-1.5 border-b border-slate-50 last:border-0">
      <span className="text-xs text-slate-400 w-36 flex-shrink-0">{label}</span>
      <span className="text-sm text-slate-800">{value}</span>
    </div>
  );
}

function ScoreBar({ label, subscore, weight }: { label: string; subscore: number; weight: number }) {
  const pct   = Math.round(subscore * 100);
  const color = pct >= 70 ? "bg-green-500" : pct >= 40 ? "bg-amber-400" : "bg-red-400";
  return (
    <div className="mb-3">
      <div className="flex justify-between text-xs mb-1">
        <span className="text-slate-600 font-medium">{label}</span>
        <span className="text-slate-400 tabular-nums">{pct}/100 &middot; weight {Math.round(weight * 100)}%</span>
      </div>
      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function BandPill({ band }: { band: string }) {
  const map: Record<string, string> = {
    approve:              "bg-green-100 text-green-700 border-green-200",
    refer:                "bg-amber-100 text-amber-700 border-amber-200",
    decline:              "bg-red-100   text-red-700   border-red-200",
    pending_human_review: "bg-blue-100  text-blue-700  border-blue-200",
    decided:              "bg-green-100 text-green-700 border-green-200",
    awaiting_information: "bg-amber-100 text-amber-700 border-amber-200",
    hold_for_document:    "bg-orange-100 text-orange-700 border-orange-200",
    flag_fairness_fail:   "bg-red-100   text-red-700   border-red-200",
    error:                "bg-slate-100 text-slate-500 border-slate-200",
  };
  const label = band.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  return (
    <span className={`inline-flex px-2.5 py-1 rounded-md text-xs font-semibold border ${map[band] ?? "bg-slate-100 text-slate-600 border-slate-200"}`}>
      {label}
    </span>
  );
}

// ── Decision bar ──────────────────────────────────────────────────────────

function DecisionBar({ record, onDecisionMade }: {
  record: DecisionRecord;
  onDecisionMade: (r: DecisionRecord) => void;
}) {
  const [reviewerId, setReviewerId]       = useState("");
  const [overrideReason, setOverrideReason] = useState("");
  const [busy, setBusy]                   = useState(false);
  const [err, setErr]                     = useState<string | null>(null);

  const isDecided = record.human_decision !== null;
  const isPending = !isDecided && (
    record.status === "pending_human_review" ||
    record.status === "flag_fairness_fail"   ||
    record.status === "awaiting_information"
  );

  async function decide(decision: Band) {
    if (!reviewerId.trim()) { setErr("Reviewer ID is required."); return; }
    const isOverride = decision !== record.agent_recommendation;
    if (isOverride && overrideReason.trim().length < 20) {
      setErr("Override reason must be at least 20 characters."); return;
    }
    setErr(null);
    setBusy(true);
    try {
      const updated = await api.recordDecision(record.application_id, {
        human_decision: decision,
        human_reviewer: reviewerId.trim(),
        override_reason: isOverride ? overrideReason.trim() : undefined,
      });
      onDecisionMade(updated);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Decision failed.");
    } finally {
      setBusy(false);
    }
  }

  if (isDecided) {
    return (
      <div className="sticky bottom-0 z-30 bg-white/95 backdrop-blur border-t border-slate-200 px-6 py-3 flex items-center gap-3" role="status">
        <div className="flex items-center gap-2 text-green-700">
          <svg width="15" height="15" viewBox="0 0 15 15" fill="none" aria-hidden="true">
            <circle cx="7.5" cy="7.5" r="6.5" stroke="currentColor" strokeWidth="1.4"/>
            <path d="M4.5 7.5L6.5 9.5L10.5 5.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <span className="text-sm font-semibold">Decision recorded: <span className="capitalize">{record.human_decision}</span></span>
        </div>
        {record.human_reviewer && <span className="text-xs text-slate-400">by {record.human_reviewer}</span>}
        {record.decided_at && (
          <span className="text-xs text-slate-400 ml-auto tabular-nums">
            {new Date(record.decided_at).toLocaleString()}
          </span>
        )}
      </div>
    );
  }

  if (!isPending) return null;

  return (
    <div className="sticky bottom-0 z-30 bg-white/95 backdrop-blur border-t border-slate-200 px-6 py-4" role="toolbar" aria-label="Decision actions">
      {err && <p className="text-xs text-red-600 mb-2" role="alert">{err}</p>}

      <div className="flex flex-wrap items-end gap-3">
        <div>
          <label className="block text-xs text-slate-500 mb-1">Reviewer ID</label>
          <input
            type="text"
            value={reviewerId}
            onChange={(e) => setReviewerId(e.target.value)}
            placeholder="underwriter_1"
            className="border border-slate-200 rounded px-2.5 py-1.5 text-sm w-40 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="flex-1 min-w-48">
          <label className="block text-xs text-slate-500 mb-1">
            Override reason <span className="text-slate-300">(required when overriding agent)</span>
          </label>
          <input
            type="text"
            value={overrideReason}
            onChange={(e) => setOverrideReason(e.target.value)}
            placeholder="Reason for overriding agent recommendation..."
            className="border border-slate-200 rounded px-2.5 py-1.5 text-sm w-full focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="flex gap-2 flex-wrap">
          <button onClick={() => decide("approve")} disabled={busy}
            className="px-4 py-2 text-sm font-semibold rounded border border-green-600 text-green-700 hover:bg-green-600 hover:text-white transition-colors disabled:opacity-50">
            Approve
          </button>
          <button onClick={() => decide("refer")} disabled={busy}
            className="px-4 py-2 text-sm font-semibold rounded border border-amber-500 text-amber-700 hover:bg-amber-500 hover:text-white transition-colors disabled:opacity-50">
            Refer
          </button>
          <button onClick={() => decide("decline")} disabled={busy}
            className="px-4 py-2 text-sm font-semibold rounded border border-red-500 text-red-600 hover:bg-red-500 hover:text-white transition-colors disabled:opacity-50">
            Decline
          </button>
        </div>

        <div className="ml-auto text-xs text-slate-400 hidden md:block">
          Agent recommends: <span className="font-semibold text-slate-700 capitalize">{record.agent_recommendation}</span>
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────

export default function ApplicationDetailPage() {
  const { id }   = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [record, setRecord]   = useState<DecisionRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true); setError(null);
    try { setRecord(await api.getApplication(id)); }
    catch (e) { setError(e instanceof Error ? e.message : "Failed to load."); }
    finally { setLoading(false); }
  }, [id]);

  useEffect(() => { void load(); }, [load]);

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-8 py-8 space-y-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-28 bg-slate-100 animate-pulse rounded-lg" />
        ))}
      </div>
    );
  }

  if (error || !record) {
    return (
      <div className="max-w-3xl mx-auto px-8 py-20 text-center">
        <p className="text-sm text-red-600 mb-3">{error ?? "Application not found."}</p>
        <button onClick={() => navigate("/")} className="text-sm text-blue-600 hover:underline">
          Back to queue
        </button>
      </div>
    );
  }

  const sb = record.score_breakdown;

  return (
    <>
      <div className="max-w-3xl mx-auto px-8 py-6 pb-32 space-y-4">

        {/* Back link */}
        <Link to="/" className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 group">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" className="group-hover:-translate-x-0.5 transition-transform">
            <path d="M8 2L4 6L8 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Case Queue
        </Link>

        {/* Header */}
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900 tracking-tight">{record.application_id}</h1>
            <p className="text-xs text-slate-400 mt-1 tabular-nums">
              Submitted {new Date(record.created_at).toLocaleString()}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-slate-400 bg-slate-100 border border-slate-200 px-2 py-1 rounded">
              {record.policy_version}
            </span>
            <BandPill band={record.status} />
          </div>
        </div>

        {/* Awaiting info banner */}
        {record.status === "awaiting_information" && record.awaiting_info_items.length > 0 && (
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800">
            <p className="font-semibold mb-1">Awaiting information from applicant:</p>
            <ul className="space-y-0.5">
              {record.awaiting_info_items.map((item, i) => <li key={i}>· {item}</li>)}
            </ul>
          </div>
        )}

        {/* 1. Applicant details */}
        <Section id="applicant" label="Applicant Details">
          <KV label="Full Name"      value={record.applicant_name || "—"} />
          <KV label="Address"        value={record.applicant_address || "—"} />
          <KV label="Loan Requested" value={record.loan_amount_requested > 0
            ? `£${record.loan_amount_requested.toLocaleString("en-GB", { minimumFractionDigits: 2 })}`
            : "—"} />
          {record.applicant_notes && <KV label="Notes" value={record.applicant_notes} />}
        </Section>

        {/* 2. Missing docs */}
        {record.missing_docs && record.missing_docs.length > 0 && (
          <Section id="missing-docs" label="Missing Documents" accent="warning">
            <ul className="text-sm text-amber-800 space-y-1">
              {record.missing_docs.map((d) => (
                <li key={d}>· {d.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}</li>
              ))}
            </ul>
          </Section>
        )}

        {/* 3. Score breakdown */}
        {sb && (
          <Section id="score" label="Score Breakdown">
            <div className="flex items-center gap-4 mb-5">
              <div className="text-center">
                <div className="text-4xl font-bold text-slate-900 tabular-nums leading-none">
                  {Math.round(sb.composite_score * 100)}
                </div>
                <div className="text-[10px] text-slate-400 uppercase tracking-wider mt-1">/ 100</div>
              </div>
              <div className="flex-1">
                <BandPill band={sb.band} />
                <p className="text-xs text-slate-400 mt-1">{sb.policy_version}</p>
              </div>
            </div>
            <ScoreBar label="Debt-to-Income"   subscore={sb.dti_subscore}              weight={sb.weights["dti"] ?? 0.4} />
            <ScoreBar label="Credit History"   subscore={sb.credit_history_subscore}   weight={sb.weights["credit_history"] ?? 0.35} />
            <ScoreBar label="Income Stability" subscore={sb.income_stability_subscore} weight={sb.weights["income_stability"] ?? 0.25} />
            <p className="text-xs text-slate-400 mt-3 tabular-nums">
              DTI ratio: <span className="font-semibold text-slate-700">{(sb.dti_ratio * 100).toFixed(1)}%</span>
              {sb.dti_ratio > 0.43 && <span className="ml-2 text-red-500">above 43% threshold</span>}
            </p>
            {sb.clause_citations.length > 0 && (
              <div className="mt-4 pt-4 border-t border-slate-100 space-y-1.5">
                <p className="text-[10px] text-slate-400 uppercase tracking-wider">Policy clauses cited</p>
                {sb.clause_citations.map((c) => (
                  <div key={c.clause_id} className="flex gap-2 text-xs">
                    <span className="font-mono text-blue-600 flex-shrink-0">[{c.clause_id}]</span>
                    <span className="text-slate-600">{c.clause_text}</span>
                  </div>
                ))}
              </div>
            )}
          </Section>
        )}

        {/* 4. Agent recommendation */}
        <Section id="recommendation" label="Agent Recommendation">
          <div className="flex items-center gap-3 mb-3">
            <BandPill band={record.agent_recommendation} />
            {sb && (
              <span className="text-sm text-slate-500">
                Composite: <span className="font-semibold text-slate-900">{Math.round(sb.composite_score * 100)}/100</span>
              </span>
            )}
          </div>
          <p className="text-sm leading-relaxed text-slate-700">{record.rationale}</p>
        </Section>

        {/* 5. Adverse action notice */}
        {(record.adverse_action_draft || record.approved_notice_text) && (
          <Section id="notice" label="Adverse Action Notice" accent={record.approved_notice_text ? "success" : "warning"}>
            {!record.approved_notice_text && (
              <p className="text-xs text-amber-700 mb-3">
                Draft — generated by the AI. Review before finalising the decision.
              </p>
            )}
            <pre className="text-xs text-slate-700 bg-slate-50 border border-slate-200 rounded p-3 whitespace-pre-wrap font-sans leading-relaxed">
              {record.approved_notice_text ?? record.adverse_action_draft}
            </pre>
          </Section>
        )}

        {/* PDF */}
        <div className="text-right pt-1">
          <a
            href={api.getPdfUrl(record.application_id)}
            target="_blank"
            rel="noreferrer"
            className="text-xs text-blue-600 hover:underline inline-flex items-center gap-1"
          >
            Download full PDF report
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
              <path d="M2 5H8M6 3L8 5L6 7" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </a>
        </div>
      </div>

      <DecisionBar record={record} onDecisionMade={setRecord} />
    </>
  );
}
