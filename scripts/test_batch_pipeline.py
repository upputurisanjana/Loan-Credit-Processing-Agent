"""
Quick diagnostic: run extract + score on all batch fixtures and compare
expected band vs actual band.
"""
import sys, json, os, glob
sys.path.insert(0, '.')
os.environ.setdefault('POLICY_PATH', './policy/policy_v1.yaml')
os.environ.setdefault('DATABASE_URL', 'sqlite:///./audit.db')

from dotenv import load_dotenv
load_dotenv('.env')

import logging
logging.basicConfig(level=logging.WARNING)

from app.models.application import ApplicationRaw
from app.agent.nodes.extract import run_extract
from app.agent.nodes.score import run_score

results = {'approve': [], 'refer': [], 'decline': []}
mismatches = []
errors = []

for category in ['approve', 'decline']:
    pattern = f'tests/fixtures/batch/{category}/*/application.json'
    for path in sorted(glob.glob(pattern)):
        app_id = path.replace('\\', '/').split('/')[-2]
        try:
            with open(path) as f:
                data = json.load(f)
            raw = ApplicationRaw(**data)
            fields = run_extract(raw)
            sb = run_score(fields)
            result_band = sb.band
            results[result_band].append(app_id)
            status = 'OK' if result_band == category else 'MISMATCH'
            print(f'[{status}] {app_id}: expected={category} actual={result_band} '
                  f'composite={sb.composite_score:.4f} '
                  f'(dti={sb.dti_subscore:.2f} ch={sb.credit_history_subscore:.2f} inc={sb.income_stability_subscore:.2f})')
            if result_band != category:
                mismatches.append({
                    'app_id': app_id,
                    'expected': category,
                    'actual': result_band,
                    'composite': sb.composite_score,
                    'income': fields.income_monthly,
                    'debt': fields.debt_monthly,
                    'credit_history_years': fields.credit_history_years,
                    'credit_history_flags': fields.credit_history_flags,
                    'employment_months': fields.employment_months_current,
                })
        except Exception as e:
            errors.append(f'{app_id}: {e}')
            print(f'[ERROR] {app_id}: {e}')

# Also test the standard fixtures
print('\n--- Standard fixtures ---')
for fname, expected in [('clear_approve.json', 'approve'), ('borderline_refer.json', 'refer')]:
    path = f'tests/fixtures/{fname}'
    try:
        with open(path) as f:
            data = json.load(f)
        raw = ApplicationRaw(**data)
        fields = run_extract(raw)
        sb = run_score(fields)
        status = 'OK' if sb.band == expected else 'MISMATCH'
        print(f'[{status}] {fname}: expected={expected} actual={sb.band} composite={sb.composite_score:.4f}')
        print(f'         income={fields.income_monthly} debt={fields.debt_monthly} '
              f'history={fields.credit_history_years}y flags={fields.credit_history_flags} '
              f'months={fields.employment_months_current}')
    except Exception as e:
        print(f'[ERROR] {fname}: {e}')

print('\n=== SUMMARY ===')
print(f'Total mismatches: {len(mismatches)}')
if mismatches:
    print('Mismatched fixtures:')
    for m in mismatches:
        print(f"  {m['app_id']}: expected={m['expected']} got={m['actual']} "
              f"composite={m['composite']:.4f} "
              f"income={m['income']} debt={m['debt']} "
              f"history={m['credit_history_years']}y months={m['employment_months']}")
