"""
Fresher & B.Tech Job Discovery, Extraction, Ingestion, and Matching Engine.
Tailored for Candidate 1 and Candidate 3 (Gundelli Abhilash - B.Tech student / Fresher).
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import func, select, or_
from db.database import AsyncSessionLocal
from discovery.providers.firecrawl_provider import FirecrawlProvider
from models.candidate import Candidate
from models.canonical_job import CanonicalJob, CanonicalJobSource, VacancyStatus
from models.job import Job
from models.source import Company, DiscoveredJob
from jobs.extraction_service import JobExtractionService
from deduplication.dedup_service import JobDeduplicationService
from embeddings.job_embedder import JobEmbeddingService
from matching.matching_service import MatchingService


async def main():
    print("=" * 70, flush=True)
    print("AI JOB SEARCH AGENT - FRESHER & B.TECH PIPELINE", flush=True)
    print("=" * 70, flush=True)

    async with AsyncSessionLocal() as db:
        # 1. Target Companies for fresher engineering intake
        comp_stmt = select(Company).where(
            or_(
                Company.normalized_name.like("%inmobi%"),
                Company.normalized_name.like("%groww%"),
                Company.normalized_name.like("%zoho%"),
                Company.normalized_name.like("%swiggy%"),
                Company.normalized_name.like("%razorpay%"),
            )
        ).limit(5)
        companies = (await db.execute(comp_stmt)).scalars().all()
        print(f"Targeting {len(companies)} tech employers for fresher roles: {[c.name for c in companies]}", flush=True)

        fc = FirecrawlProvider()
        new_disc_count = 0

        for comp in companies:
            domain = comp.primary_domain or "techcorp.in"
            career_url = f"https://{domain}/careers"
            jobs = await fc.discover_jobs(
                identifier=career_url,
                company_name=comp.name,
                source_url=career_url,
            )
            print(f"[{comp.name}] Firecrawl discovered {len(jobs)} fresher/intern openings", flush=True)

            for job in jobs:
                norm_url = job.job_url.lower().strip().rstrip("/")
                norm_id = (job.external_job_id or "").strip().lower()
                dedup_key = f"{comp.id}|firecrawl|{norm_id}|{norm_url}"

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
                    new_disc_count += 1

        await db.commit()
        print(f"Step 1 Complete: {new_disc_count} new Firecrawl fresher jobs saved to discovered_jobs.", flush=True)

        # 2. Extract unextracted jobs
        print("\nStep 2: Extracting Discovered Postings...", flush=True)
        extractor_svc = JobExtractionService()
        ext_res = await extractor_svc.extract_all_unextracted(db=db, limit=50)
        print(f"Step 2 Complete: Extracted {ext_res.get('extracted_count', 0)} jobs.", flush=True)

        # 3. Deduplicate and merge into CanonicalJob
        print("\nStep 3: Deduplicating and Updating Canonical Vacancies...", flush=True)
        dedup_svc = JobDeduplicationService()
        dedup_res = await dedup_svc.run_deduplication(db=db, auto_merge=True)
        print(f"Step 3 Complete: {dedup_res.get('merged_groups_count', 0)} merged groups.", flush=True)

        total_canon = (await db.execute(select(func.count(CanonicalJob.id)).where(CanonicalJob.vacancy_status == VacancyStatus.ACTIVE.value))).scalar() or 0
        print(f"Total Active Canonical Vacancies in DB: {total_canon}", flush=True)

        # 4. Embed only un-embedded canonical jobs
        print("\nStep 4: Vectorizing Canonical Vacancies with fine-tuned SBERT (384-d)...", flush=True)
        embed_svc = JobEmbeddingService()
        emb_res = await embed_svc.generate_batch_embeddings(db=db, force=False)
        print(f"Step 4 Complete: {emb_res.get('successful_embeddings', 0)} new embeddings, {emb_res.get('skipped_incremental', 0)} cached.", flush=True)

        # 5. Run matching for Candidate 1 (active in UI) and Candidate 3
        print("\nStep 5: Running SBERT Matching & Technical Gate for Active Candidates...", flush=True)
        match_svc = MatchingService()

        for cand_id in [1, 3]:
            cand = (await db.execute(select(Candidate).where(Candidate.id == cand_id))).scalar_one_or_none()
            if not cand:
                continue

            matches = await match_svc.run_matching_for_candidate(db=db, candidate_id=cand_id, force=True)
            print(f"\n========================================================")
            print(f" CANDIDATE #{cand_id}: {cand.filename}")
            print(f" Total Matches Evaluated: {len(matches)}")
            print(f"========================================================")

            relevant = [m for m in matches if getattr(m, 'is_relevant', True)]
            eligible = [m for m in relevant if m.eligibility_status == "ELIGIBLE"]

            print(f"Relevant Roles: {len(relevant)} | 100% Eligible Fresher Roles: {len(eligible)}")
            print("\nTop 10 Technical Recommendations for this Candidate:")
            for i, m in enumerate(relevant[:10], 1):
                cj = m.canonical_job
                title = cj.title if cj else "Unknown"
                company = cj.company_name if cj else "Unknown"
                loc = cj.location if cj else "India"
                exp = f"{cj.experience_min_years or 0:.0f} yrs"
                emp = (cj.employment_type or "FULL_TIME").replace("_", " ")
                print(f"  {i}. [{m.composite_score:.1f}%] {company} — {title}")
                print(f"     Location: {loc} | Type: {emp} | Min Exp: {exp}")
                print(f"     Status: {m.eligibility_status} ({m.match_classification}) | Role Family: {getattr(m, 'role_family', 'TECHNICAL')}")

    print("\n" + "=" * 70, flush=True)
    print("SUCCESS: FRESHER & B.TECH DISCOVERY & MATCHING COMPLETE", flush=True)
    print("=" * 70, flush=True)


if __name__ == "__main__":
    asyncio.run(main())

