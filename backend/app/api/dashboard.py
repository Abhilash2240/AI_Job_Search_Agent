# backend/app/api/dashboard.py
"""
Dashboard Analytics API Router.
Provides real-time aggregated metrics across candidates, discovery, matching,
saved jobs, and application tracking for the frontend dashboard.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from db.database import get_db
from models.canonical_job import CanonicalJob, VacancyStatus
from models.source import DiscoveredJob, Company, JobSource
from models.candidate import Candidate
from models.candidate_job_match import CandidateJobMatch, EligibilityStatus
from models.job_embedding import JobEmbedding
from models.saved_job import SavedJob
from models.application import JobApplication, ApplicationStatus
from models.pipeline_execution import PipelineExecution

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard Analytics"])


@router.get("/stats")
async def get_dashboard_stats(
    candidate_id: Optional[int] = Query(None, description="Optional candidate ID for personalized metrics"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns live aggregated system and candidate dashboard metrics.
    Guarantees no hardcoded statistics.
    """
    # System-level counts
    total_candidates = (await db.execute(select(func.count(Candidate.id)))).scalar() or 0
    total_discovered = (await db.execute(select(func.count(DiscoveredJob.id)))).scalar() or 0
    total_canonical = (await db.execute(select(func.count(CanonicalJob.id)))).scalar() or 0
    active_canonical = (
        await db.execute(
            select(func.count(CanonicalJob.id)).where(CanonicalJob.vacancy_status == VacancyStatus.ACTIVE.value)
        )
    ).scalar() or 0

    total_companies = (await db.execute(select(func.count(Company.id)))).scalar() or 0
    total_sources = (await db.execute(select(func.count(JobSource.id)))).scalar() or 0
    total_embeddings = (await db.execute(select(func.count(JobEmbedding.id)))).scalar() or 0

    # Fallback to candidate 3 (or first candidate) if none provided
    target_cand_id = candidate_id
    if not target_cand_id:
        c_res = (await db.execute(select(Candidate.id).order_by(Candidate.id.asc()).limit(1))).scalar_one_or_none()
        target_cand_id = c_res or 1

    # Candidate-specific metrics
    matches_stmt = (
        select(CandidateJobMatch, CanonicalJob)
        .join(CanonicalJob, CandidateJobMatch.canonical_job_id == CanonicalJob.id)
        .where(CandidateJobMatch.candidate_id == target_cand_id)
    )
    all_matches_with_jobs = (await db.execute(matches_stmt)).all()

    total_evaluated = len(all_matches_with_jobs)
    
    # Filter active vacancies and eligible matches
    active_matches = [
        (m, job) for m, job in all_matches_with_jobs
        if job.vacancy_status == VacancyStatus.ACTIVE.value
    ]
    eligible_matches = [
        (m, job) for m, job in active_matches
        if m.eligibility_status in {EligibilityStatus.ELIGIBLE.value, EligibilityStatus.ELIGIBLE_WITH_CONDITIONS.value}
        and getattr(m, "is_relevant", True) is True
    ]

    relevant_jobs = sum(1 for m, _ in active_matches if getattr(m, "is_relevant", True) is True and m.composite_score >= 35.0)
    highly_recommended = sum(
        1 for m, _ in eligible_matches if getattr(m, "is_relevant", True) is True and m.composite_score >= 50.0
    )

    if eligible_matches:
        # Sort by composite_score descending
        eligible_matches.sort(key=lambda pair: pair[0].composite_score, reverse=True)
        best_match, best_job = eligible_matches[0]
        top_score = best_match.composite_score
        top_score_fraction = round(top_score / 100.0, 4) if top_score > 1.0 else round(top_score, 4)
        best_job_id = best_job.id
        best_job_title = best_job.title
        best_company_name = best_job.company_name
        ts = getattr(best_match, 'evaluated_at', getattr(best_match, 'created_at', None))
        last_matching_at = ts.isoformat() if ts else None
        matching_status = "EVALUATED"
    elif total_evaluated > 0:
        top_score = None
        top_score_fraction = None
        best_job_id = None
        best_job_title = None
        best_company_name = None
        first_m = all_matches_with_jobs[0][0]
        ts = getattr(first_m, 'evaluated_at', getattr(first_m, 'created_at', None))
        last_matching_at = ts.isoformat() if ts else None
        matching_status = "NO_ELIGIBLE_MATCHES"
    else:
        top_score = None
        top_score_fraction = None
        best_job_id = None
        best_job_title = None
        best_company_name = None
        last_matching_at = None
        matching_status = "AWAITING_MATCHING"

    # Saved jobs count
    saved_count = (
        await db.execute(
            select(func.count(SavedJob.id)).where(
                and_(SavedJob.candidate_id == target_cand_id, SavedJob.is_active.is_(True))
            )
        )
    ).scalar() or 0

    # Application counts
    apps_stmt = select(JobApplication.status, func.count(JobApplication.id)).where(
        JobApplication.candidate_id == target_cand_id
    ).group_by(JobApplication.status)
    app_counts = dict((await db.execute(apps_stmt)).all())

    total_applied = sum(app_counts.values())
    interviews = app_counts.get(ApplicationStatus.INTERVIEW.value, 0)
    offers = app_counts.get(ApplicationStatus.OFFER.value, 0)
    in_review = app_counts.get(ApplicationStatus.ASSESSMENT.value, 0) + app_counts.get(ApplicationStatus.APPLIED.value, 0)

    # Recent pipeline runs
    recent_runs = (
        await db.execute(
            select(PipelineExecution).order_by(PipelineExecution.started_at.desc()).limit(3)
        )
    ).scalars().all()
    recent_runs_data = [
        {
            "run_id": r.run_id,
            "trigger": r.trigger_type,
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "jobs_discovered": r.jobs_discovered,
            "matches_computed": r.matches_computed,
        }
        for r in recent_runs
    ]

    return {
        "candidate_id": target_cand_id,
        "system": {
            "total_candidates": total_candidates,
            "total_companies": total_companies,
            "total_sources": total_sources,
            "total_discovered_jobs": total_discovered,
            "total_canonical_vacancies": total_canonical,
            "canonical_vacancies": total_canonical,
            "verified_active_vacancies": active_canonical,
            "job_embeddings": total_embeddings,
        },
        "recommendations": {
            "total_matches_evaluated": total_evaluated,
            "relevant_opportunities": relevant_jobs,
            "highly_recommended_jobs": highly_recommended,
            "top_match_score": top_score_fraction,
            "top_composite_score": top_score,
            "best_job_id": best_job_id,
            "best_job_title": best_job_title,
            "best_company_name": best_company_name,
            "eligible_matching_jobs": len(eligible_matches),
            "last_matching_at": last_matching_at,
            "matching_status": matching_status,
            "candidate_matches_count": total_evaluated,
        },
        "saved_jobs": {
            "total_saved": saved_count,
        },
        "saved": {
            "total_saved": saved_count,
        },
        "applications": {
            "total_applications": total_applied,
            "active_in_pipeline": in_review,
            "active_applications": in_review,
            "interviews_scheduled": interviews,
            "offers_received": offers,
            "status_breakdown": app_counts,
        },
        "recent_pipeline_runs": recent_runs_data,
    }

