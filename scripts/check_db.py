import sqlite3

conn = sqlite3.connect("audit.db")
conn.row_factory = sqlite3.Row

# Show tables
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("Tables:", [t[0] for t in tables])

for table in [t[0] for t in tables]:
    cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
    print(f"\nColumns in {table}:", [c[1] for c in cols])
    rows = conn.execute(f"SELECT * FROM {table}").fetchall()
    for r in rows:
        d = dict(r)
        print(" ", {k: v for k, v in d.items() if k in ("application_id", "applicant_name", "created_at", "agent_recommendation")})

conn.close()
