# backend/models/job_embedding.py
"""
Job Embedding Model for AI Job Search Agent (Phase 6).
Persists semantic vector embeddings for canonical job vacancies using the
fine-tuned SBERT model (384 dimensions, normalized).
"""

import enum
import json
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    LargeBinary,
    func,
)
from sqlalchemy.orm import relationship
import numpy as np

from db.database import Base


class EmbeddingStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    STALE = "STALE"
    FAILED = "FAILED"


class JobEmbedding(Base):
    """
    Persistent semantic vector embedding for a Canonical Job Vacancy.
    Uses fine-tuned SBERT (384 dimensions, L2-normalized).
    Stores both raw float32 BLOB (1536 bytes) and JSON text (portable/inspectable).
    Tracks SHA-256 content hash for deterministic freshness and change detection.
    """
    __tablename__ = "job_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    canonical_job_id = Column(
        Integer,
        ForeignKey("canonical_jobs.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )

    # Vector representations
    embedding_blob = Column(LargeBinary, nullable=True)  # Raw 384-d float32 bytes
    embedding_json = Column(Text, nullable=True)        # JSON array representation

    # Metadata & Freshness
    model_name = Column(String, default="fine-tuned-sbert", nullable=False)
    dimensions = Column(Integer, default=384, nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)
    status = Column(String, default=EmbeddingStatus.COMPLETED.value, nullable=False, index=True)
    last_error = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationship to Canonical Job
    canonical_job = relationship("CanonicalJob", back_populates="embedding_rel")

    def get_vector(self) -> np.ndarray:
        """Returns 1-D numpy array of 384 dimensions."""
        if self.embedding_blob:
            return np.frombuffer(self.embedding_blob, dtype=np.float32)
        if self.embedding_json:
            return np.array(json.loads(self.embedding_json), dtype=np.float32)
        raise ValueError(f"JobEmbedding ID {self.id} has no vector data.")

    def set_vector(self, vector: np.ndarray) -> None:
        """Stores vector as both float32 bytes BLOB and JSON string."""
        vec32 = np.array(vector, dtype=np.float32)
        self.embedding_blob = vec32.tobytes()
        self.embedding_json = json.dumps(vec32.tolist())
        self.dimensions = len(vec32)

