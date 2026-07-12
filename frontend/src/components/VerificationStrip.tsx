/**
 * VerificationStrip — compact row of document-check icons + consistency flags.
 * Shown at the top of the Application Detail screen.
 *
 * Per UI_UX_DESIGN.md §3.2: "compact row of check icons — ID present ✓,
 * Pay stub present ✓, Bank statement present ✓/⚠, consistency flags if any"
 */

interface Props {
  missingDocs?: string[];
  consistencyFlags?: string[];
}

const KNOWN_DOCS: Array<{ id: string; label: string }> = [
  { id: "government_id",    label: "Gov ID" },
  { id: "pay_stub",         label: "Pay stub" },
  { id: "bank_statement",   label: "Bank stmt" },
  { id: "employment_letter", label: "Employ. letter" },
];

export default function VerificationStrip({ missingDocs = [], consistencyFlags = [] }: Props) {
  const missingSet = new Set(missingDocs.map((d) => d.toLowerCase().replace(/\s+/g, "_")));

  return (
    <div
      className="flex flex-wrap items-center gap-x-4 gap-y-1 py-2 px-3
                 border border-[#D6D0C4] rounded-sm bg-[#FAF8F3] text-sm"
      role="region"
      aria-label="Document verification status"
    >
      {/* Document checks */}
      {KNOWN_DOCS.map(({ id, label }) => {
        const missing = missingSet.has(id);
        return (
          <span
            key={id}
            className={`inline-flex items-center gap-1 ${missing ? "text-[#8C3B2E]" : "text-[#3A6B4C]"}`}
            aria-label={`${label}: ${missing ? "missing" : "present"}`}
          >
            {missing ? (
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                <circle cx="7" cy="7" r="6" stroke="currentColor" strokeWidth="1.5" />
                <path d="M4.5 4.5L9.5 9.5M9.5 4.5L4.5 9.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            ) : (
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                <circle cx="7" cy="7" r="6" stroke="currentColor" strokeWidth="1.5" />
                <path d="M4.5 7L6.5 9L9.5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            )}
            <span className="text-xs">{label}</span>
          </span>
        );
      })}

      {/* Consistency flags */}
      {consistencyFlags.length > 0 && (
        <>
          <span className="text-[#D6D0C4] select-none" aria-hidden="true">|</span>
          {consistencyFlags.map((flag, i) => (
            <span
              key={i}
              className="inline-flex items-center gap-1 text-[#C48A2A] text-xs"
              role="alert"
              aria-label={`Consistency flag: ${flag}`}
            >
              <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
                <path d="M6.5 1L12 11.5H1L6.5 1Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
                <path d="M6.5 5.5V8" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
                <circle cx="6.5" cy="9.5" r="0.6" fill="currentColor" />
              </svg>
              ⚠ {flag}
            </span>
          ))}
        </>
      )}

      {/* All clear */}
      {missingDocs.length === 0 && consistencyFlags.length === 0 && (
        <span className="text-[#3A6B4C] text-xs ml-auto">All documents verified, no flags</span>
      )}
    </div>
  );
}
