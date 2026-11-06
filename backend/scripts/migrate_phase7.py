# backend/scripts/migrate_phase7.py
"""
Migration script for Phase 7: Candidate-to-Job Matching and Scoring Engine.
Creates `candidate_embeddings` and `candidate_job_matches` tables and associated indices.
Preserves all existing tables and data.
"""

import sys
import os
import sqlite3

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DB_PATH = os.path.join(backend_dir, "ai_job_search.db")


def migrate():
    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. candidate_embeddings
    cur.execute("""
    CREATE TABLE IF NOT EXISTS candidate_embeddings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_id INTEGER NOT NULL UNIQUE,
        embedding_blob BLOB,
        embedding_json TEXT,
        model_name VARCHAR NOT NULL DEFAULT 'fine-tuned-sbert',
        dimensions INTEGER NOT NULL DEFAULT 384,
        content_hash VARCHAR(64) NOT NULL,
        status VARCHAR NOT NULL DEFAULT 'COMPLETED',
        last_error TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (candidate_id) REFERENCES candidates (id) ON DELETE CASCADE
    );
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS ix_candidate_embeddings_id ON candidate_embeddings (id);")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_candidate_embeddings_candidate_id ON candidate_embeddings (candidate_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_candidate_embeddings_content_hash ON candidate_embeddings (content_hash);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_candidate_embeddings_status ON candidate_embeddings (status);")

    # 2. candidate_job_matches
    cur.execute("""
    CREATE TABLE IF NOT EXISTS candidate_job_matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_id INTEGER NOT NULL,
        canonical_job_id INTEGER NOT NULL,
        composite_score REAL NOT NULL,
        semantic_score REAL NOT NULL,
        skill_score REAL NOT NULL,
        role_score REAL NOT NULL,
        experience_score REAL NOT NULL,
        education_score REAL NOT NULL,
        location_score REAL NOT NULL,
        score_coverage REAL NOT NULL DEFAULT 1.0,
        eligibility_status VARCHAR NOT NULL DEFAULT 'ELIGIBLE',
        match_classification VARCHAR NOT NULL DEFAULT 'RECOMMENDED',
        matched_skills TEXT,
        missing_skills TEXT,
        inferred_skills_potential TEXT,
        matched_roles TEXT,
        explanation_data TEXT,
        disqualification_reasons TEXT,
        component_evidence TEXT,
        candidate_content_hash VARCHAR(64) NOT NULL,
        job_content_hash VARCHAR(64) NOT NULL,
        algorithm_version VARCHAR NOT NULL DEFAULT 'phase7-v1.0',
        matching_status VARCHAR NOT NULL DEFAULT 'COMPLETED',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        evaluated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (candidate_id) REFERENCES candidates (id) ON DELETE CASCADE,
        FOREIGN KEY (canonical_job_id) REFERENCES canonical_jobs (id) ON DELETE CASCADE,
        UNIQUE (candidate_id, canonical_job_id)
    );
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS ix_candidate_job_matches_id ON candidate_job_matches (id);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_candidate_job_matches_candidate_id ON candidate_job_matches (candidate_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_candidate_job_matches_canonical_job_id ON candidate_job_matches (canonical_job_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_candidate_job_matches_composite_score ON candidate_job_matches (composite_score);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_candidate_job_matches_eligibility_status ON candidate_job_matches (eligibility_status);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_candidate_job_matches_match_classification ON candidate_job_matches (match_classification);")

    conn.commit()

    # Verify tables
    cur.execute("SELECT count(*) FROM candidates;")
    cand_count = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM canonical_jobs;")
    job_count = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM candidate_embeddings;")
    cand_emb_count = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM candidate_job_matches;")
    match_count = cur.fetchone()[0]

    print("[OK] Phase 7 database migration completed successfully.")
    print(f" - Candidates: {cand_count}")
    print(f" - Canonical jobs: {job_count}")
    print(f" - Candidate embeddings: {cand_emb_count}")
    print(f" - Candidate job matches: {match_count}")

    conn.close()


if __name__ == "__main__":
    migrate()

