# backend/models/user_preferences.py
"""
Candidate Job Search Preferences Model for AI Job Search Agent.
Persists location, remote/on-site, employment types, salary/stipend targets, and thresholds.
"""

from sqlalchemy import Column, Integer, Float, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from db.database import Base


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    preferred_locations = Column(Text, nullable=True)  # JSON list, e.g. '["Bengaluru", "Hyderabad", "Remote"]'
    work_modes = Column(Text, nullable=True)           # JSON list, e.g. '["REMOTE", "HYBRID", "ON_SITE"]'
    employment_types = Column(Text, nullable=True)     # JSON list, e.g. '["FULL_TIME", "INTERNSHIP"]'
    min_salary = Column(Float, nullable=True)
    min_stipend = Column(Float, nullable=True)
    min_match_score = Column(Float, default=30.0, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    candidate = relationship("Candidate", backref="preferences", uselist=False)

