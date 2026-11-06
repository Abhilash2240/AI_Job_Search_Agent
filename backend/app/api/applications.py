# backend/app/api/applications.py
"""
Job Applications Tracker API Endpoints.
Provides complete application lifecycle tracking: status transitions,
interview scheduling, follow-ups, duplicate protection, and pipeline statistics.
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from db.database import get_db
from models.application import JobApplication, ApplicationStatus, ApplicationStatusHistory
from models.canonical_job import CanonicalJob
from models.candidate import Candidate
from schemas.application import (
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationStatusUpdate,
    ApplicationResponse,
    ApplicationListResponse,
    ApplicationStatsResponse,
    ApplicationStatusHistoryItem,
)

router = APIRouter(prefix="/api/applications", tags=["Job Applications"])


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(
    req: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new application tracking record.
    Guarantees no duplicate applications for the same candidate and canonical job.
    """
    # Verify candidate exists
    cand = (await db.execute(select(Candidate).where(Candidate.id == req.candidate_id))).scalar_one_or_none()
    if not cand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Candidate {req.candidate_id} not found")

    # If canonical_job_id provided, check for existing application
    if req.canonical_job_id:
        existing = (
            await db.execute(
                select(JobApplication).where(
                    and_(
                        JobApplication.candidate_id == req.candidate_id,
                        JobApplication.canonical_job_id == req.canonical_job_id,
                    )
                )
            )
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Application for canonical job {req.canonical_job_id} already exists (ID: {existing.id}, Status: {existing.status})",
            )

    applied_date = req.applied_at or datetime.now(timezone.utc)
    app_status = req.status or ApplicationStatus.APPLIED.value

    app_record = JobApplication(
        candidate_id=req.candidate_id,
        canonical_job_id=req.canonical_job_id,
        company_name=req.company_name,
        job_title=req.job_title,
        application_url=req.application_url,
        status=app_status,
        applied_at=applied_date,
        notes=req.notes,
        interview_date=req.interview_date,
        follow_up_date=req.follow_up_date,
        salary_offered=req.salary_offered,
    )
    db.add(app_record)
    await db.flush()

    # Record initial status in history
    history = ApplicationStatusHistory(
        application_id=app_record.id,
        from_status=None,
        to_status=app_status,
        notes="Application record created",
    )
    db.add(history)
    await db.commit()
    await db.refresh(app_record)

    return await _load_full_application(app_record.id, db)


