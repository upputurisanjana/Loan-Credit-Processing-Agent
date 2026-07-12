# UI_UX_DESIGN.md — Loan / Credit Application Processing Agent

Goal: **clean, easy to navigate, unique** — not a generic admin-panel template. The sample interface in the workshop deck is "illustrative, not a required design" — this spec deliberately goes further and gives it a distinct visual identity, since a credit-ops tool lives or dies on how fast an underwriter can find the one number that matters.

---

## 1. Design language

**Concept: "Ledger, not dashboard."** Most AI-tool UIs default to a generic SaaS dashboard look (card grids, purple gradients, floating shadows everywhere). This one should feel like a precision instrument for a regulated financial workflow — closer to a well-typeset audit ledger or an underwriting terminal than a consumer app. That's the differentiator against the other five submissions of this same project.

- **Palette**: deep ink navy (`#12213A`) as primary, warm off-white paper background (`#FAF8F3`) rather than pure white, a single confident accent — amber/gold (`#C48A2A`) — used *only* for the thing that needs a human's attention (pending gate, flagged fairness mismatch). Status colors are restrained: approve = muted forest green (`#3A6B4C`), refer = the amber accent, decline = muted brick red (`#8C3B2E`). No neon, no gradient buttons.
- **Typography**: a serif or slab-serif for numbers and headings (e.g., Source Serif Pro / Lora) to reinforce the "ledger/document of record" feel, paired with a clean grotesk (Inter) for UI chrome and body text. Tabular figures (`font-variant-numeric: tabular-nums`) everywhere money/scores appear, so columns of numbers align.
- **Density**: information-dense but never cluttered — underwriters process many files a day; whitespace should separate *sections*, not pad every element.
- **Motion**: minimal, purposeful only — a score bar fills once on load, a state transition (REFER → decision made) gets a single subtle checkmark animation. No decorative motion.

---

## 2. Screen inventory

1. **Case Queue** (home)
2. **Application Detail / Decision Workspace** (the core screen)
3. **Score Breakdown Panel** (embedded in Detail, also a standalone drill-down)
4. **Fairness & Challenger Panel** (embedded in Detail)
5. **Human Gate / Decision Modal**
6. **Adverse Action Notice Editor** (only appears for DECLINE path)
7. **Audit Trail / Full Trace Viewer**
8. **Policy Version History** (Admin)

---

## 3. Screen-by-screen spec

### 3.1 Case Queue (home)
- Left: a slim vertical nav — Queue, Audit, Policy (admin only), not a heavy sidebar.
- Main: a table, ledger-styled (thin hairline rows, no zebra striping, tabular numerals), columns: `Applicant (masked by default)` · `Requested` · `Composite Score` (mini horizontal bar, colored by band) · `Band` (pill) · `Age` (time in queue, red-tinted past SLA) · `Status`.
- **Oldest-REFER-first** default sort, with a toggle for "Needs fairness review" (surfaces scenario-4-type flags) and "Challenger disagreement" filters as chips above the table, not a buried filter drawer.
- Row click → Application Detail.
- Top-right: applicant identity is masked (`A. ******`) in the queue by default, with a "reveal identity" toggle that requires a reason (logged) — reinforces the identity-blind ethos visually, not just in the backend.

### 3.2 Application Detail / Decision Workspace
This is the main screen — a single scroll, structured top to bottom in the order an underwriter actually reasons:

1. **Header bar**: application ID, submitted date, requested amount, current status pill, policy version badge (e.g., "Policy v1.2").
2. **Verification strip**: compact row of check icons — ID present ✓, Pay stub present ✓, Bank statement present ✓/⚠, consistency flags if any, shown inline (e.g., "⚠ stated income differs from pay stub by 8%").
3. **Score Breakdown Panel** (see 3.3) — the visual centerpiece.
4. **Recommendation card**: large, quiet typography — "Agent recommends: **REFER**" with the composite score, and 2–3 sentence rationale directly underneath, each clause reference as a small inline citation chip (`[DTI-01]`) that expands the clause text on hover/tap.
5. **Fairness & Challenger Panel** (see 3.4).
6. **Counterfactual box**: "What would change this" — e.g., "DTI would need to fall from 48% → 43% to reach REFER→APPROVE," styled as a quiet aside, not a promise.
7. **Human Gate action bar** (sticky at the bottom of the viewport while scrolling this screen): `Approve` (green outline) · `Override` (opens modal, reason required) · `Request more info` (returns to HOLD) — always visible, always the last thing the eye needs.

