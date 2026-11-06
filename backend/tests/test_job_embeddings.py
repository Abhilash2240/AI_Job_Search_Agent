"""
Test Suite for Phase 6: Job Embeddings & Vector Storage.
Tests the fine-tuned SBERT model loader, 384-dimensional unit vector generation,
deterministic structured text construction, URL stripping, SHA-256 content hashing,
incremental generation & caching, retry-failed recovery, and FastAPI endpoints.
"""

import json
import uuid
from datetime import datetime, timezone
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from db.database import AsyncSessionLocal
from embeddings.model_loader import get_model
from embeddings.embedding_service import embed_text, embed_batch
from embeddings.job_embedder import (
    build_canonical_job_text,
    compute_content_hash,
    sanitize_text,
    extract_skill_names,
    job_embedding_service,
)
from models.canonical_job import CanonicalJob, VacancyStatus
from models.job_embedding import JobEmbedding, EmbeddingStatus
from sqlalchemy import select


# ============================================================================
# 1. MODEL LOADING & VECTOR SPECIFICATION TESTS
# ============================================================================

def test_sbert_model_loading_and_dimensions():
    """Verify that the fine-tuned SBERT model loads and produces 384-dim vectors."""
    model = get_model()
    assert model is not None
    dim = model.get_sentence_embedding_dimension()
    assert dim == 384, f"Expected 384 dimensions from fine-tuned SBERT, got {dim}"


def test_vector_normalization_l2():
    """Verify that embeddings are L2 normalized (unit vectors) for cosine similarity."""
    sample_text = "Software Engineer with Python, FastAPI, Docker, and PostgreSQL experience."
    vec = embed_text(sample_text)
    assert isinstance(vec, np.ndarray)
    assert vec.shape == (384,)
    assert vec.dtype == np.float32

    norm = float(np.linalg.norm(vec))
    assert np.isclose(norm, 1.0, atol=1e-3), f"Expected unit norm (~1.0), got {norm}"


# ============================================================================
# 2. DETERMINISTIC TEXT BUILDER & SANITIZATION TESTS
# ============================================================================

def test_sanitize_text_removes_urls_and_emails():
    """Ensure HTTP URLs and raw emails are removed from text."""
    raw = "Apply at https://careers.company.com/job/123?utm_source=board or email jobs@company.com now."
    cleaned = sanitize_text(raw)
    assert "https://" not in cleaned
    assert "careers.company.com" not in cleaned
    assert "jobs@company.com" not in cleaned
    assert "Apply at" in cleaned
    assert "now." in cleaned


def test_extract_skill_names_segregation():
    """Verify JSON skills and string lists are properly parsed and alphabetically sorted."""
    json_skills = json.dumps([
        {"canonical_name": "Python", "category": "Languages"},
        {"skill_name": "Docker", "canonical_name": "Docker"},
        {"canonical_name": "AWS", "category": "Cloud"},
    ])
    skills = extract_skill_names(json_skills)
    assert skills == ["AWS", "Docker", "Python"]  # Case-insensitive alphabetical sort