@router.get("/candidate/{candidate_id}", response_model=ApplicationListResponse)
async def list_applications_for_candidate(
    candidate_id: int,
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all job applications for a candidate with optional filtering."""
    stmt = (
        select(JobApplication)
        .options(selectinload(JobApplication.status_history))
        .where(JobApplication.candidate_id == candidate_id)
        .order_by(JobApplication.updated_at.desc())
    )
    if status_filter:
        stmt = stmt.where(JobApplication.status == status_filter.upper())

    records = (await db.execute(stmt)).scalars().all()

    items = []
    for app in records:
        if search:
            term = search.lower()
            if term not in (app.company_name or "").lower() and term not in (app.job_title or "").lower():
                continue
        items.append(_serialize_application(app))

    return ApplicationListResponse(total=len(items), items=items)


@router.get("/candidate/{candidate_id}/stats", response_model=ApplicationStatsResponse)
async def get_application_stats_for_candidate(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Compute live application pipeline metrics and interview response rates."""
    stmt = select(JobApplication.status, func.count(JobApplication.id)).where(
        JobApplication.candidate_id == candidate_id
    ).group_by(JobApplication.status)

    counts = dict((await db.execute(stmt)).all())

    total = sum(counts.values())
    interviews = counts.get(ApplicationStatus.INTERVIEW.value, 0)
    offers = counts.get(ApplicationStatus.OFFER.value, 0)
    assessments = counts.get(ApplicationStatus.ASSESSMENT.value, 0)
    applied = counts.get(ApplicationStatus.APPLIED.value, 0)

    active_in_pipeline = interviews + offers + assessments + applied
    # Response rate = (assessments + interviews + offers) / total applied
    responses = assessments + interviews + offers
    response_rate = round((responses / total * 100.0), 1) if total > 0 else 0.0

    return ApplicationStatsResponse(
        total_applications=total,
        by_status=counts,
        interviews_scheduled=interviews,
        offers_received=offers,
        active_in_pipeline=active_in_pipeline,
        response_rate_percent=response_rate,
    )


@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_application_detail(
    application_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get single application detail with status history."""
    return await _load_full_application(application_id, db)


@router.patch("/{application_id}/status", response_model=ApplicationResponse)
async def update_application_status(
    application_id: int,
    req: ApplicationStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Transition an application's lifecycle status and record history."""
    app_record = (await db.execute(select(JobApplication).where(JobApplication.id == application_id))).scalar_one_or_none()
    if not app_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Application {application_id} not found")

    old_status = app_record.status
    new_status = req.status.upper()

    if old_status != new_status:
        app_record.status = new_status
        history = ApplicationStatusHistory(
            application_id=app_record.id,
            from_status=old_status,
            to_status=new_status,
            notes=req.notes or f"Status changed from {old_status} to {new_status}",
        )
        db.add(history)
        await db.commit()
        await db.refresh(app_record)

    return await _load_full_application(application_id, db)


@router.put("/{application_id}", response_model=ApplicationResponse)
async def update_application(
    application_id: int,
    req: ApplicationUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update application details, scheduled interviews, follow-ups, or notes."""
    app_record = (await db.execute(select(JobApplication).where(JobApplication.id == application_id))).scalar_one_or_none()
    if not app_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Application {application_id} not found")

    if req.company_name:
        app_record.company_name = req.company_name
    if req.job_title:
        app_record.job_title = req.job_title
    if req.application_url is not None:
        app_record.application_url = req.application_url
    if req.notes is not None:
        app_record.notes = req.notes
    if req.interview_date is not None:
        app_record.interview_date = req.interview_date
    if req.follow_up_date is not None:
        app_record.follow_up_date = req.follow_up_date
    if req.salary_offered is not None:
        app_record.salary_offered = req.salary_offered

    if req.status and req.status.upper() != app_record.status:
        old_status = app_record.status
        app_record.status = req.status.upper()
        history = ApplicationStatusHistory(
            application_id=app_record.id,
            from_status=old_status,
            to_status=app_record.status,
            notes=req.notes or "Updated via application edit",
        )
        db.add(history)

    await db.commit()
    await db.refresh(app_record)
    return await _load_full_application(application_id, db)


@router.delete("/{application_id}", status_code=status.HTTP_200_OK)
async def delete_application(
    application_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete an application record."""
    app_record = (await db.execute(select(JobApplication).where(JobApplication.id == application_id))).scalar_one_or_none()
    if not app_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Application {application_id} not found")

    await db.delete(app_record)
    await db.commit()
    return {"status": "SUCCESS", "message": f"Application {application_id} deleted successfully"}


async def _load_full_application(app_id: int, db: AsyncSession) -> ApplicationResponse:
    stmt = (
        select(JobApplication)
        .options(selectinload(JobApplication.status_history))
        .where(JobApplication.id == app_id)
    )
    record = (await db.execute(stmt)).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Application {app_id} not found")
    return _serialize_application(record)


def _serialize_application(app: JobApplication) -> ApplicationResponse:
    history_items = []
    if app.status_history:
        for h in app.status_history:
            history_items.append(
                ApplicationStatusHistoryItem(
                    id=h.id,
                    application_id=h.application_id,
                    from_status=h.from_status,
                    to_status=h.to_status,
                    notes=h.notes,
                    changed_at=h.changed_at,
                )
            )

    return ApplicationResponse(
        id=app.id,
        candidate_id=app.candidate_id,
        canonical_job_id=app.canonical_job_id,
        company_name=app.company_name,
        job_title=app.job_title,
        application_url=app.application_url,
        status=app.status,
        applied_at=app.applied_at,
        notes=app.notes,
        interview_date=app.interview_date,
        follow_up_date=app.follow_up_date,
        salary_offered=app.salary_offered,
        created_at=app.created_at,
        updated_at=app.updated_at,
        status_history=history_items,
    )

