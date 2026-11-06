"""
Test Suite for Phase 5: Cross-Provider Job Deduplication.
Covers exact matching, cross-provider matching, URL normalization,
location & requisition safeguards, fuzzy matching thresholds,
manual review workflow, and source provenance preservation.
"""

import json
import pytest
from datetime import datetime, timezone
from sqlalchemy import select

from models.canonical_job import (
    CanonicalJob,
    CanonicalJobSource,
    DuplicateReviewGroup,
    DuplicateType,
    DuplicateGroupStatus,
)
from models.job import Job
from deduplication.url_normalizer import CanonicalUrlNormalizer
from deduplication.similarity import JobSimilarityCalculator
from deduplication.dedup_engine import JobDeduplicationEngine
from deduplication.merger import CanonicalJobMerger
from deduplication.dedup_service import JobDeduplicationService


# ============================================================================
# 1. CANONICAL URL NORMALIZATION TESTS
# ============================================================================

def test_url_normalization_tracking_stripping():
    """Verify removal of tracking parameters, fragments, trailing slashes, and ports."""
    url = "https://www.example.com:443/jobs/123/?utm_source=linkedin&utm_medium=cpc&ref=jobboard&mode=json#apply"
    norm = CanonicalUrlNormalizer.normalize_url(url)
    assert "utm_source" not in norm
    assert "utm_medium" not in norm
    assert "ref" not in norm
    assert "mode" not in norm
    assert "#apply" not in norm
    assert ":443" not in norm
    assert "www." not in norm
    assert norm == "https://example.com/jobs/123"


def test_ats_permalink_canonicalization():
    """Verify standard canonical permalinks for Greenhouse and Lever."""
    # Greenhouse embed URL -> canonical boards URL
    gh_embed = "https://boards.greenhouse.io/embed/job_app?for=stripe&token=567890&utm_campaign=devs"
    gh_norm = CanonicalUrlNormalizer.get_canonical_permalink(gh_embed)
    assert gh_norm == "https://boards.greenhouse.io/stripe/jobs/567890"

    # Lever apply URL -> canonical job permalink
    lever_apply = "https://jobs.lever.co/cred/abc-def-123/apply?lever-origin=applied"
    lever_norm = CanonicalUrlNormalizer.get_canonical_permalink(lever_apply)
    assert lever_norm == "https://jobs.lever.co/cred/abc-def-123"


# ============================================================================
# 2. EXACT MATCHING TESTS (STAGE 1)
# ============================================================================

def test_exact_duplicate_matching():
    """Verify Stage 1 exact match via provider & external ID and canonical URLs."""
    engine = JobDeduplicationEngine()

    # 1. Same provider and external_job_id
    j1 = {
        "id": 1,
        "company_id": 10,
        "provider": "greenhouse",
        "external_job_id": "99901",
        "title": "Software Engineer",
        "application_url": "https://boards.greenhouse.io/groww/jobs/99901",
    }
    j2 = {
        "id": 2,
        "company_id": 10,
        "provider": "greenhouse",
        "external_job_id": "99901",
        "title": "Software Engineer (Backend)",
        "application_url": "https://boards.greenhouse.io/groww/jobs/99901?utm_source=portal",
    }
    eval1 = engine.evaluate_pair(j1, j2)
    assert eval1.duplicate_type == DuplicateType.EXACT_DUPLICATE.value
    assert eval1.confidence_score == 1.0
    assert eval1.can_auto_merge is True
    assert "matching_provider_and_external_job_id" in eval1.reasons

    # 2. Same canonical application URL across different providers
    j3 = {
        "id": 3,
        "company_id": 20,
        "provider": "portal",
        "title": "Backend Developer",
        "application_url": "https://jobs.lever.co/cred/xyz-888?source=naukri",
    }
    j4 = {
        "id": 4,
        "company_id": 20,
        "provider": "lever",
        "title": "Backend Developer",
        "application_url": "https://jobs.lever.co/cred/xyz-888/apply",
    }
    eval2 = engine.evaluate_pair(j3, j4)
    assert eval2.duplicate_type == DuplicateType.EXACT_DUPLICATE.value
    assert eval2.confidence_score == 1.0
    assert eval2.can_auto_merge is True


# ============================================================================
# 3. SAFEGUARDS & FALSE-POSITIVE PREVENTION TESTS
# ============================================================================

