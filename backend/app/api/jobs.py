"""
Normalized Jobs & Extraction API Endpoints (Phase 4C).
Provides endpoints to trigger, inspect, filter, and monitor normalized job postings.
"""

import json
import math
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from db.database import get_db, AsyncSessionLocal
from jobs.extraction_service import extraction_service
from jobs.job_schema import (
    JobExtractionRequest,
    SingleJobExtractionRequest,
    NormalizedJobItem,
    NormalizedJobListResponse,
    ExtractionSummaryResponse,
    SkillWithEvidence,
)
from models.job import Job
from models.source import DiscoveredJob
from models.job_embedding import JobEmbedding, EmbeddingStatus
from embeddings.job_embedder import job_embedding_service
from schemas.job_embedding import (
    JobEmbeddingItem,
    JobEmbeddingBatchRequest,
    JobEmbeddingSummaryResponse,
    JobEmbeddingBatchResponse,
    JobEmbeddingListResponse,
    RetryFailedRequest,
    RetryFailedResponse,
)

router = APIRouter(prefix="/api/jobs", tags=["Normalized Jobs"])


def _serialize_job(job: Job) -> NormalizedJobItem:
    """Helper to convert Job ORM entity into NormalizedJobItem Pydantic schema."""
    resp = json.loads(job.responsibilities) if job.responsibilities else []
    qual = json.loads(job.qualifications) if job.qualifications else []
    
    req_skills_raw = json.loads(job.required_skills) if job.required_skills else []
    pref_skills_raw = json.loads(job.preferred_skills) if job.preferred_skills else []
    
    req_skills = [SkillWithEvidence(**s) if isinstance(s, dict) else SkillWithEvidence(skill_name=str(s), canonical_name=str(s), category="Tools", evidence_snippet="") for s in req_skills_raw]
    pref_skills = [SkillWithEvidence(**s) if isinstance(s, dict) else SkillWithEvidence(skill_name=str(s), canonical_name=str(s), category="Tools", evidence_snippet="", is_required=False) for s in pref_skills_raw]

    elig_locs = json.loads(job.eligible_locations) if job.eligible_locations else []
    degrees = json.loads(job.degree_requirements) if job.degree_requirements else []
    majors = json.loads(job.field_of_study) if job.field_of_study else []
    missing = json.loads(job.missing_fields) if job.missing_fields else []

    return NormalizedJobItem(
        id=job.id,
        company_id=job.company_id,
        company_name=job.company_rel.name if job.company_rel else job.company,
        external_job_id=job.external_job_id,
        canonical_job_title=job.canonical_job_title,
        title=job.title,
        description=job.description,
        responsibilities=resp,
        qualifications=qual,
        required_skills=req_skills,
        preferred_skills=pref_skills,
        employment_type=job.employment_type,
        experience_min_years=job.experience_min_years,
        experience_max_years=job.experience_max_years,
        seniority_level=job.seniority_level,
        workplace_type=job.workplace_type,
        location_raw=job.location_raw,
        city=job.city,
        state=job.state,
        country=job.country,
        is_remote=job.is_remote,
        eligible_locations=elig_locs,
        degree_requirements=degrees,
        field_of_study=majors,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        salary_currency=job.salary_currency,
        salary_period=job.salary_period,
        application_url=job.application_url,
        source_url=job.source_url,
        provider=job.provider,
        extraction_status=job.extraction_status,
        extraction_confidence=job.extraction_confidence,
        missing_fields=missing,
        discovered_at=job.discovered_at,
        extracted_at=job.extracted_at,
    )


@router.post("/extract", status_code=status.HTTP_200_OK)
async def extract_discovered_jobs(
    request: JobExtractionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Triggers description extraction and normalization over discovered job postings.
    Can be run as a background task or synchronously.
    """
    if request.background:
        async def run_bg():
            async with AsyncSessionLocal() as session:
                await extraction_service.batch_extract(
                    db=session,
                    discovered_job_ids=request.discovered_job_ids,
                    limit=request.limit,
                    force_reextract=request.force_reextract,
                )

        background_tasks.add_task(run_bg)
        return {
            "status": "PROCESSING",
            "message": "Job description extraction dispatched in background.",
        }
    else:
        results = await extraction_service.batch_extract(
            db=db,
            discovered_job_ids=request.discovered_job_ids,
            limit=request.limit,
            force_reextract=request.force_reextract,
        )
        return {
            "status": "COMPLETED",
            **results,
        }


@router.post("/extract/{discovered_job_id}", response_model=NormalizedJobItem)
async def extract_single_discovered_job(
    discovered_job_id: int,
    request: SingleJobExtractionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Extracts and normalizes a single discovered job by ID.
    """
    stmt = (
        select(DiscoveredJob)
        .options(selectinload(DiscoveredJob.company))
        .where(DiscoveredJob.id == discovered_job_id)
    )
    res = await db.execute(stmt)
    discovered_job = res.scalar_one_or_none()
    if not discovered_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discovered job with ID {discovered_job_id} not found.",
        )

    job_record = await extraction_service.extract_from_discovered_job(
        discovered_job=discovered_job,
        db=db,
        force_reextract=request.force_reextract,
    )
    return _serialize_job(job_record)


