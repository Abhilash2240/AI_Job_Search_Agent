# backend/app/api/pipeline.py
"""
Automated Job Search Pipeline API Router.
Endpoints for triggering pipeline runs, checking live status, and inspecting execution history.
"""

import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from pipeline.orchestrator import pipeline_orchestrator
from models.pipeline_execution import PipelineExecution
from schemas.pipeline import (
    PipelineRunRequest,
    PipelineExecutionResponse,
    PipelineHistoryResponse,
)

router = APIRouter(prefix="/api/pipeline", tags=["Pipeline & Automation"])


@router.post("/run", status_code=status.HTTP_200_OK)
async def trigger_pipeline(
    req: Optional[PipelineRunRequest] = None,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger the automated job pipeline:
    Discovery -> Extraction -> Deduplication -> Verification -> Embeddings -> Matching.
    Runs asynchronously if requested or executes synchronously.
    """
    request_data = req or PipelineRunRequest()

    if pipeline_orchestrator.is_running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A pipeline run is already in progress (Run ID: {pipeline_orchestrator.current_run_id})",
        )

    # Execute pipeline
    result = await pipeline_orchestrator.execute_pipeline(
        trigger_type=request_data.trigger_type or "MANUAL",
        stages=request_data.stages,
        candidate_id=request_data.candidate_id,
        force_matching=request_data.force_matching or False,
    )

    return result


@router.get("/status")
async def get_pipeline_status():
    """Returns whether the pipeline is currently running and the active run ID."""
    return {
        "is_running": pipeline_orchestrator.is_running,
        "current_run_id": pipeline_orchestrator.current_run_id,
    }


@router.get("/history", response_model=PipelineHistoryResponse)
async def get_pipeline_history(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Returns past pipeline execution records and stage-level metrics."""
    records = await pipeline_orchestrator.get_history(db=db, limit=limit)
    items = []
    for r in records:
        stages_data = json.loads(r.stages_executed) if r.stages_executed else None
        items.append(
            PipelineExecutionResponse(
                id=r.id,
                run_id=r.run_id,
                trigger_type=r.trigger_type,
                status=r.status,
                started_at=r.started_at,
                completed_at=r.completed_at,
                stages_executed=stages_data,
                jobs_discovered=r.jobs_discovered,
                jobs_extracted=r.jobs_extracted,
                canonical_vacancies_updated=r.canonical_vacancies_updated,
                embeddings_generated=r.embeddings_generated,
                matches_computed=r.matches_computed,
                error_message=r.error_message,
            )
        )
    return PipelineHistoryResponse(total=len(items), items=items)