def test_build_canonical_job_text_determinism():
    """Verify deterministic text representation excludes URLs and orders sections predictably."""
    job = CanonicalJob(
        canonical_job_id="CANON-TEST-DET-1",
        company_name="FintechCore",
        title="backend engineer",
        canonical_job_title="Backend Engineer",
        seniority_level="MID_LEVEL",
        employment_type="FULL_TIME",
        required_skills=json.dumps([{"canonical_name": "Python"}, {"canonical_name": "PostgreSQL"}]),
        preferred_skills=json.dumps([{"canonical_name": "Kubernetes"}, {"canonical_name": "Kafka"}]),
        degree_requirements=json.dumps(["B.Tech", "M.Tech"]),
        field_of_study=json.dumps(["Computer Science"]),
        responsibilities=json.dumps(["Design robust APIs.", "Optimize SQL queries."]),
        qualifications=json.dumps(["3+ years backend experience."]),
        description="Join FintechCore to build payment systems. Visit https://fintech.example.com for more info.",
    )

    text1 = build_canonical_job_text(job)
    text2 = build_canonical_job_text(job)
    assert text1 == text2, "Text builder must be 100% deterministic"

    # Verify sections present
    assert "Title: Backend Engineer" in text1
    assert "Company: FintechCore" in text1
    assert "Seniority: MID_LEVEL" in text1
    assert "Employment Type: FULL_TIME" in text1
    assert "Required Skills: PostgreSQL, Python" in text1
    assert "Preferred Skills: Kafka, Kubernetes" in text1
    assert "Education: B.Tech, M.Tech in Computer Science" in text1
    assert "Responsibilities:\n- Design robust APIs.\n- Optimize SQL queries." in text1
    assert "Qualifications:\n- 3+ years backend experience." in text1
    assert "https://" not in text1

    # Verify SHA-256 hash determinism
    hash1 = compute_content_hash(text1)
    hash2 = compute_content_hash(text2)
    assert hash1 == hash2
    assert len(hash1) == 64


def test_content_hash_sensitivity():
    """Verify changing any content field alters the SHA-256 content hash."""
    job1 = CanonicalJob(
        canonical_job_id="CANON-HASH-1",
        company_name="Acme Corp",
        title="Data Engineer",
        canonical_job_title="Data Engineer",
        required_skills=json.dumps([{"canonical_name": "Python"}]),
        description="Data pipelines.",
    )
    job2 = CanonicalJob(
        canonical_job_id="CANON-HASH-2",
        company_name="Acme Corp",
        title="Data Engineer",
        canonical_job_title="Data Engineer",
        required_skills=json.dumps([{"canonical_name": "Python"}, {"canonical_name": "Spark"}]),
        description="Data pipelines.",
    )

    hash1 = compute_content_hash(build_canonical_job_text(job1))
    hash2 = compute_content_hash(build_canonical_job_text(job2))
    assert hash1 != hash2, "Content hash must change when required skills change"


def test_empty_or_minimal_job_handling():
    """Verify robust handling of jobs with minimal/missing fields."""
    job = CanonicalJob(
        canonical_job_id="CANON-EMPTY-1",
        company_name=None,
        title=None,
        canonical_job_title=None,
        required_skills=None,
        preferred_skills=None,
        description=None,
    )
    text = build_canonical_job_text(job)
    assert isinstance(text, str)
    # Should not raise exception
    c_hash = compute_content_hash(text)
    assert len(c_hash) == 64


# ============================================================================
# 3. VECTOR STORAGE & MODEL ROUNDTRIP TESTS
# ============================================================================

def test_job_embedding_blob_and_json_roundtrip():
    """Verify JobEmbedding stores float32 bytes BLOB and JSON, with perfect numerical fidelity."""
    original_vec = np.random.randn(384).astype(np.float32)
    # Normalize
    original_vec = original_vec / np.linalg.norm(original_vec)

    emb = JobEmbedding(
        canonical_job_id=9999,
        model_name="fine-tuned-sbert",
        dimensions=384,
        content_hash="mock-hash-12345",
        status=EmbeddingStatus.COMPLETED.value,
    )
    emb.set_vector(original_vec)

    assert len(emb.embedding_blob) == 384 * 4  # 1536 bytes
    assert emb.embedding_json.startswith("[") and emb.embedding_json.endswith("]")

    # Retrieve via BLOB
    recovered_vec = emb.get_vector()
    assert np.allclose(original_vec, recovered_vec, atol=1e-6)

    # Test retrieval via JSON when BLOB is cleared
    emb.embedding_blob = None
    recovered_json_vec = emb.get_vector()
    assert np.allclose(original_vec, recovered_json_vec, atol=1e-5)