@router.get("/normalized", response_model=NormalizedJobListResponse)
async def list_normalized_jobs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    q: Optional[str] = Query(None, description="Search title or description"),
    company_id: Optional[int] = Query(None, description="Filter by company ID"),
    seniority: Optional[str] = Query(None, description="Filter by seniority level"),
    is_remote: Optional[bool] = Query(None, description="Filter remote status"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter extraction status"),
    provider: Optional[str] = Query(None, description="Filter provider"),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns a paginated list of normalized job records with multi-criteria filtering.
    """
    conditions = []
    if company_id:
        conditions.append(Job.company_id == company_id)
    if seniority:
        conditions.append(Job.seniority_level == seniority.upper().strip())
    if is_remote is not None:
        conditions.append(Job.is_remote == is_remote)
    if status_filter:
        conditions.append(Job.extraction_status == status_filter.upper().strip())
    if provider:
        conditions.append(Job.provider == provider.lower().strip())
    if q:
        search_kw = f"%{q.strip()}%"
        conditions.append(
            or_(
                Job.canonical_job_title.ilike(search_kw),
                Job.title.ilike(search_kw),
                Job.description.ilike(search_kw),
            )
        )

    where_clause = and_(*conditions) if conditions else True

    # Total count
    count_stmt = select(func.count(Job.id)).where(where_clause)
    count_res = await db.execute(count_stmt)
    total = count_res.scalar_one()

    total_pages = math.ceil(total / page_size) if total > 0 else 0
    offset = (page - 1) * page_size

    # Fetch jobs with joined company
    stmt = (
        select(Job)
        .options(selectinload(Job.company_rel))
        .where(where_clause)
        .order_by(Job.extracted_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    res = await db.execute(stmt)
    jobs = res.scalars().all()

    items = [_serialize_job(j) for j in jobs]

    return NormalizedJobListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=items,
    )


@router.get("/normalized/{job_id}", response_model=NormalizedJobItem)
async def get_normalized_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns single normalized job record with full structured fields and evidence.
    """
    stmt = (
        select(Job)
        .options(selectinload(Job.company_rel))
        .where(Job.id == job_id)
    )
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Normalized job with ID {job_id} not found.",
        )

    return _serialize_job(job)


@router.get("/extraction/summary", response_model=ExtractionSummaryResponse)
async def get_extraction_summary(
    db: AsyncSession = Depends(get_db),
):
    """
    Returns aggregated quality and extraction metrics across all normalized jobs.
    """
    summary = await extraction_service.get_extraction_summary(db=db)
    return ExtractionSummaryResponse(**summary)


# ============================================================================
# PHASE 5: DEDUPLICATION & VERIFICATION ENDPOINTS
# ============================================================================

from models.canonical_job import (
    CanonicalJob,
    CanonicalJobSource,
    DuplicateReviewGroup,
    DuplicateGroupStatus,
    VacancyStatus,
)
from deduplication.dedup_service import deduplication_service
from verification.vacancy_verifier import vacancy_verifier
from schemas.canonical_job import (
    CanonicalJobSourceItem,
    CanonicalJobItem,
    CanonicalJobListResponse,
    DuplicateGroupItem,
    DuplicateGroupDetail,
    DuplicateGroupListResponse,
    DuplicateResolveRequest,
    DeduplicationRunRequest,
    DeduplicationRunResponse,
    VerificationRunRequest,
    VerificationSummaryResponse,
)


