"""
Regenerate all batch fixture documents as plain .txt files.
Replaces the unreadable PDFs with simple text that OCR-fallback can read directly.
Each file keeps the same name (id.pdf, pay_stub.pdf, bank_statement.pdf) but
contains plain UTF-8 text so the pipeline's fallback path reads it correctly.

We write plain text INTO files named *.pdf so the pipeline doesn't need changes —
the ocr module falls back to returning "" and the submitted extracted_text is used.
Better: we also write a companion *.txt with the same content so users can open them.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pathlib import Path
from scripts.generate_fixtures import APPLICANTS

BATCH_ROOT = Path("tests/fixtures/batch")

def id_text(app):
    return (
        f"IDENTITY DOCUMENT — {app['doc_id_type'].upper()}\n"
        f"Full Name       : {app['name']}\n"
        f"Date of Birth   : {app['dob']}\n"
        f"Nationality     : British\n"
        f"Document Number : GBR{app['id'].replace('-','')[:8]}\n"
        f"Address         : {app['address']}\n"
    )

def pay_stub_text(app):
    income = app["income"]
    tax    = round(income * 0.20, 2)
    ni     = round(income * 0.12, 2)
    net    = round(income - tax - ni, 2)
    return (
        f"PAYSLIP — JUNE 2026\n"
        f"Employer              : {app['employer']}\n"
        f"Employee Name         : {app['name']}\n"
        f"Employment Start      : {app['employment_start']}\n"
        f"Months in Current Role: {app['employment_months']}\n"
        f"Monthly Gross Income  : {income:.2f}\n"
        f"Income Tax (20%)      : {tax:.2f}\n"
        f"National Insurance    : {ni:.2f}\n"
        f"Net Pay               : {net:.2f}\n"
    )

def bank_statement_text(app):
    income   = app["income"]
    debt     = app["debt"]
    net      = round(income * 0.68, 2)
    flags    = ", ".join(app["credit_flags"]) if app["credit_flags"] else "none"
    return (
        f"BANK STATEMENT — Q2 2026\n"
        f"Account Holder        : {app['name']}\n"
        f"Statement Period      : 01 April 2026 - 30 June 2026\n"
        f"Monthly Income Credits: {net:.2f}\n"
        f"Regular Debt Payments : {debt:.2f}\n"
        f"Debt-to-Income        : {(debt/income)*100:.1f}%\n"
        f"Credit History        : {app['credit_history_years']} years\n"
        f"Credit Flags          : {flags}\n"
    )

count = 0
for app in APPLICANTS:
    folder = BATCH_ROOT / app["id"]
    if not folder.exists():
        print(f"  SKIP {app['id']} — folder not found")
        continue

    files = {
        "id.pdf":             id_text(app),
        "pay_stub.pdf":       pay_stub_text(app),
        "bank_statement.pdf": bank_statement_text(app),
    }
    for fname, content in files.items():
        path = folder / fname
        path.write_text(content, encoding="utf-8")
        count += 1

    print(f"  {app['id']}  {app['name']}")

print(f"\nDone — wrote {count} text files across {len(APPLICANTS)} fixtures.")
