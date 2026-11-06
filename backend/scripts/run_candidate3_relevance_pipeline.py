# backend/scripts/run_candidate3_relevance_pipeline.py
"""
Executes an end-to-end pipeline run for active Candidate #3:
1. Re-verifies candidate profile, skills, and confirmed roles.
2. Runs live discovery across registered ATS sources (InMobi, Groww, CRED).
3. Extracts and normalizes newly discovered vacancies.
4. Generates 384-d SBERT embeddings for new canonical jobs.
5. Executes Phase 7 matching with the Technical-Role Relevance Gate.
6. Audits relevant recommendations vs filtered irrelevant vacancies.
"""

import asyncio
import json
import logging
import os
import sys

# Ensure backend directory is in path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import select, func
from db.database import AsyncSessionLocal
from models.candidate import Candidate
from models.canonical_job import CanonicalJob, VacancyStatus
from models.candidate_job_match import CandidateJobMatch
from discovery.discovery_orchestrator import DiscoveryOrchestrator
from jobs.extraction_service import extraction_service
from deduplication.dedup_service import JobDeduplicationService
from embeddings.job_embedder import job_embedding_service
from matching.matching_service import matching_service
from matching.candidate_embedder import candidate_embedding_service
from intelligence.role_recommender import recommend_career_roles
from schemas.candidate import CandidateProfile

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("relevance_pipeline")

async def run_pipeline():
    logger.info("=" * 80)
    logger.info("STARTING ACTIVE CANDIDATE #3 RELEVANCE PIPELINE EXECUTION")
    logger.info("=" * 80)

    async with AsyncSessionLocal() as db:
        # Step 1: Audit Candidate 3
        cand = (await db.execute(select(Candidate).where(Candidate.id == 3))).scalar_one_or_none()
        if not cand:
            logger.error("Candidate 3 not found in database!")
            return

        pdata = json.loads(cand.profile_json).get("profile", {})
        logger.info(f"Candidate: {pdata.get('personal', {}).get('name')} | File: {cand.filename}")
        conf_roles = json.loads(cand.confirmed_roles_json) if cand.confirmed_roles_json else []
        logger.info(f"Confirmed Target Roles ({len(conf_roles)}): {[r.get('role_title') for r in conf_roles]}")

        # Ensure candidate embedding is fresh
        cand_emb = await candidate_embedding_service.get_or_generate_embedding(db, cand, force=True)
        logger.info(f"Candidate Embedding: {cand_emb.dimensions}-d | hash: {cand_emb.content_hash[:8]}")

        # Step 2: Live Discovery from ATS Providers
        logger.info("\n--- STEP 2: Running External ATS Discovery (InMobi, Groww, CRED) ---")
        disc_orch = DiscoveryOrchestrator()
        disc_res = await disc_orch.run_discovery(limit=10, candidate_id=3, filter_targeting=False)
        logger.info(f"Discovery Summary: Discovered={disc_res.get('jobs_discovered')}, New Persisted={disc_res.get('new_jobs_persisted')}, Updated={disc_res.get('duplicate_jobs_updated')}")

        # Step 3: Extraction & Normalization
        logger.info("\n--- STEP 3: Extracting & Normalizing Discovered Postings ---")
        ext_res = await extraction_service.extract_all_unextracted(db, limit=50)
        logger.info(f"Extraction Summary: Extracted={ext_res.get('extracted_count')}, Failed={ext_res.get('failed_count')}, Total Processed={ext_res.get('total_processed')}")

        # Step 4: Deduplication & Canonical Linking
        logger.info("\n--- STEP 4: Deduplication & Canonical Vacancy Consolidation ---")
        dedup_svc = JobDeduplicationService()
        dedup_res = await dedup_svc.run_deduplication(db, auto_merge=True)
        logger.info(f"Deduplication Summary: Merged Groups={dedup_res.get('merged_groups_count')}, Singletons={dedup_res.get('singleton_canonical_count')}")

        # Step 5: SBERT Job Embeddings Generation
        logger.info("\n--- STEP 5: Generating SBERT Job Embeddings for Canonical Vacancies ---")
        emb_res = await job_embedding_service.generate_batch_embeddings(db, force=False)
        logger.info(f"Embedding Batch: Processed={emb_res.get('total_processed')}, Generated={emb_res.get('generated')}, Skipped={emb_res.get('skipped')}")

        # Step 6: Phase 7 Matching with Technical-Role Relevance Gate
        logger.info("\n--- STEP 6: Executing Phase 7 Matching with Relevance Gate ---")
        matches = await matching_service.run_matching_for_candidate(db, candidate_id=3, force=True)
        logger.info(f"Total Matches Generated for Candidate 3: {len(matches)}")

        # Step 7: Relevance & Eligibility Breakdown
        relevant_matches = [m for m in matches if getattr(m, "is_relevant", True)]
        irrelevant_matches = [m for m in matches if not getattr(m, "is_relevant", True)]

        logger.info("\n" + "=" * 80)
        logger.info(f"MATCH AUDIT SUMMARY: Total Evaluated = {len(matches)}")
        logger.info(f"  • RELEVANT VACANCIES:   {len(relevant_matches)}")
        logger.info(f"  • IRRELEVANT VACANCIES: {len(irrelevant_matches)} (Filtered from Recommended Feed)")
        logger.info("=" * 80)

        logger.info("\nTOP RELEVANT RECOMMENDATIONS FOR CANDIDATE 3:")
        for idx, m in enumerate(relevant_matches[:8], 1):
            job = (await db.execute(select(CanonicalJob).where(CanonicalJob.id == m.canonical_job_id))).scalar_one()
            logger.info(
                f"  [{idx}] {m.composite_score:.1f}% | {job.company_name} — {job.title} "
                f"| Family: {m.role_family} | Eligibility: {m.eligibility_status}"
            )

        logger.info("\nSAMPLE IRRELEVANT VACANCIES CORRECTLY EXCLUDED:")
        for idx, m in enumerate(irrelevant_matches[:6], 1):
            job = (await db.execute(select(CanonicalJob).where(CanonicalJob.id == m.canonical_job_id))).scalar_one()
            reasons = json.loads(m.rejection_reasons or "[]")
            logger.info(
                f"  [{idx}] EXCLUDED | {job.company_name} — {job.title} "
                f"| Family: {m.role_family} | Reason: {reasons[:1]}"
            )

    logger.info("\nRELEVANCE PIPELINE COMPLETED SUCCESSFULLY.")

if __name__ == "__main__":
    asyncio.run(run_pipeline())