def _serialize_canonical_source(s: CanonicalJobSource) -> CanonicalJobSourceItem:
    return CanonicalJobSourceItem(
        id=s.id,
        canonical_job_id=s.canonical_job_id,
        job_id=s.job_id,
        raw_discovery_id=s.raw_discovery_id,
        provider=s.provider,
        external_job_id=s.external_job_id,
        source_url=s.source_url,
        application_url=s.application_url,
        discovered_title=s.discovered_title,
        discovered_location=s.discovered_location,
        is_primary=s.is_primary,
        first_seen_at=s.first_seen_at,
        last_seen_at=s.last_seen_at,
    )


def _serialize_canonical_job(c: CanonicalJob) -> CanonicalJobItem:
    resp = json.loads(c.responsibilities) if c.responsibilities else []
    qual = json.loads(c.qualifications) if c.qualifications else []

    req_skills_raw = json.loads(c.required_skills) if c.required_skills else []
    pref_skills_raw = json.loads(c.preferred_skills) if c.preferred_skills else []

    def _parse_skill_item(s, default_required: bool = True) -> SkillWithEvidence:
        if isinstance(s, dict):
            name = s.get("skill_name") or s.get("name") or "Skill"
            canon = s.get("canonical_name") or name.lower()
            cat = s.get("category") or "Tools & Technologies"
            ev = s.get("evidence_snippet") or ""
            req = s.get("is_required", default_required)
            return SkillWithEvidence(
                skill_name=name,
                canonical_name=canon,
                category=cat,
                evidence_snippet=ev,
                is_required=req,
            )
        name = str(s)
        return SkillWithEvidence(
            skill_name=name,
            canonical_name=name.lower(),
            category="Tools & Technologies",
            evidence_snippet="",
            is_required=default_required,
        )

    req_skills = [_parse_skill_item(s, True) for s in req_skills_raw]
    pref_skills = [_parse_skill_item(s, False) for s in pref_skills_raw]

    v_details = json.loads(c.verification_details) if c.verification_details else None
    evidence = json.loads(c.match_evidence) if c.match_evidence else None
    sources = [_serialize_canonical_source(s) for s in (c.sources or [])]

    return CanonicalJobItem(
        id=c.id,
        canonical_job_id=c.canonical_job_id,
        company_id=c.company_id,
        company_name=c.company_name,
        title=c.title,
        canonical_job_title=c.canonical_job_title,
        location=c.location,
        city=c.city,
        state=c.state,
        country=c.country or "India",
        is_remote=c.is_remote,
        workplace_type=c.workplace_type,
        employment_type=c.employment_type,
        seniority_level=c.seniority_level,
        experience_min_years=c.experience_min_years,
        experience_max_years=c.experience_max_years,
        description=c.description,
        responsibilities=resp,
        qualifications=qual,
        required_skills=req_skills,
        preferred_skills=pref_skills,
        salary_min=c.salary_min,
        salary_max=c.salary_max,
        salary_currency=c.salary_currency,
        salary_period=c.salary_period,
        canonical_application_url=c.canonical_application_url,
        canonical_source_url=c.canonical_source_url,
        vacancy_status=c.vacancy_status,
        first_seen_at=c.first_seen_at,
        last_seen_at=c.last_seen_at,
        last_verified_at=c.last_verified_at,
        consecutive_missing_checks=c.consecutive_missing_checks,
        verification_attempts=c.verification_attempts,
        verification_details=v_details,
        source_count=c.source_count,
        dedup_confidence=c.dedup_confidence,
        match_evidence=evidence,
        sources=sources,
    )


def _serialize_review_group(g: DuplicateReviewGroup) -> DuplicateGroupItem:
    reasons = json.loads(g.match_reasons) if g.match_reasons else []
    candidate_ids = json.loads(g.candidate_job_ids) if g.candidate_job_ids else []
    return DuplicateGroupItem(
        id=g.id,
        group_key=g.group_key,
        canonical_job_id=g.canonical_job_id,
        duplicate_type=g.duplicate_type,
        status=g.status,
        similarity_score=g.similarity_score,
        match_reasons=reasons,
        candidate_job_ids=candidate_ids,
        resolution_action=g.resolution_action,
        resolution_notes=g.resolution_notes,
        resolved_by=g.resolved_by,
        resolved_at=g.resolved_at,
        created_at=g.created_at,
    )


