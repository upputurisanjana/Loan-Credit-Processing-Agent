"""
Add credit_history_years, credit_history_flags, employment_months_current
to all batch fixture application.json files.
Values are sourced from the APPLICANTS table in generate_fixtures.py.
"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the authoritative data from generate_fixtures
from scripts.generate_fixtures import APPLICANTS
from pathlib import Path

ROOT = Path(__file__).parent.parent / "tests" / "fixtures" / "batch"

updated = 0
for app in APPLICANTS:
    app_id = app["id"]
    # Find the JSON in approve/ or decline/
    matches = list(ROOT.rglob(f"{app_id}/application.json"))
    if not matches:
        print(f"NOT FOUND: {app_id}")
        continue
    path = matches[0]
    with open(path) as f:
        data = json.load(f)
    data["credit_history_years"]       = app["credit_history_years"]
    data["credit_history_flags"]       = app["credit_flags"]
    data["employment_months_current"]  = app["employment_months"]
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  {app_id}: history={app['credit_history_years']}y  months={app['employment_months']}  flags={app['credit_flags']}")
    updated += 1

print(f"\nDone — {updated} files updated.")
