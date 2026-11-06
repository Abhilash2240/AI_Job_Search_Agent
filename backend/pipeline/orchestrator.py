# backend/pipeline/orchestrator.py
"""
Unified Pipeline Orchestrator for AI Job Search Agent.
Coordinates the end-to-end automated cycle:
Discovery -> Extraction -> Deduplication -> Verification -> Embeddings -> Matching.
Provides run locking, execution history logging, stage-level metrics, and failure recovery.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import AsyncSessionLocal
from models.pipeline_execution import PipelineExecution, PipelineTrigger, PipelineStatus
from models.canonical_job import CanonicalJob, VacancyStatus
from models.source import DiscoveredJob
from models.job import Job
from models.candidate import Candidate
from jobs.extraction_service import extraction_service
from deduplication.dedup_service import JobDeduplicationService
from verification.vacancy_verifier import VacancyVerificationService
from embeddings.job_embedder import job_embedding_service
from matching.matching_service import matching_service

logger = logging.getLogger("pipeline_orchestrator")


class PipelineOrchestrator:
    """Manages full or partial automated pipeline execution runs."""

    def __init__(self):
        self._lock: Optional[asyncio.Lock] = None
        self._is_running = False
        self._current_run_id: Optional[str] = None
        self.dedup_service = JobDeduplicationService()
        self.verification_service = VacancyVerificationService()

    @property
    def lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def current_run_id(self) -> Optional[str]:
        return self._current_run_id

    async def execute_pipeline(
        self,
        trigger_type: str = PipelineTrigger.MANUAL.value,
        stages: Optional[List[str]] = None,
        candidate_id: Optional[int] = None,
        force_matching: bool = False,
        filter_targeting: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes pipeline stages sequentially with error handling and history recording.
        filter_targeting: when True, discovery skips jobs that don't match candidate criteria.
        """
        if self.lock.locked() or self._is_running:
            return {
                "status": "BUSY",
                "message": "A pipeline run is currently in progress",
                "run_id": self._current_run_id,
            }

        async with self.lock:
            self._is_running = True
            run_id = f"RUN-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
            self._current_run_id = run_id

            valid_stages = {"discovery", "extraction", "deduplication", "verification", "embeddings", "matching"}
            stages_to_run = set(s.lower() for s in stages) if stages else valid_stages

            stage_metrics: Dict[str, Any] = {}
            error_message: Optional[str] = None
            pipeline_status = PipelineStatus.COMPLETED.value

            async with AsyncSessionLocal() as db:
                record = PipelineExecution(
                    run_id=run_id,
                    trigger_type=trigger_type,
                    status=PipelineStatus.RUNNING.value,
                    started_at=datetime.now(timezone.utc),
                )
                db.add(record)
                await db.commit()

                try:
                    # 1. DISCOVERY STAGE
                    if "discovery" in stages_to_run:
                        logger.info(f"[{run_id}] Stage 1: Running Discovery...")
                        disc_count_before = (await db.execute(select(func.count(DiscoveredJob.id)))).scalar() or 0

                        from discovery.discovery_orchestrator import DiscoveryOrchestrator
                        disc_orch = DiscoveryOrchestrator()
                        disc_res = await disc_orch.run_discovery(
                            limit=10,
                            candidate_id=candidate_id,
                            filter_targeting=filter_targeting,
                        )

                        disc_count_after = (await db.execute(select(func.count(DiscoveredJob.id)))).scalar() or 0
                        new_disc = max(0, disc_count_after - disc_count_before)
                        record.jobs_discovered = new_disc
                        stage_metrics["discovery"] = {
                            "status": "COMPLETED",
                            "new_discovered": new_disc,
                            "summary": disc_res,
                        }
                    else:
                        stage_metrics["discovery"] = {"status": "SKIPPED"}

                    # 2. EXTRACTION STAGE
                    if "extraction" in stages_to_run:
                        logger.info(f"[{run_id}] Stage 2: Running Extraction...")
                        ext_res = await extraction_service.extract_all_unextracted(db=db, limit=50)
                        extracted = ext_res.get("extracted_count", 0)
                        record.jobs_extracted = extracted
                        stage_metrics["extraction"] = {
                            "status": "COMPLETED",
                            "extracted_count": extracted,
                        }
                    else:
                        stage_metrics["extraction"] = {"status": "SKIPPED"}

                    # 3. DEDUPLICATION STAGE
                    if "deduplication" in stages_to_run:
                        logger.info(f"[{run_id}] Stage 3: Running Deduplication...")
                        dedup_res = await self.dedup_service.run_deduplication(db=db, auto_merge=True)
                        merged = dedup_res.get("merged_groups_count", 0)
                        canonical_active = (
                            await db.execute(
                                select(func.count(CanonicalJob.id)).where(
                                    CanonicalJob.vacancy_status == VacancyStatus.ACTIVE.value
                                )
                            )
                        ).scalar() or 0
                        record.canonical_vacancies_updated = canonical_active
                        stage_metrics["deduplication"] = {
                            "status": "COMPLETED",
                            "merged_groups": merged,
                            "total_canonical_active": canonical_active,
                        }
                    else:
                        stage_metrics["deduplication"] = {"status": "SKIPPED"}

                    # 4. VERIFICATION STAGE
                    if "verification" in stages_to_run:
                        logger.info(f"[{run_id}] Stage 4: Running Vacancy Verification...")
                        verif_res = await self.verification_service.run_batch_verification(db=db, limit=10)
                        stage_metrics["verification"] = {
                            "status": "COMPLETED",
                            "verified_count": verif_res.get("total_checked", 0),
                            "active_count": verif_res.get("active", 0),
                            "closed_count": verif_res.get("closed", 0),
                        }
                    else:
                        stage_metrics["verification"] = {"status": "SKIPPED"}

                    # 5. EMBEDDINGS STAGE
                    if "embeddings" in stages_to_run:
                        logger.info(f"[{run_id}] Stage 5: Running Job Embeddings...")
                        emb_res = await job_embedding_service.generate_batch_embeddings(db=db, force=False)
                        generated_embs = emb_res.get("generated_count", 0)
                        record.embeddings_generated = generated_embs
                        stage_metrics["embeddings"] = {
                            "status": "COMPLETED",
                            "generated_count": generated_embs,
                            "skipped_count": emb_res.get("skipped_count", 0),
                        }
                    else:
                        stage_metrics["embeddings"] = {"status": "SKIPPED"}

                    # 6. MATCHING STAGE
                    if "matching" in stages_to_run:
                        logger.info(f"[{run_id}] Stage 6: Running Candidate Matching...")
                        if candidate_id:
                            matches = await matching_service.run_matching_for_candidate(
                                db=db, candidate_id=candidate_id, force=force_matching
                            )
                            matches_count = len(matches)
                            candidates_eval = 1
                        else:
                            batch_res = await matching_service.run_batch_matching(db=db, force=force_matching)
                            matches_count = batch_res.get("total_matches_generated", 0)
                            candidates_eval = batch_res.get("candidates_evaluated", 0)

                        record.matches_computed = matches_count
                        stage_metrics["matching"] = {
                            "status": "COMPLETED",
                            "matches_computed": matches_count,
                            "candidates_evaluated": candidates_eval,
                        }
                    else:
                        stage_metrics["matching"] = {"status": "SKIPPED"}

                except Exception as ex:
                    logger.error(f"[{run_id}] Pipeline execution failed: {ex}", exc_info=True)
                    pipeline_status = PipelineStatus.FAILED.value
                    error_message = str(ex)

                finally:
                    record.status = pipeline_status
                    record.completed_at = datetime.now(timezone.utc)
                    record.stages_executed = json.dumps(stage_metrics)
                    record.error_message = error_message
                    await db.commit()
                    self._is_running = False
                    self._current_run_id = None

            return {
                "run_id": run_id,
                "status": pipeline_status,
                "stages": stage_metrics,
                "error": error_message,
                "completed_at": record.completed_at.isoformat() if record.completed_at else None,
            }

    async def get_history(self, db: AsyncSession, limit: int = 20) -> List[PipelineExecution]:
        """Retrieve recent pipeline execution runs."""
        stmt = (
            select(PipelineExecution)
            .order_by(PipelineExecution.started_at.desc())
            .limit(limit)
        )
        return (await db.execute(stmt)).scalars().all()

    # Backward-compat alias
    async def verify_batch(self, db: AsyncSession, limit: int = 10):
        return await self.verification_service.run_batch_verification(db=db, limit=limit)


pipeline_orchestrator = PipelineOrchestrator()
