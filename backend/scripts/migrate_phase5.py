# backend/scripts/migrate_phase5.py
"""Migration script to create Phase 5 tables and columns in SQLite database."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.database import init, engine
from sqlalchemy import text


async def main():
    print("[1/2] Initializing database and creating Phase 5 tables...")
    await init()
    
    async with engine.connect() as conn:
        print("[2/2] Checking created tables...")
        result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
        tables = [row[0] for row in result.fetchall()]
        print(f"  Existing tables: {tables}")
        assert "canonical_jobs" in tables, "canonical_jobs table missing!"
        assert "canonical_job_sources" in tables, "canonical_job_sources table missing!"
        assert "duplicate_review_groups" in tables, "duplicate_review_groups table missing!"
        
        # Verify columns on jobs
        res_jobs = await conn.execute(text("PRAGMA table_info(jobs);"))
        job_columns = [row[1] for row in res_jobs.fetchall()]
        print(f"  Jobs columns: {job_columns}")
        assert "canonical_job_id" in job_columns, "canonical_job_id column missing!"
        assert "is_canonical_primary" in job_columns, "is_canonical_primary column missing!"
        assert "dedup_status" in job_columns, "dedup_status column missing!"

    print("Phase 5 database migration completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())

