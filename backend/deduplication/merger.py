"""
Canonical Vacancy Merger & Provenance Preserver (Phase 5).
Combines duplicate postings into authoritative CanonicalJob records
while maintaining complete source provenance in CanonicalJobSource.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.canonical_job import (
    CanonicalJob,
    CanonicalJobSource,
    DuplicateReviewGroup,
    DuplicateGroupStatus,
    VacancyStatus,
)
from models.job import Job
from deduplication.dedup_engine import MatchEvaluation


class CanonicalJobMerger:
    """Manages the creation, merging, and provenance persistence of canonical job records."""

    @classmethod
    def generate_canonical_id(cls, company_name: str, primary_job_id: int) -> str:
        """Generates a readable, stable canonical vacancy identifier."""
        clean_comp = "".join(c for c in company_name.upper() if c.isalnum())[:10] or "COMP"
        short_uuid = str(uuid.uuid4()).replace("-", "")[:8].upper()
        return f"CANON-{clean_comp}-{primary_job_id}-{short_uuid}"

    @classmethod
    def _combine_json_lists(cls, list1_json: Optional[str], list2_json: Optional[str]) -> List[Any]:
        """Combines two JSON-serialized lists, removing exact string duplicates."""
        combined = []
        seen = set()

        for j_str in (list1_json, list2_json):
            if not j_str:
                continue
            try:
                items = json.loads(j_str)
                if isinstance(items, list):
                    for it in items:
                        key = json.dumps(it, sort_keys=True) if isinstance(it, dict) else str(it).lower().strip()
                        if key not in seen:
                            seen.add(key)
                            combined.append(it)
            except Exception:
                pass
        return combined

    @classmethod
    def _combine_skills(cls, skills1_json: Optional[str], skills2_json: Optional[str]) -> List[Dict[str, Any]]:
        """Merges skill records preserving names, canonical names, and evidence snippets."""
        merged = []
        seen_names = set()

        for j_str in (skills1_json, skills2_json):
            if not j_str:
                continue
            try:
                skills = json.loads(j_str)
                if isinstance(skills, list):
                    for s in skills:
                        if isinstance(s, dict):
                            name = (s.get("canonical_name") or s.get("skill_name") or s.get("name") or "").lower().strip()
                            if name and name not in seen_names:
                                seen_names.add(name)
                                merged.append(s)
            except Exception:
                pass
        return merged

    async def merge_or_create_canonical(
        self,
        db: AsyncSession,
        primary_job: Job,
        secondary_jobs: Optional[List[Job]] = None,
        evaluation: Optional[MatchEvaluation] = None,
    ) -> CanonicalJob:
        """
        Creates or updates a CanonicalJob record from a primary Job and optional secondary duplicate Jobs.
        Saves individual CanonicalJobSource entries for every source without data loss.
        """
        secondary_jobs = secondary_jobs or []
        now = datetime.now(timezone.utc)

        # 1. Determine if primary_job already belongs to a CanonicalJob
        canonical: Optional[CanonicalJob] = None
        if primary_job.canonical_job_id:
            stmt = (
                select(CanonicalJob)
                .options(selectinload(CanonicalJob.sources))
                .where(CanonicalJob.id == primary_job.canonical_job_id)
            )
            canonical = (await db.execute(stmt)).scalar_one_or_none()

        # Check if any secondary already has a canonical
        if not canonical:
            for sec in secondary_jobs:
                if sec.canonical_job_id:
                    stmt = (
                        select(CanonicalJob)
                        .options(selectinload(CanonicalJob.sources))
                        .where(CanonicalJob.id == sec.canonical_job_id)
                    )
                    canonical = (await db.execute(stmt)).scalar_one_or_none()
                    if canonical:
                        break

        # 2. If no canonical exists, create a new one
        if not canonical:
            canonical_code = self.generate_canonical_id(primary_job.company, primary_job.id)
            canonical = CanonicalJob(
                canonical_job_id=canonical_code,
                company_id=primary_job.company_id,
                company_name=primary_job.company,
                title=primary_job.title,
                canonical_job_title=primary_job.canonical_job_title,
                normalized_title=primary_job.canonical_job_title.lower().strip(),
                location=primary_job.location or primary_job.location_raw,
                city=primary_job.city,
                state=primary_job.state,
                country=primary_job.country or "India",
                is_remote=primary_job.is_remote,
                workplace_type=primary_job.workplace_type or "UNSPECIFIED",
                employment_type=primary_job.employment_type or "FULL_TIME",
                seniority_level=primary_job.seniority_level or "UNKNOWN",
                experience_min_years=primary_job.experience_min_years,
                experience_max_years=primary_job.experience_max_years,
                degree_requirements=primary_job.degree_requirements,
                field_of_study=primary_job.field_of_study,
                description=primary_job.description,
                responsibilities=primary_job.responsibilities,
                qualifications=primary_job.qualifications,
                required_skills=primary_job.required_skills,
                preferred_skills=primary_job.preferred_skills,
                salary_min=primary_job.salary_min,
                salary_max=primary_job.salary_max,
                salary_currency=primary_job.salary_currency,
                salary_period=primary_job.salary_period,
                canonical_application_url=primary_job.application_url,
                canonical_source_url=primary_job.source_url,
                vacancy_status=VacancyStatus.ACTIVE.value,
                first_seen_at=primary_job.extracted_at or now,
                last_seen_at=primary_job.extracted_at or now,
                last_status_change_at=now,
                consecutive_missing_checks=0,
                verification_attempts=0,
                source_count=1,
                dedup_confidence=evaluation.confidence_score if evaluation else 1.0,
                match_evidence=json.dumps(evaluation.evidence) if evaluation else None,
            )
            db.add(canonical)
            await db.flush()

        # 3. Add or update primary source observation
        primary_source_stmt = select(CanonicalJobSource).where(
            CanonicalJobSource.canonical_job_id == canonical.id,
            CanonicalJobSource.job_id == primary_job.id,
        )
        existing_src = (await db.execute(primary_source_stmt)).scalar_one_or_none()

        if not existing_src:
            primary_src = CanonicalJobSource(
                canonical_job_id=canonical.id,
                job_id=primary_job.id,
                raw_discovery_id=primary_job.raw_discovery_id,
                provider=primary_job.provider or "unknown",
                external_job_id=primary_job.external_job_id,
                source_url=primary_job.source_url,
                application_url=primary_job.application_url,
                discovered_title=primary_job.title,
                discovered_location=primary_job.location_raw or primary_job.location,
                is_primary=True,
                first_seen_at=primary_job.extracted_at or now,
                last_seen_at=primary_job.extracted_at or now,
            )
            db.add(primary_src)
        else:
            existing_src.last_seen_at = now

        primary_job.canonical_job_id = canonical.id
        primary_job.is_canonical_primary = True
        primary_job.dedup_status = "CANONICAL"

        # 4. Process and merge secondary duplicate jobs
        for sec in secondary_jobs:
            # Check if source already recorded
            sec_source_stmt = select(CanonicalJobSource).where(
                CanonicalJobSource.canonical_job_id == canonical.id,
                CanonicalJobSource.job_id == sec.id,
            )
            sec_src = (await db.execute(sec_source_stmt)).scalar_one_or_none()

            if not sec_src:
                sec_src = CanonicalJobSource(
                    canonical_job_id=canonical.id,
                    job_id=sec.id,
                    raw_discovery_id=sec.raw_discovery_id,
                    provider=sec.provider or "unknown",
                    external_job_id=sec.external_job_id,
                    source_url=sec.source_url,
                    application_url=sec.application_url,
                    discovered_title=sec.title,
                    discovered_location=sec.location_raw or sec.location,
                    is_primary=False,
                    first_seen_at=sec.extracted_at or now,
                    last_seen_at=sec.extracted_at or now,
                )
                db.add(sec_src)
            else:
                sec_src.last_seen_at = now

            sec.canonical_job_id = canonical.id
            sec.is_canonical_primary = False
            sec.dedup_status = "MERGED_DUPLICATE"

            # Merge fields into canonical without destroying richer information
            # Longer description
            if sec.description and len(sec.description) > len(canonical.description or ""):
                canonical.description = sec.description

            # Responsibilities & Qualifications
            merged_resp = self._combine_json_lists(canonical.responsibilities, sec.responsibilities)
            if merged_resp:
                canonical.responsibilities = json.dumps(merged_resp)

            merged_qual = self._combine_json_lists(canonical.qualifications, sec.qualifications)
            if merged_qual:
                canonical.qualifications = json.dumps(merged_qual)

            # Skills
            merged_req_skills = self._combine_skills(canonical.required_skills, sec.required_skills)
            if merged_req_skills:
                canonical.required_skills = json.dumps(merged_req_skills)

            merged_pref_skills = self._combine_skills(canonical.preferred_skills, sec.preferred_skills)
            if merged_pref_skills:
                canonical.preferred_skills = json.dumps(merged_pref_skills)

            # Salary fallback
            if canonical.salary_min is None and sec.salary_min is not None:
                canonical.salary_min = sec.salary_min
                canonical.salary_max = sec.salary_max
                canonical.salary_currency = sec.salary_currency
                canonical.salary_period = sec.salary_period

            # Last seen date (handle naive vs aware datetimes safely)
            if sec.extracted_at:
                sec_dt = sec.extracted_at.replace(tzinfo=None) if getattr(sec.extracted_at, "tzinfo", None) else sec.extracted_at
                canon_dt = canonical.last_seen_at.replace(tzinfo=None) if (canonical.last_seen_at and getattr(canonical.last_seen_at, "tzinfo", None)) else canonical.last_seen_at
                if canon_dt is None or sec_dt > canon_dt:
                    canonical.last_seen_at = sec.extracted_at

        # Update source count
        count_stmt = select(func.count(CanonicalJobSource.id)).where(
            CanonicalJobSource.canonical_job_id == canonical.id
        )
        total_sources = (await db.execute(count_stmt)).scalar() or (1 + len(secondary_jobs))
        canonical.source_count = total_sources

        # 5. Record duplicate review group if secondary jobs merged
        if secondary_jobs:
            all_ids = sorted([primary_job.id] + [s.id for s in secondary_jobs])
            group_key = f"GRP-{canonical.id}-{'-'.join(str(i) for i in all_ids)}"

            group_stmt = select(DuplicateReviewGroup).where(DuplicateReviewGroup.group_key == group_key)
            existing_group = (await db.execute(group_stmt)).scalar_one_or_none()

            dup_type = evaluation.duplicate_type if evaluation else "HIGH_CONFIDENCE_DUPLICATE"
            sim_score = evaluation.confidence_score if evaluation else 0.95
            reasons_json = json.dumps(evaluation.reasons) if evaluation else json.dumps(["exact_or_high_confidence"])

            if not existing_group:
                new_group = DuplicateReviewGroup(
                    group_key=group_key,
                    canonical_job_id=canonical.id,
                    duplicate_type=dup_type,
                    status=DuplicateGroupStatus.MERGED.value,
                    similarity_score=sim_score,
                    match_reasons=reasons_json,
                    candidate_job_ids=json.dumps(all_ids),
                    resolution_action="AUTO_MERGE",
                    resolved_by="system_merger",
                    resolved_at=now,
                )
                db.add(new_group)

        await db.commit()
        await db.refresh(canonical)
        return canonical

    async def record_pending_review_group(
        self,
        db: AsyncSession,
        job1: Job,
        job2: Job,
        evaluation: MatchEvaluation,
    ) -> DuplicateReviewGroup:
        """Records an uncertain match for manual review without automatically merging."""
        all_ids = sorted([job1.id, job2.id])
        group_key = f"REVIEW-{job1.company_id}-{'-'.join(str(i) for i in all_ids)}"

        stmt = select(DuplicateReviewGroup).where(DuplicateReviewGroup.group_key == group_key)
        existing = (await db.execute(stmt)).scalar_one_or_none()

        if existing:
            return existing

        group = DuplicateReviewGroup(
            group_key=group_key,
            canonical_job_id=job1.canonical_job_id or job2.canonical_job_id,
            duplicate_type=evaluation.duplicate_type,
            status=DuplicateGroupStatus.PENDING_REVIEW.value,
            similarity_score=evaluation.confidence_score,
            match_reasons=json.dumps(evaluation.reasons),
            candidate_job_ids=json.dumps(all_ids),
        )
        db.add(group)
        job1.dedup_status = "NEEDS_REVIEW"
        job2.dedup_status = "NEEDS_REVIEW"
        await db.commit()
        await db.refresh(group)
        return group