@router.post("/deduplicate", response_model=DeduplicationRunResponse)
async def run_deduplication(
    request: DeduplicationRunRequest = DeduplicationRunRequest(),
    db: AsyncSession = Depends(get_db),
):
    """
    Executes cross-provider deduplication across normalized jobs.
    Merges high-confidence and exact duplicates; flags borderline matches for review.
    """
    summary = await deduplication_service.run_deduplication(
        db=db,
        company_id=request.company_id,
        auto_merge=request.auto_merge,
        similarity_threshold=request.similarity_threshold,
    )
    return DeduplicationRunResponse(status="COMPLETED", summary=summary)


@router.get("/duplicates", response_model=DuplicateGroupListResponse)
async def list_duplicate_groups(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by review status"),
    duplicate_type: Optional[str] = Query(None, description="Filter by duplicate type"),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists duplicate review groups with pagination and filtering.
    """
    conditions = []
    if status_filter:
        conditions.append(DuplicateReviewGroup.status == status_filter.upper().strip())
    if duplicate_type:
        conditions.append(DuplicateReviewGroup.duplicate_type == duplicate_type.upper().strip())

    where_clause = and_(*conditions) if conditions else True

    count_stmt = select(func.count(DuplicateReviewGroup.id)).where(where_clause)
    total = (await db.execute(count_stmt)).scalar_one()

    total_pages = math.ceil(total / page_size) if total > 0 else 0
    offset = (page - 1) * page_size

    stmt = (
        select(DuplicateReviewGroup)
        .where(where_clause)
        .order_by(DuplicateReviewGroup.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    groups = (await db.execute(stmt)).scalars().all()
    items = [_serialize_review_group(g) for g in groups]

    return DuplicateGroupListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=items,
    )


@router.get("/duplicates/{group_id}", response_model=DuplicateGroupDetail)
async def get_duplicate_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns full details for a duplicate review group, including all candidate jobs.
    """
    stmt = select(DuplicateReviewGroup).where(DuplicateReviewGroup.id == group_id)
    group = (await db.execute(stmt)).scalar_one_or_none()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Duplicate review group {group_id} not found.",
        )

    job_ids = json.loads(group.candidate_job_ids) if group.candidate_job_ids else []
    jobs_stmt = select(Job).options(selectinload(Job.company_rel)).where(Job.id.in_(job_ids))
    jobs = (await db.execute(jobs_stmt)).scalars().all()

    base_dict = _serialize_review_group(group).model_dump()
    return DuplicateGroupDetail(
        **base_dict,
        candidate_jobs=[_serialize_job(j) for j in jobs],
    )


@router.post("/duplicates/{group_id}/resolve", response_model=DuplicateGroupItem)
async def resolve_duplicate_group(
    group_id: int,
    request: DuplicateResolveRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Manually resolves a duplicate review group (MERGE, REJECT_DISTINCT, or KEEP_SEPARATE).
    """
    try:
        updated_group = await deduplication_service.resolve_duplicate_group(
            db=db,
            group_id=group_id,
            action=request.action,
            notes=request.notes,
        )
        return _serialize_review_group(updated_group)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))


@router.get("/verification/summary", response_model=VerificationSummaryResponse)
async def get_verification_summary(
    db: AsyncSession = Depends(get_db),
):
    """
    Returns aggregated vacancy verification metrics and status distribution.
    """
    count_stmt = select(func.count(CanonicalJob.id))
    total = (await db.execute(count_stmt)).scalar_one()

    status_stmt = select(CanonicalJob.vacancy_status, func.count(CanonicalJob.id)).group_by(CanonicalJob.vacancy_status)
    status_counts = (await db.execute(status_stmt)).all()

    by_status = {s: 0 for s in ["ACTIVE", "CLOSED", "EXPIRED", "BROKEN_LINK", "BLOCKED", "REDIRECTED", "UNKNOWN", "NEEDS_REVIEW"]}
    for stat, cnt in status_counts:
        by_status[stat] = cnt

    active_cnt = by_status.get("ACTIVE", 0)
    ratio = round(active_cnt / total, 3) if total > 0 else 0.0

    return VerificationSummaryResponse(
        total_canonical_jobs=total,
        by_status=by_status,
        active_ratio=ratio,
    )


@router.post("/verification/run")
async def run_verification(
    request: VerificationRunRequest = VerificationRunRequest(),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
):
    """
    Executes vacancy verification across CanonicalJob records.
    """
    if request.background:
        async def run_bg():
            async with AsyncSessionLocal() as session:
                await vacancy_verifier.run_batch_verification(
                    db=session,
                    limit=request.limit,
                    status_filter=request.status_filter,
                )

        background_tasks.add_task(run_bg)
        return {
            "status": "PROCESSING",
            "message": f"Vacancy verification batch of up to {request.limit} jobs dispatched in background.",
        }
    else:
        results = await vacancy_verifier.run_batch_verification(
            db=db,
            limit=request.limit,
            status_filter=request.status_filter,
        )
        return {
            "status": "COMPLETED",
            **results,
        }


@router.post("/verification/{job_id}", response_model=CanonicalJobItem)
async def verify_single_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Verifies a single canonical vacancy URL and updates its lifecycle status.
    """
    try:
        verified_job = await vacancy_verifier.verify_canonical_job(db=db, job_id=job_id)
        # Eager load sources
        stmt = (
            select(CanonicalJob)
            .options(selectinload(CanonicalJob.sources))
            .where(CanonicalJob.id == verified_job.id)
        )
        full_job = (await db.execute(stmt)).scalar_one()
        return _serialize_canonical_job(full_job)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))


