import sqlite3

conn = sqlite3.connect("backend/ai_job_search.db")
c = conn.cursor()

# Update InMobi (355)
c.execute("""
UPDATE company_career_sources 
SET ats_provider = 'greenhouse', ats_identifier = 'inmobi', verification_status = 'VERIFIED'
WHERE company_id = 355
""")
print("Updated InMobi ATS in company_career_sources:", c.rowcount)

# Verify
rows = c.execute("SELECT company_id, career_url, ats_provider, ats_identifier FROM company_career_sources WHERE ats_provider IS NOT NULL").fetchall()
print("All companies with active ATS:")
for r in rows:
    print(r)

conn.commit()
conn.close()

