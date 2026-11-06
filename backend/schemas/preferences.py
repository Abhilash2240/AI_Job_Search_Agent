# backend/schemas/preferences.py
"""
Pydantic Schemas for Candidate Job Search Preferences.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class UserPreferencesCreate(BaseModel):
    candidate_id: int
    preferred_locations: Optional[List[str]] = None
    work_modes: Optional[List[str]] = None
    employment_types: Optional[List[str]] = None
    min_salary: Optional[float] = None
    min_stipend: Optional[float] = None
    min_match_score: Optional[float] = 30.0


class UserPreferencesUpdate(BaseModel):
    preferred_locations: Optional[List[str]] = None
    work_modes: Optional[List[str]] = None
    employment_types: Optional[List[str]] = None
    min_salary: Optional[float] = None
    min_stipend: Optional[float] = None
    min_match_score: Optional[float] = None


class UserPreferencesResponse(BaseModel):
    id: int
    candidate_id: int
    preferred_locations: List[str] = []
    work_modes: List[str] = []
    employment_types: List[str] = []
    min_salary: Optional[float] = None
    min_stipend: Optional[float] = None
    min_match_score: float = 30.0
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

