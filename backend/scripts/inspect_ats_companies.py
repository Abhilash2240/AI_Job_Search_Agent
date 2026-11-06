import sqlite3

conn = sqlite3.connect("backend/ai_job_search.db")
cur = conn.cursor()

cur.execute("SELECT id, company_id, career_url, ats_provider, ats_identifier FROM company_career_sources WHERE company_id IN (295, 156, 355, 480)")
for r in cur.fetchall():
    print(r)

conn.close()
