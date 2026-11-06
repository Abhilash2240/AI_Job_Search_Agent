"""
Audit and execution script for Phase 5 Deduplication and Vacancy Verification.
Runs deduplication on existing database normalized jobs, records provenance,
and tests vacancy verification reporting.
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select, func
from db.database import AsyncSessionLocal
from models.canonical_job import CanonicalJob, CanonicalJobSource, DuplicateReviewGroup
from models.job import Job
from deduplication.dedup_service import deduplication_service
from verification.vacancy_verifier import vacancy_verifier


async def main():
    print("=" * 70)
    print("PHASE 5 LIVE DEDUPLICATION & VERIFICATION AUDIT")
    print("=" * 70)

    async with AsyncSessionLocal() as db:
        # 1. Run Deduplication across all jobs in DB
        print("\n[1/3] Running Cross-Provider Deduplication...")
        summary = await deduplication_service.run_deduplication(db=db, auto_merge=True, similarity_threshold=0.85)
        print("  Deduplication Execution Summary:")
        for k, v in summary.items():
            print(f"    - {k}: {v}")

        # 2. Inspect Canonical Vacancies & Source Provenance
        print("\n[2/3] Inspecting Created Canonical Vacancies & Sources...")
        stmt_canon = select(CanonicalJob).order_by(CanonicalJob.id)
        canon_jobs = (await db.execute(stmt_canon)).scalars().all()
        print(f"  Total Canonical Vacancies: {len(canon_jobs)}")

        for cj in canon_jobs:
            stmt_src = select(CanonicalJobSource).where(CanonicalJobSource.canonical_job_id == cj.id)
            sources = (await db.execute(stmt_src)).scalars().all()
            print(f"  • [{cj.canonical_job_id}] '{cj.title}' @ {cj.company_name}")
            print(f"      Workplace: {cj.workplace_type} | Location: {cj.city or cj.location} | Status: {cj.vacancy_status}")
            print(f"      Sources ({len(sources)}): {[s.provider + ':' + (s.external_job_id or 'url') for s in sources]}")

        # 3. Verification Summary & Sample Verification Check
        print("\n[3/3] Inspecting Vacancy Verification Status...")
        verif_summary = await vacancy_verifier.run_batch_verification(db=db, limit=len(canon_jobs))
        print("  Batch Verification Summary:")
        for k, v in verif_summary.items():
            print(f"    - {k}: {v}")

        # Re-check canonical statuses
        stmt_status = select(CanonicalJob.vacancy_status, func.count(CanonicalJob.id)).group_by(CanonicalJob.vacancy_status)
        status_dist = (await db.execute(stmt_status)).all()
        print("\n  Updated Canonical Vacancy Status Distribution:")
        for stat, cnt in status_dist:
            print(f"    - {stat}: {cnt}")

        review_groups_cnt = (await db.execute(select(func.count(DuplicateReviewGroup.id)))).scalar()
        print(f"\n  Duplicate Review Groups Created: {review_groups_cnt}")


if __name__ == "__main__":
    asyncio.run(main())

