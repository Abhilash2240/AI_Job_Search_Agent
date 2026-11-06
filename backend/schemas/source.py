# backend/schemas/source.py
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class JobSourceItem(BaseModel):
    id: int
    name: str
    source_type: str
    base_url: str
    normalized_url: str
    category: Optional[str] = None
    country_scope: str = "India"
    is_active: bool = True
    access_method: str = "direct"
    source_document: Optional[str] = None
    source_page: Optional[int] = None
    verification_status: str = "NOT_CHECKED"
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class JobSourceListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[JobSourceItem]


class CompanyCareerSourceItem(BaseModel):
    id: int
    company_id: int
    career_url: str
    normalized_url: str
    source_document: str
    source_page: Optional[int] = None
    verification_status: str = "NOT_CHECKED"
    last_verified_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CompanyContactItem(BaseModel):
    id: int
    company_id: int
    email: str
    contact_type: str = "hr_recruitment"
    source_document: str
    source_page: Optional[int] = None
    verification_status: str = "NOT_CHECKED"
    last_verified_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CompanyItem(BaseModel):
    id: int
    canonical_name: str
    normalized_name: str
    primary_domain: Optional[str] = None
    country: str = "India"
    industry: Optional[str] = None
    relevance_category: str = "Unknown"
    is_active: bool = True
    career_sources_count: int = 0
    contacts_count: int = 0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CompanyDetailResponse(BaseModel):
    id: int
    canonical_name: str
    normalized_name: str
    primary_domain: Optional[str] = None
    country: str = "India"
    industry: Optional[str] = None
    relevance_category: str = "Unknown"
    is_active: bool = True
    career_sources: List[CompanyCareerSourceItem] = []
    contacts: List[CompanyContactItem] = []
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CompanyListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[CompanyItem]


class SourcesSummaryResponse(BaseModel):
    total_sources: int
    total_job_boards: int
    total_companies: int
    total_career_sources: int
    total_contact_emails: int
    categories: Dict[str, int]
    verification_breakdown: Dict[str, int]
    relevance_breakdown: Dict[str, int]


class SourceImportBatchItem(BaseModel):
    id: int
    filename: str
    imported_at: Optional[datetime] = None
    total_extracted: int
    total_imported: int
    total_duplicates: int
    total_invalid: int
    total_needs_review: int
    import_status: str
    details: Optional[str] = None

    class Config:
        from_attributes = True

