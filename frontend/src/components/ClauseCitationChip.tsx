import { useState } from "react";
import type { ClauseCitation } from "../api/client";

interface Props {
  citation: ClauseCitation;
}

export default function ClauseCitationChip({ citation }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <span className="relative inline-block">
      <button
        className="inline-flex items-center px-1.5 py-0.5 rounded-sm text-2xs font-mono
                   bg-[#12213A]/8 text-[#12213A] border border-[#12213A]/20
                   hover:bg-[#12213A]/15 focus:outline-none focus:ring-1 focus:ring-[#C48A2A]
                   transition-colors cursor-pointer"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-label={`Policy clause ${citation.clause_id} — click to expand`}
      >
        [{citation.clause_id}]
      </button>

      {open && (
        <span
          role="tooltip"
          className="absolute z-20 left-0 top-full mt-1 w-72 bg-[#12213A] text-[#FAF8F3]
                     text-xs rounded-sm px-3 py-2 shadow-lg leading-relaxed"
        >
          <span className="block font-semibold mb-1 text-[#C48A2A]">{citation.clause_id}</span>
          <span className="block text-[#FAF8F3]/80 capitalize mb-1">Factor: {citation.factor.replace(/_/g, " ")}</span>
          {citation.clause_text}
          <button
            className="block mt-2 text-[#C48A2A] hover:underline focus:outline-none"
            onClick={() => setOpen(false)}
            aria-label="Close clause detail"
          >
            Close
          </button>
        </span>
      )}
    </span>
  );
}
