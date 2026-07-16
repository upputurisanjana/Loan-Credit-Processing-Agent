"""
Full pipeline trace for a single fixture.
Usage: python scripts/trace_pipeline.py <path_to_application.json>
"""
import sys, json, os
sys.path.insert(0, '.')
os.environ.setdefault('POLICY_PATH', './policy/policy_v1.yaml')
os.environ.setdefault('DATABASE_URL', 'sqlite:///./audit.db')

from dotenv import load_dotenv
load_dotenv('.env')

import logging
logging.basicConfig(level=logging.INFO, format='%(name)s %(levelname)s %(message)s')

from app.models.application import ApplicationRaw
from app.agent.graph import run_pipeline

fixture = sys.argv[1] if len(sys.argv) > 1 else 'tests/fixtures/batch/approve/APP-B05/application.json'

with open(fixture) as f:
    data = json.load(f)

raw = ApplicationRaw(**data)
print(f"\n{'='*60}")
print(f"Running full pipeline for: {raw.application_id}")
print(f"{'='*60}\n")

result = run_pipeline(raw)

if isinstance(result, dict):
    print(f"\nPipeline result (dict): status={result.get('status')}")
    print(json.dumps(result, indent=2, default=str))
else:
    # DecisionRecord
    dr = result
    print(f"\n{'='*60}")
    print(f"PIPELINE RESULT")
    print(f"{'='*60}")
    print(f"  agent_recommendation : {dr.agent_recommendation}")
    print(f"  composite_score      : {dr.score_breakdown.composite_score:.4f}")
    print(f"  band                 : {dr.score_breakdown.band}")
    print(f"  dti_sub              : {dr.score_breakdown.dti_subscore:.4f}")
    print(f"  ch_sub               : {dr.score_breakdown.credit_history_subscore:.4f}")
    print(f"  inc_sub              : {dr.score_breakdown.income_stability_subscore:.4f}")
    print(f"  fairness.match       : {dr.fairness_check.match}")
    print(f"  fairness.llm_flag    : {dr.fairness_check.llm_review_flag}")
    print(f"  fairness.llm_note    : {dr.fairness_check.llm_review_note}")
    if dr.challenger_result:
        print(f"  challenger primary   : {dr.challenger_result.primary_band}")
        print(f"  challenger band      : {dr.challenger_result.challenger_band}")
        print(f"  challenger agrees    : {dr.challenger_result.bands_agree}")
    print(f"\nRATIONALE:\n{dr.rationale}")
    print(f"\nPIPELINE TRACE:")
    for step in dr.pipeline_trace:
        node = step.pop('node', '?')
        ts = step.pop('timestamp', '')
        print(f"  [{node}] {step}")
