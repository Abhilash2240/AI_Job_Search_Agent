# backend/models/candidate_job_match.py
"""
Candidate-to-Job Matching Models for AI Job Search Agent (Phase 7).
Stores explainable multi-component matching results, candidate embeddings,
and eligibility determinations.
"""

import enum
import json
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    LargeBinary,
    func,
)
from sqlalchemy.orm import relationship
import numpy as np

from db.database import Base


class EligibilityStatus(str, enum.Enum):
    ELIGIBLE = "ELIGIBLE"
    ELIGIBLE_WITH_CONDITIONS = "ELIGIBLE_WITH_CONDITIONS"
    INELIGIBLE = "INELIGIBLE"
    DISQUALIFIED = "INELIGIBLE"   # backward-compat alias → maps to INELIGIBLE
    NEEDS_REVIEW = "NEEDS_REVIEW"
    UNKNOWN = "UNKNOWN"


class MatchClassification(str, enum.Enum):
    HIGHLY_RECOMMENDED = "HIGHLY_RECOMMENDED"
    RECOMMENDED = "RECOMMENDED"
    BORDERLINE = "BORDERLINE"
    LOW_COMPATIBILITY = "LOW_COMPATIBILITY"


class CandidateEmbedding(Base):
    """
    Persisted semantic vector embedding for a Candidate Technical Profile.
    Generated with fine-tuned SBERT (384 dimensions, L2-normalized).
    Tracks SHA-256 content hash of the synthesized profile for cache invalidation.
    """
    __tablename__ = "candidate_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(
        Integer,
        ForeignKey("candidates.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )

    embedding_blob = Column(LargeBinary, nullable=True)  # Raw 384-d float32 bytes (1536 bytes)
    embedding_json = Column(Text, nullable=True)        # JSON array representation

    model_name = Column(String, default="fine-tuned-sbert", nullable=False)
    dimensions = Column(Integer, default=384, nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)
    status = Column(String, default="COMPLETED", nullable=False, index=True)
    last_error = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    candidate = relationship("Candidate", back_populates="embedding_rel")

    def get_vector(self) -> np.ndarray:
        if self.embedding_blob:
            return np.frombuffer(self.embedding_blob, dtype=np.float32)
        if self.embedding_json:
            return np.array(json.loads(self.embedding_json), dtype=np.float32)
        raise ValueError(f"CandidateEmbedding ID {self.id} has no vector data.")

    def set_vector(self, vector: np.ndarray) -> None:
        vec32 = np.array(vector, dtype=np.float32)
        self.embedding_blob = vec32.tobytes()
        self.embedding_json = json.dumps(vec32.tolist())
        self.dimensions = len(vec32)


class CandidateJobMatch(Base):
    """
    Explainable Candidate-to-Job Matching Record.
    Stores composite score, normalized component scores (0-1), score coverage,
    eligibility status, detailed evidence breakdowns, and invalidation hashes.
    """
    __tablename__ = "candidate_job_matches"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(
        Integer,
        ForeignKey("candidates.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    canonical_job_id = Column(
        Integer,
        ForeignKey("canonical_jobs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # Composite & Component Scores
    composite_score = Column(Float, nullable=False, index=True)  # 0.0 - 100.0 scale
    semantic_score = Column(Float, nullable=False)               # 0.0 - 1.0 scale
    skill_score = Column(Float, nullable=False)                  # 0.0 - 1.0 scale
    role_score = Column(Float, nullable=False)                   # 0.0 - 1.0 scale
    experience_score = Column(Float, nullable=False)             # 0.0 - 1.0 scale
    education_score = Column(Float, nullable=False)              # 0.0 - 1.0 scale
    location_score = Column(Float, nullable=False)               # 0.0 - 1.0 scale
    score_coverage = Column(Float, nullable=False, default=1.0)  # Proportion of weight supported by evaluable data

    # Classification & Eligibility
    eligibility_status = Column(
        String,
        default=EligibilityStatus.ELIGIBLE.value,
        nullable=False,
        index=True,
    )
    match_classification = Column(
        String,
        default=MatchClassification.RECOMMENDED.value,
        nullable=False,
        index=True,
    )

    # Relevance Gate
    is_relevant = Column(Boolean, default=True, nullable=False, index=True)
    role_family = Column(String(100), default="SOFTWARE_ENGINEERING", nullable=True, index=True)
    relevance_score = Column(Float, default=1.0, nullable=True)
    rejection_reasons = Column(Text, nullable=True)  # JSON list of reasons if IRRELEVANT

    # Detailed Evidence & Breakdown (JSON)
    matched_skills = Column(Text, nullable=True)             # JSON list of matched skills with candidate evidence
    missing_skills = Column(Text, nullable=True)             # JSON list of missing required/preferred skills
    inferred_skills_potential = Column(Text, nullable=True)  # JSON list of candidate inferred skills that might align
    matched_roles = Column(Text, nullable=True)              # JSON object of best matching candidate role & source
    explanation_data = Column(Text, nullable=True)           # Human-readable paragraph explanation
    disqualification_reasons = Column(Text, nullable=True)   # JSON list of reasons if INELIGIBLE or NEEDS_REVIEW
    component_evidence = Column(Text, nullable=True)         # JSON dict of fine-grained component metrics

    # Incremental Invalidation & Versioning
    candidate_content_hash = Column(String(64), nullable=False)
    job_content_hash = Column(String(64), nullable=False)
    algorithm_version = Column(String, default="phase7-v1.0", nullable=False)
    matching_status = Column(String, default="COMPLETED", nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    evaluated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("candidate_id", "canonical_job_id", name="uq_candidate_job_match"),
    )

    candidate = relationship("Candidate", back_populates="matches")
    canonical_job = relationship("CanonicalJob", back_populates="matches")

