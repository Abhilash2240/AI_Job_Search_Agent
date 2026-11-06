# backend/app/api/preferences.py
"""
Candidate Job Search Preferences API Endpoints.
Allows candidates to inspect and update target locations, work modes,
employment types, salary/stipend floors, and minimum score thresholds.
"""

import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.database import get_db
from models.candidate import Candidate
from models.user_preferences import UserPreferences
from schemas.preferences import (
    UserPreferencesCreate,
    UserPreferencesUpdate,
    UserPreferencesResponse,
)

router = APIRouter(prefix="/api/preferences", tags=["Candidate Preferences"])


@router.get("/candidate/{candidate_id}", response_model=UserPreferencesResponse)
async def get_candidate_preferences(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get preferences for a candidate. Creates sensible defaults if not yet customized."""
    # Check candidate
    cand = (await db.execute(select(Candidate).where(Candidate.id == candidate_id))).scalar_one_or_none()
    if not cand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Candidate {candidate_id} not found")

    pref = (await db.execute(select(UserPreferences).where(UserPreferences.candidate_id == candidate_id))).scalar_one_or_none()
    if not pref:
        # Default preferences based on candidate profile if available
        pref = UserPreferences(
            candidate_id=candidate_id,
            preferred_locations=json.dumps(["Bengaluru", "Hyderabad", "Pune", "Remote"]),
            work_modes=json.dumps(["REMOTE", "HYBRID", "ON_SITE"]),
            employment_types=json.dumps(["FULL_TIME", "INTERNSHIP"]),
            min_salary=None,
            min_stipend=None,
            min_match_score=30.0,
        )
        db.add(pref)
        await db.commit()
        await db.refresh(pref)

    return _serialize_preferences(pref)


@router.put("/candidate/{candidate_id}", response_model=UserPreferencesResponse)
async def update_candidate_preferences(
    candidate_id: int,
    req: UserPreferencesUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update job search preferences for a candidate."""
    cand = (await db.execute(select(Candidate).where(Candidate.id == candidate_id))).scalar_one_or_none()
    if not cand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Candidate {candidate_id} not found")

    pref = (await db.execute(select(UserPreferences).where(UserPreferences.candidate_id == candidate_id))).scalar_one_or_none()
    if not pref:
        pref = UserPreferences(candidate_id=candidate_id)
        db.add(pref)

    if req.preferred_locations is not None:
        pref.preferred_locations = json.dumps(req.preferred_locations)
    if req.work_modes is not None:
        pref.work_modes = json.dumps(req.work_modes)
    if req.employment_types is not None:
        pref.employment_types = json.dumps(req.employment_types)
    if req.min_salary is not None:
        pref.min_salary = req.min_salary
    if req.min_stipend is not None:
        pref.min_stipend = req.min_stipend
    if req.min_match_score is not None:
        pref.min_match_score = req.min_match_score

    await db.commit()
    await db.refresh(pref)
    return _serialize_preferences(pref)


def _serialize_preferences(pref: UserPreferences) -> UserPreferencesResponse:
    locs = json.loads(pref.preferred_locations) if pref.preferred_locations else []
    modes = json.loads(pref.work_modes) if pref.work_modes else []
    types = json.loads(pref.employment_types) if pref.employment_types else []

    return UserPreferencesResponse(
        id=pref.id,
        candidate_id=pref.candidate_id,
        preferred_locations=locs,
        work_modes=modes,
        employment_types=types,
        min_salary=pref.min_salary,
        min_stipend=pref.min_stipend,
        min_match_score=pref.min_match_score,
        updated_at=pref.updated_at,
    )

