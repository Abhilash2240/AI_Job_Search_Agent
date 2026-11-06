import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine, inspect, text
from db.database import Base
from models import source

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ai_job_search.db"))
engine = create_engine(f"sqlite:///{db_path}")

# Create tables defined in models (including discovered_jobs)
Base.metadata.create_all(engine)

# Add missing columns to company_career_sources if any
insp = inspect(engine)
existing_cols = {c["name"] for c in insp.get_columns("company_career_sources")}

with engine.connect() as conn:
    if "ats_provider" not in existing_cols:
        conn.execute(text("ALTER TABLE company_career_sources ADD COLUMN ats_provider VARCHAR(100)"))
        print("Added ats_provider column")
    if "ats_identifier" not in existing_cols:
        conn.execute(text("ALTER TABLE company_career_sources ADD COLUMN ats_identifier VARCHAR(255)"))
        print("Added ats_identifier column")
    conn.commit()

insp_updated = inspect(engine)
print("Tables:", insp_updated.get_table_names())
print("discovered_jobs columns:", [c["name"] for c in insp_updated.get_columns("discovered_jobs")])
print("company_career_sources columns:", [c["name"] for c in insp_updated.get_columns("company_career_sources")])