@router.get("/verified", response_model=CanonicalJobListResponse)
async def list_verified_jobs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by vacancy status"),
    company_id: Optional[int] = Query(None, description="Filter by company ID"),
    is_remote: Optional[bool] = Query(None, description="Filter remote status"),
    q: Optional[str] = Query(None, description="Search title or company"),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns paginated list of canonical verified job vacancies.
    """
    conditions = []
    if status_filter:
        conditions.append(CanonicalJob.vacancy_status == status_filter.upper().strip())
    if company_id:
        conditions.append(CanonicalJob.company_id == company_id)
    if is_remote is not None:
        conditions.append(CanonicalJob.is_remote == is_remote)
    if q:
        kw = f"%{q.strip()}%"
        conditions.append(
            or_(
                CanonicalJob.canonical_job_title.ilike(kw),
                CanonicalJob.title.ilike(kw),
                CanonicalJob.company_name.ilike(kw),
            )
        )

    where_clause = and_(*conditions) if conditions else True

    count_stmt = select(func.count(CanonicalJob.id)).where(where_clause)
    total = (await db.execute(count_stmt)).scalar_one()

    total_pages = math.ceil(total / page_size) if total > 0 else 0
    offset = (page - 1) * page_size

    stmt = (
        select(CanonicalJob)
        .options(selectinload(CanonicalJob.sources))
        .where(where_clause)
        .order_by(CanonicalJob.last_seen_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    jobs = (await db.execute(stmt)).scalars().all()
    items = [_serialize_canonical_job(j) for j in jobs]

    return CanonicalJobListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=items,
    )


@router.get("/feed")
async def get_jobs_feed(
    candidate_id: Optional[int] = Query(None, description="Candidate ID to enrich with match scores"),
    q: Optional[str] = Query(None, description="Search title or company"),
    location: Optional[str] = Query(None, description="Filter location"),
    work_mode: Optional[str] = Query(None, description="Filter work mode"),
    employment_type: Optional[str] = Query(None, description="Filter employment type"),
    min_score: Optional[float] = Query(None, ge=0.0, le=100.0, description="Minimum match score"),
    eligibility: Optional[str] = Query(None, description="Filter eligibility status"),
    relevance: Optional[str] = Query("RELEVANT", description="Filter relevance: RELEVANT (default), ALL, IRRELEVANT"),
    vacancy_status: Optional[str] = Query("ACTIVE", description="Filter vacancy status"),
    sort_by: Optional[str] = Query("score", description="Sort by: score, date, company"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Unified Job Feed API.
    Combines canonical vacancies with personalized candidate match scores,
    eligibility badges, saved status, and application status.
    """
    from models.candidate_job_match import CandidateJobMatch
    from models.saved_job import SavedJob
    from models.application import JobApplication

    # Fallback to candidate 3 if none specified
    target_cand_id = candidate_id
    if not target_cand_id:
        c_res = (await db.execute(select(Candidate.id).order_by(Candidate.id.asc()).limit(1))).scalar_one_or_none()
        target_cand_id = c_res or 1

    # Load candidate matches
    matches_map = {}
    if target_cand_id:
        m_stmt = select(CandidateJobMatch).where(CandidateJobMatch.candidate_id == target_cand_id)
        m_records = (await db.execute(m_stmt)).scalars().all()
        matches_map = {m.canonical_job_id: m for m in m_records}

    # Load saved jobs
    saved_set = set()
    if target_cand_id:
        s_stmt = select(SavedJob.canonical_job_id).where(
            and_(SavedJob.candidate_id == target_cand_id, SavedJob.is_active.is_(True))
        )
        saved_set = set((await db.execute(s_stmt)).scalars().all())

    # Load applications
    apps_map = {}
    if target_cand_id:
        a_stmt = select(JobApplication).where(JobApplication.candidate_id == target_cand_id)
        a_records = (await db.execute(a_stmt)).scalars().all()
        apps_map = {a.canonical_job_id: a.status for a in a_records if a.canonical_job_id}

    # Query canonical jobs
    conditions = []
    if vacancy_status and vacancy_status.upper() != "ALL":
        conditions.append(CanonicalJob.vacancy_status == vacancy_status.upper())
    if q:
        kw = f"%{q.strip()}%"
        conditions.append(or_(
            CanonicalJob.title.ilike(kw),
            CanonicalJob.canonical_job_title.ilike(kw),
            CanonicalJob.company_name.ilike(kw),
            CanonicalJob.description.ilike(kw),
        ))
    if location:
        conditions.append(CanonicalJob.location.ilike(f"%{location.strip()}%"))
    if work_mode:
        conditions.append(CanonicalJob.workplace_type.ilike(f"%{work_mode.strip()}%"))
    if employment_type:
        conditions.append(CanonicalJob.employment_type.ilike(f"%{employment_type.strip()}%"))

    where_clause = and_(*conditions) if conditions else True
    stmt = (
        select(CanonicalJob)
        .options(selectinload(CanonicalJob.sources))
        .where(where_clause)
    )
    jobs = (await db.execute(stmt)).scalars().all()

    # Enrich and filter by match score / eligibility
    enriched = []
    for j in jobs:
        m = matches_map.get(j.id)
        comp_score = m.composite_score if m else 0.0
        elig_status = m.eligibility_status if m else "UNRATED"
        matched_skills = json.loads(m.matched_skills) if (m and m.matched_skills) else []
        missing_skills = json.loads(m.missing_skills) if (m and m.missing_skills) else []

        is_rel = getattr(m, "is_relevant", True) if m else True
        role_fam = getattr(m, "role_family", "SOFTWARE_ENGINEERING") if m else "SOFTWARE_ENGINEERING"
        rejection_reasons = json.loads(getattr(m, "rejection_reasons", "[]") or "[]") if m else []
        relevance_score = getattr(m, "relevance_score", 1.0) if m else 1.0

        if relevance:
            rel_u = relevance.upper().strip()
            if rel_u == "RELEVANT" and not is_rel:
                continue
            elif rel_u == "IRRELEVANT" and is_rel:
                continue

        if min_score is not None and comp_score < min_score:
            continue
        if eligibility and elig_status.upper() != eligibility.upper():
            continue

        salary_str = None
        if j.salary_min or j.salary_max:
            salary_str = f"{j.salary_currency or 'INR'} {j.salary_min or 0:,.0f} - {j.salary_max or 0:,.0f}"

        item = {
            "id": j.id,
            "canonical_job_id": j.canonical_job_id,
            "title": j.title,
            "canonical_job_title": j.canonical_job_title or j.title,
            "company_name": j.company_name or "Unknown Company",
            "company_id": j.company_id,
            "location": j.location or "India",
            "city": j.city,
            "country": j.country or "India",
            "work_mode": j.workplace_type or ("REMOTE" if j.is_remote else "ON_SITE"),
            "workplace_type": j.workplace_type or ("REMOTE" if j.is_remote else "ON_SITE"),
            "is_remote": j.is_remote,
            "employment_type": j.employment_type or "FULL_TIME",
            "experience_level": j.seniority_level or "ENTRY_LEVEL",
            "experience_min_years": j.experience_min_years,
            "experience_max_years": j.experience_max_years,
            "salary_range": salary_str,
            "stipend_range": None,
            "vacancy_status": j.vacancy_status,
            "is_active": j.vacancy_status == "ACTIVE",
            "first_seen_at": j.first_seen_at.isoformat() if j.first_seen_at else None,
            "last_verified_at": j.last_verified_at.isoformat() if j.last_verified_at else None,
            "original_job_url": j.canonical_application_url or j.canonical_source_url,
            # Relevance metadata
            "is_relevant": is_rel,
            "relevance_status": "RELEVANT" if is_rel else "IRRELEVANT",
            "role_family": role_fam,
            "relevance_score": relevance_score,
            "rejection_reasons": rejection_reasons,
            # Match enrichment
            "match_score": comp_score,
            "semantic_score": m.semantic_score if m else 0.0,
            "eligibility_status": elig_status,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "explanation": m.explanation_data if m else "Match score not computed yet",
            # State
            "is_saved": j.id in saved_set,
            "application_status": apps_map.get(j.id),
        }
        enriched.append(item)

    # Sort
    if sort_by == "score":
        # Prioritize relevant vacancies first, then sort by highest match score
        enriched.sort(key=lambda x: (1 if x["is_relevant"] else 0, x["match_score"]), reverse=True)
    elif sort_by == "company":
        enriched.sort(key=lambda x: x["company_name"].lower())
    else:  # date
        enriched.sort(key=lambda x: (1 if x["is_relevant"] else 0, x["first_seen_at"] or ""), reverse=True)

    total = len(enriched)
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    offset = (page - 1) * page_size
    paged_items = enriched[offset: offset + page_size]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "items": paged_items,
    }


