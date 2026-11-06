"""
Job Extraction Service (Phase 4C).
Orchestrates provider-specific extraction, normalization, deduplication,
quality scoring, and database persistence for discovered job postings.
"""

import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from discovery.discovery_logger import get_logger
from jobs.extraction.base_extractor import BaseJobExtractor
from jobs.extraction.firecrawl_extractor import FirecrawlExtractor
from jobs.extraction.greenhouse_extractor import GreenhouseExtractor
from jobs.extraction.lever_extractor import LeverExtractor
from jobs.job_schema import ExtractionStatus
from models.job import Job
from models.source import Company, DiscoveredJob

logger = get_logger("extraction_service")


class JobExtractionService:
    """Manages the lifecycle of extracting and normalizing discovered job postings."""

    def __init__(self):
        self.extractors: Dict[str, BaseJobExtractor] = {
            "greenhouse": GreenhouseExtractor(),
            "lever": LeverExtractor(),
            "firecrawl": FirecrawlExtractor(),
        }
        self.default_extractor = GreenhouseExtractor()

    def get_extractor(self, provider: Optional[str]) -> BaseJobExtractor:
        """Selects provider-specific extractor or default fallback."""
        if not provider:
            return self.default_extractor
        return self.extractors.get(provider.lower().strip(), self.default_extractor)

    async def extract_from_discovered_job(
        self,
        discovered_job: DiscoveredJob,
        db: AsyncSession,
        force_reextract: bool = False,
    ) -> Job:
        """
        Extracts, normalizes, and persists a single discovered job record.
        """
        # Check if already normalized
        stmt = select(Job).where(Job.raw_discovery_id == discovered_job.id)
        res = await db.execute(stmt)
        existing_job = res.scalar_one_or_none()

        if existing_job and not force_reextract:
            return existing_job

        # Parse raw payload
        raw_payload = {}
        if discovered_job.raw_payload:
            try:
                raw_payload = json.loads(discovered_job.raw_payload)
            except Exception:
                raw_payload = {}

        company_name = discovered_job.company.name if discovered_job.company else None
        extractor = self.get_extractor(discovered_job.provider)

        # Run extraction pipeline
        extracted = extractor.run_pipeline(
            raw_payload=raw_payload,
            fallback_title=discovered_job.discovered_title,
            fallback_location=discovered_job.discovered_location,
            source_url=discovered_job.source_url,
            application_url=discovered_job.application_url or discovered_job.job_url,
            company_name=company_name,
        )

        # Serialize structured lists to JSON strings
        resp_json = json.dumps(extracted["responsibilities"])
        qual_json = json.dumps(extracted["qualifications"])
        req_skills_json = json.dumps([s.model_dump() for s in extracted["required_skills"]])
        pref_skills_json = json.dumps([s.model_dump() for s in extracted["preferred_skills"]])
        elig_locs_json = json.dumps(extracted["eligible_locations"])
        degrees_json = json.dumps(extracted["degree_requirements"])
        majors_json = json.dumps(extracted["field_of_study"])
        missing_json = json.dumps(extracted["missing_fields"])

        if existing_job:
            # Update existing
            job_obj = existing_job
            job_obj.canonical_job_title = extracted["canonical_job_title"]
            job_obj.title = extracted["title"]
            job_obj.company = extracted["company"]
            job_obj.location = extracted["location"]
            job_obj.description = extracted["description"]
            job_obj.responsibilities = resp_json
            job_obj.qualifications = qual_json
            job_obj.required_skills = req_skills_json
            job_obj.preferred_skills = pref_skills_json
            job_obj.employment_type = extracted["employment_type"]
            job_obj.experience_min_years = extracted["experience_min_years"]
            job_obj.experience_max_years = extracted["experience_max_years"]
            job_obj.seniority_level = extracted["seniority_level"]
            job_obj.workplace_type = extracted["workplace_type"]
            job_obj.seniority = extracted["seniority"]
            job_obj.location_raw = extracted["location_raw"]
            job_obj.city = extracted["city"]
            job_obj.state = extracted["state"]
            job_obj.country = extracted["country"]
            job_obj.is_remote = extracted["is_remote"]
            job_obj.eligible_locations = elig_locs_json
            job_obj.degree_requirements = degrees_json
            job_obj.field_of_study = majors_json
            job_obj.salary_min = extracted["salary_min"]
            job_obj.salary_max = extracted["salary_max"]
            job_obj.salary_currency = extracted["salary_currency"]
            job_obj.salary_period = extracted["salary_period"]
            job_obj.application_url = extracted["application_url"]
            job_obj.source_url = extracted["source_url"]
            job_obj.provider = extracted["provider"]
            job_obj.source_job_id = extracted["source_job_id"]
            job_obj.extraction_status = extracted["extraction_status"]
            job_obj.extraction_confidence = extracted["extraction_confidence"]
            job_obj.missing_fields = missing_json
        else:
            # Create new Job
            job_obj = Job(
                company_id=discovered_job.company_id,
                external_job_id=discovered_job.external_job_id or extracted["external_job_id"],
                canonical_job_title=extracted["canonical_job_title"],
                title=extracted["title"],
                company=extracted["company"],
                location=extracted["location"],
                description=extracted["description"],
                responsibilities=resp_json,
                qualifications=qual_json,
                required_skills=req_skills_json,
                preferred_skills=pref_skills_json,
                employment_type=extracted["employment_type"],
                experience_min_years=extracted["experience_min_years"],
                experience_max_years=extracted["experience_max_years"],
                seniority_level=extracted["seniority_level"],
                workplace_type=extracted["workplace_type"],
                seniority=extracted["seniority"],
                location_raw=extracted["location_raw"],
                city=extracted["city"],
                state=extracted["state"],
                country=extracted["country"],
                is_remote=extracted["is_remote"],
                eligible_locations=elig_locs_json,
                degree_requirements=degrees_json,
                field_of_study=majors_json,
                salary_min=extracted["salary_min"],
                salary_max=extracted["salary_max"],
                salary_currency=extracted["salary_currency"],
                salary_period=extracted["salary_period"],
                application_url=extracted["application_url"],
                source_url=extracted["source_url"],
                provider=extracted["provider"],
                source_job_id=extracted["source_job_id"],
                raw_discovery_id=discovered_job.id,
                discovered_at=discovered_job.first_discovered_at,
                extraction_status=extracted["extraction_status"],
                extraction_confidence=extracted["extraction_confidence"],
                missing_fields=missing_json,
            )
            db.add(job_obj)

        await db.commit()
        await db.refresh(job_obj)

        # Phase 5 Integration: Link or merge with CanonicalJob vacancies
        try:
            from models.canonical_job import CanonicalJob
            from deduplication.dedup_engine import JobDeduplicationEngine
            from deduplication.merger import CanonicalJobMerger

            stmt_canon = (
                select(CanonicalJob)
                .options(selectinload(CanonicalJob.sources))
                .where(CanonicalJob.company_id == job_obj.company_id)
            )
            canon_jobs = (await db.execute(stmt_canon)).scalars().all()

            engine = JobDeduplicationEngine()
            matched_canonical = None
            best_eval = None

            for cj in canon_jobs:
                eval_res = engine.evaluate_pair(job_obj, cj)
                if eval_res.duplicate_type in ("EXACT_DUPLICATE", "HIGH_CONFIDENCE_DUPLICATE") and eval_res.can_auto_merge:
                    matched_canonical = cj
                    best_eval = eval_res
                    break

            merger = CanonicalJobMerger()
            if matched_canonical:
                # Attach to existing canonical vacancy without duplicate canonical creation
                job_obj.canonical_job_id = matched_canonical.id
                await merger.merge_or_create_canonical(
                    db=db,
                    primary_job=job_obj,
                    secondary_jobs=[],
                    evaluation=best_eval,
                )
            elif not job_obj.canonical_job_id:
                # Create initial canonical vacancy for new unique job
                await merger.merge_or_create_canonical(
                    db=db,
                    primary_job=job_obj,
                    secondary_jobs=[],
                )
            await db.refresh(job_obj)
        except Exception as e:
            logger.warning(f"Canonical job deduplication deferred during extraction: {e}")

        return job_obj

    async def batch_extract(
        self,
        db: AsyncSession,
        discovered_job_ids: Optional[List[int]] = None,
        limit: Optional[int] = None,
        force_reextract: bool = False,
    ) -> Dict[str, Any]:
        """
        Processes a batch of discovered job postings into normalized Job records.
        """
        start_time = time.monotonic()
        query = select(DiscoveredJob).options(selectinload(DiscoveredJob.company))

        if discovered_job_ids:
            query = query.where(DiscoveredJob.id.in_(discovered_job_ids))
        elif not force_reextract:
            # Only process discovered jobs that don't yet have a normalized Job record
            subq = select(Job.raw_discovery_id).where(Job.raw_discovery_id.isnot(None))
            query = query.where(DiscoveredJob.id.not_in(subq))

        query = query.order_by(DiscoveredJob.id)
        if limit is not None:
            query = query.limit(limit)

        res = await db.execute(query)
        discovered_jobs = res.scalars().all()

        counts = {
            "total_processed": len(discovered_jobs),
            "complete": 0,
            "partial": 0,
            "needs_review": 0,
            "failed": 0,
        }

        for dj in discovered_jobs:
            try:
                job_record = await self.extract_from_discovered_job(
                    discovered_job=dj, db=db, force_reextract=force_reextract
                )
                status_key = job_record.extraction_status.lower()
                if status_key in counts:
                    counts[status_key] += 1
            except Exception as err:
                logger.error(f"Error extracting discovered job ID {dj.id}: {err}", exc_info=True)
                counts["failed"] += 1

        duration = round(time.monotonic() - start_time, 2)
        counts["duration_seconds"] = duration
        return counts

    async def extract_all_unextracted(
        self,
        db: AsyncSession,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Alias for pipeline orchestrator to extract all unextracted discovered jobs."""
        res = await self.batch_extract(db=db, limit=limit, force_reextract=False)
        return {
            "extracted_count": res.get("complete", 0) + res.get("partial", 0),
            "failed_count": res.get("failed", 0),
            "total_processed": res.get("total_processed", 0),
            "duration_seconds": res.get("duration_seconds", 0.0),
        }

    async def get_extraction_summary(self, db: AsyncSession) -> Dict[str, Any]:
        """Calculates comprehensive extraction and normalization metrics across all jobs."""
        # Total normalized jobs
        total_res = await db.execute(select(func.count(Job.id)))
        total_jobs = total_res.scalar_one()

        # By status
        status_stmt = select(Job.extraction_status, func.count(Job.id)).group_by(Job.extraction_status)
        status_res = await db.execute(status_stmt)
        by_status = {row[0]: row[1] for row in status_res.all()}

        # By provider
        prov_stmt = select(Job.provider, func.count(Job.id)).group_by(Job.provider)
        prov_res = await db.execute(prov_stmt)
        by_provider = {row[0] or "unknown": row[1] for row in prov_res.all()}

        # Fresher eligible (min_years <= 1.0 or entry_level)
        fresher_stmt = select(func.count(Job.id)).where(
            (Job.experience_min_years <= 1.0) | (Job.seniority_level.in_(["ENTRY_LEVEL", "INTERN"]))
        )
        fresher_res = await db.execute(fresher_stmt)
        fresher_count = fresher_res.scalar_one()

        # Remote jobs
        remote_res = await db.execute(select(func.count(Job.id)).where(Job.is_remote == True))
        remote_count = remote_res.scalar_one()

        # Average confidence
        avg_stmt = select(func.avg(Job.extraction_confidence))
        avg_res = await db.execute(avg_stmt)
        avg_confidence = round(float(avg_res.scalar_one() or 0.0), 2)

        # Most common missing fields
        missing_stmt = select(Job.missing_fields).where(Job.missing_fields.isnot(None))
        missing_res = await db.execute(missing_stmt)
        missing_counts: Dict[str, int] = {}
        for row in missing_res.scalars().all():
            try:
                fields = json.loads(row)
                for f in fields:
                    missing_counts[f] = missing_counts.get(f, 0) + 1
            except Exception:
                pass

        return {
            "total_normalized_jobs": total_jobs,
            "by_status": by_status,
            "by_provider": by_provider,
            "fresher_eligible_count": fresher_count,
            "remote_jobs_count": remote_count,
            "average_confidence": avg_confidence,
            "most_common_missing_fields": missing_counts,
        }


# Global service instance
extraction_service = JobExtractionService()

