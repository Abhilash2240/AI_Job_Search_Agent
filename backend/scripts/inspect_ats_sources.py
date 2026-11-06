import sqlite3

conn = sqlite3.connect("backend/ai_job_search.db")
c = conn.cursor()

# Check sources with greenhouse or lever in URL
query = """
SELECT c.id, c.canonical_name, s.career_url, s.ats_provider, s.ats_identifier 
FROM companies c 
JOIN company_career_sources s ON c.id = s.company_id 
WHERE s.career_url LIKE '%greenhouse%' OR s.career_url LIKE '%lever%'
"""
rows = c.execute(query).fetchall()
print("Matches with greenhouse or lever in URL:", len(rows))
for r in rows:
    print(r)

# Check InMobi
inmobi = c.execute("SELECT c.id, c.canonical_name, s.career_url, s.ats_provider, s.ats_identifier FROM companies c JOIN company_career_sources s ON c.id = s.company_id WHERE c.id = 355").fetchall()
print("InMobi:", inmobi)

conn.close()

