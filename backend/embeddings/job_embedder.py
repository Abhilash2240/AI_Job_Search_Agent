# backend/embeddings/job_embedder.py
"""
Job Embedding Service for AI Job Search Agent (Phase 6).
Generates, tracks, updates, and persists 384-dimensional semantic embeddings
for canonical job vacancies using the local fine-tuned SBERT model.
"""

import hashlib
import json
import logging
import re
from typing import List, Dict, Any, Optional, Tuple

import numpy as np
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from embeddings.model_loader import get_model
from embeddings.embedding_service import embed_batch, embed_text
from models.canonical_job import CanonicalJob
from models.job_embedding import JobEmbedding, EmbeddingStatus

logger = logging.getLogger(__name__)

# Model specifications
DEFAULT_MODEL_NAME = "fine-tuned-sbert"
EXPECTED_DIMENSIONS = 384


def sanitize_text(text: Optional[str]) -> str:
    """Strips URLs, excessive whitespace, and control characters."""
    if not text:
        return ""
    # Remove HTTP/HTTPS URLs
    text = re.sub(r"https?://\S+", "", text)
    # Remove tracking tokens / URL-like query artifacts
    text = re.sub(r"[\w.-]+@[\w.-]+", "", text)  # remove raw emails to protect privacy
    # Collapse multiple whitespaces/tabs
    text = re.sub(r"[ \t]+", " ", text)
    # Normalize excessive newlines to double newlines
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def extract_skill_names(skills_field: Any) -> List[str]:
    """
    Extracts distinct canonical skill names from JSON string or list of dicts/strings.
    Sorts alphabetically for deterministic hash generation.
    """
    if not skills_field:
        return []
    
    parsed = skills_field
    if isinstance(skills_field, str):
        try:
            parsed = json.loads(skills_field)
        except Exception:
            parsed = [skills_field]
            
    names = set()
    if isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, dict):
                name = item.get("canonical_name") or item.get("skill_name") or item.get("name")
                if name:
                    clean = str(name).strip()
                    if clean:
                        names.add(clean)
            elif isinstance(item, str):
                clean = item.strip()
                if clean:
                    names.add(clean)
                    
    return sorted(list(names), key=lambda s: s.lower())


def extract_text_list(field: Any) -> List[str]:
    """Extracts a list of strings from JSON string or list."""
    if not field:
        return []
    
    parsed = field
    if isinstance(field, str):
        try:
            parsed = json.loads(field)
        except Exception:
            parsed = [field]
            
    items = []
    if isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, str) and item.strip():
                items.append(item.strip())
            elif isinstance(item, dict):
                text = item.get("text") or item.get("name") or str(item)
                if text.strip():
                    items.append(text.strip())
    return items


def build_canonical_job_text(job: CanonicalJob) -> str:
    """
    Constructs a deterministic, clean structured text representation of a CanonicalJob
    suitable for semantic embedding with fine-tuned SBERT.
    
    Excludes all URLs, external IDs, tracking parameters, raw payloads, and verification logs.
    Preserves exact field ordering for repeatable hashing.
    """
    sections = []

    # 1. Job Title
    title = (job.canonical_job_title or job.title or "").strip()
    if title:
        sections.append(f"Title: {title}")

    # 2. Company Name
    company = (job.company_name or "").strip()
    if company:
        sections.append(f"Company: {company}")

    # 3. Seniority Level
    if job.seniority_level:
        sections.append(f"Seniority: {job.seniority_level.strip()}")

    # 4. Employment Type
    if job.employment_type:
        sections.append(f"Employment Type: {job.employment_type.strip()}")

    # 5. Required Skills (segregated and deterministic)
    req_skills = extract_skill_names(job.required_skills)
    if req_skills:
        sections.append(f"Required Skills: {', '.join(req_skills)}")

    # 6. Preferred Skills
    pref_skills = extract_skill_names(job.preferred_skills)
    if pref_skills:
        sections.append(f"Preferred Skills: {', '.join(pref_skills)}")

    # 7. Education Requirements
    degrees = extract_text_list(job.degree_requirements)
    majors = extract_text_list(job.field_of_study)
    edu_parts = []
    if degrees:
        edu_parts.append(", ".join(degrees))
    if majors:
        edu_parts.append(f"in {', '.join(majors)}")
    if edu_parts:
        sections.append(f"Education: {' '.join(edu_parts)}")

    # 8. Responsibilities
    resp = extract_text_list(job.responsibilities)
    if resp:
        resp_bullets = "\n".join(f"- {sanitize_text(r)}" for r in resp if r.strip())
        if resp_bullets:
            sections.append(f"Responsibilities:\n{resp_bullets}")

    # 9. Qualifications
    qual = extract_text_list(job.qualifications)
    if qual:
        qual_bullets = "\n".join(f"- {sanitize_text(q)}" for q in qual if q.strip())
        if qual_bullets:
            sections.append(f"Qualifications:\n{qual_bullets}")

    # 10. Sanitized Job Description
    clean_desc = sanitize_text(job.description)
    if clean_desc:
        sections.append(f"Description:\n{clean_desc}")

    return "\n\n".join(sections).strip()


