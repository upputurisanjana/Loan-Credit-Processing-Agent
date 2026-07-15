import sqlite3
import shutil
from pathlib import Path

TARGET_IDS = ["APP-001", "APP-002"]

# ── Database removal ──────────────────────────────────────────────────────────
conn = sqlite3.connect("audit.db")

for app_id in TARGET_IDS:
    # Remove from decision_amendments first (FK child table)
    cur = conn.execute(
        "DELETE FROM decision_amendments WHERE original_application_id = ?", (app_id,)
    )
    print(f"Deleted {cur.rowcount} amendment row(s) for {app_id}")

    # Remove from decision_records
    cur = conn.execute(
        "DELETE FROM decision_records WHERE application_id = ?", (app_id,)
    )
    print(f"Deleted {cur.rowcount} decision record(s) for {app_id}")

conn.commit()

# Verify
remaining = conn.execute(
    "SELECT application_id FROM decision_records WHERE application_id IN ('APP-001','APP-002')"
).fetchall()
if remaining:
    print("WARNING: still in DB:", remaining)
else:
    print("DB clean - APP-001 and APP-002 fully removed")

conn.close()

# ── Uploaded files removal ────────────────────────────────────────────────────
uploads_root = Path("uploads")
for app_id in TARGET_IDS:
    app_dir = uploads_root / app_id
    if app_dir.exists():
        shutil.rmtree(app_dir)
        print(f"Removed uploads folder: {app_dir}")
    else:
        print(f"No uploads folder found for {app_id} (already clean)")

print("\nDone.")
