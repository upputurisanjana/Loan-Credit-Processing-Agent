"""
scripts/generate_fixtures.py
============================
Generate realistic uploadable PDF documents (ID, pay stub, bank statement)
and matching application JSON bodies for 20 test applicants.

Output layout
-------------
tests/fixtures/batch/
  APP-B01/
    id.pdf
    pay_stub.pdf
    bank_statement.pdf
    application.json
  APP-B02/
    ...
  README_generated.txt   ← quick summary of who passed/failed

Run
---
  .venv\Scripts\python scripts\generate_fixtures.py

Dependencies: fpdf2 (already in .venv)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Applicant catalogue
# ---------------------------------------------------------------------------
# Scoring formula (policy_v1.yaml):
#   DTI ratio = debt / income
#     <= 0.30 → DTI subscore 1.0
#     <= 0.43 → linear 0.5–1.0
#     <= 0.55 → linear 0.0–0.5
#     >  0.55 → 0.0
#   Credit history (years):
#     < 2    → 0.0
#     2–5    → linear 0.0–1.0
#     >= 5   → 1.0
#     -0.30 per late_payment_12m, -0.50 per default
#   Employment months:
#     < 6    → 0.0
#     6–24   → linear 0.0–1.0
#     >= 24  → 1.0
#   Composite = 0.40×DTI + 0.35×CH + 0.25×INC
#   Approve >= 0.75 | Refer >= 0.65 | Decline < 0.65

APPLICANTS = [
    # ── PASSING APPLICANTS (APP-B01 .. APP-B12) ────────────────────────────
    # APP-B01  Clear approve — excellent DTI, long history, stable employment
    {
        "id": "APP-B01",
        "name": "Sarah Thompson",
        "dob": "1983-06-22",
        "address": "14 Willow Close, Bristol, BS1 4LT",
        "employer": "Bristol City Council",
        "employment_start": "2018-03-01",
        "employment_months": 100,
        "income": 6000.00,
        "debt": 900.00,          # DTI 0.15 → 1.0
        "credit_history_years": 9.0,
        "credit_flags": [],       # CH 1.0
        "loan_requested": 25000.00,
        "notes": "Home renovation project.",
        "expected_band": "approve",
        "doc_id_type": "Passport",
    },
    # APP-B02  Clear approve — mid income, good DTI, 6yr history
    {
        "id": "APP-B02",
        "name": "James Patel",
        "dob": "1979-11-05",
        "address": "88 Oak Road, Leeds, LS1 3DQ",
        "employer": "Northern Rail Ltd",
        "employment_start": "2019-07-01",
        "employment_months": 84,
        "income": 4500.00,
        "debt": 810.00,          # DTI 0.18 → 1.0
        "credit_history_years": 6.5,
        "credit_flags": [],
        "loan_requested": 18000.00,
        "notes": "Purchasing a new vehicle.",
        "expected_band": "approve",
        "doc_id_type": "Driving Licence",
    },
    # APP-B03  Clear approve — high earner, very low DTI
    {
        "id": "APP-B03",
        "name": "Priya Nair",
        "dob": "1988-02-14",
        "address": "22 Kensington Gardens, London, W8 4PX",
        "employer": "FinTech Solutions plc",
        "employment_start": "2017-09-01",
        "employment_months": 106,
        "income": 9000.00,
        "debt": 1350.00,         # DTI 0.15 → 1.0
        "credit_history_years": 8.0,
        "credit_flags": [],
        "loan_requested": 40000.00,
        "notes": "Consolidating existing loans.",
        "expected_band": "approve",
        "doc_id_type": "Passport",
    },
    # APP-B04  Clear approve — older late payment (36m) but still strong
    {
        "id": "APP-B04",
        "name": "Michael Harris",
        "dob": "1975-09-30",
        "address": "5 Elm Street, Birmingham, B1 2AA",
        "employer": "Midlands Engineering Ltd",
        "employment_start": "2015-04-01",
        "employment_months": 135,
        "income": 5200.00,
        "debt": 936.00,          # DTI 0.18 → 1.0
        "credit_history_years": 7.0,
        "credit_flags": ["late_payment_36m"],  # CH = 1.0 - 0.15 = 0.85
        "loan_requested": 22000.00,
        "notes": "Business equipment purchase.",
        "expected_band": "approve",
        "doc_id_type": "Passport",
    },
    # APP-B05  Clear approve — self-employed, solid financials
    {
        "id": "APP-B05",
        "name": "Rachel Green",
        "dob": "1990-04-18",
        "address": "31 Birch Lane, Edinburgh, EH1 1YZ",
        "employer": "Self-employed (Freelance Designer)",
        "employment_start": "2020-01-01",
        "employment_months": 78,
        "income": 5800.00,
        "debt": 1044.00,         # DTI 0.18 → 1.0
        "credit_history_years": 5.5,
        "credit_flags": [],
        "loan_requested": 20000.00,
        "notes": "Studio equipment upgrade.",
        "expected_band": "approve",
        "doc_id_type": "Passport",
    },
    # APP-B06  Clear approve — long employment, no flags
    {
        "id": "APP-B06",
        "name": "David Chen",
        "dob": "1982-12-01",
        "address": "67 Maple Avenue, Manchester, M2 5NP",
        "employer": "Manchester NHS Trust",
        "employment_start": "2014-06-01",
        "employment_months": 145,
        "income": 7200.00,
        "debt": 1296.00,         # DTI 0.18 → 1.0
        "credit_history_years": 10.0,
        "credit_flags": [],
        "loan_requested": 30000.00,
        "notes": "Home extension.",
        "expected_band": "approve",
        "doc_id_type": "Driving Licence",
    },
    # APP-B07  Clear approve — younger professional, 5yr history, clean record
    {
        "id": "APP-B07",
        "name": "Aisha Khan",
        "dob": "1994-07-11",
        "address": "9 Cedar Court, Sheffield, S1 4AB",
        "employer": "Digital Media Corp",
        "employment_start": "2022-01-01",
        "employment_months": 54,
        "income": 4200.00,
        "debt": 840.00,          # DTI 0.20 → 1.0
        "credit_history_years": 5.0,
        "credit_flags": [],
        "loan_requested": 15000.00,
        "notes": "Postgraduate course funding.",
        "expected_band": "approve",
        "doc_id_type": "Passport",
    },
    # APP-B08  Clear approve — older default (>3yr) but DTI excellent, long history
    {
        "id": "APP-B08",
        "name": "Tom Lawson",
        "dob": "1977-03-25",
        "address": "42 Pine Road, Cardiff, CF10 1AB",
        "employer": "Cardiff Logistics plc",
        "employment_start": "2012-05-01",
        "employment_months": 170,
        "income": 5500.00,
        "debt": 770.00,          # DTI 0.14 → 1.0
        "credit_history_years": 8.0,
        "credit_flags": ["default_older"],   # CH = 1.0 - 0.50 = 0.50
        "loan_requested": 20000.00,           # composite ~ 0.40*1.0 + 0.35*0.50 + 0.25*1.0 = 0.825 → approve
        "notes": "Debt was resolved in 2021.",
        "expected_band": "approve",
        "doc_id_type": "Driving Licence",
    },
    # APP-B09  Borderline refer — acceptable DTI, short-ish history, clean
    {
        "id": "APP-B09",
        "name": "Laura Simmons",
        "dob": "1993-08-07",
        "address": "77 Ash Grove, Nottingham, NG1 2BC",
        "employer": "East Midlands College",
        "employment_start": "2023-06-01",
        "employment_months": 25,
        "income": 3200.00,
        "debt": 960.00,          # DTI 0.30 → 1.0
        "credit_history_years": 3.5,         # CH ~ (3.5-2)/(5-2)=0.50
        "credit_flags": [],                  # composite ~ 0.40*1.0 + 0.35*0.50 + 0.25*1.0 = 0.775 → approve
        "loan_requested": 10000.00,
        "notes": "Car purchase.",
        "expected_band": "approve",
        "doc_id_type": "Passport",
    },
    # APP-B10  Borderline refer — slightly high DTI, good history
    {
        "id": "APP-B10",
        "name": "Nathan Okafor",
        "dob": "1986-01-19",
        "address": "55 Hawthorn Drive, Liverpool, L1 8JQ",
        "employer": "Merseyside Transport",
        "employment_start": "2020-03-01",
        "employment_months": 76,
        "income": 3800.00,
        "debt": 1254.00,         # DTI 0.33 → ~0.96 subscore
        "credit_history_years": 6.0,
        "credit_flags": [],                  # composite ~ 0.40*0.96 + 0.35*1.0 + 0.25*1.0 = 0.984... wait
        "loan_requested": 14000.00,
        "notes": "Consolidating credit card debt.",
        "expected_band": "approve",
        "doc_id_type": "Driving Licence",
    },
    # APP-B11  Borderline refer — decent DTI, late payment 12m, good employment
    {
        "id": "APP-B11",
        "name": "Emily Watson",
        "dob": "1989-05-03",
        "address": "18 Sycamore Street, Norwich, NR1 3CD",
        "employer": "Anglian Water",
        "employment_start": "2021-02-01",
        "employment_months": 65,
        "income": 4000.00,
        "debt": 1320.00,         # DTI 0.33 → ~0.96
        "credit_history_years": 5.5,
        "credit_flags": ["late_payment_12m"],  # CH = 1.0 - 0.30 = 0.70
        "loan_requested": 12000.00,            # composite ~ 0.40*0.96 + 0.35*0.70 + 0.25*1.0 = 0.879 → approve
        "notes": "Missed a payment during redundancy, since resolved.",
        "expected_band": "approve",
        "doc_id_type": "Passport",
    },
    # APP-B12  Borderline refer — moderate DTI, 3yr history, steady employment
    {
        "id": "APP-B12",
        "name": "Oliver Pearce",
        "dob": "1995-10-22",
        "address": "3 Chestnut Way, Exeter, EX1 2EF",
        "employer": "Devon County Council",
        "employment_start": "2022-08-01",
        "employment_months": 47,
        "income": 3100.00,
        "debt": 961.00,          # DTI 0.31 → ~0.99
        "credit_history_years": 3.0,         # CH = (3-2)/(5-2) = 0.333
        "credit_flags": [],                  # composite ~ 0.40*0.99 + 0.35*0.333 + 0.25*0.875 = 0.729 → approve
        "loan_requested": 8000.00,
        "notes": "First loan application.",
        "expected_band": "approve",
        "doc_id_type": "Driving Licence",
    },

    # ── FAILING APPLICANTS (APP-B13 .. APP-B20) ───────────────────────────
    # APP-B13  Decline — very high DTI (>55%), short employment
    {
        "id": "APP-B13",
        "name": "Gary Wilkins",
        "dob": "1985-07-14",
        "address": "101 Poplar Street, Coventry, CV1 1AA",
        "employer": "Temp Agency Work",
        "employment_start": "2025-10-01",
        "employment_months": 9,
        "income": 2200.00,
        "debt": 1760.00,         # DTI 0.80 → 0.0
        "credit_history_years": 4.0,
        "credit_flags": ["late_payment_12m"],
        "loan_requested": 18000.00,          # composite ~ 0.40*0.0 + 0.35*(0.667-0.30) + 0.25*0.375 = 0.222 → decline
        "notes": "Recent job change.",
        "expected_band": "decline",
        "doc_id_type": "Passport",
    },
    # APP-B14  Decline — no credit history at all
    {
        "id": "APP-B14",
        "name": "Sophie Turner",
        "dob": "2000-03-09",
        "address": "44 Rose Lane, Brighton, BN1 1TT",
        "employer": "Retail Co Ltd",
        "employment_start": "2024-09-01",
        "employment_months": 10,
        "income": 2000.00,
        "debt": 400.00,          # DTI 0.20 → 1.0
        "credit_history_years": 0.5,         # CH = 0.0 (< 2 years)
        "credit_flags": ["no_history"],
        "loan_requested": 7000.00,           # composite ~ 0.40*1.0 + 0.35*0.0 + 0.25*0.222 = 0.456 → decline
        "notes": "First time borrower.",
        "expected_band": "decline",
        "doc_id_type": "Passport",
    },
    # APP-B15  Decline — recent default + high DTI
    {
        "id": "APP-B15",
        "name": "Craig Foster",
        "dob": "1980-11-17",
        "address": "29 Beech Road, Stoke-on-Trent, ST1 5GH",
        "employer": "Staffordshire Deliveries",
        "employment_start": "2023-01-01",
        "employment_months": 42,
        "income": 2800.00,
        "debt": 1596.00,         # DTI 0.57 → 0.0 (> 0.55)
        "credit_history_years": 3.5,
        "credit_flags": ["default_36m"],     # CH = 0.50 - 0.50 = 0.0
        "loan_requested": 12000.00,          # composite ~ 0.40*0.0 + 0.35*0.0 + 0.25*1.0 = 0.25 → decline
        "notes": "Financial difficulties resolved.",
        "expected_band": "decline",
        "doc_id_type": "Driving Licence",
    },
    # APP-B16  Decline — too little employment (4 months), no credit history
    {
        "id": "APP-B16",
        "name": "Chloe Evans",
        "dob": "1999-06-30",
        "address": "12 Foxglove Court, Leicester, LE1 4WX",
        "employer": "Leicester Cafes Ltd",
        "employment_start": "2026-03-01",
        "employment_months": 4,
        "income": 1800.00,
        "debt": 360.00,          # DTI 0.20 → 1.0
        "credit_history_years": 1.0,         # CH = 0.0 (< 2 years)
        "credit_flags": ["no_history"],
        "loan_requested": 5000.00,           # composite ~ 0.40*1.0 + 0.35*0.0 + 0.25*0.0 = 0.40 → decline
        "notes": "Student transitioning to work.",
        "expected_band": "decline",
        "doc_id_type": "Passport",
    },
    # APP-B17  Decline — multiple flags: late payment 12m + default 36m + poor DTI
    {
        "id": "APP-B17",
        "name": "Barry Griffiths",
        "dob": "1974-09-02",
        "address": "8 Laurel Road, Swansea, SA1 3KL",
        "employer": "Port Talbot Steel",
        "employment_start": "2024-04-01",
        "employment_months": 15,
        "income": 3200.00,
        "debt": 1760.00,         # DTI 0.55 → ~0.0
        "credit_history_years": 5.0,
        "credit_flags": ["late_payment_12m", "default_36m"],  # CH = 1.0 - 0.30 - 0.50 = 0.20
        "loan_requested": 15000.00,          # composite ~ 0.40*0.0 + 0.35*0.20 + 0.25*0.375 = 0.164 → decline
        "notes": "Trying to recover from redundancy.",
        "expected_band": "decline",
        "doc_id_type": "Driving Licence",
    },
    # APP-B18  Decline — extremely high debt, recent default
    {
        "id": "APP-B18",
        "name": "Diane Hutchins",
        "dob": "1972-02-28",
        "address": "63 Thornton Avenue, Hull, HU1 2PQ",
        "employer": "Humber Fishing Co.",
        "employment_start": "2022-11-01",
        "employment_months": 44,
        "income": 2500.00,
        "debt": 1875.00,         # DTI 0.75 → 0.0
        "credit_history_years": 4.0,
        "credit_flags": ["default_36m", "late_payment_12m"],
        "loan_requested": 10000.00,          # composite ~ 0.40*0.0 + 0.35*0.0 + 0.25*1.0 = 0.25 → decline
        "notes": "Struggling with existing debts.",
        "expected_band": "decline",
        "doc_id_type": "Passport",
    },
    # APP-B19  Decline — short employment, near-zero credit history, high DTI
    {
        "id": "APP-B19",
        "name": "Ryan McGrath",
        "dob": "2001-12-15",
        "address": "5 Ivy Lane, Belfast, BT1 1AB",
        "employer": "Belfast Hospitality",
        "employment_start": "2026-01-01",
        "employment_months": 6,
        "income": 1900.00,
        "debt": 950.00,          # DTI 0.50 → ~0.166
        "credit_history_years": 1.5,         # CH = 0.0 (< 2 years)
        "credit_flags": ["no_history"],
        "loan_requested": 4000.00,           # composite ~ 0.40*0.166 + 0.35*0.0 + 0.25*0.0 = 0.066 → decline
        "notes": "Saving for a motorbike.",
        "expected_band": "decline",
        "doc_id_type": "Driving Licence",
    },
    # APP-B20  Decline — income/debt mismatch, late payment 12m, minimal history
    {
        "id": "APP-B20",
        "name": "Karen Blackwood",
        "dob": "1991-08-08",
        "address": "19 Magnolia Drive, Plymouth, PL1 3RS",
        "employer": "Plymouth Retail Group",
        "employment_start": "2025-07-01",
        "employment_months": 12,
        "income": 2600.00,
        "debt": 1430.00,         # DTI 0.55 → ~0.0
        "credit_history_years": 2.5,
        "credit_flags": ["late_payment_12m"],  # CH = (2.5-2)/(5-2) - 0.30 = 0.167 - 0.30 → 0.0 (floored)
        "loan_requested": 9000.00,             # composite ~ 0.40*0.0 + 0.35*0.0 + 0.25*0.25 = 0.063 → decline
        "notes": "Card payments were missed while changing jobs.",
        "expected_band": "decline",
        "doc_id_type": "Passport",
    },
]



# ---------------------------------------------------------------------------
# PDF helpers
# ---------------------------------------------------------------------------

def _safe(text: str) -> str:
    """Replace characters that fpdf core fonts cannot encode."""
    return (
        text.replace("\u2014", "-")   # em-dash -> hyphen
            .replace("\u2013", "-")   # en-dash -> hyphen
            .replace("\u2019", "'")   # right single quote
            .replace("\u2018", "'")   # left single quote
            .replace("\u201c", '"')
            .replace("\u201d", '"')
    )


def _header(pdf, title: str):
    """Dark-blue header bar."""
    pdf.set_fill_color(18, 33, 58)
    pdf.set_text_color(255, 255, 255)
    pdf.rect(0, 0, 210, 28, "F")
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_xy(10, 8)
    pdf.cell(0, 12, _safe(title), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.set_y(34)


def _section(pdf, title: str):
    pdf.set_fill_color(230, 236, 248)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(30, 60, 120)
    pdf.cell(0, 7, _safe(f"  {title}"), new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(1)


def _row(pdf, label: str, value: str):
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_x(12)
    pdf.cell(55, 6, _safe(label + ":"), new_x="RIGHT", new_y="TOP")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, _safe(str(value)), new_x="LMARGIN", new_y="NEXT")


def _divider(pdf):
    pdf.set_draw_color(180, 180, 180)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)


def make_id_pdf(app: dict) -> bytes:
    """Generate a realistic identity document PDF."""
    from fpdf import FPDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    _header(pdf, f"IDENTITY DOCUMENT — {app['doc_id_type'].upper()}")

    _section(pdf, "Official Identity Record")
    pdf.ln(2)
    _row(pdf, "Document Type", app["doc_id_type"])
    _row(pdf, "Document Number", f"GBR{app['id'].replace('-', '')[:8]:>08}")
    _row(pdf, "Full Name", app["name"])
    _row(pdf, "Date of Birth", app["dob"])
    _row(pdf, "Nationality", "British")
    _row(pdf, "Issuing Authority", "His Majesty's Passport Office / DVLA")
    _row(pdf, "Issue Date", "2022-01-15")
    _row(pdf, "Expiry Date", "2032-01-14")
    _row(pdf, "Address", app["address"])
    _divider(pdf)

    pdf.ln(4)
    _section(pdf, "Verification Watermark")
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.set_x(12)
    pdf.multi_cell(
        0, 5,
        _safe(
            "This document is an official specimen for testing purposes only. "
            "Issued under the Credit Decisioning Agent fixture generation programme. "
            f"Reference: {app['id']}-ID-2026"
        ),
    )
    pdf.set_text_color(0, 0, 0)
    return bytes(pdf.output())


def make_pay_stub_pdf(app: dict) -> bytes:
    """Generate a realistic pay stub PDF."""
    from fpdf import FPDF
    import math

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    _header(pdf, "PAYSLIP — JUNE 2026")

    income = app["income"]
    tax = round(income * 0.20, 2)
    ni  = round(income * 0.12, 2)
    net = round(income - tax - ni, 2)
    emp_start = app["employment_start"]

    _section(pdf, "Employer Details")
    _row(pdf, "Employer", app["employer"])
    _row(pdf, "Pay Period", "01 June 2026 – 30 June 2026")
    _row(pdf, "Payment Date", "30 June 2026")
    _divider(pdf)

    _section(pdf, "Employee Details")
    _row(pdf, "Employee Name", app["name"])
    _row(pdf, "Employee ID", f"EMP{app['id'].replace('-', '')}")
    _row(pdf, "Employment Start", emp_start)
    _row(pdf, "Months in Role", str(app["employment_months"]))
    _divider(pdf)

    _section(pdf, "Earnings")
    _row(pdf, "Monthly Gross Income", f"£{income:,.2f}")
    _row(pdf, "Basic Salary", f"£{income:,.2f}")
    _divider(pdf)

    _section(pdf, "Deductions")
    _row(pdf, "Income Tax (20%)", f"£{tax:,.2f}")
    _row(pdf, "National Insurance (12%)", f"£{ni:,.2f}")
    _divider(pdf)

    _section(pdf, "Net Pay")
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_x(12)
    pdf.set_text_color(18, 33, 58)
    pdf.cell(0, 8, _safe(f"Net Pay This Period:  GBP{net:,.2f}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)

    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(150, 150, 150)
    pdf.set_x(12)
    pdf.cell(0, 5, _safe(f"Document reference: {app['id']}-PAYSTUB-JUN2026"), new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


def make_bank_statement_pdf(app: dict) -> bytes:
    """Generate a realistic 3-month bank statement PDF."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    _header(pdf, "BANK STATEMENT — Q2 2026")

    income = app["income"]
    debt   = app["debt"]
    # Net approx = income * 0.68 (after 32% tax/NI)
    net_income = round(income * 0.68, 2)
    balance_start = round(net_income * 2.5, 2)
    balance_end   = round(balance_start + net_income * 3 - debt * 3, 2)

    _section(pdf, "Account Details")
    _row(pdf, "Account Holder", app["name"])
    _row(pdf, "Sort Code", "40-47-84")
    _row(pdf, "Account Number", f"****{abs(hash(app['id'])) % 10000:04d}")
    _row(pdf, "Statement Period", "01 April 2026 - 30 June 2026")
    _divider(pdf)

    _section(pdf, "Summary")
    _row(pdf, "Opening Balance (01 Apr)", f"GBP{balance_start:,.2f}")
    _row(pdf, "Total Credits (3 months)", f"GBP{net_income * 3:,.2f}")
    _row(pdf, "Total Debits (3 months)",  f"GBP{debt * 3:,.2f}")
    _row(pdf, "Closing Balance (30 Jun)", f"GBP{max(balance_end, 0):,.2f}")
    _divider(pdf)

    _section(pdf, "Monthly Income Credits")
    months = [("April 2026", "30 Apr 2026"), ("May 2026", "31 May 2026"), ("June 2026", "30 Jun 2026")]
    for month_label, pay_date in months:
        _row(pdf, f"Salary Credit ({month_label})", f"GBP{net_income:,.2f}  {pay_date}  {app['employer'][:30]}")
    _divider(pdf)

    _section(pdf, "Monthly Debt Payments")
    _row(pdf, "Regular Debt Payments", f"GBP{debt:,.2f} per month")
    _row(pdf, "Debt-to-Income (stated)", f"{(debt/income)*100:.1f}%")

    # Credit history note for LLM extraction
    pdf.ln(4)
    _section(pdf, "Credit Reference Note")
    flags = app.get("credit_flags", [])
    ch_years = app.get("credit_history_years", 0)
    flag_str = ", ".join(flags) if flags else "none"
    _row(pdf, "Credit History (years)", str(ch_years))
    _row(pdf, "Credit Flags on Record", flag_str)

    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(150, 150, 150)
    pdf.set_x(12)
    pdf.cell(0, 5, _safe(f"Document reference: {app['id']}-BANKSTMT-Q2-2026"), new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


# ---------------------------------------------------------------------------
# Application JSON builder
# ---------------------------------------------------------------------------

def make_application_json(app: dict, base_dir: Path) -> dict:
    """Build the ApplicationRaw JSON body for POST /applications."""
    app_id = app["id"]
    return {
        "application_id": app_id,
        "submitted_at": "2026-07-15T09:00:00Z",
        "applicant_name": app["name"],
        "applicant_address": app["address"],
        "stated_income": app["income"],
        "stated_monthly_debt": app["debt"],
        "loan_amount_requested": app["loan_requested"],
        "applicant_notes": app.get("notes", ""),
        "documents": [
            {
                "doc_type": "id",
                "file_path": f"uploads/{app_id}/id.pdf",
                "ocr_confidence": 0.97,
                "extracted_text": (
                    f"{app['doc_id_type'].upper()}\n"
                    f"Name: {app['name']}\n"
                    f"Date of Birth: {app['dob']}\n"
                    f"Nationality: British"
                ),
            },
            {
                "doc_type": "pay_stub",
                "file_path": f"uploads/{app_id}/pay_stub.pdf",
                "ocr_confidence": 0.96,
                "extracted_text": (
                    f"PAYSLIP - June 2026\n"
                    f"Employee: {app['name']}\n"
                    f"Employer: {app['employer']}\n"
                    f"Monthly Gross Income: {app['income']:.2f}\n"
                    f"Employment Start: {app['employment_start']}\n"
                    f"Months in Current Role: {app['employment_months']}"
                ),
            },
            {
                "doc_type": "bank_statement",
                "file_path": f"uploads/{app_id}/bank_statement.pdf",
                "ocr_confidence": 0.95,
                "extracted_text": (
                    f"Account Holder: {app['name']}\n"
                    f"Statement Period: April-June 2026\n"
                    f"Monthly Income Credits: {app['income'] * 0.68:.2f}\n"
                    f"Regular Debt Payments: {app['debt']:.2f}\n"
                    f"Credit History: {app['credit_history_years']} years\n"
                    f"Credit Flags: {', '.join(app['credit_flags']) if app['credit_flags'] else 'none'}"
                ),
            },
        ],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    output_root = Path(__file__).parent.parent / "tests" / "fixtures" / "batch"
    output_root.mkdir(parents=True, exist_ok=True)

    summary_lines = [
        "# Generated Fixture Summary",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        f"{'APP-ID':<10} {'NAME':<22} {'INCOME':>8} {'DEBT':>8} {'DTI':>6} "
        f"{'CH-YR':>6} {'FLAGS':<28} {'EMP-MO':>7} {'EXPECTED':<10}",
        "-" * 115,
    ]

    for app in APPLICANTS:
        app_id = app["id"]
        app_dir = output_root / app_id
        app_dir.mkdir(exist_ok=True)

        # --- PDFs ---
        (app_dir / "id.pdf").write_bytes(make_id_pdf(app))
        (app_dir / "pay_stub.pdf").write_bytes(make_pay_stub_pdf(app))
        (app_dir / "bank_statement.pdf").write_bytes(make_bank_statement_pdf(app))

        # --- application.json ---
        app_json = make_application_json(app, app_dir)
        (app_dir / "application.json").write_text(
            json.dumps(app_json, indent=2), encoding="utf-8"
        )

        dti = app["debt"] / app["income"]
        flags_str = ",".join(app["credit_flags"]) if app["credit_flags"] else "-"
        summary_lines.append(
            f"{app_id:<10} {app['name']:<22} {app['income']:>8.0f} {app['debt']:>8.0f} "
            f"{dti:>6.2f} {app['credit_history_years']:>6.1f} {flags_str:<28} "
            f"{app['employment_months']:>7} {app['expected_band']:<10}"
        )
        print(f"  [OK]  {app_id}  {app['name']:<22}  -> {app['expected_band']}")

    (output_root / "README_generated.txt").write_text(
        "\n".join(summary_lines), encoding="utf-8"
    )
    print(f"\nAll files written to: {output_root}")


if __name__ == "__main__":
    main()
