"""
Job Discovery API Endpoints (Phase 4B).
Provides endpoints to trigger, monitor, inspect, and query discovered job postings.
"""

import math
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from db.database import get_db
from discovery.discovery_orchestrator import discovery_orchestrator
from models.source import Company, DiscoveredJob
from schemas.discovery import (
    DiscoveryRunRequest,
    SingleCompanyDiscoveryRequest,
    DiscoveredJobItem,
    DiscoveredJobListResponse,
    DiscoveryProviderInfo,
    DiscoveryStatusResponse,
    DiscoverySummaryResponse,
)

router = APIRouter(prefix="/api/discovery", tags=["Job Discovery"])


@router.post("/run", response_model=DiscoveryStatusResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_discovery_run(
    request: DiscoveryRunRequest,
    background_tasks: BackgroundTasks,
):
    """
    Triggers job discovery across registered companies.
    Can be run as a background task (recommended) or synchronously.
    """
    current_status = discovery_orchestrator.get_status()
    if current_status.get("status") == "RUNNING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A job discovery run is already in progress.",
        )

    if request.background:
        started = discovery_orchestrator.trigger_background_run(
            company_ids=request.company_ids,
            limit=request.limit,
            dry_run=request.dry_run,
            candidate_id=request.candidate_id,
            filter_targeting=request.filter_targeting,
        )
        if not started:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Could not start discovery run: another job is running.",
            )
        return DiscoveryStatusResponse(
            status="RUNNING",
            message=f"Discovery job dispatched in background for {len(request.company_ids) if request.company_ids else 'all'} companies.",
        )
    else:
        # Run synchronously
        summary = await discovery_orchestrator.run_discovery(
            company_ids=request.company_ids,
            limit=request.limit,
            dry_run=request.dry_run,
            candidate_id=request.candidate_id,
            filter_targeting=request.filter_targeting,
        )
        return DiscoveryStatusResponse(**summary)


@router.post("/run/company/{company_id}", response_model=DiscoveryStatusResponse)
async def run_discovery_for_company(
    company_id: int,
    request: SingleCompanyDiscoveryRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Executes immediate job discovery for a specific company by ID.
    """
    stmt = select(Company).where(Company.id == company_id)
    res = await db.execute(stmt)
    company = res.scalar_one_or_none()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID {company_id} does not exist.",
        )

    summary = await discovery_orchestrator.run_discovery(
        company_ids=[company_id],
        limit=1,
        dry_run=request.dry_run,
        candidate_id=request.candidate_id,
        filter_targeting=False,
    )
    return DiscoveryStatusResponse(**summary)


@router.get("/status", response_model=DiscoveryStatusResponse)
async def get_discovery_status():
    """
    Returns the current execution state or the summary of the last completed run.
    """
    return discovery_orchestrator.get_status()


@router.get("/providers", response_model=List[DiscoveryProviderInfo])
async def list_discovery_providers():
    """
    Returns registered discovery providers, connection health, and operational limits.
    """
    return await discovery_orchestrator.get_providers_status()


@router.get("/results", response_model=DiscoveredJobListResponse)
async def list_discovered_jobs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    company_id: Optional[int] = Query(None, description="Filter by company ID"),
    provider: Optional[str] = Query(None, description="Filter by discovery provider"),
    q: Optional[str] = Query(None, description="Search title or department"),
    location: Optional[str] = Query(None, description="Filter by location"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by discovery status"),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns a paginated list of discovered vacancies with optional filtering.
    """
    conditions = []
    if company_id:
        conditions.append(DiscoveredJob.company_id == company_id)
    if provider:
        conditions.append(DiscoveredJob.provider == provider.lower().strip())
    if status_filter:
        conditions.append(DiscoveredJob.discovery_status == status_filter.upper().strip())
    if location:
        conditions.append(DiscoveredJob.discovered_location.ilike(f"%{location.strip()}%"))
    if q:
        search_filter = f"%{q.strip()}%"
        conditions.append(
            or_(
                DiscoveredJob.discovered_title.ilike(search_filter),
                DiscoveredJob.department.ilike(search_filter),
            )
        )

    where_clause = and_(*conditions) if conditions else True

    # Count matching
    count_stmt = select(func.count(DiscoveredJob.id)).where(where_clause)
    count_res = await db.execute(count_stmt)
    total = count_res.scalar_one()

    total_pages = math.ceil(total / page_size) if total > 0 else 0
    offset = (page - 1) * page_size

    # Fetch items with joined Company
    items_stmt = (
        select(DiscoveredJob)
        .options(selectinload(DiscoveredJob.company))
        .where(where_clause)
        .order_by(DiscoveredJob.last_discovered_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    items_res = await db.execute(items_stmt)
    discovered_jobs = items_res.scalars().all()

    items = [
        DiscoveredJobItem(
            id=job.id,
            company_id=job.company_id,
            company_name=job.company.name if job.company else None,
            provider=job.provider,
            external_job_id=job.external_job_id,
            discovered_title=job.discovered_title,
            discovered_location=job.discovered_location,
            department=job.department,
            job_url=job.job_url,
            application_url=job.application_url,
            source_url=job.source_url,
            discovery_status=job.discovery_status,
            first_discovered_at=job.first_discovered_at,
            last_discovered_at=job.last_discovered_at,
        )
        for job in discovered_jobs
    ]

    return DiscoveredJobListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=items,
    )


@router.get("/summary", response_model=DiscoverySummaryResponse)
async def get_discovery_summary(db: AsyncSession = Depends(get_db)):
    """
    Returns aggregated metrics on discovered jobs, providers, and coverage.
    """
    # Total jobs
    total_res = await db.execute(select(func.count(DiscoveredJob.id)))
    total_jobs = total_res.scalar_one()

    # Active jobs
    active_res = await db.execute(
        select(func.count(DiscoveredJob.id)).where(DiscoveredJob.discovery_status == "ACTIVE")
    )
    active_jobs = active_res.scalar_one()

    # Jobs by provider
    provider_stmt = select(DiscoveredJob.provider, func.count(DiscoveredJob.id)).group_by(DiscoveredJob.provider)
    provider_res = await db.execute(provider_stmt)
    by_provider = {row[0]: row[1] for row in provider_res.all()}

    # Companies with at least one discovered job
    companies_res = await db.execute(
        select(func.count(func.distinct(DiscoveredJob.company_id)))
    )
    companies_with_jobs = companies_res.scalar_one()

    last_run = discovery_orchestrator.get_status()

    return DiscoverySummaryResponse(
        total_discovered_jobs=total_jobs,
        active_jobs=active_jobs,
        jobs_by_provider=by_provider,
        companies_with_jobs=companies_with_jobs,
        last_run=last_run if last_run.get("status") != "IDLE" else None,
    )

