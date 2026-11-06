import sqlite3
import json

conn = sqlite3.connect("backend/ai_job_search.db")
c = conn.cursor()

print("--- CANDIDATE 3 MATCHES AUDIT ---")
query = """
SELECT 
    m.id, 
    j.company_name, 
    j.title, 
    m.composite_score, 
    m.semantic_score,
    m.skill_score,
    m.role_score,
    m.is_relevant, 
    m.role_family, 
    m.eligibility_status,
    m.rejection_reasons
FROM candidate_job_matches m
JOIN canonical_jobs j ON m.canonical_job_id = j.id
WHERE m.candidate_id = 3
ORDER BY m.is_relevant DESC, m.composite_score DESC
"""

rows = c.execute(query).fetchall()
print(f"Total Matches in Database: {len(rows)}")

relevant = [r for r in rows if r[7] == 1]
irrelevant = [r for r in rows if r[7] == 0]

print(f"\nRELEVANT JOBS ({len(relevant)}):")
for r in relevant:
    print(f"  • {r[3]:.1f}% | {r[1]:8} — {r[2]:40} | Fam: {r[8]:22} | Elig: {r[9]}")

print(f"\nIRRELEVANT JOBS EXCLUDED ({len(irrelevant)} total, showing first 12):")
for r in irrelevant[:12]:
    rej = json.loads(r[10]) if r[10] else []
    print(f"  • EXCLUDED | {r[1]:8} — {r[2]:40} | Fam: {r[8]:22} | Rej: {rej[:1]}")

# Top match score check
eligible_relevant = [r for r in relevant if r[9] in ("ELIGIBLE", "ELIGIBLE_WITH_CONDITIONS")]
if eligible_relevant:
    best = eligible_relevant[0]
    print(f"\nBEST ELIGIBLE RELEVANT JOB FOR DASHBOARD: {best[1]} — {best[2]} (Score: {best[3]:.1f}%, Status: {best[9]})")

conn.close()

