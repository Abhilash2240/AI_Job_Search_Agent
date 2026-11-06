# backend/schemas/job_embedding.py
"""
Pydantic Schemas for Phase 6: Job Embeddings & Vector Storage.
"""

from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict


class JobEmbeddingItem(BaseModel):
    id: int
    canonical_job_id: int
    canonical_job_code: str
    job_title: str
    company_name: str
    model_name: str
    dimensions: int
    content_hash: str
    status: str
    last_error: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class JobEmbeddingBatchRequest(BaseModel):
    canonical_job_ids: Optional[List[Any]] = Field(
        default=None,
        description="Optional list of Canonical Job IDs (integers or strings) to embed.",
    )
    limit: Optional[int] = Field(
        default=None,
        ge=1,
        description="Maximum number of canonical jobs to process.",
    )
    force: bool = Field(
        default=False,
        description="Whether to re-embed and overwrite even if content hash is unchanged.",
    )


class JobEmbeddingSummaryResponse(BaseModel):
    total_canonical_jobs: int
    total_embeddings: int
    completed_embeddings: int
    pending_embeddings: int
    stale_embeddings: int
    failed_embeddings: int
    missing_embeddings: int
    model_name: str
    dimensions: int


class JobEmbeddingBatchResponse(BaseModel):
    status: str
    total_considered: int
    generated_count: int
    skipped_count: int
    failed_count: int
    items: List[JobEmbeddingItem]


class JobEmbeddingListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[JobEmbeddingItem]


class RetryFailedRequest(BaseModel):
    limit: Optional[int] = Field(
        default=None,
        ge=1,
        description="Maximum number of failed embeddings to retry.",
    )


class RetryFailedResponse(BaseModel):
    status: str
    retried_count: int
    succeeded_count: int
    failed_count: int
    message: Optional[str] = None
