# backend/scripts/run_job_embeddings_validation.py
"""
Phase 6 Live Validation: Canonical Job Semantic Embeddings & Vector Storage.
Generates embeddings for all canonical jobs in the database, verifies:
1. Model loading & dimensions (384).
2. Content hash determinism.
3. Vector L2 normalization (norm == 1.0).
4. Raw float32 BLOB and JSON storage.
5. Skipping unchanged embeddings on repeat invocation.
6. Summary metrics.
"""

import asyncio
import os
import sys
import numpy as np

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from db.database import AsyncSessionLocal, init, close
from embeddings.job_embedder import job_embedding_service, build_canonical_job_text, compute_content_hash
from models.canonical_job import CanonicalJob
from models.job_embedding import JobEmbedding
from sqlalchemy import select


async def run_validation():
    await init()
    print("=" * 80)
    print("PHASE 6: CANONICAL JOB EMBEDDING VALIDATION & AUDIT")
    print("=" * 80)

    async with AsyncSessionLocal() as session:
        # Step 1: Check initial canonical jobs & embeddings
        jobs = (await session.execute(select(CanonicalJob).order_by(CanonicalJob.id.asc()))).scalars().all()
        print(f"[1] Loaded {len(jobs)} canonical jobs from database.")
        if not jobs:
            print("[ERROR] No canonical jobs found. Please ensure Phase 5 deduplication has been run.")
            return

        # Inspect deterministic text builder on first job
        first_job = jobs[0]
        sample_text = build_canonical_job_text(first_job)
        first_hash = compute_content_hash(sample_text)
        print(f"\n[2] Sample Deterministic Input Text for {first_job.canonical_job_id}:")
        print("-" * 60)
        print(sample_text[:400] + "\n... [truncated] ...")
        print("-" * 60)
        print(f"Content SHA-256 Hash: {first_hash}")
        assert "http" not in sample_text, "Found raw URL in deterministic text!"
        print("[PASS] Text sanitization excludes URLs and tracking artifacts.")

        # Step 2: Run embedding generation
        print(f"\n[3] Generating semantic embeddings for {len(jobs)} canonical jobs (with force=True to test full generation)...")
        result = await job_embedding_service.generate_batch_embeddings(
            db=session,
            force=True,
        )
        print(f"Generation Result: considered={result['total_considered']}, generated={result['generated_count']}, "
              f"skipped={result['skipped_count']}, failed={result['failed_count']}")
        assert result["failed_count"] == 0, f"Expected 0 failures, got {result['failed_count']}"
        assert result["generated_count"] == len(jobs), f"Expected {len(jobs)} generated, got {result['generated_count']}"
        print("[PASS] Batch embedding generated successfully.")

        # Step 3: Verify embeddings in database
        print("\n[4] Auditing persisted vector embeddings...")
        stmt = select(JobEmbedding).order_by(JobEmbedding.canonical_job_id.asc())
        embeddings = (await session.execute(stmt)).scalars().all()
        print(f"Total embeddings persisted: {len(embeddings)}")
        assert len(embeddings) == len(jobs), f"Expected {len(jobs)} records in job_embeddings"

        for emb in embeddings:
            vec = emb.get_vector()
            norm = float(np.linalg.norm(vec))
            assert len(vec) == 384, f"Invalid vector dimensions: {len(vec)}"
            assert np.isclose(norm, 1.0, atol=1e-3), f"Vector norm is not 1.0: {norm}"
            assert emb.embedding_blob is not None and len(emb.embedding_blob) == 384 * 4, "Invalid BLOB size"
            assert emb.embedding_json is not None and len(emb.embedding_json) > 100, "Missing JSON vector string"
            assert emb.status == "COMPLETED", f"Status is {emb.status}"
            assert emb.model_name == "fine-tuned-sbert", f"Unexpected model name: {emb.model_name}"

        print(f"[PASS] All {len(embeddings)} vectors verified: 384 dimensions, L2 norm == 1.0, BLOB size == 1536 bytes.")

        # Step 4: Verify incremental caching (skipping unchanged jobs)
        print("\n[5] Testing incremental skip behavior (re-running batch without force)...")
        repeat_result = await job_embedding_service.generate_batch_embeddings(
            db=session,
            force=False,
        )
        print(f"Repeat Result: considered={repeat_result['total_considered']}, generated={repeat_result['generated_count']}, "
              f"skipped={repeat_result['skipped_count']}, failed={repeat_result['failed_count']}")
        assert repeat_result["generated_count"] == 0, "Expected 0 new embeddings generated!"
        assert repeat_result["skipped_count"] == len(jobs), f"Expected {len(jobs)} skipped!"
        print("[PASS] Incremental caching correctly skipped 100% of unchanged vacancies.")

        # Step 5: Verify Summary API output
        print("\n[6] Checking system summary metrics...")
        summary = await job_embedding_service.get_summary(db=session)
        print("Summary stats:", summary)
        assert summary["total_canonical_jobs"] == len(jobs)
        assert summary["completed_embeddings"] == len(jobs)
        assert summary["missing_embeddings"] == 0
        assert summary["failed_embeddings"] == 0
        assert summary["dimensions"] == 384
        assert summary["model_name"] == "fine-tuned-sbert"
        print("[PASS] Summary stats verified.")

    await close()
    print("\n" + "=" * 80)
    print("ALL PHASE 6 LIVE VALIDATION CHECKS PASSED [OK]")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_validation())
