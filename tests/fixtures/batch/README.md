# Batch Test Fixtures — 20 Applicants

This folder contains realistic uploadable documents and application bodies for
20 test applicants (12 pass, 8 fail) used to verify the end-to-end pipeline:
document upload → LLM extraction → scoring → human-gate → reviewer PDF.

---

## Folder layout

```
tests/fixtures/batch/
  APP-B01/
    id.pdf              ← Identity document (Passport or Driving Licence)
    pay_stub.pdf        ← June 2026 payslip with monthly gross income
    bank_statement.pdf  ← Q2 2026 statement with income credits + debt payments
    application.json    ← ApplicationRaw body for POST /applications
  APP-B02/ ...
  README.md             ← this file
  README_generated.txt  ← auto-generated score summary table
```

---

## How to regenerate the PDFs

```powershell
.venv\Scripts\python scripts\generate_fixtures.py
```

---

## How to run the full batch submission

Make sure the server is running first:

```powershell
.\start.ps1          # starts backend + frontend
```

Then submit all 20 applicants, verify LLM extraction ran, and confirm
every reviewer PDF is accessible:

```powershell
.\scripts\batch_submit.ps1
```

The script prints a summary table showing, for each applicant:
- Whether documents uploaded successfully
- Whether the application was submitted
- Whether the LLM reviewed the documents (agent_recommendation populated)
- The score band the LLM/scorer assigned
- Whether the reviewer PDF report is accessible via GET /applications/{id}/pdf

---

## What the LLM reviews

The pipeline has two LLM nodes:

| Node      | What it does                                               |
|-----------|------------------------------------------------------------|
| EXTRACT   | Reads `extracted_text` from each uploaded document and extracts structured fields: `income_monthly`, `debt_monthly`, `credit_history_years`, `credit_history_flags`, `employment_months_current` |
| RECOMMEND | Receives the computed ScoreBreakdown and writes a plain-English rationale for the underwriter |

The SCORE node is pure Python — no LLM. The LLM only runs in EXTRACT and RECOMMEND.

---

## What the reviewer receives

`GET /applications/{id}/pdf` generates a PDF containing:
- Application summary (ID, status, policy version)
- Applicant details (name, address, loan amount)
- Score breakdown (composite score, DTI, credit history, income stability)
- Agent recommendation and full rationale from the LLM
- Adverse action notice draft (if applicable)
- Policy clauses cited
- List of every uploaded document with verification status

The reviewer can also download individual documents:
`GET /applications/{id}/documents/{filename}`

---

## Applicant catalogue

### Passing applicants (expect approve)

| APP-ID   | Name              | Income | Debt  | DTI   | CH-Yrs | Flags               | Emp-Mo | Why it passes                        |
|----------|-------------------|--------|-------|-------|--------|---------------------|--------|--------------------------------------|
| APP-B01  | Sarah Thompson    | 6 000  |   900 | 0.15  | 9.0    | none                | 100    | Excellent DTI, long clean history    |
| APP-B02  | James Patel       | 4 500  |   810 | 0.18  | 6.5    | none                |  84    | Good DTI, strong history             |
| APP-B03  | Priya Nair        | 9 000  | 1 350 | 0.15  | 8.0    | none                | 106    | High earner, very low DTI            |
| APP-B04  | Michael Harris    | 5 200  |   936 | 0.18  | 7.0    | late_payment_36m    | 135    | Old minor flag, still strong overall |
| APP-B05  | Rachel Green      | 5 800  | 1 044 | 0.18  | 5.5    | none                |  78    | Self-employed, solid financials      |
| APP-B06  | David Chen        | 7 200  | 1 296 | 0.18  | 10.0   | none                | 145    | Long NHS employment, perfect history |
| APP-B07  | Aisha Khan        | 4 200  |   840 | 0.20  | 5.0    | none                |  54    | Young professional, exactly 5yr hist |
| APP-B08  | Tom Lawson        | 5 500  |   770 | 0.14  | 8.0    | default_older       | 170    | Very low DTI offsets old default     |
| APP-B09  | Laura Simmons     | 3 200  |   960 | 0.30  | 3.5    | none                |  25    | Borderline — DTI excellent, 3.5yr    |
| APP-B10  | Nathan Okafor     | 3 800  | 1 254 | 0.33  | 6.0    | none                |  76    | Borderline — slightly above 30% DTI  |
| APP-B11  | Emily Watson      | 4 000  | 1 320 | 0.33  | 5.5    | late_payment_12m    |  65    | Recent late payment but DTI/hist OK  |
| APP-B12  | Oliver Pearce     | 3 100  |   961 | 0.31  | 3.0    | none                |  47    | Borderline — modest history, clean   |