def test_different_location_protection():
    """CRITICAL SAFEGUARD: Vacancies in different cities must NOT be merged."""
    engine = JobDeduplicationEngine()

    job_bengaluru = {
        "id": 10,
        "company_id": 15,
        "title": "Senior Python Engineer",
        "canonical_job_title": "Python Developer",
        "location": "Bengaluru, Karnataka",
        "city": "Bengaluru",
        "is_remote": False,
        "description": "We are seeking a senior python engineer to scale our distributed database backend in Bengaluru.",
    }
    job_hyderabad = {
        "id": 11,
        "company_id": 15,
        "title": "Senior Python Engineer",
        "canonical_job_title": "Python Developer",
        "location": "Hyderabad, Telangana",
        "city": "Hyderabad",
        "is_remote": False,
        "description": "We are seeking a senior python engineer to scale our distributed database backend in Hyderabad.",
    }

    eval_loc = engine.evaluate_pair(job_bengaluru, job_hyderabad)
    assert eval_loc.duplicate_type == DuplicateType.DISTINCT_JOB.value
    assert eval_loc.can_auto_merge is False
    assert any("location_distinction_conflict" in r for r in eval_loc.reasons)


def test_different_requisition_id_protection():
    """CRITICAL SAFEGUARD: Vacancies with conflicting requisition codes must NOT be merged."""
    engine = JobDeduplicationEngine()

    job_req1 = {
        "id": 20,
        "company_id": 30,
        "title": "Security Analyst (REQ-1002)",
        "external_job_id": "REQ-1002",
        "location": "Remote",
        "is_remote": True,
        "description": "Threat analysis, SIEM monitoring and incident response team alpha.",
    }
    job_req2 = {
        "id": 21,
        "company_id": 30,
        "title": "Security Analyst (REQ-9904)",
        "external_job_id": "REQ-9904",
        "location": "Remote",
        "is_remote": True,
        "description": "Threat analysis, SIEM monitoring and incident response team beta.",
    }

    eval_req = engine.evaluate_pair(job_req1, job_req2)
    assert eval_req.duplicate_type == DuplicateType.DISTINCT_JOB.value
    assert eval_req.can_auto_merge is False
    assert any("requisition_id_conflict" in r for r in eval_req.reasons)


def test_incompatible_employment_type_protection():
    """CRITICAL SAFEGUARD: Full-time vs Internship must NOT be merged."""
    engine = JobDeduplicationEngine()

    job_ft = {
        "id": 30,
        "company_id": 40,
        "title": "Frontend Engineer",
        "employment_type": "FULL_TIME",
        "description": "Develop React applications and component library.",
    }
    job_intern = {
        "id": 31,
        "company_id": 40,
        "title": "Frontend Engineer",
        "employment_type": "INTERNSHIP",
        "description": "Develop React applications and component library.",
    }

    eval_emp = engine.evaluate_pair(job_ft, job_intern)
    assert eval_emp.duplicate_type == DuplicateType.DISTINCT_JOB.value
    assert eval_emp.can_auto_merge is False
    assert any("employment_type_conflict" in r for r in eval_emp.reasons)


def test_title_only_matching_safeguard():
    """CRITICAL SAFEGUARD: High title similarity with low description overlap requires manual review."""
    engine = JobDeduplicationEngine()

    job_dev1 = {
        "id": 40,
        "company_id": 50,
        "title": "Software Engineer",
        "location": "Bengaluru",
        "city": "Bengaluru",
        "description": "Build high frequency quantitative trading algorithms in C++ with low latency kernels.",
    }
    job_dev2 = {
        "id": 41,
        "company_id": 50,
        "title": "Software Engineer",
        "location": "Bengaluru",
        "city": "Bengaluru",
        "description": "Create consumer facing web applications in Next.js, CSS animations, and GraphQL APIs.",
    }

    eval_desc = engine.evaluate_pair(job_dev1, job_dev2)
    assert eval_desc.duplicate_type == DuplicateType.NEEDS_MANUAL_REVIEW.value
    assert eval_desc.can_auto_merge is False
    assert "manual_review_required" in eval_desc.reasons


# ============================================================================
# 4. NORMALIZED & FUZZY MATCHING TESTS (STAGE 2 & 3)
# ============================================================================

