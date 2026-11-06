# backend/models/source.py
import enum
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, ForeignKey, func
)
from sqlalchemy.orm import relationship
from db.database import Base


class VerificationStatus(str, enum.Enum):
    NOT_CHECKED = "NOT_CHECKED"
    VALID = "VALID"
    REDIRECTED = "REDIRECTED"
    BROKEN = "BROKEN"
    BLOCKED = "BLOCKED"
    REQUIRES_MANUAL_REVIEW = "REQUIRES_MANUAL_REVIEW"


class SourceType(str, enum.Enum):
    JOB_BOARD = "job_board"
    COMPANY_CAREER_PAGE = "company_career_page"


class RelevanceCategory(str, enum.Enum):
    IT_SERVICES = "IT Services"
    PRODUCT_COMPANIES = "Product Companies"
    SAAS = "SaaS"
    AI_ML = "AI/ML"
    FINTECH = "FinTech"
    CLOUD_INFRASTRUCTURE = "Cloud and Infrastructure"
    CYBERSECURITY = "Cybersecurity"
    ENTERPRISE_SOFTWARE = "Enterprise Software"
    TECHNOLOGY_STARTUPS = "Technology Startups"
    OTHER = "Other"
    UNKNOWN = "Unknown"


class JobSource(Base):
    __tablename__ = "job_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    source_type = Column(String, default=SourceType.JOB_BOARD.value, nullable=False)
    base_url = Column(String, nullable=False)
    normalized_url = Column(String, nullable=False, index=True)
    category = Column(String, nullable=True, index=True)
    country_scope = Column(String, default="India", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    access_method = Column(String, default="direct", nullable=False)
    source_document = Column(String, nullable=True)
    source_page = Column(Integer, nullable=True)
    verification_status = Column(String, default=VerificationStatus.NOT_CHECKED.value, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    canonical_name = Column(String, nullable=False, index=True)
    normalized_name = Column(String, nullable=False, index=True)
    primary_domain = Column(String, nullable=True, index=True)
    country = Column(String, default="India", nullable=False)
    industry = Column(String, nullable=True)
    relevance_category = Column(String, default=RelevanceCategory.UNKNOWN.value, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    @property
    def name(self) -> str:
        return self.canonical_name

    # Relationships
    career_sources = relationship("CompanyCareerSource", back_populates="company", cascade="all, delete-orphan")
    contacts = relationship("CompanyContact", back_populates="company", cascade="all, delete-orphan")
    discovered_jobs = relationship("DiscoveredJob", back_populates="company", cascade="all, delete-orphan")
    normalized_jobs = relationship("Job", back_populates="company_rel", cascade="all, delete-orphan")
    canonical_jobs = relationship("CanonicalJob", back_populates="company_rel", cascade="all, delete-orphan")


class CompanyCareerSource(Base):
    __tablename__ = "company_career_sources"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    career_url = Column(String, nullable=False)
    normalized_url = Column(String, nullable=False, index=True)
    source_document = Column(String, nullable=False)
    source_page = Column(Integer, nullable=True)
    verification_status = Column(String, default=VerificationStatus.NOT_CHECKED.value, nullable=False)
    ats_provider = Column(String, nullable=True, index=True)  # greenhouse, lever, workday, etc.
    ats_identifier = Column(String, nullable=True, index=True)  # board_token or site_id
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    company = relationship("Company", back_populates="career_sources")


class CompanyContact(Base):
    __tablename__ = "company_contacts"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String, nullable=False, index=True)
    contact_type = Column(String, default="hr_recruitment", nullable=False)
    source_document = Column(String, nullable=False)
    source_page = Column(Integer, nullable=True)
    verification_status = Column(String, default=VerificationStatus.NOT_CHECKED.value, nullable=False)
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    company = relationship("Company", back_populates="contacts")


class SourceImportBatch(Base):
    __tablename__ = "source_import_batches"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    imported_at = Column(DateTime(timezone=True), server_default=func.now())
    total_extracted = Column(Integer, default=0, nullable=False)
    total_imported = Column(Integer, default=0, nullable=False)
    total_duplicates = Column(Integer, default=0, nullable=False)
    total_invalid = Column(Integer, default=0, nullable=False)
    total_needs_review = Column(Integer, default=0, nullable=False)
    import_status = Column(String, default="COMPLETED", nullable=False)
    details = Column(Text, nullable=True)


class DiscoveredJob(Base):
    __tablename__ = "discovered_jobs"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String, nullable=False, index=True)  # greenhouse, lever, firecrawl
    external_job_id = Column(String, nullable=True, index=True)
    dedup_key = Column(String, nullable=False, unique=True, index=True)
    discovered_title = Column(String, nullable=False, index=True)
    discovered_location = Column(String, nullable=True)
    department = Column(String, nullable=True)
    job_url = Column(String, nullable=False)
    application_url = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    raw_payload = Column(Text, nullable=True)  # Original JSON payload string
    first_discovered_at = Column(DateTime(timezone=True), server_default=func.now())
    last_discovered_at = Column(DateTime(timezone=True), server_default=func.now())
    discovery_status = Column(String, default="DISCOVERED", nullable=False, index=True)

    company = relationship("Company", back_populates="discovered_jobs")


