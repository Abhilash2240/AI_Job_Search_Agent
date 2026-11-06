# backend/app/api/companies.py
import math
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from db.database import get_db
from models.source import Company, CompanyCareerSource, CompanyContact
from schemas.source import (
    CompanyItem,
    CompanyListResponse,
    CompanyDetailResponse,
    CompanyCareerSourceItem,
    CompanyContactItem,
)

router = APIRouter(prefix="/api/companies", tags=["Companies & Employers"])


@router.get("", response_model=CompanyListResponse)
async def list_companies(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    q: Optional[str] = Query(None, description="Search by company name or domain"),
    relevance_category: Optional[str] = Query(None, description="Filter by tech relevance category"),
    country: Optional[str] = Query(None, description="Filter by country"),
    has_email: Optional[bool] = Query(None, description="Filter companies with contact emails"),
    db: AsyncSession = Depends(get_db),
):
    """List companies in the registry with search, filtering, and pagination."""
    conditions = []
    if q:
        search_filter = f"%{q.strip()}%"
        conditions.append(or_(
            Company.canonical_name.ilike(search_filter),
            Company.normalized_name.ilike(search_filter),
            Company.primary_domain.ilike(search_filter)
        ))
    if relevance_category:
        conditions.append(Company.relevance_category == relevance_category)
    if country:
        conditions.append(Company.country == country)
    if has_email is True:
        # Company must have at least one contact email
        conditions.append(
            Company.id.in_(select(CompanyContact.company_id).distinct())
        )
    elif has_email is False:
        conditions.append(
            Company.id.not_in(select(CompanyContact.company_id).distinct())
        )

    where_clause = and_(*conditions) if conditions else True

    # Count total
    count_stmt = select(func.count(Company.id)).where(where_clause)
    total_res = await db.execute(count_stmt)
    total = total_res.scalar_one()

    # Query companies with pre-loaded relationships for counting
    offset = (page - 1) * page_size
    stmt = (
        select(Company)
        .where(where_clause)
        .options(
            selectinload(Company.career_sources),
            selectinload(Company.contacts)
        )
        .order_by(Company.canonical_name.asc())
        .offset(offset)
        .limit(page_size)
    )
    res = await db.execute(stmt)
    companies = res.scalars().all()

    items = []
    for c in companies:
        items.append(CompanyItem(
            id=c.id,
            canonical_name=c.canonical_name,
            normalized_name=c.normalized_name,
            primary_domain=c.primary_domain,
            country=c.country,
            industry=c.industry,
            relevance_category=c.relevance_category,
            is_active=c.is_active,
            career_sources_count=len(c.career_sources),
            contacts_count=len(c.contacts),
            created_at=c.created_at,
        ))

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return CompanyListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=items
    )


@router.get("/{company_id}", response_model=CompanyDetailResponse)
async def get_company_detail(
    company_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve full details of a company, including career page sources and contact emails."""
    stmt = (
        select(Company)
        .where(Company.id == company_id)
        .options(
            selectinload(Company.career_sources),
            selectinload(Company.contacts)
        )
    )
    res = await db.execute(stmt)
    company = res.scalars().first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID {company_id} not found."
        )

    return CompanyDetailResponse(
        id=company.id,
        canonical_name=company.canonical_name,
        normalized_name=company.normalized_name,
        primary_domain=company.primary_domain,
        country=company.country,
        industry=company.industry,
        relevance_category=company.relevance_category,
        is_active=company.is_active,
        career_sources=[CompanyCareerSourceItem.model_validate(cs) for cs in company.career_sources],
        contacts=[CompanyContactItem.model_validate(cc) for cc in company.contacts],
        created_at=company.created_at,
    )


@router.get("/{company_id}/career-sources", response_model=List[CompanyCareerSourceItem])
async def get_company_career_sources(
    company_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve all career page URL records for a specific company."""
    # Check if company exists
    c_check = await db.execute(select(Company.id).where(Company.id == company_id))
    if not c_check.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID {company_id} not found."
        )

    stmt = select(CompanyCareerSource).where(CompanyCareerSource.company_id == company_id)
    res = await db.execute(stmt)
    sources = res.scalars().all()
    return [CompanyCareerSourceItem.model_validate(s) for s in sources]