def compute_content_hash(text: str) -> str:
    """Computes a SHA-256 hash of the deterministic job text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class JobEmbeddingService:
    """
    Manages vector embeddings for canonical vacancies.
    Supports single embedding, batch processing, incremental change detection,
    failure recovery, and summary metrics.
    """

    async def get_canonical_job(
        self, db: AsyncSession, job_identifier: Any
    ) -> Optional[CanonicalJob]:
        """Resolves CanonicalJob by integer primary key or string canonical_job_id."""
        if isinstance(job_identifier, int) or (isinstance(job_identifier, str) and job_identifier.isdigit()):
            stmt = (
                select(CanonicalJob)
                .options(selectinload(CanonicalJob.embedding_rel))
                .where(CanonicalJob.id == int(job_identifier))
            )
        else:
            stmt = (
                select(CanonicalJob)
                .options(selectinload(CanonicalJob.embedding_rel))
                .where(CanonicalJob.canonical_job_id == str(job_identifier).strip())
            )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def generate_single_embedding(
        self,
        db: AsyncSession,
        job_identifier: Any,
        force: bool = False,
    ) -> JobEmbedding:
        """
        Generates or refreshes embedding for a single CanonicalJob.
        Skips recomputation if content hash matches and status is COMPLETED (unless force=True).
        """
        job = await self.get_canonical_job(db, job_identifier)
        if not job:
            raise ValueError(f"Canonical job not found: {job_identifier}")

        text = build_canonical_job_text(job)
        if not text:
            text = f"Title: {job.title or 'Unknown'}\nCompany: {job.company_name or 'Unknown'}"

        content_hash = compute_content_hash(text)

        # Check existing embedding directly from table
        emb_stmt = select(JobEmbedding).where(JobEmbedding.canonical_job_id == job.id)
        existing = (await db.execute(emb_stmt)).scalar_one_or_none()

        if existing and not force:
            if existing.status == EmbeddingStatus.COMPLETED.value and existing.content_hash == content_hash:
                logger.info(f"Embedding up to date for canonical job {job.canonical_job_id} (hash={content_hash[:8]}). Skipping.")
                return existing

        # Generate embedding vector
        try:
            vec = embed_text(text)
            norm = float(np.linalg.norm(vec))
            if norm == 0.0:
                raise ValueError("Embedding returned zero vector")

            if existing is None:
                existing = JobEmbedding(
                    canonical_job_id=job.id,
                    model_name=DEFAULT_MODEL_NAME,
                    dimensions=len(vec),
                    content_hash=content_hash,
                    status=EmbeddingStatus.COMPLETED.value,
                    last_error=None,
                )
                existing.set_vector(vec)
                db.add(existing)
            else:
                existing.content_hash = content_hash
                existing.model_name = DEFAULT_MODEL_NAME
                existing.dimensions = len(vec)
                existing.status = EmbeddingStatus.COMPLETED.value
                existing.last_error = None
                existing.set_vector(vec)

            await db.commit()
            await db.refresh(existing)
            return existing

        except Exception as err:
            logger.error(f"Failed to generate embedding for job {job.canonical_job_id}: {err}")
            if existing is None:
                existing = JobEmbedding(
                    canonical_job_id=job.id,
                    model_name=DEFAULT_MODEL_NAME,
                    dimensions=EXPECTED_DIMENSIONS,
                    content_hash=content_hash,
                    status=EmbeddingStatus.FAILED.value,
                    last_error=str(err),
                )
                db.add(existing)
            else:
                existing.status = EmbeddingStatus.FAILED.value
                existing.last_error = str(err)

            await db.commit()
            await db.refresh(existing)
            return existing

    async def generate_batch_embeddings(
        self,
        db: AsyncSession,
        canonical_job_ids: Optional[List[Any]] = None,
        limit: Optional[int] = None,
        force: bool = False,
        batch_size: int = 32,
    ) -> Dict[str, Any]:
        """
        Batch generates embeddings for canonical jobs.
        Implements incremental processing: skips unchanged jobs, updates changed/stale jobs,
        and isolates errors per job.
        """
        stmt = (
            select(CanonicalJob)
            .order_by(CanonicalJob.id.asc())
        )

        if canonical_job_ids:
            int_ids = [int(i) for i in canonical_job_ids if isinstance(i, int) or (isinstance(i, str) and i.isdigit())]
            str_ids = [str(i) for i in canonical_job_ids if isinstance(i, str) and not i.isdigit()]
            conds = []
            if int_ids:
                conds.append(CanonicalJob.id.in_(int_ids))
            if str_ids:
                conds.append(CanonicalJob.canonical_job_id.in_(str_ids))
            if conds:
                stmt = stmt.where(or_(*conds))

        if limit is not None and limit > 0:
            stmt = stmt.limit(limit)

        jobs = (await db.execute(stmt)).scalars().all()
        total_considered = len(jobs)
        if not jobs:
            return {
                "status": "COMPLETED",
                "total_considered": 0,
                "generated_count": 0,
                "skipped_count": 0,
                "failed_count": 0,
                "job_embeddings": [],
            }

        # Query existing embeddings directly for robustness
        job_ids = [j.id for j in jobs]
        emb_stmt = select(JobEmbedding).where(JobEmbedding.canonical_job_id.in_(job_ids))
        existing_map = {e.canonical_job_id: e for e in (await db.execute(emb_stmt)).scalars().all()}

        items_to_embed: List[Tuple[CanonicalJob, str, str, Optional[JobEmbedding]]] = []
        skipped_count = 0
        failed_count = 0
        generated_count = 0
        result_embeddings: List[JobEmbedding] = []

        for job in jobs:
            text = build_canonical_job_text(job)
            if not text:
                text = f"Title: {job.title or 'Unknown'}\nCompany: {job.company_name or 'Unknown'}"
            c_hash = compute_content_hash(text)
            existing = existing_map.get(job.id)

            if existing and not force:
                if existing.status == EmbeddingStatus.COMPLETED.value and existing.content_hash == c_hash:
                    skipped_count += 1
                    result_embeddings.append(existing)
                    continue

            items_to_embed.append((job, text, c_hash, existing))

        # Process in batches
        for i in range(0, len(items_to_embed), batch_size):
            chunk = items_to_embed[i : i + batch_size]
            texts = [item[1] for item in chunk]

            try:
                vectors = embed_batch(texts)
                for (job, text, c_hash, existing), vec in zip(chunk, vectors):
                    try:
                        if existing is None:
                            emb = JobEmbedding(
                                canonical_job_id=job.id,
                                model_name=DEFAULT_MODEL_NAME,
                                dimensions=len(vec),
                                content_hash=c_hash,
                                status=EmbeddingStatus.COMPLETED.value,
                                last_error=None,
                            )
                            emb.set_vector(vec)
                            db.add(emb)
                            existing_map[job.id] = emb
                        else:
                            emb = existing
                            emb.content_hash = c_hash
                            emb.model_name = DEFAULT_MODEL_NAME
                            emb.dimensions = len(vec)
                            emb.status = EmbeddingStatus.COMPLETED.value
                            emb.last_error = None
                            emb.set_vector(vec)

                        result_embeddings.append(emb)
                        generated_count += 1
                    except Exception as err:
                        failed_count += 1
                        logger.error(f"Error persisting vector for job {job.id}: {err}")
                        if existing:
                            existing.status = EmbeddingStatus.FAILED.value
                            existing.last_error = str(err)
                            result_embeddings.append(existing)

            except Exception as batch_err:
                logger.error(f"Batch embedding failed for chunk {i}: {batch_err}")
                # Fallback to individual embedding to isolate which one failed
                for job, text, c_hash, existing in chunk:
                    try:
                        vec = embed_text(text)
                        if existing is None:
                            emb = JobEmbedding(
                                canonical_job_id=job.id,
                                model_name=DEFAULT_MODEL_NAME,
                                dimensions=len(vec),
                                content_hash=c_hash,
                                status=EmbeddingStatus.COMPLETED.value,
                                last_error=None,
                            )
                            emb.set_vector(vec)
                            db.add(emb)
                            existing_map[job.id] = emb
                        else:
                            emb = existing
                            emb.content_hash = c_hash
                            emb.dimensions = len(vec)
                            emb.status = EmbeddingStatus.COMPLETED.value
                            emb.last_error = None
                            emb.set_vector(vec)
                        result_embeddings.append(emb)
                        generated_count += 1
                    except Exception as single_err:
                        failed_count += 1
                        if existing is None:
                            emb = JobEmbedding(
                                canonical_job_id=job.id,
                                model_name=DEFAULT_MODEL_NAME,
                                dimensions=EXPECTED_DIMENSIONS,
                                content_hash=c_hash,
                                status=EmbeddingStatus.FAILED.value,
                                last_error=str(single_err),
                            )
                            db.add(emb)
                            existing_map[job.id] = emb
                        else:
                            emb = existing
                            emb.status = EmbeddingStatus.FAILED.value
                            emb.last_error = str(single_err)
                        result_embeddings.append(emb)

        await db.commit()

        return {
            "status": "COMPLETED",
            "total_considered": total_considered,
            "generated_count": generated_count,
            "skipped_count": skipped_count,
            "failed_count": failed_count,
            "job_embeddings": result_embeddings,
        }

    async def retry_failed_embeddings(
        self, db: AsyncSession, limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Finds all embeddings with status FAILED and retries generation."""
        stmt = (
            select(JobEmbedding)
            .where(JobEmbedding.status == EmbeddingStatus.FAILED.value)
            .order_by(JobEmbedding.updated_at.asc())
        )
        if limit is not None and limit > 0:
            stmt = stmt.limit(limit)

        failed_records = (await db.execute(stmt)).scalars().all()
        if not failed_records:
            return {
                "status": "COMPLETED",
                "retried_count": 0,
                "succeeded_count": 0,
                "failed_count": 0,
                "message": "No failed embeddings found to retry.",
            }

        job_ids = [r.canonical_job_id for r in failed_records]
        res = await self.generate_batch_embeddings(
            db=db, canonical_job_ids=job_ids, force=True
        )

        return {
            "status": "COMPLETED",
            "retried_count": len(failed_records),
            "succeeded_count": res.get("generated_count", 0),
            "failed_count": res.get("failed_count", 0),
        }

    async def get_summary(self, db: AsyncSession) -> Dict[str, Any]:
        """Computes summary statistics for canonical jobs and embeddings."""
        total_canonical = (await db.execute(select(func.count(CanonicalJob.id)))).scalar_one()

        # Group by status in job_embeddings
        stmt = select(JobEmbedding.status, func.count(JobEmbedding.id)).group_by(JobEmbedding.status)
        status_counts = dict((await db.execute(stmt)).all())

        total_embeddings = sum(status_counts.values())
        completed = status_counts.get(EmbeddingStatus.COMPLETED.value, 0)
        pending = status_counts.get(EmbeddingStatus.PENDING.value, 0)
        stale = status_counts.get(EmbeddingStatus.STALE.value, 0)
        failed = status_counts.get(EmbeddingStatus.FAILED.value, 0)
        missing = max(0, total_canonical - total_embeddings)

        return {
            "total_canonical_jobs": total_canonical,
            "total_embeddings": total_embeddings,
            "completed_embeddings": completed,
            "pending_embeddings": pending,
            "stale_embeddings": stale,
            "failed_embeddings": failed,
            "missing_embeddings": missing,
            "model_name": DEFAULT_MODEL_NAME,
            "dimensions": EXPECTED_DIMENSIONS,
        }

    async def get_status_list(
        self,
        db: AsyncSession,
        status_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """Returns paginated list of job embedding records with canonical job info."""
        conditions = []
        if status_filter:
            conditions.append(JobEmbedding.status == status_filter.upper().strip())

        where_clause = and_(*conditions) if conditions else True

        total = (
            await db.execute(select(func.count(JobEmbedding.id)).where(where_clause))
        ).scalar_one()

        offset = (page - 1) * page_size
        stmt = (
            select(JobEmbedding)
            .options(selectinload(JobEmbedding.canonical_job))
            .where(where_clause)
            .order_by(JobEmbedding.updated_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        records = (await db.execute(stmt)).scalars().all()

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "items": records,
        }


job_embedding_service = JobEmbeddingService()
