# backend/schemas/pipeline.py
"""
Pydantic Schemas for Automated Job Search Pipeline Execution.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class PipelineRunRequest(BaseModel):
    trigger_type: Optional[str] = "MANUAL"
    stages: Optional[List[str]] = None  # None means all: discovery, extraction, deduplication, verification, embeddings, matching
    candidate_id: Optional[int] = None
    force_matching: Optional[bool] = False


class PipelineExecutionResponse(BaseModel):
    id: int
    run_id: str
    trigger_type: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    stages_executed: Optional[Dict[str, Any]] = None
    jobs_discovered: int
    jobs_extracted: int
    canonical_vacancies_updated: int
    embeddings_generated: int
    matches_computed: int
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PipelineHistoryResponse(BaseModel):
    total: int
    items: List[PipelineExecutionResponse]