@router.get("/{canonical_job_id}")
async def get_canonical_job_detail(
    canonical_job_id: str,
    candidate_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Get full detail of a canonical job vacancy including description,
    requirements, skills breakdown, company details, match scores, and status.
    Accepts integer ID (e.g. 1) or string code (e.g. CANON-CRED-1001).
    """
    from models.candidate_job_match import CandidateJobMatch
    from models.saved_job import SavedJob
    from models.application import JobApplication

    # Query job by id or canonical_job_id
    if canonical_job_id.isdigit():
        stmt = (
            select(CanonicalJob)
            .options(selectinload(CanonicalJob.sources))
            .where(CanonicalJob.id == int(canonical_job_id))
        )
    else:
        stmt = (
            select(CanonicalJob)
            .options(selectinload(CanonicalJob.sources))
            .where(CanonicalJob.canonical_job_id == canonical_job_id)
        )

    job = (await db.execute(stmt)).scalars().first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Canonical job {canonical_job_id} not found."
        )

    # Match details if candidate_id provided
    target_cand_id = candidate_id or 3
    match_record = None
    is_saved = False
    app_status = None

    if target_cand_id:
        m_stmt = select(CandidateJobMatch).where(
            and_(CandidateJobMatch.candidate_id == target_cand_id, CandidateJobMatch.canonical_job_id == job.id)
        )
        match_record = (await db.execute(m_stmt)).scalar_one_or_none()

        s_stmt = select(SavedJob).where(
            and_(SavedJob.candidate_id == target_cand_id, SavedJob.canonical_job_id == job.id, SavedJob.is_active.is_(True))
        )
        is_saved = (await db.execute(s_stmt)).scalar_one_or_none() is not None

        a_stmt = select(JobApplication.status).where(
            and_(JobApplication.candidate_id == target_cand_id, JobApplication.canonical_job_id == job.id)
        )
        app_status = (await db.execute(a_stmt)).scalar_one_or_none()

    serialized = _serialize_canonical_job(job)
    data = serialized.model_dump()

    # Append match & tracking metadata
    if match_record:
        data["match_details"] = {
            "composite_score": match_record.composite_score,
            "semantic_score": match_record.semantic_score,
            "skill_score": match_record.skill_score,
            "role_score": match_record.role_score,
            "experience_score": match_record.experience_score,
            "education_score": match_record.education_score,
            "location_score": match_record.location_score,
            "score_coverage": match_record.score_coverage,
            "eligibility_status": match_record.eligibility_status,
            "is_relevant": getattr(match_record, "is_relevant", True),
            "role_family": getattr(match_record, "role_family", "SOFTWARE_ENGINEERING"),
            "relevance_score": getattr(match_record, "relevance_score", 1.0),
            "rejection_reasons": json.loads(getattr(match_record, "rejection_reasons", "[]") or "[]"),
            "explanation": match_record.explanation_data,
            "matched_skills": json.loads(match_record.matched_skills) if match_record.matched_skills else [],
            "missing_skills": json.loads(match_record.missing_skills) if match_record.missing_skills else [],
            "disqualification_reasons": json.loads(match_record.disqualification_reasons) if match_record.disqualification_reasons else [],
        }
    else:
        data["match_details"] = None

    data["is_saved"] = is_saved
    data["application_status"] = app_status
    return data


def _serialize_job_embedding(emb: JobEmbedding) -> JobEmbeddingItem:
    canon = emb.canonical_job
    return JobEmbeddingItem(
        id=emb.id,
        canonical_job_id=emb.canonical_job_id,
        canonical_job_code=canon.canonical_job_id if canon else f"CANON-{emb.canonical_job_id}",
        job_title=(canon.canonical_job_title or canon.title) if canon else "Unknown",
        company_name=canon.company_name if canon else "Unknown",
        model_name=emb.model_name,
        dimensions=emb.dimensions,
        content_hash=emb.content_hash,
        status=emb.status,
        last_error=emb.last_error,
        created_at=emb.created_at,
        updated_at=emb.updated_at,
    )


# ---------------------------------------------------------------------------
# Phase 6: Job Embeddings & Vector Storage Endpoints
# ---------------------------------------------------------------------------

@router.post("/embeddings/generate", response_model=JobEmbeddingBatchResponse)
async def generate_embeddings_batch(
    request: Optional[JobEmbeddingBatchRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Triggers batch semantic embedding generation for canonical vacancies using
    the local fine-tuned SBERT model.
    Skips unchanged jobs with identical content hash, updates stale jobs, and
    records per-job errors safely.
    """
    req = request or JobEmbeddingBatchRequest()
    result = await job_embedding_service.generate_batch_embeddings(
        db=db,
        canonical_job_ids=req.canonical_job_ids,
        limit=req.limit,
        force=req.force,
    )
    # Eager load canonical jobs for serialization
    emb_ids = [e.id for e in result["job_embeddings"]]
    if emb_ids:
        stmt = (
            select(JobEmbedding)
            .options(selectinload(JobEmbedding.canonical_job))
            .where(JobEmbedding.id.in_(emb_ids))
        )
        loaded = (await db.execute(stmt)).scalars().all()
        loaded_dict = {e.id: e for e in loaded}
        items = [_serialize_job_embedding(loaded_dict[e.id]) for e in result["job_embeddings"] if e.id in loaded_dict]
    else:
        items = []

    return JobEmbeddingBatchResponse(
        status=result["status"],
        total_considered=result["total_considered"],
        generated_count=result["generated_count"],
        skipped_count=result["skipped_count"],
        failed_count=result["failed_count"],
        items=items,
    )


@router.post("/embeddings/generate/{canonical_job_id}", response_model=JobEmbeddingItem)
async def generate_single_job_embedding(
    canonical_job_id: str,
    force: bool = Query(False, description="Force re-generation even if content hash unchanged"),
    db: AsyncSession = Depends(get_db),
):
    """
    Generates or refreshes the semantic vector embedding for a single canonical job vacancy.
    """
    try:
        emb = await job_embedding_service.generate_single_embedding(
            db=db, job_identifier=canonical_job_id, force=force
        )
        stmt = (
            select(JobEmbedding)
            .options(selectinload(JobEmbedding.canonical_job))
            .where(JobEmbedding.id == emb.id)
        )
        full_emb = (await db.execute(stmt)).scalar_one()
        return _serialize_job_embedding(full_emb)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))


