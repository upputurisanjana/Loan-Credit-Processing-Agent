/**
 * DecisionActionBar — sticky bottom bar in Application Detail.
 * Approve · Override (opens modal) · Request more info — always visible while pending.
 */
import { useState } from "react";
import type { DecisionRecord } from "../api/client";
import DecisionModal from "./DecisionModal";

type ModalVariant = "approve" | "override" | "request_info";

interface Props {
  record: DecisionRecord;
  onDecisionMade: (updated: DecisionRecord) => void;
}

export default function DecisionActionBar({ record, onDecisionMade }: Props) {
  const [modal, setModal] = useState<ModalVariant | null>(null);

  const isPending = record.status === "pending_human_review" || record.status === "flag_fairness_fail";
  const isDecided = record.human_decision !== null;
  const isFairFail = record.status === "flag_fairness_fail";

  // ── Already decided ───────────────────────────────────────────────────
  if (isDecided) {
    return (
      <div
        className="sticky bottom-0 z-30 bg-white/95 backdrop-blur border-t border-[#D6D0C4]
                   px-6 py-3 flex items-center gap-3"
        role="status"
        aria-label="Decision recorded"
      >
        <div className="flex items-center gap-2 text-[#3A6B4C]">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5"/>
            <path d="M5 8L7 10L11 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <span className="text-sm font-semibold">
            Decision recorded: <span className="capitalize">{record.human_decision}</span>
          </span>
        </div>
        {record.human_reviewer && (
          <span className="text-xs text-[#8A8072]">by {record.human_reviewer}</span>
        )}
        {record.decided_at && (
          <span className="text-xs text-[#8A8072] ml-auto tabular-nums">
            {new Date(record.decided_at).toLocaleString()}
          </span>
        )}
      </div>
    );
  }

  if (!isPending) return null;

  return (
    <>
      <div
        className="sticky bottom-0 z-30 bg-white/95 backdrop-blur border-t border-[#D6D0C4]
                   px-6 py-4"
        role="toolbar"
        aria-label="Decision actions"
      >
        {/* Fairness warning banner */}
        {isFairFail && (
          <div className="flex items-center gap-2 text-xs text-[#8C3B2E] bg-[#8C3B2E]/5 border border-[#8C3B2E]/25 rounded px-3 py-2 mb-3">
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true" className="flex-shrink-0">
              <circle cx="6.5" cy="6.5" r="5.5" stroke="currentColor" strokeWidth="1.3"/>
              <path d="M6.5 3.5V7" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
              <circle cx="6.5" cy="9.5" r="0.6" fill="currentColor"/>
            </svg>
            <strong>Fairness flag:</strong>&nbsp;Identity-masked re-score produced a different band. Mandatory human review required.
          </div>
        )}

        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-xs text-[#8A8072] hidden sm:inline mr-1">Underwriter action:</span>

          {/* Approve */}
          <button
            onClick={() => setModal("approve")}
            className="px-5 py-2 text-sm font-semibold rounded border border-[#3A6B4C] text-[#3A6B4C]
                       hover:bg-[#3A6B4C] hover:text-white transition-colors
                       focus:outline-none focus:ring-2 focus:ring-[#3A6B4C] focus:ring-offset-1"
          >
            ✓ Approve
          </button>

          {/* Override */}
          <button
            onClick={() => setModal("override")}
            className="px-5 py-2 text-sm font-semibold rounded border border-[#8C3B2E] text-[#8C3B2E]
                       hover:bg-[#8C3B2E] hover:text-white transition-colors
                       focus:outline-none focus:ring-2 focus:ring-[#8C3B2E] focus:ring-offset-1"
          >
            Override
          </button>

          {/* Request more info */}
          <button
            onClick={() => setModal("request_info")}
            className="px-5 py-2 text-sm font-semibold rounded border border-[#C48A2A] text-[#C48A2A]
                       hover:bg-[#C48A2A] hover:text-white transition-colors
                       focus:outline-none focus:ring-2 focus:ring-[#C48A2A] focus:ring-offset-1"
          >
            Request info
          </button>

          <div className="ml-auto text-xs text-[#8A8072] hidden md:flex items-center gap-1">
            Agent recommends:
            <span className="ml-1 font-semibold capitalize text-[#12213A]">
              {record.agent_recommendation}
            </span>
          </div>
        </div>
      </div>

      {modal && (
        <DecisionModal
          record={record}
          variant={modal}
          onClose={() => setModal(null)}
          onSuccess={(updated) => {
            setModal(null);
            onDecisionMade(updated);
          }}
        />
      )}
    </>
  );
}
