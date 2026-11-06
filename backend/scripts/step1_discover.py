import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select, or_
from db.database import AsyncSessionLocal
from models.source import Company, DiscoveredJob
from discovery.providers.firecrawl_provider import FirecrawlProvider

async def main():
    async with AsyncSessionLocal() as db:
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
        print(f"Targeting companies: {[c.name for c in companies]}")

        fc = FirecrawlProvider()
        new_count = 0

        for comp in companies:
            domain = comp.primary_domain or "techcorp.in"
            url = f"https://{domain}/careers"
            jobs = await fc.discover_jobs(identifier=url, company_name=comp.name, source_url=url)
            print(f"[{comp.name}] Firecrawl generated {len(jobs)} fresher/intern openings")

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
                    new_count += 1

        await db.commit()
        print(f"Successfully committed {new_count} new Firecrawl fresher jobs to discovered_jobs.")

if __name__ == "__main__":
    asyncio.run(main())

