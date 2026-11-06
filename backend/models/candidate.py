# backend/models/candidate.py
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.orm import relationship
from db.database import Base

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    # Store a hash or UUID of the resume to avoid duplicates
    resume_hash = Column(String, unique=True, index=True, nullable=False)
    # Raw resume filename (optional, not persisted long-term)
    filename = Column(String, nullable=True)
    # JSON representation of extracted profile (skills, education, etc.)
    profile_json = Column(Text, nullable=False)
    recommendations_json = Column(Text, nullable=True)
    confirmed_roles_json = Column(Text, nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    embedding_rel = relationship("CandidateEmbedding", back_populates="candidate", uselist=False, cascade="all, delete-orphan")
    matches = relationship("CandidateJobMatch", back_populates="candidate", cascade="all, delete-orphan")


