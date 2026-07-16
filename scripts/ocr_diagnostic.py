"""
OCR diagnostic: read actual uploaded PDFs and show what text comes out.
"""
import sys, os
sys.path.insert(0, '.')
os.environ.setdefault('POLICY_PATH', './policy/policy_v1.yaml')
from dotenv import load_dotenv
load_dotenv('.env')
import logging
logging.basicConfig(level=logging.WARNING)
from app.tools.ocr import ocr_file
from pathlib import Path

upload_root = Path('uploads')
for app_dir in sorted(upload_root.iterdir()):
    app_id = app_dir.name
    if app_id.startswith('.'):
        continue
    print(f'\n=== {app_id} ===')
    for fname in ['pay_stub.pdf', 'bank_statement.pdf']:
        fpath = app_dir / fname
        if not fpath.exists():
            print(f'  {fname}: NOT FOUND')
            continue
        text, conf = ocr_file(app_id, fname)
        if text:
            print(f'  {fname} (conf={conf}):')
            for line in text.strip().splitlines():
                print(f'    {line}')
        else:
            print(f'  {fname}: empty OCR result (conf={conf})')
