import sqlite3
import json

conn = sqlite3.connect('backend/ai_job_search.db')
cur = conn.cursor()

cur.execute("PRAGMA table_info(candidates)")
cols = [c[1] for c in cur.fetchall()]
print("CANDIDATES COLUMNS:", cols)

cur.execute("SELECT id, filename, profile_json FROM candidates WHERE id IN (20, 21)")
rows = cur.fetchall()
for cid, fname, pjson in rows:
    pdata = json.loads(pjson) if pjson else {}
    name = pdata.get('personal', {}).get('name')
    email = pdata.get('personal', {}).get('email')
    print(f"CANDIDATE {cid}: filename={fname}, name={name}, email={email}")

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cur.fetchall()]
print("\nALL DATABASE TABLES:")
for t in tables:
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    print(f"  {t}: {cur.fetchone()[0]}")
