# backend/schemas/application.py
"""
Pydantic Schemas for Job Application Tracking API.
"""

from typing import Optional, List, Dict
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ApplicationStatusHistoryItem(BaseModel):
    id: int
    application_id: int
    from_status: Optional[str] = None
    to_status: str
    notes: Optional[str] = None
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApplicationCreate(BaseModel):
    candidate_id: int
    canonical_job_id: Optional[int] = None
    company_name: str
    job_title: str
    application_url: Optional[str] = None
    status: Optional[str] = "APPLIED"
    applied_at: Optional[datetime] = None
    notes: Optional[str] = None
    interview_date: Optional[datetime] = None
    follow_up_date: Optional[datetime] = None
    salary_offered: Optional[str] = None


class ApplicationUpdate(BaseModel):
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    application_url: Optional[str] = None
    status: Optional[str] = None
    applied_at: Optional[datetime] = None
    notes: Optional[str] = None
    interview_date: Optional[datetime] = None
    follow_up_date: Optional[datetime] = None
    salary_offered: Optional[str] = None


class ApplicationStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


class ApplicationResponse(BaseModel):
    id: int
    candidate_id: int
    canonical_job_id: Optional[int] = None
    company_name: str
    job_title: str
    application_url: Optional[str] = None
    status: str
    applied_at: Optional[datetime] = None
    notes: Optional[str] = None
    interview_date: Optional[datetime] = None
    follow_up_date: Optional[datetime] = None
    salary_offered: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    status_history: Optional[List[ApplicationStatusHistoryItem]] = None

    model_config = ConfigDict(from_attributes=True)


class ApplicationListResponse(BaseModel):
    total: int
    items: List[ApplicationResponse]


class ApplicationStatsResponse(BaseModel):
    total_applications: int
    by_status: Dict[str, int]
    interviews_scheduled: int
    offers_received: int
    active_in_pipeline: int
    response_rate_percent: float

