"""
Pydantic Schemas for Job Discovery API (Phase 4B).
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DiscoveryRunRequest(BaseModel):
    company_ids: Optional[List[int]] = Field(None, description="List of company IDs to target")
    limit: Optional[int] = Field(None, description="Max companies to scan (e.g. 50)")
    dry_run: bool = Field(False, description="Scan and discover without saving to DB")
    candidate_id: Optional[int] = Field(None, description="Candidate ID to use for confirmed role targeting")
    filter_targeting: bool = Field(False, description="Filter discovered jobs strictly by candidate roles")
    background: bool = Field(True, description="Run asynchronously in background")


class SingleCompanyDiscoveryRequest(BaseModel):
    dry_run: bool = Field(False, description="Scan without saving to DB")
    candidate_id: Optional[int] = Field(None, description="Candidate ID for role targeting")


class DiscoveredJobItem(BaseModel):
    id: int
    company_id: int
    company_name: Optional[str] = None
    provider: str
    external_job_id: Optional[str] = None
    discovered_title: str
    discovered_location: Optional[str] = None
    department: Optional[str] = None
    job_url: str
    application_url: Optional[str] = None
    source_url: Optional[str] = None
    discovery_status: str
    first_discovered_at: Optional[datetime] = None
    last_discovered_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DiscoveredJobListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[DiscoveredJobItem]


class DiscoveryProviderInfo(BaseModel):
    name: str
    display_name: str
    type: str
    status: str
    auth_required: bool
    concurrency: int
    rate_limit_rps: float
    details: Optional[str] = None


class DiscoveryStatusResponse(BaseModel):
    status: str = "COMPLETED"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    dry_run: Optional[bool] = None
    total_companies: Optional[int] = None
    processed_companies: Optional[int] = None
    jobs_discovered: Optional[int] = None
    new_jobs_persisted: Optional[int] = None
    duplicate_jobs_updated: Optional[int] = None
    duration_seconds: Optional[float] = None
    errors: Optional[List[Dict[str, Any]]] = None
    message: Optional[str] = None


class DiscoverySummaryResponse(BaseModel):
    total_discovered_jobs: int
    active_jobs: int
    jobs_by_provider: Dict[str, int]
    companies_with_jobs: int
    last_run: Optional[Dict[str, Any]] = None
