# backend/scripts/migrate_relevance_schema.py
import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ai_job_search.db")
conn = sqlite3.connect(db_path)
c = conn.cursor()

cols = [r[1] for r in c.execute("PRAGMA table_info(candidate_job_matches)").fetchall()]
print("Current columns:", cols)

if "is_relevant" not in cols:
    c.execute("ALTER TABLE candidate_job_matches ADD COLUMN is_relevant BOOLEAN DEFAULT 1")
    print("Added is_relevant")

if "role_family" not in cols:
    c.execute("ALTER TABLE candidate_job_matches ADD COLUMN role_family VARCHAR(100) DEFAULT 'SOFTWARE_ENGINEERING'")
    print("Added role_family")

if "relevance_score" not in cols:
    c.execute("ALTER TABLE candidate_job_matches ADD COLUMN relevance_score FLOAT DEFAULT 1.0")
    print("Added relevance_score")

if "rejection_reasons" not in cols:
    c.execute("ALTER TABLE candidate_job_matches ADD COLUMN rejection_reasons TEXT")
    print("Added rejection_reasons")

conn.commit()
conn.close()
print("Migration completed successfully.")

