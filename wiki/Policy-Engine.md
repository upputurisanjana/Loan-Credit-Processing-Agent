# Policy Engine

The scoring engine is **pure Python** — zero LLM imports. Same inputs always produce the same output, making it deterministic, unit-testable, and audit-reproducible.

---

## Policy File

Active policy: `policy/policy_v1.yaml`

```yaml
version: "v1.2"
effective_date: "2026-01-01"

weights:
  dti: 0.40
  credit_history: 0.35
  income_stability: 0.25

bands:
  approve_min: 0.75    # composite >= 0.75 → APPROVE
  refer_min: 0.65      # composite >= 0.65 → REFER, else DECLINE
```

Changes to weights/thresholds in this file take effect on the next application run — no code change required. Every decision record stores the `policy_version` string so decisions remain reproducible against the policy that was live at decisioning time.

---

## Scoring Formula

```
composite_score = dti_subscore × 0.40
                + credit_history_subscore × 0.35
                + income_stability_subscore × 0.25
```

Each sub-score is a float in [0.0, 1.0].

---

## DTI Sub-Score

**Input:** `dti_ratio = debt_monthly / income_monthly`

| DTI Range | Sub-Score | Clause |
|-----------|-----------|--------|
| ≤ 30% | 1.0 (excellent) | DTI-02 |
| 30%–43% | Linear interpolation 1.0 → 0.5 | DTI-01 |
| 43%–55% | Linear interpolation 0.5 → 0.0 | DTI-01 |
| > 55% | 0.0 | DTI-01 |

**Policy clauses:**
- **DTI-01:** DTI must not exceed 43% for automatic approval consideration
- **DTI-02:** DTI at or below 30% receives maximum weighting

---

## Credit History Sub-Score

**Inputs:** `credit_history_years`, `credit_history_flags`

| Condition | Effect | Clause |
|-----------|--------|--------|
| < 2 years | Hard zero (0.0) | CH-01 |
| 2–5 years | Linear interpolation 0.0 → 1.0 | CH-01 |
| ≥ 5 years | Base = 1.0 | CH-01 |
| `late_payment_12m` in flags | Deduct 0.30 | CH-02 |
| `late_payment_36m` in flags | Deduct 0.15 | CH-02 |
| `default_36m` or `default_older` in flags | Deduct 0.50 | CH-03 |

Final: `max(0.0, base - deductions)`

**Policy clauses:**
- **CH-01:** Minimum 2 years of credit history required
- **CH-02:** Late payments in last 12 months reduce sub-score proportionally
- **CH-03:** Any recorded default applies additional 0.50 deduction

---

## Income Stability Sub-Score

**Input:** `employment_months_current`

| Employment Length | Sub-Score | Clause |
|-------------------|-----------|--------|
| < 6 months | 0.0 | INC-01 |
| 6–24 months | Linear interpolation 0.0 → 1.0 | INC-01 |
| ≥ 24 months | 1.0 | INC-02 |

**Policy clauses:**
- **INC-01:** Minimum 6 months in current employment required
- **INC-02:** 24+ months continuous employment receives maximum sub-score

---

## Band Thresholds

| Composite Score | Band | Action |
|-----------------|------|--------|
| ≥ 0.75 | **approve** | Agent recommends approval; underwriter confirms |
| 0.65–0.75 | **refer** | Agent recommends referral; mandatory human review |
| < 0.65 | **decline** | Agent recommends decline; adverse action notice drafted |

---

## Worked Example

**Applicant:** Income £5,000/mo, Debt £900/mo, 9 years credit history, no flags, 100 months employment.

```
DTI ratio = 900 / 5000 = 0.18
DTI sub-score = 1.0 (≤ 30%)

Credit history = 9 years
Credit history sub-score = 1.0 (≥ 5 years, no penalties)

Employment = 100 months
Income stability sub-score = 1.0 (≥ 24 months)

Composite = 1.0 × 0.40 + 1.0 × 0.35 + 1.0 × 0.25 = 1.0
Band = APPROVE (≥ 0.75)

Clauses cited: DTI-02, CH-01, INC-02
```

---

## Clause Citations

Every clause that is triggered during scoring is attached to the `ScoreBreakdown` as a `ClauseCitation`:

```python
class ClauseCitation(BaseModel):
    clause_id: str       # e.g. "DTI-01"
    clause_text: str     # Full text from policy YAML
    factor: str          # "dti" | "credit_history" | "income_stability"
```

These citations are used by the RECOMMEND node to compose the rationale, and are displayed in the UI as clickable chips that expand the full clause text.

---

## Changing the Policy

1. Edit `policy/policy_v1.yaml`
2. Update the `version` string (e.g., `"v1.3"`)
3. Restart the server (or clear the `@lru_cache` on `_load_policy`)
4. All new applications will use the new policy
5. Existing decision records retain their original `policy_version` — audit trail intact

**No code changes needed** — the engine reads thresholds and weights from YAML at runtime.

---

## Determinism Guarantee

The scoring function `run_score()` in `app/agent/nodes/score.py`:
- Contains **zero LLM imports**
- Uses only Python standard library + PyYAML
- Is pure arithmetic against the policy config
- Is verified by `test_score_is_deterministic` (100 repeated calls, bit-for-bit identical output)