def test_high_confidence_fuzzy_duplicate():
    """Verify high title and description overlap results in HIGH_CONFIDENCE_DUPLICATE."""
    engine = JobDeduplicationEngine(auto_merge_threshold=0.85)

    job_a = {
        "id": 50,
        "company_id": 60,
        "title": "Lead Python Backend Engineer",
        "canonical_job_title": "Python Backend Engineer",
        "location": "Bengaluru, India",
        "city": "Bengaluru",
        "description": "We are seeking a Lead Python Backend Engineer with 5+ years of experience building high-throughput FastAPI and PostgreSQL microservices in Docker and AWS.",
    }
    job_b = {
        "id": 51,
        "company_id": 60,
        "title": "Python Backend Engineer (Lead)",
        "canonical_job_title": "Python Backend Engineer",
        "location": "Bengaluru, India",
        "city": "Bengaluru",
        "description": "Seeking a Lead Python Backend Engineer with 5+ years of experience building high-throughput FastAPI and PostgreSQL microservices in Docker and AWS.",
    }

    eval_fuzzy = engine.evaluate_pair(job_a, job_b)
    assert eval_fuzzy.duplicate_type == DuplicateType.HIGH_CONFIDENCE_DUPLICATE.value
    assert eval_fuzzy.confidence_score >= 0.85
    assert eval_fuzzy.can_auto_merge is True


# ============================================================================
# 5. CANONICAL MERGING & PROVENANCE PRESERVATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_canonical_merging_and_provenance_preservation():
    """Verify that merging jobs retains every original provider, URL, and metadata in CanonicalJobSource."""
    from db.database import AsyncSessionLocal
    merger = CanonicalJobMerger()

    async with AsyncSessionLocal() as db:
        # Create 2 mock Job records
        now = datetime.now(timezone.utc)
        job1 = Job(
            company_id=999,
            company="TestCorp",
            canonical_job_title="DevOps Engineer",
            title="DevOps Engineer (Greenhouse)",
            provider="greenhouse",
            external_job_id="GH-777",
            source_url="https://boards.greenhouse.io/testcorp/jobs/777",
            application_url="https://boards.greenhouse.io/testcorp/jobs/777",
            description="Manage Kubernetes clusters and Terraform infrastructure.",
            responsibilities=json.dumps(["Maintain CI/CD pipelines"]),
            required_skills=json.dumps([{"name": "Docker", "category": "DevOps", "evidence_snippet": "Docker"}]),
            extracted_at=now,
        )
        job2 = Job(
            company_id=999,
            company="TestCorp",
            canonical_job_title="DevOps Engineer",
            title="DevOps Engineer (Lever)",
            provider="lever",
            external_job_id="LV-888",
            source_url="https://jobs.lever.co/testcorp/888",
            application_url="https://jobs.lever.co/testcorp/888",
            description="Manage Kubernetes clusters and Terraform infrastructure. Ensure 99.99% uptime.",
            responsibilities=json.dumps(["Maintain CI/CD pipelines", "Monitor Prometheus"]),
            required_skills=json.dumps([{"name": "Kubernetes", "category": "DevOps", "evidence_snippet": "Kubernetes"}]),
            extracted_at=now,
        )
        db.add_all([job1, job2])
        await db.commit()
        await db.refresh(job1)
        await db.refresh(job2)

        # Merge job2 into job1's canonical vacancy
        canonical = await merger.merge_or_create_canonical(
            db=db,
            primary_job=job1,
            secondary_jobs=[job2],
        )

        assert canonical is not None
        assert canonical.company_name == "TestCorp"
        assert canonical.source_count == 2
        # Check longer description selected
        assert "Ensure 99.99% uptime" in canonical.description

        # Check skills merged without loss
        merged_skills = json.loads(canonical.required_skills)
        skill_names = [s.get("name") or s.get("canonical_name") for s in merged_skills]
        assert "Docker" in skill_names
        assert "Kubernetes" in skill_names

        # Check sources provenance
        stmt_sources = select(CanonicalJobSource).where(CanonicalJobSource.canonical_job_id == canonical.id)
        sources = (await db.execute(stmt_sources)).scalars().all()
        assert len(sources) == 2
        providers = {s.provider for s in sources}
        assert "greenhouse" in providers
        assert "lever" in providers

        # Cleanup
        await db.delete(canonical)
        await db.delete(job1)
        await db.delete(job2)
        await db.commit()


