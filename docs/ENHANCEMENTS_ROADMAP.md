# ENHANCEMENTS_ROADMAP.md — Loan / Credit Application Processing Agent

What to build after Day 8, once the MVP passes all test scenarios. Ordered by priority — do these roughly in order, since later items depend on earlier ones being solid.

---

## Phase 1 — Harden the MVP (do first, low effort / high value)

1. **Real OCR confidence thresholds** — tune `pytesseract` confidence cutoffs against a small labeled set of real scanned documents rather than a guessed threshold; add a manual "re-scan" action in the UI when confidence is low.
2. **Structured logging + request IDs** — every API call and agent node execution gets a correlation ID threaded through logs, so a support engineer can reconstruct a single application's path across services.
3. **Retry/backoff on GitHub Models calls** — wrap the client in exponential backoff for 429s; surface a clear "model temporarily unavailable, application held" state rather than a raw error in the UI.
4. **Automated migration from SQLite → Postgres** — write the schema so a real deployment isn't blocked on outgrowing SQLite; keep the append-only pattern identical in both.
5. **CI pipeline** — GitHub Actions running `pytest` on every push, blocking merge if any of the 10 scenarios fail.

## Phase 2 — Governance depth

6. **Adverse-action reason generator, regulator-grade** — move from a demo draft to output that matches actual ECOA/Reg B (or local equivalent) formatting requirements, reviewed against real compliance templates rather than a general LLM draft.
7. **Batch fairness dashboard** — beyond the single-file identity-swap, run a rolling approval-rate parity report across a batch of synthetic applications varying only in protected-class proxy fields; alert if disparity crosses a set threshold (e.g., 80% rule / four-fifths rule as a starting heuristic, not a legal conclusion).
8. **Policy change impact simulation** — before publishing a new policy version, re-run it against the last N decided applications and show how many bands would flip — lets Head of Credit Ops see blast radius before going live.
9. **Full immutable audit export for regulators** — a one-click export of a date range's decision records + traces in a format suitable for handing to an examiner, with a checksum/signature so tampering is detectable.

## Phase 3 — Model & scoring sophistication

10. **Challenger-model disagreement analytics** — track disagreement rate over time by model pair; if a challenger model consistently disagrees on a particular clause type, that's a signal to review the clause wording, not just the model.
11. **Affordability stress-testing** — simulate the applicant's DTI under a rate shock (e.g., +2% interest) or income shock (e.g., -15%) and surface both the base and stressed bands side by side — informational, not a scoring input, to avoid quietly tightening policy through the back door.
12. **Counterfactual generator upgrade** — move from a single "what would need to change" line to a small set of realistic alternative paths (e.g., "co-signer," "lower loan amount," "12 more months of history"), still clearly framed as informational only.
13. **Second-look queue for near-miss declines** — composite scores just below the decline cutoff get automatically queued for a senior underwriter's optional second look, separate from the standard REFER queue.

## Phase 4 — Product & scale

14. **Multi-tenant policy sets** — support more than one lending product (e.g., personal loan vs. auto loan) with separate policy YAMLs, selectable at intake.
15. **Applicant-facing status page** — a read-only, identity-verified view where the applicant can see their application status (not the score breakdown) and upload missing documents directly, closing the loop on `HOLD_FOR_DOCUMENT` without a phone call.
16. **Real bureau integration** — replace synthetic bureau data with a real credit bureau API integration behind a feature flag, with the same Pydantic contracts so nothing downstream changes.
17. **SSO + role-based access** — replace the demo role toggle with real authentication (underwriter, senior underwriter, compliance officer, admin), with the audit log recording actual authenticated identities.
18. **Localization** — if used beyond one jurisdiction, externalize policy clause text and adverse-action notice templates per-locale, since lending regulations are jurisdiction-specific.

## Phase 5 — Longer-term / research

19. **Active learning from overrides** — when underwriters consistently override in the same direction for a case pattern, surface that pattern to Head of Credit Ops as a candidate policy revision — humans still decide whether to change the policy, the system only surfaces the signal.
20. **Formal fairness audit partnership** — bring in an external fairness/compliance review of the scoring methodology once real (not synthetic) data volume exists, rather than relying solely on the identity-swap structural test.

---

## What NOT to do, even later
- Do not let the LLM ever compute the score directly, even as an optimization — the deterministic scorer is a governance feature, not a performance shortcut to remove.
- Do not automate the final decision at any phase — "licensed human makes the final call" is a permanent architectural constraint for this product category, not an MVP limitation to graduate out of.
