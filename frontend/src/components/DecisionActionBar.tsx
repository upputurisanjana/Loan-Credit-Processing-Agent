/**
 * DecisionActionBar — sticky bottom bar in Application Detail.
 * Per UI_UX_DESIGN.md §3.2: "sticky at the bottom of the viewport while
 * scrolling this screen: Approve (green outline) · Override (opens modal,
 * reason required) · Request more info (returns to HOLD) — always visible."
 *
 * Only shown when status === "pending_human_review".
 * Disabled when status === "decided".
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

  if (isDecided) {
    return (
      <div
        className="sticky bottom-0 z-30 bg-[#FAF8F3]/95 backdrop-blur-sm border-t border-[#D6D0C4] px-6 py-3
                   flex items-center gap-3"
        role="status"
        aria-label="Decision recorded"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true" className="text-[#3A6B4C]">
          <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.4"/>
          <path d="M5 8L7 10L11 6" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        <span className="text-sm text-[#3A6B4C] font-semibold capitalize">
          Decision recorded: {record.human_decision}
        </span>
        {record.human_reviewer && (
          <span className="text-xs text-[#8A8072] ml-1">by {record.human_reviewer}</span>
        )}
        {record.decided_at && (
          <span className="text-xs text-[#8A8072] ml-auto" data-numeric>
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
        className="sticky bottom-0 z-30 bg-[#FAF8F3]/95 backdrop-blur-sm border-t border-[#D6D0C4] px-6 py-3
                   flex items-center gap-3 flex-wrap"
        role="toolbar"
        aria-label="Decision actions"
      >
        <span className="text-xs text-[#8A8072] mr-2 hidden sm:inline">Awaiting underwriter decision:</span>

        {/* Approve — only show if agent recommends approve, or always available */}
        <button
          onClick={() => setModal("approve")}
          className="px-5 py-2 text-sm font-semibold rounded-sm border border-[#3A6B4C] text-[#3A6B4C]
                     hover:bg-[#3A6B4C] hover:text-white transition-colors
                     focus:outline-none focus:ring-2 focus:ring-[#3A6B4C] focus:ring-offset-1"
          aria-label="Approve application"
        >
          Approve
        </button>

        {/* Override — opens modal to pick different decision + mandatory reason */}
        <button
          onClick={() => setModal("override")}
          className="px-5 py-2 text-sm font-semibold rounded-sm border border-[#8C3B2E] text-[#8C3B2E]
                     hover:bg-[#8C3B2E] hover:text-white transition-colors
                     focus:outline-none focus:ring-2 focus:ring-[#8C3B2E] focus:ring-offset-1"
          aria-label="Override agent recommendation"
        >
          Override
        </button>

        {/* Request more info */}
        <button
          onClick={() => setModal("request_info")}
          className="px-5 py-2 text-sm font-semibold rounded-sm border border-[#C48A2A] text-[#C48A2A]
                     hover:bg-[#C48A2A] hover:text-white transition-colors
                     focus:outline-none focus:ring-2 focus:ring-[#C48A2A] focus:ring-offset-1"
          aria-label="Request additional information"
        >
          Request more info
        </button>

        <div className="ml-auto text-xs text-[#8A8072] hidden md:block">
          Agent recommends:{" "}
          <span className="font-semibold capitalize text-[#12213A]">
            {record.agent_recommendation}
          </span>
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
