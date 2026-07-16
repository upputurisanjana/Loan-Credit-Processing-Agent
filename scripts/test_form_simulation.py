"""
Form-simulation test: runs 3 candidates through the full pipeline
using only name, financials, credit/employment fields, and dummy doc files —
exactly what the Streamlit form submits after the fix.
No JSON fixtures used.
"""
import sys, os
sys.path.insert(0, '.')
os.environ.setdefault('POLICY_PATH', './policy/policy_v1.yaml')
os.environ.setdefault('DATABASE_URL', 'sqlite:///./audit.db')
from dotenv import load_dotenv
load_dotenv('.env')
import logging
logging.basicConfig(level=logging.WARNING)

from app.models.application import ApplicationRaw
from app.agent.graph import run_pipeline

CANDIDATES = [
    {
        "app_id":        "APP-FORM-A",
        "name":          "Alice Johnson",
        "address":       "12 Park Lane, London, W1K 1AA",
        "income":        5500.0,
        "debt":          800.0,
        "loan":          22000.0,
        "credit_years":  7.0,
        "emp_months":    48,
        "flag":          "none",
        "expected_band": "approve",
    },
    {
        "app_id":        "APP-FORM-B",
        "name":          "Robert Brown",
        "address":       "18 Oak Avenue, Manchester, M1 1AD",
        "income":        3200.0,
        "debt":          1350.0,
        "loan":          15000.0,
        "credit_years":  4.0,
        "emp_months":    24,
        "flag":          "none",
        "expected_band": "refer",
    },
    {
        "app_id":        "APP-FORM-C",
        "name":          "Gary Wilkins",
        "address":       "101 Poplar Street, Coventry, CV1 1AA",
        "income":        2200.0,
        "debt":          1760.0,
        "loan":          18000.0,
        "credit_years":  4.0,
        "emp_months":    9,
        "flag":          "late_payment_12m",
        "expected_band": "decline",
    },
]

print("=" * 60)
print("FORM-SIMULATION PIPELINE TEST")
print("(No JSON fixtures — pure name + numbers + documents)")
print("=" * 60)

all_passed = True

for c in CANDIDATES:
    name        = c["name"]
    income      = c["income"]
    debt        = c["debt"]
    flag        = c["flag"]
    credit_years = c["credit_years"]
    emp_months  = c["emp_months"]

    # Exactly what app.py now builds in the form submit handler
    ps_text = (
        f"PAYSLIP\n"
        f"Employee: {name}\n"
        f"Monthly Gross Income: {income:.2f}\n"
        f"Months in Current Role: {emp_months}\n"
    )
    bs_text = (
        f"BANK STATEMENT\n"
        f"Account Holder: {name}\n"
        f"Monthly Income Credits: {income:.2f}\n"
        f"Regular Debt Payments: {debt:.2f}\n"
        f"Credit History: {credit_years:.1f} years\n"
        f"Credit Flags: {flag}\n"
    )
    id_text = f"IDENTITY DOCUMENT\nName: {name}\nFile: id.pdf"

    raw = ApplicationRaw(
        application_id=c["app_id"],
        applicant_name=name,
        applicant_address=c["address"],
        stated_income=income,
        stated_monthly_debt=debt,
        loan_amount_requested=c["loan"],
        applicant_notes=None,
        documents=[
            {"doc_type": "id",             "file_path": "id.pdf",             "ocr_confidence": 0.95, "extracted_text": id_text},
            {"doc_type": "pay_stub",       "file_path": "pay_stub.pdf",       "ocr_confidence": 0.95, "extracted_text": ps_text},
            {"doc_type": "bank_statement", "file_path": "bank_statement.pdf", "ocr_confidence": 0.95, "extracted_text": bs_text},
        ],
    )

    result = run_pipeline(raw)
    if isinstance(result, dict):
        print(f"\n[ERROR] {c['app_id']}: pipeline returned dict — {result.get('status')}")
        all_passed = False
        continue

    sb       = result.score_breakdown
    rec      = result.agent_recommendation
    expected = c["expected_band"]
    passed   = rec == expected
    if not passed:
        all_passed = False

    status = "[PASS]" if passed else "[FAIL]"
    print(f"\n{status}  {c['app_id']} — {name}")
    print(f"  Expected  : {expected.upper()}")
    print(f"  Got       : {rec.upper()}  (composite {sb.composite_score:.4f} = {round(sb.composite_score*100)}/100)")
    print(f"  Breakdown : DTI {sb.dti_subscore:.2f}  |  Credit {sb.credit_history_subscore:.2f}  |  Income Stab {sb.income_stability_subscore:.2f}")
    print(f"  DTI ratio : {sb.dti_ratio*100:.1f}%")
    print(f"  Rationale : {result.rationale[:160]}...")

print()
print("=" * 60)
print(f"RESULT: {'ALL PASSED' if all_passed else 'SOME FAILED'}")
print("=" * 60)