### Failing applicants (expect decline)

| APP-ID   | Name              | Income | Debt  | DTI   | CH-Yrs | Flags                          | Emp-Mo | Why it fails                              |
|----------|-------------------|--------|-------|-------|--------|--------------------------------|--------|-------------------------------------------|
| APP-B13  | Gary Wilkins      | 2 200  | 1 760 | 0.80  | 4.0    | late_payment_12m               |   9    | DTI > 55% → DTI subscore 0; short employ  |
| APP-B14  | Sophie Turner     | 2 000  |   400 | 0.20  | 0.5    | no_history                     |  10    | Credit history < 2 yrs → CH subscore 0   |
| APP-B15  | Craig Foster      | 2 800  | 1 596 | 0.57  | 3.5    | default_36m                    |  42    | DTI > 55% + recent default → both 0      |
| APP-B16  | Chloe Evans       | 1 800  |   360 | 0.20  | 1.0    | no_history                     |   4    | CH < 2 yrs AND employment < 6 mo → both 0|
| APP-B17  | Barry Griffiths   | 3 200  | 1 760 | 0.55  | 5.0    | late_payment_12m, default_36m  |  15    | Borderline DTI + stacked flag penalties   |
| APP-B18  | Diane Hutchins    | 2 500  | 1 875 | 0.75  | 4.0    | default_36m, late_payment_12m  |  44    | Extremely high DTI, recent default        |
| APP-B19  | Ryan McGrath      | 1 900  |   950 | 0.50  | 1.5    | no_history                     |   6    | CH < 2 yrs → 0; employment just 6 mo     |
| APP-B20  | Karen Blackwood   | 2 600  | 1 430 | 0.55  | 2.5    | late_payment_12m               |  12    | DTI at limit + late payment kills CH sub  |

---

## Scoring formula reference

```
DTI ratio = monthly_debt / monthly_income
  <= 0.30  → DTI subscore 1.0
  <= 0.43  → linear interpolation 0.5–1.0
  <= 0.55  → linear interpolation 0.0–0.5
  >  0.55  → 0.0

Credit history:
  < 2 years           → 0.0  (hard zero, policy clause CH-01)
  2–5 years           → linear 0.0–1.0
  >= 5 years          → 1.0
  late_payment_12m    → -0.30
  default_36m/older   → -0.50

Employment stability:
  < 6 months          → 0.0
  6–24 months         → linear 0.0–1.0
  >= 24 months        → 1.0

Composite = 0.40 × DTI + 0.35 × CreditHistory + 0.25 × Employment
  >= 0.75  → approve
  >= 0.65  → refer
  <  0.65  → decline
```

---

## Manual single-applicant workflow

```powershell
# 1. Upload documents
$AppId = "APP-B01"
$base  = "http://localhost:8000"

Invoke-RestMethod -Method Post `
  -Uri "$base/applications/$AppId/documents" `
  -Form @{ files = @(Get-Item "tests\fixtures\batch\$AppId\id.pdf",
                            "tests\fixtures\batch\$AppId\pay_stub.pdf",
                            "tests\fixtures\batch\$AppId\bank_statement.pdf")
           doc_types = "id,pay_stub,bank_statement" }

# 2. Submit application
$body = Get-Content "tests\fixtures\batch\$AppId\application.json" -Raw
Invoke-RestMethod -Method Post -Uri "$base/applications" `
  -ContentType "application/json" -Body $body | ConvertTo-Json -Depth 10

# 3. Get status (LLM recommendation should be populated)
Invoke-RestMethod -Uri "$base/applications/$AppId" | ConvertTo-Json -Depth 10

# 4. Download reviewer PDF
Invoke-WebRequest -Uri "$base/applications/$AppId/pdf" `
  -OutFile "review_$AppId.pdf"
Start-Process "review_$AppId.pdf"

# 5. Approve / decline (human gate)
$decision = '{"human_decision":"approve","human_reviewer":"underwriter_1"}'
Invoke-RestMethod -Method Post -Uri "$base/applications/$AppId/decision" `
  -ContentType "application/json" -Body $decision | ConvertTo-Json -Depth 10
```
