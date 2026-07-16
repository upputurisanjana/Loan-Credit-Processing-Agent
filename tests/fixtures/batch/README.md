# Batch Test Fixtures — Grouped by Expected Outcome

20 applicants organised into three outcome groups.
Each folder contains: id.pdf, pay_stub.pdf, bank_statement.pdf, application.json

---

## approve/ — 12 applicants expected to score APPROVE (composite ≥ 0.75)

| Ref     | Name              | Income | Debt  | DTI  | CH-Yrs | Employment | Why it passes                         |
|---------|-------------------|--------|-------|------|--------|------------|---------------------------------------|
| APP-B01 | Sarah Thompson    | £6,000 |  £900 | 15%  |  9.0   | 100 months | Excellent DTI, long clean history     |
| APP-B02 | James Patel       | £4,500 |  £810 | 18%  |  6.5   |  84 months | Good DTI, strong history              |
| APP-B03 | Priya Nair        | £9,000 | £1350 | 15%  |  8.0   | 106 months | High earner, very low DTI             |
| APP-B04 | Michael Harris    | £5,200 |  £936 | 18%  |  7.0   | 135 months | Older late payment, still strong      |
| APP-B05 | Rachel Green      | £5,800 | £1044 | 18%  |  5.5   |  78 months | Self-employed, solid financials       |
| APP-B06 | David Chen        | £7,200 | £1296 | 18%  | 10.0   | 145 months | NHS employment, perfect history       |
| APP-B07 | Aisha Khan        | £4,200 |  £840 | 20%  |  5.0   |  54 months | Young professional, exactly 5yr hist  |
| APP-B08 | Tom Lawson        | £5,500 |  £770 | 14%  |  8.0   | 170 months | Low DTI offsets older default         |
| APP-B09 | Laura Simmons     | £3,200 |  £960 | 30%  |  3.5   |  25 months | DTI excellent, 3.5yr history          |
| APP-B10 | Nathan Okafor     | £3,800 | £1254 | 33%  |  6.0   |  76 months | Slightly above 30% DTI but clean      |
| APP-B11 | Emily Watson      | £4,000 | £1320 | 33%  |  5.5   |  65 months | Late payment 12m but DTI/hist OK      |
| APP-B12 | Oliver Pearce     | £3,100 |  £961 | 31%  |  3.0   |  47 months | Modest history, clean record          |

---

## refer/ — 0 applicants

No applicants in this batch land exactly in the REFER band (0.65–0.74).
APP-B09 through APP-B12 are borderline approves that an underwriter should
review carefully — they're close to the refer threshold.

---

## decline/ — 8 applicants expected to score DECLINE (composite < 0.65)

| Ref     | Name              | Income | Debt  | DTI  | CH-Yrs | Employment | Why it fails                              |
|---------|-------------------|--------|-------|------|--------|------------|-------------------------------------------|
| APP-B13 | Gary Wilkins      | £2,200 | £1760 | 80%  |  4.0   |   9 months | DTI > 55% → subscore 0; short employment  |
| APP-B14 | Sophie Turner     | £2,000 |  £400 | 20%  |  0.5   |  10 months | Credit history < 2 yrs → CH subscore 0    |
| APP-B15 | Craig Foster      | £2,800 | £1596 | 57%  |  3.5   |  42 months | DTI > 55% + recent default → both 0       |
| APP-B16 | Chloe Evans       | £1,800 |  £360 | 20%  |  1.0   |   4 months | CH < 2 yrs AND employment < 6 mo → both 0 |
| APP-B17 | Barry Griffiths   | £3,200 | £1760 | 55%  |  5.0   |  15 months | Borderline DTI + stacked flag penalties    |
| APP-B18 | Diane Hutchins    | £2,500 | £1875 | 75%  |  4.0   |  44 months | Extremely high DTI, recent default         |
| APP-B19 | Ryan McGrath      | £1,900 |  £950 | 50%  |  1.5   |   6 months | CH < 2 yrs → 0; employment borderline     |
| APP-B20 | Karen Blackwood   | £2,600 | £1430 | 55%  |  2.5   |  12 months | DTI at limit + late payment kills CH sub  |

---

## Scoring Formula (Policy v1.2)

```
DTI ratio = monthly_debt / monthly_income
  <= 0.30  → subscore 1.0
  <= 0.43  → linear 1.0 → 0.5
  <= 0.55  → linear 0.5 → 0.0
  >  0.55  → 0.0

Credit History:
  < 2 years  → 0.0 (hard zero)
  2–5 years  → linear 0.0 → 1.0
  >= 5 years → 1.0
  late_payment_12m → -0.30
  default_36m      → -0.50

Employment:
  < 6 months  → 0.0
  6–24 months → linear 0.0 → 1.0
  >= 24 months → 1.0

Composite = 0.40 × DTI + 0.35 × CreditHistory + 0.25 × Employment
  >= 0.75 → APPROVE
  >= 0.65 → REFER
  <  0.65 → DECLINE
```

---

## How to submit all 20 in one go

```powershell
.\scripts\batch_submit.ps1
```

## How to submit a single applicant manually

```powershell
$id   = "APP-B01"
$band = "approve"   # subfolder
$base = "http://localhost:8000"

# 1. Upload documents
$form = @{
  files = @(
    Get-Item "tests\fixtures\batch\$band\$id\id.pdf",
    Get-Item "tests\fixtures\batch\$band\$id\pay_stub.pdf",
    Get-Item "tests\fixtures\batch\$band\$id\bank_statement.pdf"
  )
  doc_types = "id,pay_stub,bank_statement"
}
Invoke-RestMethod -Method Post -Uri "$base/applications/$id/documents" -Form $form

# 2. Submit application
$body = Get-Content "tests\fixtures\batch\$band\$id\application.json" -Raw
Invoke-RestMethod -Method Post -Uri "$base/applications" -ContentType "application/json" -Body $body

# 3. Check status
Invoke-RestMethod -Uri "$base/applications/$id" | ConvertTo-Json -Depth 5

# 4. Download reviewer PDF
Invoke-WebRequest -Uri "$base/applications/$id/pdf" -OutFile "review_$id.pdf"
```
