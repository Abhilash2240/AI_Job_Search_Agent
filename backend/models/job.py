# backend/models/job.py
"""Normalized Job Model for AI Job Search Agent (Phase 4C)."""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Float,
    Boolean,
    ForeignKey,
    func,
)
from sqlalchemy.orm import relationship
from db.database import Base


class Job(Base):
    """
    Normalized Job Posting Model.
    Stores clean, structured job requirements extracted from discovered postings
    (Greenhouse, Lever, Firecrawl) without inventing or fabricating data.
    """
    __tablename__ = "jobs"

    # Identity
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True)
    external_job_id = Column(String, nullable=True, index=True)
    canonical_job_title = Column(String, nullable=False, index=True)
    
    # Backward compatibility aliases/fields
    title = Column(String, nullable=False)  # Raw / original job title
    company = Column(String, nullable=False)  # Company display name
    location = Column(String, nullable=True)  # Raw / display location

    # Description & Content
    description = Column(Text, nullable=False)  # Full cleaned job description
    responsibilities = Column(Text, nullable=True)  # JSON list of responsibilities
    qualifications = Column(Text, nullable=True)  # JSON list of qualifications
    required_skills = Column(Text, nullable=True)  # JSON list of SkillWithEvidence dicts
    preferred_skills = Column(Text, nullable=True)  # JSON list of SkillWithEvidence dicts

    # Employment & Seniority
    employment_type = Column(String, nullable=True)  # FULL_TIME, PART_TIME, CONTRACT, INTERNSHIP
    experience_min_years = Column(Float, nullable=True)
    experience_max_years = Column(Float, nullable=True)
    seniority_level = Column(String, nullable=True, index=True)  # ENTRY_LEVEL, MID_LEVEL, SENIOR, LEAD, etc.
    workplace_type = Column(String, nullable=True)  # REMOTE, HYBRID, ON_SITE
    seniority = Column(String, nullable=True)  # Backward-compatible alias

    # Location Details
    location_raw = Column(String, nullable=True)
    city = Column(String, nullable=True, index=True)
    state = Column(String, nullable=True)
    country = Column(String, nullable=True, index=True)
    is_remote = Column(Boolean, default=False, nullable=False, index=True)
    eligible_locations = Column(Text, nullable=True)  # JSON list of countries/regions

    # Education Requirements
    degree_requirements = Column(Text, nullable=True)  # JSON list of degree types
    field_of_study = Column(Text, nullable=True)  # JSON list of majors/fields

    # Compensation (Explicit Only)
    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    salary_currency = Column(String, nullable=True)  # INR, USD, EUR, etc.
    salary_period = Column(String, nullable=True)  # YEAR, MONTH, HOUR

    # Application & Provenance
    application_url = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    provider = Column(String, nullable=True, index=True)  # greenhouse, lever, firecrawl
    source_job_id = Column(String, nullable=True)
    raw_discovery_id = Column(
        Integer, ForeignKey("discovered_jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Extraction Metadata
    discovered_at = Column(DateTime(timezone=True), nullable=True)
    extracted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    extraction_status = Column(String, default="COMPLETE", nullable=False, index=True)  # COMPLETE, PARTIAL, FAILED, NEEDS_REVIEW
    extraction_confidence = Column(Float, default=1.0, nullable=False)  # 0.0 to 1.0 based on explicit evidence
    missing_fields = Column(Text, nullable=True)  # JSON list of missing optional fields

    # Deduplication & Canonical Linking (Phase 5)
    canonical_job_id = Column(Integer, ForeignKey("canonical_jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    is_canonical_primary = Column(Boolean, default=False, nullable=False)
    dedup_status = Column(String, default="UNPROCESSED", nullable=False, index=True)  # UNPROCESSED, CANONICAL, MERGED_DUPLICATE, NEEDS_REVIEW

    # SBERT & Intelligence placeholders (Preserved for Phase 5)
    embedding = Column(Text, nullable=True)
    match_score = Column(Float, nullable=True)
    posted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    company_rel = relationship("Company", back_populates="normalized_jobs")
    discovered_job_rel = relationship("DiscoveredJob", foreign_keys=[raw_discovery_id])
    canonical_job_rel = relationship("CanonicalJob", back_populates="normalized_jobs", foreign_keys=[canonical_job_id])