# ============================================================================
# 6. MANUAL REVIEW WORKFLOW TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_duplicate_review_group_resolution():
    """Verify manual resolution of borderline matches via MERGE and REJECT_DISTINCT."""
    from db.database import AsyncSessionLocal
    service = JobDeduplicationService()

    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        j1 = Job(
            company_id=998,
            company="ReviewCorp",
            canonical_job_title="Data Engineer",
            title="Data Engineer I",
            description="Build Spark pipelines.",
            extracted_at=now,
        )
        j2 = Job(
            company_id=998,
            company="ReviewCorp",
            canonical_job_title="Data Engineer",
            title="Data Engineer II",
            description="Build Spark pipelines with Flink streaming.",
            extracted_at=now,
        )
        db.add_all([j1, j2])
        await db.commit()
        await db.refresh(j1)
        await db.refresh(j2)

        # Create review group
        eval_obj = JobDeduplicationEngine().evaluate_pair(j1, j2)
        group = await service.merger.record_pending_review_group(db, j1, j2, eval_obj)
        assert group.status == DuplicateGroupStatus.PENDING_REVIEW.value

        # Resolve via MERGE
        resolved_group = await service.resolve_duplicate_group(
            db=db,
            group_id=group.id,
            action="MERGE",
            notes="Confirmed same team vacancy",
            resolved_by="admin_test",
        )
        assert resolved_group.status == DuplicateGroupStatus.MERGED.value
        assert resolved_group.resolution_action == "MERGE"
        assert resolved_group.canonical_job_id is not None

        # Cleanup
        stmt_c = select(CanonicalJob).where(CanonicalJob.id == resolved_group.canonical_job_id)
        canon = (await db.execute(stmt_c)).scalar_one_or_none()
        if canon:
            await db.delete(canon)
        await db.delete(resolved_group)
        await db.delete(j1)
        await db.delete(j2)
        await db.commit()


# ============================================================================
# 7. CANDIDATE ROLE RELEVANCE SEPARATION TESTS
# ============================================================================

def test_role_relevance_classification():
    """Verify lightweight keyword role classification without discarding non-matches."""
    from intelligence.role_relevance import RoleRelevanceClassifier

    confirmed = ["Python Backend Engineer", "Software Engineer"]
    cand_skills = ["Python", "FastAPI", "Docker", "PostgreSQL"]

    # Relevant job
    job_skills_1 = [{"canonical_name": "Python"}, {"canonical_name": "FastAPI"}, {"canonical_name": "AWS"}]
    res1 = RoleRelevanceClassifier.evaluate_relevance(
        canonical_title="Python Backend Engineer",
        job_skills=job_skills_1,
        confirmed_roles=confirmed,
        candidate_skills=cand_skills,
    )
    assert res1["is_relevant"] is True
    assert res1["relevance_score"] >= 0.70
    assert "Python Backend Engineer" in res1["matching_roles"]

    # Irrelevant job (e.g. Sales / Marketing)
    job_skills_2 = [{"canonical_name": "Lead Generation"}, {"canonical_name": "Cold Calling"}]
    res2 = RoleRelevanceClassifier.evaluate_relevance(
        canonical_title="Sales Executive",
        job_skills=job_skills_2,
        confirmed_roles=confirmed,
        candidate_skills=cand_skills,
    )
    assert res2["is_relevant"] is False
    assert res2["relevance_score"] == 0.0


# ============================================================================
# 8. FASTAPI PHASE 5 ENDPOINTS CONTRACT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_api_phase5_endpoints_contract():
    """Test deduplication and verification API endpoints via httpx AsyncClient."""
    from app.main import app
    import httpx

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. POST /api/jobs/deduplicate
        resp_dedup = await client.post("/api/jobs/deduplicate", json={"auto_merge": True, "similarity_threshold": 0.85})
        assert resp_dedup.status_code == 200
        dedup_data = resp_dedup.json()
        assert dedup_data["status"] == "COMPLETED"
        assert "total_jobs_evaluated" in dedup_data["summary"]

        # 2. GET /api/jobs/duplicates
        resp_dups = await client.get("/api/jobs/duplicates")
        assert resp_dups.status_code == 200
        dups_data = resp_dups.json()
        assert "total" in dups_data
        assert "items" in dups_data

        # 3. GET /api/jobs/verification/summary
        resp_verif_sum = await client.get("/api/jobs/verification/summary")
        assert resp_verif_sum.status_code == 200
        verif_data = resp_verif_sum.json()
        assert "total_canonical_jobs" in verif_data
        assert "by_status" in verif_data
        assert "active_ratio" in verif_data

        # 4. GET /api/jobs/verified
        resp_verified = await client.get("/api/jobs/verified")
        assert resp_verified.status_code == 200
        verified_data = resp_verified.json()
        assert "total" in verified_data
        assert "items" in verified_data

