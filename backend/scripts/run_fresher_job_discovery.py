"""
Script to discover, extract, embed, and match Fresher & B.Tech student vacancies
using FirecrawlProvider, JobExtractionService, JobEmbeddingService, and MatchingService.
Tailored for Candidate 1 and Candidate 3 (Gundelli Abhilash - B.Tech student, fresher).
"""

import asyncio
import json
import os
import sys

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import func, select, or_
from db.database import AsyncSessionLocal
from discovery.providers.firecrawl_provider import FirecrawlProvider
from models.candidate import Candidate
from models.canonical_job import CanonicalJob, VacancyStatus
from models.job import Job
from models.source import Company, DiscoveredJob
from jobs.extraction_service import JobExtractionService
from deduplication.dedup_service import JobDeduplicationService
from embeddings.job_embedder import JobEmbeddingService
from matching.matching_service import MatchingService


async def run_fresher_job_discovery():
    print("=" * 70, flush=True)
    print("AI JOB SEARCH AGENT - FRESHER & B.TECH VACANCY DISCOVERY PIPELINE", flush=True)
    print("=" * 70, flush=True)

    async with AsyncSessionLocal() as db:
        # Step 1: Verify Active Candidates
        cands_stmt = select(Candidate).where(Candidate.id.in_([1, 3]))
        candidates = (await db.execute(cands_stmt)).scalars().all()
        print(f"\n[Step 1] Verified Active Candidates ({len(candidates)}):", flush=True)
        for c in candidates:
            prof = json.loads(c.profile_json) if c.profile_json else {}
            pers = prof.get("profile", {}).get("personal", {})
            edu = prof.get("profile", {}).get("education", [{}])[0]
            print(f"  - Candidate #{c.id}: {pers.get('name')} | {pers.get('email')} | Resume: {c.filename}", flush=True)
            print(f"    Degree: {edu.get('degree')} in {edu.get('specialization')} ({edu.get('start_year')}-{edu.get('graduation_year')}) at {edu.get('university')}", flush=True)

        # Step 2: Use FirecrawlProvider to discover fresher & B.Tech jobs across Indian employers
        print("\n[Step 2] Executing Firecrawl Fresher & B.Tech Discovery...", flush=True)
        firecrawl = FirecrawlProvider()

        # Select target tech employers
        comp_stmt = select(Company).where(
            or_(
                Company.normalized_name.like("%inmobi%"),
                Company.normalized_name.like("%groww%"),
                Company.normalized_name.like("%hackerrank%"),
                Company.normalized_name.like("%postman%"),
                Company.normalized_name.like("%browserstack%"),
                Company.normalized_name.like("%swiggy%"),
                Company.normalized_name.like("%razorpay%"),
                Company.normalized_name.like("%zoho%"),
                Company.normalized_name.like("%yellow%"),
                Company.normalized_name.like("%zeta%"),
            )
        ).limit(5)
        companies = (await db.execute(comp_stmt)).scalars().all()
        if not companies:
            comp_stmt = select(Company).limit(5)
            companies = (await db.execute(comp_stmt)).scalars().all()

        print(f"Targeting {len(companies)} tech employers for fresher openings:", flush=True)
        for comp in companies:
            print(f"  - {comp.name} (ID: {comp.id})", flush=True)

        total_discovered = 0
        persisted_discovered = 0

        for comp in companies:
            jobs = await firecrawl.discover_jobs(
                identifier=f"https://{comp.primary_domain or 'careers.company.com'}/careers",
                company_name=comp.name,
                source_url=f"https://{comp.primary_domain or 'careers.company.com'}/careers",
            )
            total_discovered += len(jobs)

            for job in jobs:
                norm_url = job.job_url.lower().strip().rstrip("/")
                norm_id = (job.external_job_id or "").strip().lower()
                dedup_key = f"{comp.id}|firecrawl|{norm_id}|{norm_url}"

                # Check if already present
                stmt = select(DiscoveredJob).where(DiscoveredJob.dedup_key == dedup_key)
                existing = (await db.execute(stmt)).scalar_one_or_none()
                if not existing:
                    new_disc = DiscoveredJob(
                        company_id=comp.id,
                        provider="firecrawl",
                        external_job_id=job.external_job_id,
                        dedup_key=dedup_key,
                        discovered_title=job.title,
                        discovered_location=job.location,
                        department=job.department,
                        job_url=job.job_url,
                        application_url=job.application_url or job.job_url,
                        source_url=job.source_url,
                        raw_payload=json.dumps(job.raw_payload) if job.raw_payload else None,
                        discovery_status="ACTIVE",
                    )
                    db.add(new_disc)
                    persisted_discovered += 1

        await db.commit()
        print(f"-> Discovered: {total_discovered} roles | Newly Persisted: {persisted_discovered} roles.", flush=True)

        # Step 3: Run Job Extraction
        print("\n[Step 3] Running Job Extraction Pipeline...", flush=True)
        extraction_service = JobExtractionService()
        ext_res = await extraction_service.extract_all_unextracted(db=db, limit=50)
        print(f"-> Extraction Complete: {ext_res.get('extracted_count', 0)} jobs extracted (Failed: {ext_res.get('failed_count', 0)})", flush=True)

        # Step 4: Run Deduplication into CanonicalJob
        print("\n[Step 4] Running Deduplication & Canonical Merging...", flush=True)
        dedup_service = JobDeduplicationService()
        dedup_res = await dedup_service.run_deduplication(db=db, auto_merge=True)
        print(f"-> Deduplication Complete: {dedup_res.get('merged_groups_count', 0)} merged groups.", flush=True)

        canon_count = (await db.execute(select(func.count(CanonicalJob.id)).where(CanonicalJob.vacancy_status == VacancyStatus.ACTIVE.value))).scalar() or 0
        print(f"-> Total Active Canonical Jobs: {canon_count}", flush=True)

        # Step 5: Generate SBERT 384-d Embeddings for Canonical Jobs
        print("\n[Step 5] Generating SBERT (384-d) Vector Embeddings...", flush=True)
        job_embedder = JobEmbeddingService()
        emb_res = await job_embedder.generate_batch_embeddings(db=db, force=False)
        print(f"-> Embeddings Generated: {emb_res.get('successful_embeddings', 0)} new, {emb_res.get('skipped_incremental', 0)} unchanged.", flush=True)

        # Step 6: Run Candidate Matching for Candidate 1 & 3
        print("\n[Step 6] Running Technical & Eligibility Matching for Fresher Candidate...", flush=True)
        matching_service = MatchingService()

        for cand in candidates:
            print(f"\n--- Matching for Candidate #{cand.id} ({cand.filename}) ---", flush=True)
            matches = await matching_service.run_matching_for_candidate(
                db=db, candidate_id=cand.id, force=True
            )
            print(f"Total Matches Evaluated: {len(matches)}", flush=True)

            # Display top technical, eligible matches
            relevant_matches = [m for m in matches if getattr(m, 'is_relevant', True)]
            eligible_matches = [m for m in relevant_matches if m.eligibility_status == "ELIGIBLE"]

            print(f"Relevant Matches: {len(relevant_matches)} | Fully Eligible Matches: {len(eligible_matches)}", flush=True)
            print("Top Matching Vacancies for Fresher / B.Tech Profile:", flush=True)
            for idx, m in enumerate(relevant_matches[:8], 1):
                job_title = m.canonical_job.title if m.canonical_job else "Unknown"
                company = m.canonical_job.company_name if m.canonical_job else "Unknown"
                loc = m.canonical_job.location if m.canonical_job else "India"
                exp = f"{m.canonical_job.experience_min_years or 0} yrs"
                emp = m.canonical_job.employment_type or "FULL_TIME"
                print(
                    f"  {idx}. [{m.composite_score:.1f}%] {company} - {job_title} "
                    f"({loc} | {emp} | Exp: {exp}) -> {m.eligibility_status} ({m.match_classification})",
                    flush=True,
                )

        print("\n" + "=" * 70, flush=True)
        print("FRESHER & B.TECH JOB DISCOVERY & MATCHING COMPLETE", flush=True)
        print("=" * 70, flush=True)


if __name__ == "__main__":
    asyncio.run(run_fresher_job_discovery())
