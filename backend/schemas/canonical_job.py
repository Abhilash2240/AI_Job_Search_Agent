"""
Pydantic Schemas for Canonical Vacancies, Deduplication Groups, and Verification (Phase 5).
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from jobs.job_schema import NormalizedJobItem, SkillWithEvidence


class CanonicalJobSourceItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    canonical_job_id: int
    job_id: Optional[int] = None
    raw_discovery_id: Optional[int] = None
    provider: str
    external_job_id: Optional[str] = None
    source_url: Optional[str] = None
    application_url: Optional[str] = None
    discovered_title: Optional[str] = None
    discovered_location: Optional[str] = None
    is_primary: bool = False
    first_seen_at: datetime
    last_seen_at: datetime


class CanonicalJobItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    canonical_job_id: str
    company_id: Optional[int] = None
    company_name: str
    title: str
    canonical_job_title: str
    location: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = "India"
    is_remote: bool = False
    workplace_type: Optional[str] = None
    employment_type: Optional[str] = None
    seniority_level: Optional[str] = None
    experience_min_years: Optional[float] = None
    experience_max_years: Optional[float] = None
    description: str
    responsibilities: List[str] = Field(default_factory=list)
    qualifications: List[str] = Field(default_factory=list)
    required_skills: List[SkillWithEvidence] = Field(default_factory=list)
    preferred_skills: List[SkillWithEvidence] = Field(default_factory=list)
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    salary_period: Optional[str] = None
    canonical_application_url: Optional[str] = None
    canonical_source_url: Optional[str] = None
    vacancy_status: str
    first_seen_at: datetime
    last_seen_at: datetime
    last_verified_at: Optional[datetime] = None
    consecutive_missing_checks: int = 0
    verification_attempts: int = 0
    verification_details: Optional[Dict[str, Any]] = None
    source_count: int = 1
    dedup_confidence: float = 1.0
    match_evidence: Optional[Dict[str, Any]] = None
    sources: List[CanonicalJobSourceItem] = Field(default_factory=list)


class CanonicalJobListResponse(BaseModel):
    total: int
    items: List[CanonicalJobItem]
    page: int
    page_size: int
    total_pages: int


class DuplicateGroupItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_key: str
    canonical_job_id: Optional[int] = None
    duplicate_type: str
    status: str
    similarity_score: float
    match_reasons: List[str] = Field(default_factory=list)
    candidate_job_ids: List[int] = Field(default_factory=list)
    resolution_action: Optional[str] = None
    resolution_notes: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime


class DuplicateGroupDetail(DuplicateGroupItem):
    candidate_jobs: List[NormalizedJobItem] = Field(default_factory=list)


class DuplicateGroupListResponse(BaseModel):
    total: int
    items: List[DuplicateGroupItem]
    page: int
    page_size: int
    total_pages: int


class DuplicateResolveRequest(BaseModel):
    action: str = Field(..., description="'MERGE', 'REJECT_DISTINCT', or 'KEEP_SEPARATE'")
    notes: Optional[str] = None


class DeduplicationRunRequest(BaseModel):
    company_id: Optional[int] = None
    auto_merge: bool = True
    similarity_threshold: float = 0.85


class DeduplicationRunResponse(BaseModel):
    status: str
    summary: Dict[str, Any]


class VerificationRunRequest(BaseModel):
    limit: int = 20
    status_filter: Optional[str] = None
    background: bool = False


class VerificationSummaryResponse(BaseModel):
    total_canonical_jobs: int
    by_status: Dict[str, int]
    active_ratio: float

