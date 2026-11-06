"""
Pydantic Schemas and Dataclasses for Normalized Job Postings (Phase 4C).
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ExtractionStatus(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    FAILED = "FAILED"


class WorkplaceType(str, Enum):
    REMOTE = "REMOTE"
    HYBRID = "HYBRID"
    ON_SITE = "ON_SITE"
    UNSPECIFIED = "UNSPECIFIED"


class EmploymentType(str, Enum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    CONTRACT = "CONTRACT"
    INTERNSHIP = "INTERNSHIP"
    TEMPORARY = "TEMPORARY"
    UNSPECIFIED = "UNSPECIFIED"


class SeniorityLevel(str, Enum):
    INTERN = "INTERN"
    ENTRY_LEVEL = "ENTRY_LEVEL"
    MID_LEVEL = "MID_LEVEL"
    SENIOR = "SENIOR"
    LEAD_STAFF = "LEAD_STAFF"
    DIRECTOR_EXEC = "DIRECTOR_EXEC"
    UNKNOWN = "UNKNOWN"


class SkillWithEvidence(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill_name: str
    canonical_name: str
    category: str
    evidence_snippet: str
    is_required: bool = True


class SalaryInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    currency: Optional[str] = None
    period: Optional[str] = None  # YEAR, MONTH, HOUR, STIPEND
    raw_text: Optional[str] = None


class ExperienceRequirements(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    min_years: Optional[float] = None
    max_years: Optional[float] = None
    is_fresher_eligible: bool = False
    is_internship: bool = False
    seniority_level: SeniorityLevel = SeniorityLevel.UNKNOWN
    evidence: Optional[str] = None


class EducationRequirements(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    degree_requirements: List[str] = Field(default_factory=list)
    fields_of_study: List[str] = Field(default_factory=list)
    preferred_education: List[str] = Field(default_factory=list)
    evidence: Optional[str] = None


class LocationInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    raw_location: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    is_remote: bool = False
    workplace_type: WorkplaceType = WorkplaceType.UNSPECIFIED
    eligible_locations: List[str] = Field(default_factory=list)


class JobExtractionRequest(BaseModel):
    discovered_job_ids: Optional[List[int]] = Field(None, description="Specific discovered job IDs to extract")
    limit: Optional[int] = Field(None, description="Max jobs to extract (e.g. 50)")
    force_reextract: bool = Field(False, description="Re-extract even if already normalized")
    background: bool = Field(False, description="Run extraction in background task")


class SingleJobExtractionRequest(BaseModel):
    force_reextract: bool = Field(False, description="Re-extract even if already normalized")


class NormalizedJobItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    external_job_id: Optional[str] = None
    canonical_job_title: str
    title: str
    description: str
    responsibilities: List[str] = Field(default_factory=list)
    qualifications: List[str] = Field(default_factory=list)
    required_skills: List[SkillWithEvidence] = Field(default_factory=list)
    preferred_skills: List[SkillWithEvidence] = Field(default_factory=list)
    employment_type: Optional[str] = None
    experience_min_years: Optional[float] = None
    experience_max_years: Optional[float] = None
    seniority_level: Optional[str] = None
    workplace_type: Optional[str] = None
    location_raw: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    is_remote: bool = False
    eligible_locations: List[str] = Field(default_factory=list)
    degree_requirements: List[str] = Field(default_factory=list)
    field_of_study: List[str] = Field(default_factory=list)
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    salary_period: Optional[str] = None
    application_url: Optional[str] = None
    source_url: Optional[str] = None
    provider: Optional[str] = None
    extraction_status: str
    extraction_confidence: float
    missing_fields: List[str] = Field(default_factory=list)
    discovered_at: Optional[datetime] = None
    extracted_at: Optional[datetime] = None


class NormalizedJobListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[NormalizedJobItem]


class ExtractionSummaryResponse(BaseModel):
    total_normalized_jobs: int
    by_status: Dict[str, int]
    by_provider: Dict[str, int]
    fresher_eligible_count: int
    remote_jobs_count: int
    average_confidence: float
    most_common_missing_fields: Dict[str, int]

