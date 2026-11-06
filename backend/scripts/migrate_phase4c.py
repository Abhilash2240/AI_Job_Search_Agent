import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine, inspect, text
from db.database import Base
from models import candidate, source, job

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ai_job_search.db"))
engine = create_engine(f"sqlite:///{db_path}")

insp = inspect(engine)
if "jobs" in insp.get_table_names():
    with engine.connect() as conn:
        # Check row count
        count = conn.execute(text("SELECT COUNT(*) FROM jobs")).scalar()
        if count == 0:
            conn.execute(text("DROP TABLE jobs"))
            conn.commit()
            print("Dropped empty legacy jobs table for schema recreation.")

# Recreate tables defined in models
Base.metadata.create_all(engine)

insp_updated = inspect(engine)
print("Updated jobs columns:")
for col in insp_updated.get_columns("jobs"):
    print(f"  - {col['name']} ({col['type']})")

