# backend/models/application.py
"""
Job Application and Lifecycle Tracking Models for AI Job Search Agent.
Tracks candidate application progress, interview schedules, follow-ups, and status transitions.
"""

import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship
from db.database import Base


class ApplicationStatus(str, enum.Enum):
    INTERESTED = "INTERESTED"
    SAVED = "SAVED"
    APPLIED = "APPLIED"
    ASSESSMENT = "ASSESSMENT"
    INTERVIEW = "INTERVIEW"
    OFFER = "OFFER"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"


class JobApplication(Base):
    __tablename__ = "job_applications"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    canonical_job_id = Column(Integer, ForeignKey("canonical_jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    company_name = Column(String(255), nullable=False, index=True)
    job_title = Column(String(255), nullable=False, index=True)
    application_url = Column(Text, nullable=True)
    status = Column(String(50), default=ApplicationStatus.APPLIED.value, nullable=False, index=True)
    applied_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    interview_date = Column(DateTime(timezone=True), nullable=True)
    follow_up_date = Column(DateTime(timezone=True), nullable=True)
    salary_offered = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    candidate = relationship("Candidate", backref="applications")
    canonical_job = relationship("CanonicalJob", backref="applications")
    status_history = relationship(
        "ApplicationStatusHistory",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationStatusHistory.changed_at.desc()",
    )

    __table_args__ = (
        UniqueConstraint("candidate_id", "canonical_job_id", name="uq_candidate_job_application"),
    )


class ApplicationStatusHistory(Base):
    __tablename__ = "application_status_history"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("job_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    from_status = Column(String(50), nullable=True)
    to_status = Column(String(50), nullable=False)
    notes = Column(Text, nullable=True)
    changed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    application = relationship("JobApplication", back_populates="status_history")

