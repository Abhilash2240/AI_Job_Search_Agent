# backend/app/api/sources.py
import math
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from db.database import get_db
from models.source import (
    JobSource,
    Company,
    CompanyCareerSource,
    CompanyContact,
    SourceImportBatch,
)
from schemas.source import (
    JobSourceItem,
    JobSourceListResponse,
    SourcesSummaryResponse,
    SourceImportBatchItem,
)

router = APIRouter(prefix="/api/sources", tags=["Job Discovery Sources"])


@router.get("", response_model=JobSourceListResponse)
async def list_sources(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    q: Optional[str] = Query(None, description="Search by name or URL"),
    category: Optional[str] = Query(None, description="Filter by job category"),
    country_scope: Optional[str] = Query(None, description="Filter by geographic scope"),
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    is_active: Optional[bool] = Query(None, description="Filter active status"),
    db: AsyncSession = Depends(get_db),
):
    """List registered job discovery portal sources with filtering and pagination."""
    conditions = []
    if q:
        search_filter = f"%{q.strip()}%"
        conditions.append(or_(
            JobSource.name.ilike(search_filter),
            JobSource.base_url.ilike(search_filter),
            JobSource.normalized_url.ilike(search_filter)
        ))
    if category:
        conditions.append(JobSource.category == category)
    if country_scope:
        conditions.append(JobSource.country_scope == country_scope)
    if source_type:
        conditions.append(JobSource.source_type == source_type)
    if is_active is not None:
        conditions.append(JobSource.is_active == is_active)

    where_clause = and_(*conditions) if conditions else True

    # Count total matching
    count_stmt = select(func.count(JobSource.id)).where(where_clause)
    total_res = await db.execute(count_stmt)
    total = total_res.scalar_one()

    # Query paginated rows
    offset = (page - 1) * page_size
    stmt = (
        select(JobSource)
        .where(where_clause)
        .order_by(JobSource.id.asc())
        .offset(offset)
        .limit(page_size)
    )
    res = await db.execute(stmt)
    sources = res.scalars().all()

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return JobSourceListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=[JobSourceItem.model_validate(s) for s in sources]
    )


@router.get("/summary", response_model=SourcesSummaryResponse)
async def get_sources_summary(db: AsyncSession = Depends(get_db)):
    """Retrieve high-level statistics across all job portals, companies, career URLs, and contacts."""
    # Total job boards
    js_count = (await db.execute(select(func.count(JobSource.id)))).scalar_one()
    
    # Total companies
    c_count = (await db.execute(select(func.count(Company.id)))).scalar_one()

    # Total career sources
    cs_count = (await db.execute(select(func.count(CompanyCareerSource.id)))).scalar_one()

    # Total contacts
    cc_count = (await db.execute(select(func.count(CompanyContact.id)))).scalar_one()

    # Portal category breakdown
    cat_stmt = select(JobSource.category, func.count(JobSource.id)).group_by(JobSource.category)
    cat_rows = (await db.execute(cat_stmt)).all()
    categories_breakdown = {row[0] or "Uncategorized": row[1] for row in cat_rows}

    # Verification status breakdown across career sources
    ver_stmt = select(CompanyCareerSource.verification_status, func.count(CompanyCareerSource.id)).group_by(CompanyCareerSource.verification_status)
    ver_rows = (await db.execute(ver_stmt)).all()
    verification_breakdown = {row[0] or "NOT_CHECKED": row[1] for row in ver_rows}

    # Relevance category breakdown across companies
    rel_stmt = select(Company.relevance_category, func.count(Company.id)).group_by(Company.relevance_category)
    rel_rows = (await db.execute(rel_stmt)).all()
    relevance_breakdown = {row[0] or "Unknown": row[1] for row in rel_rows}

    return SourcesSummaryResponse(
        total_sources=js_count + cs_count,
        total_job_boards=js_count,
        total_companies=c_count,
        total_career_sources=cs_count,
        total_contact_emails=cc_count,
        categories=categories_breakdown,
        verification_breakdown=verification_breakdown,
        relevance_breakdown=relevance_breakdown,
    )


@router.get("/import-batches", response_model=List[SourceImportBatchItem])
async def list_import_batches(db: AsyncSession = Depends(get_db)):
    """Retrieve the audit log of all source import batches."""
    stmt = select(SourceImportBatch).order_by(SourceImportBatch.id.desc())
    res = await db.execute(stmt)
    batches = res.scalars().all()
    return [SourceImportBatchItem.model_validate(b) for b in batches]

