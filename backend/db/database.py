import os
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_FILE = os.path.join(BACKEND_DIR, "ai_job_search.db").replace("\\", "/")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{DEFAULT_DB_FILE}")

engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False}
)

# Async session factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
)

Base = declarative_base()

from sqlalchemy import text

async def init() -> None:
    # Import models to ensure they are registered with Base.metadata
    from models import (
        candidate,
        job,
        source,
        canonical_job,
        job_embedding,
        candidate_job_match,
        saved_job,
        application,
        pipeline_execution,
        user_preferences,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # Self-healing lightweight schema migration for existing SQLite DBs
        def migrate_schema(sync_conn):
            try:
                res = sync_conn.execute(text("PRAGMA table_info(candidates);"))
                columns = [row[1] for row in res.fetchall()]
                if columns:
                    if "recommendations_json" not in columns:
                        sync_conn.execute(text("ALTER TABLE candidates ADD COLUMN recommendations_json TEXT;"))
                    if "confirmed_roles_json" not in columns:
                        sync_conn.execute(text("ALTER TABLE candidates ADD COLUMN confirmed_roles_json TEXT;"))
                    if "confirmed_at" not in columns:
                        sync_conn.execute(text("ALTER TABLE candidates ADD COLUMN confirmed_at DATETIME;"))

                # Check jobs table
                res_jobs = sync_conn.execute(text("PRAGMA table_info(jobs);"))
                job_columns = [row[1] for row in res_jobs.fetchall()]
                if job_columns:
                    if "canonical_job_id" not in job_columns:
                        sync_conn.execute(text("ALTER TABLE jobs ADD COLUMN canonical_job_id INTEGER;"))
                    if "is_canonical_primary" not in job_columns:
                        sync_conn.execute(text("ALTER TABLE jobs ADD COLUMN is_canonical_primary BOOLEAN DEFAULT 0;"))
                    if "dedup_status" not in job_columns:
                        sync_conn.execute(text("ALTER TABLE jobs ADD COLUMN dedup_status VARCHAR DEFAULT 'UNPROCESSED';"))
            except Exception:
                pass
        await conn.run_sync(migrate_schema)

async def close() -> None:
    await engine.dispose()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


