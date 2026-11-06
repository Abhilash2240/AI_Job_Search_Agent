# backend/app/api/saved_jobs.py
"""
Saved Jobs API Endpoints.
Allows candidates to save, unsave, filter, and monitor bookmarked canonical vacancies.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from db.database import get_db
from models.saved_job import SavedJob
from models.canonical_job import CanonicalJob, VacancyStatus
from models.candidate import Candidate
from schemas.saved_job import (
    SavedJobCreate,
    SavedJobUpdate,
    SavedJobResponse,
    SavedJobListResponse,
    CanonicalJobSummary,
)

router = APIRouter(prefix="/api/saved-jobs", tags=["Saved Jobs"])


@router.post("", response_model=SavedJobResponse, status_code=status.HTTP_201_CREATED)
async def save_job(
    req: SavedJobCreate,
    db: AsyncSession = Depends(get_db),
):
    """Save/bookmark a canonical job vacancy for a candidate."""
    # Verify candidate exists
    cand = (await db.execute(select(Candidate).where(Candidate.id == req.candidate_id))).scalar_one_or_none()
    if not cand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Candidate {req.candidate_id} not found")

    # Verify canonical job exists
    job = (await db.execute(select(CanonicalJob).where(CanonicalJob.id == req.canonical_job_id))).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Canonical job {req.canonical_job_id} not found")

    # Check if already saved
    stmt = select(SavedJob).where(
        and_(
            SavedJob.candidate_id == req.candidate_id,
            SavedJob.canonical_job_id == req.canonical_job_id,
        )
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            if req.notes:
                existing.notes = req.notes
            await db.commit()
            await db.refresh(existing)
        return _serialize_saved_job(existing, job)

    saved = SavedJob(
        candidate_id=req.candidate_id,
        canonical_job_id=req.canonical_job_id,
        notes=req.notes,
        is_active=True,
    )
    db.add(saved)
    await db.commit()
    await db.refresh(saved)
    return _serialize_saved_job(saved, job)


@router.get("/candidate/{candidate_id}", response_model=SavedJobListResponse)
async def get_saved_jobs_for_candidate(
    candidate_id: int,
    active_only: bool = Query(True, description="Only return active bookmarks"),
    search: Optional[str] = Query(None, description="Search by title or company"),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve saved jobs for a candidate with vacancy status checks."""
    stmt = (
        select(SavedJob)
        .options(selectinload(SavedJob.canonical_job))
        .where(SavedJob.candidate_id == candidate_id)
    )
    if active_only:
        stmt = stmt.where(SavedJob.is_active.is_(True))

    stmt = stmt.order_by(SavedJob.created_at.desc())
    records = (await db.execute(stmt)).scalars().all()

    items = []
    for s in records:
        job = s.canonical_job
        if search and job:
            term = search.lower()
            if term not in (job.title or "").lower() and term not in (job.company_name or "").lower():
                continue
        items.append(_serialize_saved_job(s, job))

    return SavedJobListResponse(total=len(items), items=items)


@router.delete("/candidate/{candidate_id}/job/{canonical_job_id}", status_code=status.HTTP_200_OK)
async def unsave_job(
    candidate_id: int,
    canonical_job_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Unsave/remove a canonical job bookmark."""
    stmt = select(SavedJob).where(
        and_(
            SavedJob.candidate_id == candidate_id,
            SavedJob.canonical_job_id == canonical_job_id,
        )
    )
    saved = (await db.execute(stmt)).scalar_one_or_none()
    if not saved:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved job not found")

    saved.is_active = False
    await db.commit()
    return {"status": "SUCCESS", "message": "Job unsaved successfully"}


@router.patch("/{saved_job_id}", response_model=SavedJobResponse)
async def update_saved_job(
    saved_job_id: int,
    req: SavedJobUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update notes or active status for a saved job."""
    stmt = (
        select(SavedJob)
        .options(selectinload(SavedJob.canonical_job))
        .where(SavedJob.id == saved_job_id)
    )
    saved = (await db.execute(stmt)).scalar_one_or_none()
    if not saved:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved job record not found")

    if req.notes is not None:
        saved.notes = req.notes
    if req.is_active is not None:
        saved.is_active = req.is_active

    await db.commit()
    await db.refresh(saved)
    return _serialize_saved_job(saved, saved.canonical_job)


def _serialize_saved_job(saved: SavedJob, job: Optional[CanonicalJob]) -> SavedJobResponse:
    job_summary = None
    if job:
        salary_str = None
        if job.salary_min or job.salary_max:
            salary_str = f"{job.salary_currency or 'INR'} {job.salary_min or 0:,.0f} - {job.salary_max or 0:,.0f}"

        job_summary = CanonicalJobSummary(
            id=job.id,
            canonical_job_id=job.canonical_job_id,
            title=job.title,
            company_name=job.company_name,
            location=job.location,
            workplace_type=job.workplace_type,
            employment_type=job.employment_type,
            vacancy_status=job.vacancy_status,
            is_active=job.vacancy_status == VacancyStatus.ACTIVE.value,
            salary_range=salary_str,
            stipend_range=None,
        )

    return SavedJobResponse(
        id=saved.id,
        candidate_id=saved.candidate_id,
        canonical_job_id=saved.canonical_job_id,
        notes=saved.notes,
        is_active=saved.is_active,
        created_at=saved.created_at,
        updated_at=saved.updated_at,
        job=job_summary,
    )

