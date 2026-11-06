# backend/app/api/matching.py
"""
Candidate-to-Job Matching API Endpoints (Phase 7).
Provides endpoints to trigger matching, inspect ranked matches, retrieve
explainable breakdowns, execute batch matching, and monitor summary metrics.
"""

import json
import math
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from db.database import get_db
from models.candidate import Candidate
from models.canonical_job import CanonicalJob
from models.candidate_job_match import CandidateJobMatch
from matching.matching_service import matching_service
from schemas.matching import (
    CandidateJobMatchItem,
    CandidateMatchListResponse,
    MatchComponentScores,
    BatchMatchRequest,
    BatchMatchResponse,
    MatchingSummaryResponse,
)

router = APIRouter(prefix="/api/matching", tags=["Candidate Matching"])


def _serialize_match(match: CandidateJobMatch) -> CandidateJobMatchItem:
    """Helper to serialize CandidateJobMatch ORM entity to Pydantic schema."""
    canon = match.canonical_job
    matched_skills = json.loads(match.matched_skills) if match.matched_skills else []
    missing_skills = json.loads(match.missing_skills) if match.missing_skills else []
    inferred_potential = json.loads(match.inferred_skills_potential) if match.inferred_skills_potential else []
    matched_roles = json.loads(match.matched_roles) if match.matched_roles else None
    disqual = json.loads(match.disqualification_reasons) if match.disqualification_reasons else []

    component_scores = MatchComponentScores(
        semantic_score=match.semantic_score,
        skill_score=match.skill_score,
        role_score=match.role_score,
        experience_score=match.experience_score,
        education_score=match.education_score,
        location_score=match.location_score,
        score_coverage=match.score_coverage,
    )

    return CandidateJobMatchItem(
        id=match.id,
        candidate_id=match.candidate_id,
        canonical_job_id=match.canonical_job_id,
        canonical_job_code=canon.canonical_job_id if canon else f"CANON-{match.canonical_job_id}",
        company_name=canon.company_name if canon else "Unknown",
        job_title=canon.title if canon else "Unknown",
        canonical_job_title=canon.canonical_job_title if canon else "Unknown",
        composite_score=match.composite_score,
        component_scores=component_scores,
        eligibility_status=match.eligibility_status,
        match_classification=match.match_classification,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        inferred_skills_potential=inferred_potential,
        matched_roles=matched_roles,
        explanation=match.explanation_data or "No explanation generated.",
        disqualification_reasons=disqual,
        is_remote=canon.is_remote if canon else False,
        location=canon.location if canon else None,
        seniority_level=canon.seniority_level if canon else None,
        employment_type=canon.employment_type if canon else None,
        evaluated_at=match.evaluated_at,
    )


@router.post("/candidate/{candidate_id}", response_model=List[CandidateJobMatchItem])
async def match_single_candidate(
    candidate_id: int,
    force: bool = Query(False, description="Force re-evaluation even if profile and job hashes are unchanged"),
    limit: Optional[int] = Query(None, description="Limit number of vacancies evaluated"),
    db: AsyncSession = Depends(get_db),
):
    """
    Runs explainable candidate-to-job matching for one candidate against eligible canonical vacancies.
    """
    try:
        matches = await matching_service.run_matching_for_candidate(
            db=db, candidate_id=candidate_id, force=force, limit=limit
        )
        # Eager load canonical job relationships
        match_ids = [m.id for m in matches]
        if not match_ids:
            return []

        stmt = (
            select(CandidateJobMatch)
            .options(selectinload(CandidateJobMatch.canonical_job))
            .where(CandidateJobMatch.id.in_(match_ids))
            .order_by(CandidateJobMatch.is_relevant.desc(), CandidateJobMatch.composite_score.desc())
        )
        loaded = (await db.execute(stmt)).scalars().all()
        return [_serialize_match(m) for m in loaded]

    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))


@router.get("/candidate/{candidate_id}", response_model=CandidateMatchListResponse)
async def get_candidate_matches(
    candidate_id: int,
    min_score: Optional[float] = Query(None, description="Minimum composite match score filter (0-100)"),
    eligibility_status: Optional[str] = Query(None, description="Filter by eligibility status"),
    match_classification: Optional[str] = Query(None, description="Filter by match classification"),
    is_remote: Optional[bool] = Query(None, description="Filter remote positions"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves ranked matches for a candidate with optional filtering and pagination.
    Returns all evaluated canonical vacancies by default, ranked from highest to lowest score.
    """
    # Verify candidate exists
    cand = (await db.execute(select(Candidate).where(Candidate.id == candidate_id))).scalar_one_or_none()
    if not cand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Candidate {candidate_id} not found")

    conditions = [CandidateJobMatch.candidate_id == candidate_id]
    if min_score is not None:
        conditions.append(CandidateJobMatch.composite_score >= min_score)
    if eligibility_status:
        conditions.append(CandidateJobMatch.eligibility_status == eligibility_status.upper().strip())
    if match_classification:
        conditions.append(CandidateJobMatch.match_classification == match_classification.upper().strip())

    where_clause = and_(*conditions)

    count_stmt = select(func.count(CandidateJobMatch.id)).where(where_clause)
    total = (await db.execute(count_stmt)).scalar_one()

    total_pages = math.ceil(total / page_size) if total > 0 else 0
    offset = (page - 1) * page_size

    stmt = (
        select(CandidateJobMatch)
        .options(selectinload(CandidateJobMatch.canonical_job))
        .where(where_clause)
        .order_by(CandidateJobMatch.is_relevant.desc(), CandidateJobMatch.composite_score.desc())
        .offset(offset)
        .limit(page_size)
    )
    records = (await db.execute(stmt)).scalars().all()

    # Apply canonical job-level filter if requested (e.g. is_remote)
    if is_remote is not None:
        records = [r for r in records if r.canonical_job and r.canonical_job.is_remote == is_remote]

    items = [_serialize_match(m) for m in records]

    return CandidateMatchListResponse(
        candidate_id=candidate_id,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=items,
    )


@router.get("/candidate/{candidate_id}/job/{canonical_job_id}", response_model=CandidateJobMatchItem)
async def get_match_detail(
    candidate_id: int,
    canonical_job_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns full explainable breakdown, evidence components, and eligibility for a single match pair.
    """
    stmt = (
        select(CandidateJobMatch)
        .options(selectinload(CandidateJobMatch.canonical_job))
        .where(
            and_(
                CandidateJobMatch.candidate_id == candidate_id,
                CandidateJobMatch.canonical_job_id == canonical_job_id,
            )
        )
    )
    match_rec = (await db.execute(stmt)).scalar_one_or_none()
    if not match_rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match record not found for candidate {candidate_id} and job {canonical_job_id}",
        )
    return _serialize_match(match_rec)


@router.post("/batch", response_model=BatchMatchResponse)
async def trigger_batch_matching(
    request: Optional[BatchMatchRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Triggers matching across all legitimate candidate profiles (excluding test fixtures).
    """
    req = request or BatchMatchRequest()
    result = await matching_service.run_batch_matching(db=db, force=req.force)
    return BatchMatchResponse(**result)


@router.get("/summary", response_model=MatchingSummaryResponse)
async def get_matching_summary(
    db: AsyncSession = Depends(get_db),
):
    """
    Returns aggregate matching metrics across all candidate-to-job matches.
    """
    summary = await matching_service.get_summary(db=db)
    return MatchingSummaryResponse(**summary)