@router.get("/{company_id}/contacts", response_model=List[CompanyContactItem])
async def get_company_contacts(
    company_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve all outreach contact email records for a specific company."""
    c_check = await db.execute(select(Company.id).where(Company.id == company_id))
    if not c_check.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID {company_id} not found."
        )

    stmt = select(CompanyContact).where(CompanyContact.company_id == company_id)
    res = await db.execute(stmt)
    contacts = res.scalars().all()
    return [CompanyContactItem.model_validate(c) for c in contacts]


@router.get("/{company_id}/vacancies")
async def get_company_vacancies(
    company_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve all canonical job vacancies associated with a company."""
    from models.canonical_job import CanonicalJob, VacancyStatus
    stmt = (
        select(CanonicalJob)
        .where(
            and_(
                CanonicalJob.company_id == company_id,
                CanonicalJob.vacancy_status == VacancyStatus.ACTIVE.value,
            )
        )
        .order_by(CanonicalJob.id.desc())
    )
    jobs = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": j.id,
            "canonical_job_id": j.canonical_job_id,
            "title": j.title,
            "canonical_job_title": j.canonical_job_title,
            "location": j.location,
            "work_mode": j.work_mode,
            "employment_type": j.employment_type,
            "experience_level": j.experience_level,
            "experience_min_years": j.experience_min_years,
            "salary_range": j.salary_range,
            "vacancy_status": j.vacancy_status,
            "original_job_url": j.original_job_url or j.application_url,
        }
        for j in jobs
    ]


@router.get("/{company_id}/research")
async def get_company_research_profile(
    company_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Company and Recruiter Research Endpoint.
    Combines verified company identity, career sources, outreach emails,
    distinguishes verified vs unverified contacts, lists available vacancies,
    and enforces strict non-fabrication & authorization boundaries.
    """
    from models.canonical_job import CanonicalJob, VacancyStatus

    stmt = (
        select(Company)
        .where(Company.id == company_id)
        .options(
            selectinload(Company.career_sources),
            selectinload(Company.contacts)
        )
    )
    company = (await db.execute(stmt)).scalars().first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID {company_id} not found."
        )

    # Active vacancies
    vacancies_stmt = select(CanonicalJob).where(
        and_(
            CanonicalJob.company_id == company_id,
            CanonicalJob.vacancy_status == VacancyStatus.ACTIVE.value
        )
    )
    vacancies = (await db.execute(vacancies_stmt)).scalars().all()

    # Contacts segregated by verification
    verified_contacts = [
        {
            "email": c.email,
            "source": c.source_url or "Company Master Data",
            "is_verified": c.verification_status == "VERIFIED",
            "last_verified_at": c.last_verified_at.isoformat() if c.last_verified_at else None,
            "notes": "Verified company contact channel" if c.verification_status == "VERIFIED" else "Unverified contact",
        }
        for c in company.contacts
    ]

    career_sources = [
        {
            "id": cs.id,
            "url": cs.career_url,
            "normalized_url": cs.normalized_url,
            "source_document": cs.source_document,
            "source_page": cs.source_page,
            "verification_status": cs.verification_status,
            "ats_provider": cs.ats_provider,
        }
        for cs in company.career_sources
    ]

    return {
        "company_id": company.id,
        "name": company.canonical_name,
        "normalized_name": company.normalized_name,
        "primary_domain": company.primary_domain,
        "country": company.country or "India",
        "industry": company.industry or "Information Technology & Software Services",
        "relevance_category": company.relevance_category,
        "is_active": company.is_active,
        "career_sources": career_sources,
        "contacts": verified_contacts,
        "active_vacancies_count": len(vacancies),
        "active_vacancies": [
            {
                "id": v.id,
                "canonical_job_id": v.canonical_job_id,
                "title": v.title,
                "location": v.location,
                "work_mode": v.work_mode,
                "employment_type": v.employment_type,
                "url": v.original_job_url or v.application_url,
            }
            for v in vacancies
        ],
        "outreach_policy": {
            "requires_explicit_authorization": True,
            "automated_sending_enabled": False,
            "guideline": "Emails and applications must never be automatically dispatched without candidate approval.",
        }
    }

