# backend/models/saved_job.py
"""
Saved Jobs Model for AI Job Search Agent.
Allows candidates to bookmark canonical vacancies, track notes, and monitor closure status.
"""

from sqlalchemy import Column, Integer, Text, Boolean, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship
from db.database import Base


class SavedJob(Base):
    __tablename__ = "saved_jobs"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    canonical_job_id = Column(Integer, ForeignKey("canonical_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    candidate = relationship("Candidate", backref="saved_jobs")
    canonical_job = relationship("CanonicalJob", backref="saved_by_candidates")

    __table_args__ = (
        UniqueConstraint("candidate_id", "canonical_job_id", name="uq_candidate_saved_job"),
    )

