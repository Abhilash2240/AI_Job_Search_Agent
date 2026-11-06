# backend/models/canonical_job.py
"""
Canonical Job and Provenance Models for AI Job Search Agent (Phase 5).
Manages deduplicated canonical vacancies, multi-source provenance,
duplicate review groups, and vacancy verification lifecycle tracking.
"""

import enum
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


class VacancyStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    EXPIRED = "EXPIRED"
    BROKEN_LINK = "BROKEN_LINK"
    BLOCKED = "BLOCKED"
    REDIRECTED = "REDIRECTED"
    UNKNOWN = "UNKNOWN"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class DuplicateType(str, enum.Enum):
    EXACT_DUPLICATE = "EXACT_DUPLICATE"
    HIGH_CONFIDENCE_DUPLICATE = "HIGH_CONFIDENCE_DUPLICATE"
    POSSIBLE_DUPLICATE = "POSSIBLE_DUPLICATE"
    DISTINCT_JOB = "DISTINCT_JOB"
    NEEDS_MANUAL_REVIEW = "NEEDS_MANUAL_REVIEW"


class DuplicateGroupStatus(str, enum.Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    MERGED = "MERGED"
    REJECTED = "REJECTED"
    RESOLVED = "RESOLVED"


class CanonicalJob(Base):
    """
    Canonical Vacancy Model.
    Represents a unified, authoritative job vacancy aggregated across multiple
    discovery sources and providers without losing individual source records.
    """
    __tablename__ = "canonical_jobs"

    id = Column(Integer, primary_key=True, index=True)
    canonical_job_id = Column(String, unique=True, index=True, nullable=False)  # e.g. "CANON-GROWW-1001"
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True)
    company_name = Column(String, nullable=False, index=True)

    # Title & Archetype Normalization
    title = Column(String, nullable=False)  # Representative job title
    canonical_job_title = Column(String, nullable=False, index=True)  # Standardized role title
    normalized_title = Column(String, nullable=False, index=True)  # Lowercase normalized key

    # Location & Workplace Details
    location = Column(String, nullable=True)
    city = Column(String, nullable=True, index=True)
    state = Column(String, nullable=True)
    country = Column(String, nullable=True, index=True)
    is_remote = Column(Boolean, default=False, nullable=False, index=True)
    workplace_type = Column(String, nullable=True)  # REMOTE, HYBRID, ON_SITE, UNSPECIFIED

    # Employment & Requirements
    employment_type = Column(String, nullable=True)  # FULL_TIME, PART_TIME, CONTRACT, INTERNSHIP
    seniority_level = Column(String, nullable=True, index=True)  # ENTRY_LEVEL, MID_LEVEL, SENIOR, LEAD_STAFF
    experience_min_years = Column(Float, nullable=True)
    experience_max_years = Column(Float, nullable=True)
    degree_requirements = Column(Text, nullable=True)  # JSON list
    field_of_study = Column(Text, nullable=True)  # JSON list

    # Content & Skills
    description = Column(Text, nullable=False)
    responsibilities = Column(Text, nullable=True)  # JSON list
    qualifications = Column(Text, nullable=True)  # JSON list
    required_skills = Column(Text, nullable=True)  # JSON list of dicts
    preferred_skills = Column(Text, nullable=True)  # JSON list of dicts

    # Compensation
    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    salary_currency = Column(String, nullable=True)
    salary_period = Column(String, nullable=True)

    # Primary URLs
    canonical_application_url = Column(String, nullable=True)
    canonical_source_url = Column(String, nullable=True)

    # Vacancy Lifecycle Tracking
    vacancy_status = Column(String, default=VacancyStatus.ACTIVE.value, nullable=False, index=True)
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    last_status_change_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    consecutive_missing_checks = Column(Integer, default=0, nullable=False)
    verification_attempts = Column(Integer, default=0, nullable=False)
    verification_details = Column(Text, nullable=True)  # JSON string of verification results

    # Provenance Summary
    source_count = Column(Integer, default=1, nullable=False)
    dedup_confidence = Column(Float, default=1.0, nullable=False)
    match_evidence = Column(Text, nullable=True)  # JSON string explaining merge decisions

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    company_rel = relationship("Company", back_populates="canonical_jobs")
    normalized_jobs = relationship("Job", back_populates="canonical_job_rel")
    sources = relationship("CanonicalJobSource", back_populates="canonical_job", cascade="all, delete-orphan")
    review_groups = relationship("DuplicateReviewGroup", back_populates="canonical_job")
    embedding_rel = relationship("JobEmbedding", back_populates="canonical_job", uselist=False, cascade="all, delete-orphan")
    matches = relationship("CandidateJobMatch", back_populates="canonical_job", cascade="all, delete-orphan")


class CanonicalJobSource(Base):
    """
    Every individual source observation associated with a Canonical Vacancy.
    Retains every provider, source URL, external job ID, application URL, and metadata.
    Never discards source provenance.
    """
    __tablename__ = "canonical_job_sources"

    id = Column(Integer, primary_key=True, index=True)
    canonical_job_id = Column(Integer, ForeignKey("canonical_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    raw_discovery_id = Column(Integer, ForeignKey("discovered_jobs.id", ondelete="SET NULL"), nullable=True, index=True)

    provider = Column(String, nullable=False, index=True)  # greenhouse, lever, firecrawl, portal, etc.
    external_job_id = Column(String, nullable=True, index=True)
    source_url = Column(String, nullable=True)
    application_url = Column(String, nullable=True)
    discovered_title = Column(String, nullable=True)
    discovered_location = Column(String, nullable=True)
    department = Column(String, nullable=True)
    metadata_json = Column(Text, nullable=True)  # JSON text

    is_primary = Column(Boolean, default=False, nullable=False)
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    canonical_job = relationship("CanonicalJob", back_populates="sources")
    normalized_job = relationship("Job")
    discovered_job = relationship("DiscoveredJob")


class DuplicateReviewGroup(Base):
    """
    Tracks duplicate matches requiring review or confirmed through automatic merging.
    Classifies matches as EXACT_DUPLICATE, HIGH_CONFIDENCE_DUPLICATE, etc.
    """
    __tablename__ = "duplicate_review_groups"

    id = Column(Integer, primary_key=True, index=True)
    group_key = Column(String, unique=True, index=True, nullable=False)
    canonical_job_id = Column(Integer, ForeignKey("canonical_jobs.id", ondelete="SET NULL"), nullable=True, index=True)

    duplicate_type = Column(String, nullable=False, index=True)  # EXACT_DUPLICATE, HIGH_CONFIDENCE_DUPLICATE, etc.
    status = Column(String, default=DuplicateGroupStatus.PENDING_REVIEW.value, nullable=False, index=True)

    similarity_score = Column(Float, default=0.0, nullable=False)
    match_reasons = Column(Text, nullable=True)  # JSON text
    candidate_job_ids = Column(Text, nullable=False)  # JSON list of Job IDs

    resolution_action = Column(String, nullable=True)  # MERGE, REJECT_DISTINCT, KEEP_SEPARATE
    resolution_notes = Column(Text, nullable=True)
    resolved_by = Column(String, nullable=True)  # manual_user, auto_merger
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    canonical_job = relationship("CanonicalJob", back_populates="review_groups")

