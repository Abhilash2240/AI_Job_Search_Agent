"""
Job Discovery Orchestrator.
Coordinates ATS detection, provider queries (Greenhouse, Lever, Firecrawl),
deduplication, targeting filters, and persistence of discovered job postings.
"""

import asyncio
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from sqlalchemy import select, func, update, case
from sqlalchemy.orm import selectinload

from db.database import AsyncSessionLocal
from discovery.ats_detector import AtsDetector
from discovery.discovery_config import discovery_settings
from discovery.discovery_logger import get_logger
from discovery.discovery_query_builder import DiscoveryQueryBuilder, DiscoveryTargetCriteria
from discovery.providers.base_provider import DiscoveredJobData
from discovery.providers.greenhouse_provider import GreenhouseProvider
from discovery.providers.lever_provider import LeverProvider
from discovery.providers.firecrawl_provider import FirecrawlProvider
from models.candidate import Candidate
from models.source import Company, CompanyCareerSource, DiscoveredJob

logger = get_logger("orchestrator")


class DiscoveryOrchestrator:
    """Central orchestrator for discovering jobs across all company sources and providers."""

    def __init__(self):
        self.greenhouse_provider = GreenhouseProvider()
        self.lever_provider = LeverProvider()
        self.firecrawl_provider = FirecrawlProvider()

        # In-memory execution state
        self._current_run: Optional[Dict[str, Any]] = None
        self._last_run_summary: Optional[Dict[str, Any]] = None
        self._run_lock: Optional[asyncio.Lock] = None
        self._active_task: Optional[asyncio.Task] = None

    @property
    def run_lock(self) -> asyncio.Lock:
        if self._run_lock is None:
            self._run_lock = asyncio.Lock()
        return self._run_lock

    @classmethod
    def generate_dedup_key(cls, company_id: int, provider: str, external_job_id: Optional[str], job_url: str) -> str:
        """
        Generates a stable, reproducible deduplication key.
        Uses external_job_id if present, normalized job_url otherwise.
        """
        norm_url = job_url.lower().strip().rstrip("/")
        norm_id = (external_job_id or "").strip().lower()
        unique_string = f"{company_id}|{provider.strip().lower()}|{norm_id}|{norm_url}"
        return hashlib.sha256(unique_string.encode("utf-8")).hexdigest()

    def get_status(self) -> Dict[str, Any]:
        """Returns the current runtime status of discovery operations."""
        if self._current_run:
            return {
                "status": "RUNNING",
                **self._current_run,
            }
        elif self._last_run_summary:
            return {
                "status": "COMPLETED",
                **self._last_run_summary,
            }
        else:
            return {
                "status": "IDLE",
                "message": "No discovery runs executed yet.",
            }

    async def get_providers_status(self) -> List[Dict[str, Any]]:
        """Returns status and configuration details for all integrated providers."""
        greenhouse_available = await self.greenhouse_provider.is_available()
        lever_available = await self.lever_provider.is_available()
        firecrawl_available = await self.firecrawl_provider.is_available()

        return [
            {
                "name": "greenhouse",
                "display_name": "Greenhouse Job Boards API",
                "type": "official_ats_api",
                "status": "active" if greenhouse_available else "inactive",
                "auth_required": False,
                "concurrency": self.greenhouse_provider.max_concurrency,
                "rate_limit_rps": self.greenhouse_provider.rate_limit,
            },
            {
                "name": "lever",
                "display_name": "Lever Postings API",
                "type": "official_ats_api",
                "status": "active" if lever_available else "inactive",
                "auth_required": False,
                "concurrency": self.lever_provider.max_concurrency,
                "rate_limit_rps": self.lever_provider.rate_limit,
            },
            {
                "name": "firecrawl",
                "display_name": "Firecrawl Web Crawler & Mapper",
                "type": "crawler_service",
                "status": "configured" if firecrawl_available else "unconfigured_fallback",
                "auth_required": True,
                "concurrency": self.firecrawl_provider.max_concurrency,
                "rate_limit_rps": self.firecrawl_provider.rate_limit,
                "details": "Ready for crawling & ATS detection" if firecrawl_available else "API key missing. Gracefully falling back to URL ATS detection.",
            },
        ]

    async def _load_target_criteria(self, db, candidate_id: Optional[int] = None) -> DiscoveryTargetCriteria:
        """Loads candidate confirmed roles to formulate discovery targeting."""
        if candidate_id:
            stmt = select(Candidate).where(Candidate.id == candidate_id)
            res = await db.execute(stmt)
            candidate = res.scalar_one_or_none()
            if candidate and candidate.confirmed_roles_json:
                try:
                    roles = json.loads(candidate.confirmed_roles_json)
                    skills = []
                    if candidate.profile_json:
                        profile = json.loads(candidate.profile_json)
                        skills = profile.get("skills", [])
                    return DiscoveryQueryBuilder.from_confirmed_roles(roles, skills)
                except Exception as e:
                    logger.warning(f"Error parsing candidate {candidate_id} confirmed roles: {e}")

        # Default fallback criteria
        return DiscoveryTargetCriteria(
            target_titles=["Python Backend Engineer", "Python Developer", "Backend Developer", "Software Engineer"],
            alternative_titles=["Junior Python Developer", "Associate Software Engineer"],
            key_skills=["Python", "FastAPI", "SQL", "Docker", "REST APIs"],
            locations=["India", "Remote"],
        )

    async def discover_company_jobs(
        self,
        company: Company,
        criteria: Optional[DiscoveryTargetCriteria] = None,
        db = None,
    ) -> List[DiscoveredJobData]:
        """
        Discovers jobs for a single company:
        1. Inspects career sources.
        2. Detects ATS (Greenhouse, Lever, etc.) or uses cached ATS.
        3. Invokes corresponding provider.
        """
        all_jobs: List[DiscoveredJobData] = []

        for source in company.career_sources:
            if not source.career_url:
                continue

            ats_provider = source.ats_provider
            ats_identifier = source.ats_identifier

            # 1. Detect ATS if not previously cached
            if not ats_provider or not ats_identifier:
                detection = AtsDetector.detect_from_url(source.career_url)
                if not detection and await self.firecrawl_provider.is_available():
                    detection = await self.firecrawl_provider.detect_ats_from_site(source.career_url)

                if detection:
                    ats_provider = detection.provider
                    ats_identifier = detection.identifier
                    # Cache in DB if session provided
                    if db:
                        source.ats_provider = ats_provider
                        source.ats_identifier = ats_identifier

            # 2. Query provider according to ATS type
            if ats_provider == "greenhouse" and ats_identifier:
                jobs = await self.greenhouse_provider.discover_jobs(
                    identifier=ats_identifier,
                    company_name=company.name,
                    source_url=source.career_url,
                )
                all_jobs.extend(jobs)
            elif ats_provider == "lever" and ats_identifier:
                jobs = await self.lever_provider.discover_jobs(
                    identifier=ats_identifier,
                    company_name=company.name,
                    source_url=source.career_url,
                )
                all_jobs.extend(jobs)
            elif ats_provider in ("workday", "smartrecruiters", "ashby"):
                logger.info(
                    f"[{company.name}] ATS '{ats_provider}' detected for '{source.career_url}'. Direct API integration reserved for next iteration."
                )
            else:
                # Fallback to Firecrawl if enabled
                if await self.firecrawl_provider.is_available():
                    jobs = await self.firecrawl_provider.discover_jobs(
                        identifier=source.career_url,
                        company_name=company.name,
                        source_url=source.career_url,
                    )
                    all_jobs.extend(jobs)

        return all_jobs

    async def run_discovery(
        self,
        company_ids: Optional[List[int]] = None,
        limit: Optional[int] = None,
        dry_run: bool = False,
        candidate_id: Optional[int] = None,
        filter_targeting: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes a discovery run over specified or registered companies.
        """
        async with self.run_lock:
            start_time = datetime.now(timezone.utc)
            self._current_run = {
                "started_at": start_time.isoformat(),
                "dry_run": dry_run,
                "total_companies": 0,
                "processed_companies": 0,
                "jobs_discovered": 0,
                "new_jobs_persisted": 0,
                "duplicate_jobs_updated": 0,
                "errors": [],
            }

            try:
                async with AsyncSessionLocal() as db:
                    criteria = await self._load_target_criteria(db, candidate_id)

                    # Query companies, prioritizing those with configured ATS sources
                    ats_subq = select(CompanyCareerSource.company_id).where(CompanyCareerSource.ats_provider.isnot(None))
                    if company_ids:
                        query = select(Company).options(selectinload(Company.career_sources)).where(Company.id.in_(company_ids)).order_by(Company.id)
                    else:
                        query = (
                            select(Company)
                            .options(selectinload(Company.career_sources))
                            .join(CompanyCareerSource, Company.id == CompanyCareerSource.company_id)
                            .order_by(
                                case((Company.id.in_(ats_subq), 0), else_=1),
                                Company.id.asc()
                            )
                            .distinct()
                        )
                    if limit:
                        query = query.limit(limit)

                    result = await db.execute(query)
                    companies = result.scalars().all()

                    self._current_run["total_companies"] = len(companies)
                    logger.info(f"[Discovery] Starting discovery run for {len(companies)} companies (dry_run={dry_run})")

                    sem = asyncio.Semaphore(discovery_settings.DISCOVERY_MAX_CONCURRENCY)

                    async def process_single_company(company: Company):
                        async with sem:
                            try:
                                jobs = await self.discover_company_jobs(company, criteria=criteria, db=db)
                                return company, jobs, None
                            except Exception as err:
                                logger.error(f"[Discovery] Error processing company {company.name}: {err}")
                                return company, [], str(err)

                    # Gather company discovery results
                    tasks = [process_single_company(comp) for comp in companies]
                    batch_results = await asyncio.gather(*tasks)

                    # Process persistence and deduplication
                    for company, jobs, err in batch_results:
                        self._current_run["processed_companies"] += 1
                        if err:
                            self._current_run["errors"].append({"company": company.name, "error": err})
                            continue

                        for job in jobs:
                            self._current_run["jobs_discovered"] += 1

                            # Evaluate targeting if requested
                            is_target, score, reasons = DiscoveryQueryBuilder.evaluate_job(job, criteria)
                            if filter_targeting and not is_target:
                                continue

                            dedup_key = self.generate_dedup_key(
                                company_id=company.id,
                                provider=job.provider,
                                external_job_id=job.external_job_id,
                                job_url=job.job_url,
                            )

                            if not dry_run:
                                # Check existing record in DB
                                stmt = select(DiscoveredJob).where(DiscoveredJob.dedup_key == dedup_key)
                                existing_res = await db.execute(stmt)
                                existing_job = existing_res.scalar_one_or_none()

                                if existing_job:
                                    existing_job.last_discovered_at = func.now()
                                    existing_job.discovery_status = "ACTIVE"
                                    if job.raw_payload:
                                        existing_job.raw_payload = json.dumps(job.raw_payload)
                                    self._current_run["duplicate_jobs_updated"] += 1
                                else:
                                    # Insert new job
                                    raw_str = json.dumps(job.raw_payload) if job.raw_payload else None
                                    new_discovered = DiscoveredJob(
                                        company_id=company.id,
                                        provider=job.provider,
                                        external_job_id=job.external_job_id,
                                        dedup_key=dedup_key,
                                        discovered_title=job.title,
                                        discovered_location=job.location,
                                        department=job.department,
                                        job_url=job.job_url,
                                        application_url=job.application_url or job.job_url,
                                        source_url=job.source_url,
                                        raw_payload=raw_str,
                                        discovery_status="ACTIVE",
                                    )
                                    db.add(new_discovered)
                                    self._current_run["new_jobs_persisted"] += 1

                    if not dry_run:
                        await db.commit()

            except Exception as e:
                logger.error(f"[Discovery] Global run error: {e}", exc_info=True)
                if self._current_run:
                    self._current_run["errors"].append({"global_error": str(e)})
            finally:
                end_time = datetime.now(timezone.utc)
                duration_sec = (end_time - start_time).total_seconds()
                summary = {
                    "status": "COMPLETED",
                    **(self._current_run or {}),
                    "completed_at": end_time.isoformat(),
                    "duration_seconds": round(duration_sec, 2),
                }
                self._last_run_summary = summary
                self._current_run = None
                logger.info(
                    f"[Discovery] Completed run in {duration_sec:.2f}s: "
                    f"{summary.get('jobs_discovered', 0)} discovered, "
                    f"{summary.get('new_jobs_persisted', 0)} new, "
                    f"{summary.get('duplicate_jobs_updated', 0)} updated."
                )
                return summary

    def trigger_background_run(
        self,
        company_ids: Optional[List[int]] = None,
        limit: Optional[int] = None,
        dry_run: bool = False,
        candidate_id: Optional[int] = None,
        filter_targeting: bool = False,
    ) -> bool:
        """Triggers discovery in background if no job is currently running."""
        if self._current_run is not None:
            return False  # Already running

        self._active_task = asyncio.create_task(
            self.run_discovery(
                company_ids=company_ids,
                limit=limit,
                dry_run=dry_run,
                candidate_id=candidate_id,
                filter_targeting=filter_targeting,
            )
        )
        return True


# Global Orchestrator instance
discovery_orchestrator = DiscoveryOrchestrator()