@router.get("/embeddings/summary", response_model=JobEmbeddingSummaryResponse)
async def get_embeddings_summary(
    db: AsyncSession = Depends(get_db),
):
    """
    Returns summary statistics on total canonical jobs, vector coverage,
    completed, pending, stale, and failed embeddings.
    """
    summary = await job_embedding_service.get_summary(db=db)
    return JobEmbeddingSummaryResponse(**summary)


@router.get("/embeddings/status", response_model=JobEmbeddingListResponse)
async def list_embeddings_status(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (COMPLETED, PENDING, STALE, FAILED)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns paginated list of job embedding records with status, dimensions, and canonical vacancy metadata.
    """
    res = await job_embedding_service.get_status_list(
        db=db,
        status_filter=status_filter,
        page=page,
        page_size=page_size,
    )
    items = [_serialize_job_embedding(e) for e in res["items"]]
    return JobEmbeddingListResponse(
        total=res["total"],
        page=res["page"],
        page_size=res["page_size"],
        total_pages=res["total_pages"],
        items=items,
    )


@router.post("/embeddings/retry-failed", response_model=RetryFailedResponse)
async def retry_failed_job_embeddings(
    request: Optional[RetryFailedRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Retries embedding generation for all jobs currently marked as FAILED.
    """
    req = request or RetryFailedRequest()
    result = await job_embedding_service.retry_failed_embeddings(
        db=db, limit=req.limit
    )
    return RetryFailedResponse(**result)