# ============================================================================
# 4. ASYNC SERVICE LIFECYCLE, INCREMENTAL SKIPPING & RETRY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_job_embedding_service_workflow():
    """Test generating single, batch incremental skipping, and retry-failed workflow."""
    async with AsyncSessionLocal() as db:
        unique_id = f"CANON-TEST-EMB-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)
        test_job = CanonicalJob(
            canonical_job_id=unique_id,
            company_name="EmbeddingTestCorp",
            title="Senior AI Engineer",
            canonical_job_title="AI Engineer",
            normalized_title="ai engineer",
            seniority_level="SENIOR",
            employment_type="FULL_TIME",
            required_skills=json.dumps([{"canonical_name": "PyTorch"}, {"canonical_name": "Transformers"}]),
            preferred_skills=json.dumps([{"canonical_name": "FastAPI"}]),
            description="Build scalable NLP pipelines using fine-tuned transformer models.",
            first_seen_at=now,
            last_seen_at=now,
            last_status_change_at=now,
            vacancy_status=VacancyStatus.ACTIVE.value,
        )
        db.add(test_job)
        await db.commit()
        await db.refresh(test_job)

        try:
            # 1. Generate single embedding
            emb1 = await job_embedding_service.generate_single_embedding(
                db=db, job_identifier=test_job.id, force=False
            )
            assert emb1.status == EmbeddingStatus.COMPLETED.value
            assert emb1.dimensions == 384
            vec1 = emb1.get_vector()
            assert np.isclose(np.linalg.norm(vec1), 1.0, atol=1e-3)

            # 2. Re-run without force -> Should skip re-computation
            res_skip = await job_embedding_service.generate_batch_embeddings(
                db=db, canonical_job_ids=[test_job.id], force=False
            )
            assert res_skip["skipped_count"] == 1
            assert res_skip["generated_count"] == 0

            # 3. Simulate failure state
            emb1.status = EmbeddingStatus.FAILED.value
            emb1.last_error = "Mock network or memory error"
            await db.commit()

            # 4. Retry failed
            retry_res = await job_embedding_service.retry_failed_embeddings(db=db)
            assert retry_res["retried_count"] >= 1
            assert retry_res["succeeded_count"] >= 1

            # Refresh and verify status is back to COMPLETED
            await db.refresh(emb1)
            assert emb1.status == EmbeddingStatus.COMPLETED.value
            assert emb1.last_error is None

        finally:
            # Cleanup test records
            stmt = select(JobEmbedding).where(JobEmbedding.canonical_job_id == test_job.id)
            existing_emb = (await db.execute(stmt)).scalar_one_or_none()
            if existing_emb:
                await db.delete(existing_emb)
            await db.delete(test_job)
            await db.commit()


# ============================================================================
# 5. FASTAPI API ROUTE INTEGRATION TESTS
# ============================================================================

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_api_embeddings_summary(client):
    """GET /api/jobs/embeddings/summary returns valid schema and dimensions."""
    resp = client.get("/api/jobs/embeddings/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_canonical_jobs" in data
    assert "total_embeddings" in data
    assert "completed_embeddings" in data
    assert data["dimensions"] == 384
    assert data["model_name"] == "fine-tuned-sbert"


def test_api_embeddings_status_list(client):
    """GET /api/jobs/embeddings/status returns paginated embeddings."""
    resp = client.get("/api/jobs/embeddings/status?page=1&page_size=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "items" in data
    assert "page" in data
    if data["items"]:
        item = data["items"][0]
        assert "canonical_job_id" in item
        assert "content_hash" in item
        assert item["dimensions"] == 384
        assert item["status"] in ["COMPLETED", "PENDING", "STALE", "FAILED"]


def test_api_embeddings_retry_failed(client):
    """POST /api/jobs/embeddings/retry-failed executes cleanly."""
    resp = client.post("/api/jobs/embeddings/retry-failed", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert "retried_count" in data

