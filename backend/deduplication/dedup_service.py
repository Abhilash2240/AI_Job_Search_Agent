"""
Deduplication Orchestration Service (Phase 5).
Coordinates cross-provider matching runs, resolves duplicate review groups,
and links incoming discoveries to canonical vacancies.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.canonical_job import (
    CanonicalJob,
    CanonicalJobSource,
    DuplicateReviewGroup,
    DuplicateGroupStatus,
    DuplicateType,
)
from models.job import Job
from deduplication.dedup_engine import JobDeduplicationEngine, MatchEvaluation
from deduplication.merger import CanonicalJobMerger


class JobDeduplicationService:
    """Service for running batch cross-provider deduplication and manual review resolution."""

    def __init__(self):
        self.engine = JobDeduplicationEngine()
        self.merger = CanonicalJobMerger()

    async def run_deduplication(
        self,
        db: AsyncSession,
        company_id: Optional[int] = None,
        auto_merge: bool = True,
        similarity_threshold: float = 0.85,
    ) -> Dict[str, Any]:
        """
        Runs deduplication over normalized jobs.
        Groups duplicates, automatically merges high-confidence pairs,
        and creates review groups for borderline matches.
        """
        # Configure thresholds
        self.engine.auto_merge_threshold = similarity_threshold

        query = select(Job).order_by(Job.company_id, Job.id)
        if company_id:
            query = query.where(Job.company_id == company_id)

        res = await db.execute(query)
        all_jobs: List[Job] = res.scalars().all()

        summary = {
            "total_jobs_evaluated": len(all_jobs),
            "exact_duplicates": 0,
            "high_confidence_duplicates": 0,
            "possible_duplicates": 0,
            "distinct_jobs": 0,
            "needs_manual_review": 0,
            "canonical_jobs_created": 0,
            "jobs_merged": 0,
            "review_groups_created": 0,
        }

        if not all_jobs:
            return summary

        # Partition jobs by company to prevent cross-company comparisons
        by_company: Dict[int, List[Job]] = {}
        for j in all_jobs:
            cid = j.company_id or 0
            by_company.setdefault(cid, []).append(j)

        # Track which jobs have been assigned to a canonical vacancy in this run
        merged_job_ids = set()

        for cid, company_jobs in by_company.items():
            n = len(company_jobs)
            for i in range(n):
                job_a = company_jobs[i]
                if job_a.id in merged_job_ids:
                    continue

                duplicate_batch: List[Tuple[Job, MatchEvaluation]] = []

                for j in range(i + 1, n):
                    job_b = company_jobs[j]
                    if job_b.id in merged_job_ids:
                        continue

                    evaluation = self.engine.evaluate_pair(job_a, job_b)

                    if evaluation.duplicate_type == DuplicateType.EXACT_DUPLICATE.value:
                        summary["exact_duplicates"] += 1
                        duplicate_batch.append((job_b, evaluation))
                    elif evaluation.duplicate_type == DuplicateType.HIGH_CONFIDENCE_DUPLICATE.value:
                        summary["high_confidence_duplicates"] += 1
                        if evaluation.can_auto_merge and auto_merge:
                            duplicate_batch.append((job_b, evaluation))
                        else:
                            # Flag for review
                            summary["needs_manual_review"] += 1
                            await self.merger.record_pending_review_group(db, job_a, job_b, evaluation)
                            summary["review_groups_created"] += 1
                    elif evaluation.duplicate_type in (
                        DuplicateType.POSSIBLE_DUPLICATE.value,
                        DuplicateType.NEEDS_MANUAL_REVIEW.value,
                    ):
                        if evaluation.duplicate_type == DuplicateType.POSSIBLE_DUPLICATE.value:
                            summary["possible_duplicates"] += 1
                        else:
                            summary["needs_manual_review"] += 1
                        await self.merger.record_pending_review_group(db, job_a, job_b, evaluation)
                        summary["review_groups_created"] += 1
                    else:
                        summary["distinct_jobs"] += 1

                # If we found duplicates to merge with job_a
                secondary_jobs_to_merge = [job for job, eval_obj in duplicate_batch]
                best_eval = duplicate_batch[0][1] if duplicate_batch else None

                if not job_a.canonical_job_id or secondary_jobs_to_merge:
                    canonical = await self.merger.merge_or_create_canonical(
                        db=db,
                        primary_job=job_a,
                        secondary_jobs=secondary_jobs_to_merge,
                        evaluation=best_eval,
                    )
                    if not job_a.canonical_job_id:
                        summary["canonical_jobs_created"] += 1

                for sec in secondary_jobs_to_merge:
                    merged_job_ids.add(sec.id)
                    summary["jobs_merged"] += 1

        return summary

    async def resolve_duplicate_group(
        self,
        db: AsyncSession,
        group_id: int,
        action: str,  # "MERGE", "REJECT_DISTINCT", "KEEP_SEPARATE"
        notes: Optional[str] = None,
        resolved_by: str = "manual_user",
    ) -> DuplicateReviewGroup:
        """
        Resolves a manual duplicate review group safely with full transaction handling.
        """
        stmt = select(DuplicateReviewGroup).where(DuplicateReviewGroup.id == group_id)
        group = (await db.execute(stmt)).scalar_one_or_none()

        if not group:
            raise ValueError(f"Duplicate review group {group_id} not found.")

        job_ids = json.loads(group.candidate_job_ids)
        if not job_ids:
            group.status = DuplicateGroupStatus.RESOLVED.value
            await db.commit()
            return group

        # Fetch member jobs
        jobs_stmt = select(Job).where(Job.id.in_(job_ids))
        member_jobs = (await db.execute(jobs_stmt)).scalars().all()

        now = datetime.now(timezone.utc)
        action_upper = action.strip().upper()

        if action_upper == "MERGE":
            primary_job = member_jobs[0]
            secondary_jobs = member_jobs[1:]
            canonical = await self.merger.merge_or_create_canonical(
                db=db,
                primary_job=primary_job,
                secondary_jobs=secondary_jobs,
                evaluation=MatchEvaluation(
                    duplicate_type=group.duplicate_type,
                    confidence_score=group.similarity_score,
                    reasons=["manually_confirmed_merge"],
                    can_auto_merge=True,
                ),
            )
            group.canonical_job_id = canonical.id
            group.status = DuplicateGroupStatus.MERGED.value
            group.resolution_action = "MERGE"
        elif action_upper == "REJECT_DISTINCT":
            for j in member_jobs:
                if not j.canonical_job_id:
                    # Create distinct canonical job for each
                    await self.merger.merge_or_create_canonical(db=db, primary_job=j)
                j.dedup_status = "CANONICAL"
            group.status = DuplicateGroupStatus.REJECTED.value
            group.resolution_action = "REJECT_DISTINCT"
        else:  # KEEP_SEPARATE
            group.status = DuplicateGroupStatus.RESOLVED.value
            group.resolution_action = "KEEP_SEPARATE"

        group.resolution_notes = notes
        group.resolved_by = resolved_by
        group.resolved_at = now

        await db.commit()
        await db.refresh(group)
        return group


deduplication_service = JobDeduplicationService()