### 3.3 Score Breakdown Panel
- Three horizontal stacked bars (DTI, Credit History, Income Stability), each showing sub-score, weight, and contribution to composite, using a single accent hue with varying fill — not three different colors (keeps focus on the composite, not a rainbow chart).
- Composite score shown as a large number with a thin threshold ruler beneath it marking approve/refer/decline cutoffs, and a marker showing exactly where this application landed — an underwriter should see "how close to the line" at a glance.
- Every sub-score row has a small "view clause" link that opens the exact policy text in a side drawer (not a new page — keeps context).

### 3.4 Fairness & Challenger Panel
- Two small side-by-side cards:
  - **Fairness**: "Identity-masked re-score: MATCH ✓" (green) or a hard-stop red banner "MISMATCH — do not proceed without review" if it fails — this is the one place the UI should visually interrupt, since it's a real governance failure.
  - **Challenger**: shows primary vs. challenger band; if they disagree, a clear "Models disagree — REFER enforced" note, non-dismissible until acknowledged.

### 3.5 Human Gate / Decision Modal
- Triggered by Approve/Override/Request-info buttons.
- **Approve**: single confirm, no reason needed (agrees with recommendation).
- **Override**: reason field is **required** (cannot submit empty), free text, minimum ~20 characters enforced client-side with a gentle inline hint, not a blocking error until they try to submit.
- **Request more info**: select missing/unclear item from a checklist (auto-populated from `VerifyResult.missing_docs` and `consistency_flags`), optional note.
- Confirming any of these shows a one-line "This will be recorded permanently in the audit trail" notice — reinforces immutability without being alarmist.

### 3.6 Adverse Action Notice Editor (DECLINE only)
- Appears as a distinct screen/tab once DECLINE is confirmed.
- Left: the drafted notice (editable rich text) with each specific reason auto-linked back to the score factor that produced it.
- Right: a locked "must include" checklist (regulatory reason count, contact info, right-to-dispute language) so the underwriter can see nothing required was silently removed if they edit.
- `Approve & Queue for Send` button — sending itself can be mocked/stubbed for the demo (no real email/postal integration needed), but the approval step must be real.

### 3.7 Audit Trail / Full Trace Viewer
- A vertical timeline, one entry per agent node execution (`VERIFY`, `EXTRACT`, `SCORE`, `FAIRNESS`, `CHALLENGER`, `RECOMMEND`, `HUMAN_GATE`, `PERSIST`), each expandable to show its exact input/output JSON.
- Read-only, monospace for the JSON, ledger-style timestamps in the left gutter.
- Export button: download this application's full trace + decision record as JSON (for the audit-pass-rate KPI).

### 3.8 Policy Version History (Admin)
- Simple diff view between policy YAML versions (which weight/threshold changed, when, by whom) — reinforces that policy changes are visible and versioned, not silent.

---

## 4. Component list (for build order)

1. `StatusPill` (approve/refer/decline/hold, consistent colors app-wide)
2. `ScoreBar` (single-factor bar with label, value, weight)
3. `CompositeScoreGauge` (threshold ruler + marker)
4. `ClauseCitationChip` (hover/tap expand)
5. `QueueTable` (sortable, filterable, masked-identity toggle)
6. `VerificationStrip`
7. `FairnessCard` / `ChallengerCard`
8. `DecisionActionBar` (sticky)
9. `DecisionModal` (approve/override/request-info variants)
10. `TraceTimeline`
11. `NoticeEditor`
12. `PolicyDiffView`

Build these as standalone, prop-driven components first (Storybook-style, even without Storybook) — this lets each of the 6 individual submissions look meaningfully different even against the same backend contracts, and makes the UI reviewable independent of the agent being fully wired.

---

## 5. Accessibility & responsiveness

- All status information conveyed by color also has a text label and/or icon (never color-only).
- Full keyboard navigation through the Case Queue and Decision Workspace; the Decision Modal traps focus correctly and returns focus on close.
- Minimum contrast ratio 4.5:1 for body text against the paper background.
- Responsive down to tablet width (underwriters may review on a tablet); the Decision Workspace stacks the Score/Fairness panels vertically below ~900px rather than side-by-side.
