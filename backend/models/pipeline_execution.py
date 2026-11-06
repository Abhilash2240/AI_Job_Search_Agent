# backend/models/pipeline_execution.py
"""
Pipeline Execution Model for AI Job Search Agent.
Tracks automated and manual job discovery, extraction, deduplication,
verification, embedding generation, and candidate matching runs.
"""

import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from db.database import Base


class PipelineTrigger(str, enum.Enum):
    MANUAL = "MANUAL"
    SCHEDULED = "SCHEDULED"


class PipelineStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PipelineExecution(Base):
    __tablename__ = "pipeline_executions"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(100), unique=True, index=True, nullable=False)
    trigger_type = Column(String(50), default=PipelineTrigger.MANUAL.value, nullable=False)
    status = Column(String(50), default=PipelineStatus.PENDING.value, nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    stages_executed = Column(Text, nullable=True)  # JSON dictionary of stage metrics
    jobs_discovered = Column(Integer, default=0, nullable=False)
    jobs_extracted = Column(Integer, default=0, nullable=False)
    canonical_vacancies_updated = Column(Integer, default=0, nullable=False)
    embeddings_generated = Column(Integer, default=0, nullable=False)
    matches_computed = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)

