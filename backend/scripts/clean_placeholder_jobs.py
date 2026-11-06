import sqlite3

conn = sqlite3.connect('backend/ai_job_search.db')
c = conn.cursor()

c.execute("SELECT id, canonical_job_id, title, canonical_application_url FROM canonical_jobs WHERE canonical_job_id LIKE 'CANON-FC-%'")
rows = c.fetchall()
print(f"Found {len(rows)} placeholder jobs:")
for r in rows:
    print(r)

if rows:
    ids = [r[0] for r in rows]
    c.execute(f"DELETE FROM candidate_job_matches WHERE canonical_job_id IN ({','.join(map(str, ids))})")
    c.execute(f"DELETE FROM job_embeddings WHERE canonical_job_id IN ({','.join(map(str, ids))})")
    c.execute(f"DELETE FROM canonical_jobs WHERE id IN ({','.join(map(str, ids))})")
    c.execute("DELETE FROM discovered_jobs WHERE external_job_id LIKE 'CANON-FC-%'")
    conn.commit()
    print(f"Cleaned up {len(rows)} placeholder jobs from all tables.")

conn.close()

