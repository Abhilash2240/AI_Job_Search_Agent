# backend/schemas/saved_job.py
"""
Pydantic Schemas for Saved Jobs API.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class SavedJobCreate(BaseModel):
    candidate_id: int
    canonical_job_id: int
    notes: Optional[str] = None


class SavedJobUpdate(BaseModel):
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class CanonicalJobSummary(BaseModel):
    id: int
    canonical_job_id: str
    title: str
    company_name: Optional[str] = None
    location: Optional[str] = None
    workplace_type: Optional[str] = None
    employment_type: Optional[str] = None
    vacancy_status: str
    is_active: bool
    salary_range: Optional[str] = None
    stipend_range: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SavedJobResponse(BaseModel):
    id: int
    candidate_id: int
    canonical_job_id: int
    notes: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    job: Optional[CanonicalJobSummary] = None

    model_config = ConfigDict(from_attributes=True)


class SavedJobListResponse(BaseModel):
    total: int
    items: List[SavedJobResponse]

