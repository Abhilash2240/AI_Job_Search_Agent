# backend/scripts/migrate_phase6.py
"""
Migration script for Phase 6: Job Embeddings and Vector Storage.
Creates the `job_embeddings` table and associated indices if they do not exist.
"""

import sys
import os

# Ensure backend directory is in path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import sqlite3

DB_PATH = os.path.join(backend_dir, "ai_job_search.db")


def migrate():
    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS job_embeddings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        canonical_job_id INTEGER NOT NULL UNIQUE,
        embedding_blob BLOB,
        embedding_json TEXT,
        model_name VARCHAR NOT NULL DEFAULT 'fine-tuned-sbert',
        dimensions INTEGER NOT NULL DEFAULT 384,
        content_hash VARCHAR(64) NOT NULL,
        status VARCHAR NOT NULL DEFAULT 'COMPLETED',
        last_error TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (canonical_job_id) REFERENCES canonical_jobs (id) ON DELETE CASCADE
    );
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS ix_job_embeddings_id ON job_embeddings (id);")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_job_embeddings_canonical_job_id ON job_embeddings (canonical_job_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_job_embeddings_content_hash ON job_embeddings (content_hash);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_job_embeddings_status ON job_embeddings (status);")

    conn.commit()

    # Verify table schema
    cur.execute("PRAGMA table_info(job_embeddings);")
    columns = cur.fetchall()
    print("job_embeddings table structure:")
    for col in columns:
        print(f" - {col[1]} ({col[2]}), nullable={not col[3]}, pk={col[5]}")

    cur.execute("SELECT COUNT(*) FROM canonical_jobs;")
    canon_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM job_embeddings;")
    emb_count = cur.fetchone()[0]
    print(f"[OK] Migration completed successfully. Canonical jobs: {canon_count}, Existing embeddings: {emb_count}")

    conn.close()


if __name__ == "__main__":
    migrate()

