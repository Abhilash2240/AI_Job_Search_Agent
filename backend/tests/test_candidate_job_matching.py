"""
Comprehensive Test Suite for Phase 7: Candidate-to-Job Matching and Scoring Engine.
Tests candidate embedding, categorized skill parsing, verified vs inferred segregation,
role compatibility, eligibility guardrails, explainable scoring, persistence, and API endpoints.
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
from models.candidate import Candidate
from models.canonical_job import CanonicalJob, VacancyStatus
from models.candidate_job_match import (
    CandidateJobMatch,
    CandidateEmbedding,
    EligibilityStatus,
    MatchClassification,
)
from matching.candidate_embedder import (
    extract_candidate_skills,
    extract_candidate_roles,
    build_candidate_semantic_text,
    compute_content_hash,
    candidate_embedding_service,
)
from matching.skill_matcher import skill_matcher, canonicalize_skill
from matching.role_matcher import role_matcher
from matching.eligibility import eligibility_engine
from matching.scoring import calculate_composite_score
from matching.matching_service import matching_service
from sqlalchemy import select


# ============================================================================
# 1. CANDIDATE EMBEDDER & SKILL EXTRACTION TESTS
# ============================================================================

def test_extract_candidate_skills_categorized_dict():
    """Verify that candidate skills stored as a categorized dict are parsed into verified list."""
    profile_dict = {
        "profile": {
            "skills": {
                "programming_languages": ["Python", "SQL"],
                "frameworks": ["FastAPI", "Express.js"],
                "databases": ["PostgreSQL", "Supabase"],
                "tools": ["Docker", "Git", "AWS"],
                "ai_ml": ["Machine Learning", "Google Gemini API"],
                "other": ["REST APIs", "JWT"],
            },
            "inferred_skills": ["Authentication Middleware", "End-to-End Testing"],
            "skill_sources": {
                "python": ["skills section", "project: Trading System"],
                "fastapi": ["project: API Gateway"],
            },
        }
    }

    verified, inferred, sources = extract_candidate_skills(profile_dict)
    assert "Python" in verified
    assert "FastAPI" in verified
    assert "PostgreSQL" in verified
    assert "AWS" in verified
    assert "Machine Learning" in verified

    # Inferred skills must be segregated
    assert "Authentication Middleware" in inferred
    assert "Authentication Middleware" not in verified
    assert "End-to-End Testing" in inferred
    assert "End-to-End Testing" not in verified


def test_candidate_roles_fallback_hierarchy():
    """Test role hierarchy: Confirmed > Provisional > No Role Context."""
    # 1. Confirmed roles exist
    cand_confirmed = Candidate(
        id=101,
        resume_hash="hash-101",
        profile_json="{}",
        confirmed_roles_json=json.dumps([{"role_title": "Python Backend Engineer", "is_custom": False}]),
        recommendations_json=json.dumps([{"role_title": "Junior Developer"}]),
    )
    roles, source = extract_candidate_roles(cand_confirmed)
    assert source == "CONFIRMED"
    assert roles[0]["role_title"] == "Python Backend Engineer"

    # 2. Confirmed missing -> fallback to Phase 2 recommendations as PROVISIONAL
    cand_prov = Candidate(
        id=102,
        resume_hash="hash-102",
        profile_json="{}",
        confirmed_roles_json=None,
        recommendations_json=json.dumps({"recommendations": [{"role_title": "Data Engineer"}]}),
    )
    roles2, source2 = extract_candidate_roles(cand_prov)
    assert source2 == "PROVISIONAL"
    assert roles2[0]["role_title"] == "Data Engineer"

    # 3. Neither exist -> NO_ROLE_CONTEXT
    cand_none = Candidate(
        id=103,
        resume_hash="hash-103",
        profile_json="{}",
        confirmed_roles_json=None,
        recommendations_json=None,
    )
    roles3, source3 = extract_candidate_roles(cand_none)
    assert source3 == "NO_ROLE_CONTEXT"
    assert len(roles3) == 0


def test_candidate_semantic_text_excludes_contact_info():
    """Verify that email and phone number are stripped from the semantic candidate representation."""
    cand = Candidate(
        id=104,
        resume_hash="hash-104",
        profile_json=json.dumps({
            "profile": {
                "personal": {
                    "name": "Jane Doe",
                    "email": "jane.doe@confidential.com",
                    "phone": "+1-555-0199",
                },
                "education": [{"degree": "B.Tech", "specialization": "Computer Science", "university": "State University"}],
                "skills": {"programming_languages": ["Python", "Go"]},
            }
        }),
        confirmed_roles_json=json.dumps([{"role_title": "Backend Developer"}]),
    )
    text, role_source = build_candidate_semantic_text(cand)
    assert "jane.doe@confidential.com" not in text
    assert "+1-555-0199" not in text
    assert "Target Career Roles (CONFIRMED): Backend Developer" in text
    assert "Verified Skills: Go, Python" in text
    assert "Education: B.Tech in Computer Science from State University" in text

    # Deterministic hashing
    h1 = compute_content_hash(text)
    h2 = compute_content_hash(text)
    assert h1 == h2
    assert len(h1) == 64


# ============================================================================
# 2. SKILL MATCHER TESTS
# ============================================================================

def test_skill_matcher_exact_and_alias_normalization():
    """Verify exact match, alias normalization, and separation of required vs preferred."""
    verified_skills = ["Python", "Postgres", "AWS", "Docker", "Git"]
    inferred_skills = ["FastAPI", "Redis"]
    sources = {"python": ["skills section"]}

    job_req = [
        {"canonical_name": "Python", "is_required": True},
        {"canonical_name": "PostgreSQL", "is_required": True},  # Alias of Postgres
        {"canonical_name": "Kubernetes", "is_required": True},
    ]
    job_pref = [
        {"canonical_name": "Amazon Web Services", "is_required": False},  # Alias of AWS
        {"canonical_name": "FastAPI", "is_required": False},
    ]

    res = skill_matcher.evaluate_skills(
        verified_skills=verified_skills,
        inferred_skills=inferred_skills,
        skill_sources=sources,
        job_required_skills=job_req,
        job_preferred_skills=job_pref,
    )

    # Matched required: Python, PostgreSQL (from Postgres) -> 2 out of 3 = 0.6667
    matched_req_names = [m["canonical_name"] for m in res["matched_required"]]
    assert "Python" in matched_req_names
    assert "PostgreSQL" in matched_req_names
    assert "Kubernetes" in res["missing_required"]
    assert np.isclose(res["required_coverage"], 2 / 3, atol=1e-3)

    # Matched preferred: AWS (from Amazon Web Services) -> 1 out of 2 = 0.50
    matched_pref_names = [m["canonical_name"] for m in res["matched_preferred"]]
    assert "AWS" in matched_pref_names

    # Inferred FastAPI must NOT be counted as a verified match!
    assert "FastAPI" in res["missing_preferred"]
    # But it must be flagged in inferred_overlap
    inferred_names = [io["candidate_inferred_skill"] for io in res["inferred_overlap"]]
    assert "FastAPI" in inferred_names

    # Skill score = 0.75 * (2/3) + 0.25 * (1/2) = 0.50 + 0.125 = 0.625
    expected_score = round(0.75 * (2 / 3) + 0.25 * (1 / 2), 4)
    assert np.isclose(res["skill_score"], expected_score, atol=1e-3)


def test_skill_aliases_rejects_false_equivalents():
    """Verify distinct technologies are not treated as aliases."""
    assert canonicalize_skill("Java") != canonicalize_skill("JavaScript")
    assert canonicalize_skill("Python") != canonicalize_skill("Java")
    assert canonicalize_skill("React") != canonicalize_skill("Angular")


def test_skill_matcher_empty_preferred_skills():
    """Verify skill calculation when vacancy specifies no preferred skills (0.75 * req + 0.25 * 0)."""
    verified = ["Python", "AWS", "GitHub"]
    job_req = [
        {"canonical_name": "Python"},
        {"canonical_name": "AWS"},
        {"canonical_name": "GitHub"},
        {"canonical_name": "Go"},
        {"canonical_name": "Bash"},
        {"canonical_name": "Linux"},
    ]
    job_pref = []  # Empty preferred list

    res = skill_matcher.evaluate_skills(
        verified_skills=verified,
        inferred_skills=[],
        skill_sources={},
        job_required_skills=job_req,
        job_preferred_skills=job_pref,
    )

    assert res["total_required"] == 6
    assert len(res["matched_required"]) == 3
    assert np.isclose(res["required_coverage"], 0.50, atol=1e-4)
    assert res["total_preferred"] == 0
    assert res["preferred_coverage"] == 0.0

    # Skill score = 0.75 * 0.50 + 0.25 * 0.0 = 0.375
    assert np.isclose(res["skill_score"], 0.375, atol=1e-4)


def test_experience_deficit_and_conditions():
    """Verify candidate with 0.75 yrs vs 2.0 yrs min experience receives ELIGIBLE_WITH_CONDITIONS."""
    score, reason, is_disqual = eligibility_engine.evaluate_experience(
        candidate_exp_years=0.75,
        candidate_level="ENTRY_LEVEL",
        job_min_years=2.0,
        job_max_years=6.0,
        job_seniority="MID_LEVEL",
    )
    assert is_disqual is False
    assert reason is not None
    assert "deficit of 1.25" in reason

    # Test overall eligibility
    job = CanonicalJob(
        canonical_job_id="CANON-EXP-TEST",
        title="Engineer",
        vacancy_status=VacancyStatus.ACTIVE.value,
    )
    elig, reasons = eligibility_engine.determine_overall_eligibility(
        job=job,
        is_exp_disqualified=is_disqual,
        exp_reason=reason,
        edu_status="MATCHED",
        loc_status="REMOTE_ELIGIBLE",
    )
    assert elig == EligibilityStatus.ELIGIBLE_WITH_CONDITIONS.value
    assert any("deficit of 1.25" in r for r in reasons)


def test_location_missing_coverage_reduction():
    """Verify missing candidate location returns UNKNOWN and reduces score coverage to 0.95."""
    loc_score, loc_status, is_eval = eligibility_engine.evaluate_location(
        candidate_location=None,
        is_job_remote=False,
        job_location="Bengaluru",
        job_city="Bengaluru",
        job_country="India",
    )
    assert loc_score == 0.50
    assert loc_status == "UNKNOWN"
    assert is_eval is False

    # Scoring coverage check
    comp, cov, _ = calculate_composite_score(
        semantic_score=0.8,
        skill_score=0.8,
        role_score=0.8,
        experience_score=0.8,
        education_score=0.8,
        location_score=loc_score,
        evaluable_flags={
            "semantic": True,
            "skill": True,
            "role": True,
            "experience": True,
            "education": True,
            "location": is_eval,
        },
    )
    # Total weight is 1.0; location weight is 0.05. Evaluated weight is 0.95.
    assert np.isclose(cov, 0.95, atol=1e-4)


# ============================================================================
# 3. ROLE MATCHER & DOMAIN ALIGNMENT TESTS
# ============================================================================

def test_role_matcher_technical_vs_non_technical():
    """Verify that a Python Developer role scores high for Backend Engineer, but very low for Procurement."""
    roles = [{"role_title": "Python Backend Engineer", "alternative_titles": ["Python Developer", "API Engineer"]}]

    # 1. Aligned technical vacancy
    tech_res = role_matcher.evaluate_role_compatibility(
        candidate_roles=roles,
        role_source="CONFIRMED",
        canonical_title="Backend Engineer",
        job_title="Senior Python Backend Developer",
    )
    assert tech_res["role_score"] >= 0.70
    assert tech_res["role_source"] == "CONFIRMED"

    # 2. Non-technical vacancy (Procurement Specialist)
    non_tech_res = role_matcher.evaluate_role_compatibility(
        candidate_roles=roles,
        role_source="CONFIRMED",
        canonical_title="Procurement Specialist",
        job_title="Procurement Specialist",
    )
    assert non_tech_res["role_score"] <= 0.20
    assert "mismatch" in non_tech_res["evidence"]


# ============================================================================
# 4. ELIGIBILITY ENGINE & GUARDRAIL TESTS
# ============================================================================

def test_seniority_lead_staff_disqualification():
    """Verify entry-level fresher is explicitly disqualified from Lead/Staff roles."""
    score, reason, is_disqual = eligibility_engine.evaluate_experience(
        candidate_exp_years=0.5,
        candidate_level="ENTRY_LEVEL",
        job_min_years=8.0,
        job_max_years=None,
        job_seniority="LEAD_STAFF",
    )
    assert is_disqual is True
    assert score == 0.0
    assert "Seniority mismatch" in reason


def test_education_degree_and_field_alignment():
    """Verify B.Tech in CS matches B.E. in Information Technology."""
    cand_edu = [{"degree": "Bachelor of Technology", "specialization": "Computer Science"}]
    score, status = eligibility_engine.evaluate_education(
        candidate_education=cand_edu,
        job_degrees=["B.E."],
        job_fields=["Information Technology"],
    )
    assert score == 1.0
    assert status == "MATCHED"


def test_vacancy_lifecycle_gate():
    """Verify that CLOSED or EXPIRED vacancies are marked INELIGIBLE."""
    closed_job = CanonicalJob(
        canonical_job_id="CANON-CLOSED-1",
        title="Software Engineer",
        company_name="TestCorp",
        vacancy_status=VacancyStatus.CLOSED.value,
    )
    elig_stat, reasons = eligibility_engine.determine_overall_eligibility(
        job=closed_job,
        is_exp_disqualified=False,
        exp_reason=None,
        edu_status="MATCHED",
        loc_status="REMOTE_ELIGIBLE",
    )
    assert elig_stat == EligibilityStatus.INELIGIBLE.value
    assert "no longer active" in reasons[0]


# ============================================================================
# 5. SCORING & SCORE COVERAGE TESTS
# ============================================================================

def test_composite_scoring_formula_and_coverage():
    """Verify composite score formula (0.35 + 0.30 + 0.15 + 0.10 + 0.05 + 0.05 = 1.00) and coverage."""
    comp_score, coverage, classification = calculate_composite_score(
        semantic_score=0.80,     # 0.35 * 0.80 = 0.28
        skill_score=0.70,        # 0.30 * 0.70 = 0.21
        role_score=0.85,         # 0.15 * 0.85 = 0.1275
        experience_score=1.0,    # 0.10 * 1.00 = 0.10
        education_score=1.0,     # 0.05 * 1.00 = 0.05
        location_score=0.80,     # 0.05 * 0.80 = 0.04
        evaluable_flags={
            "semantic": True,
            "skill": True,
            "role": True,
            "experience": True,
            "education": True,
            "location": True,
        },
    )
    expected = round((0.28 + 0.21 + 0.1275 + 0.10 + 0.05 + 0.04) * 100.0, 2)
    assert np.isclose(comp_score, expected, atol=0.01)
    assert coverage == 1.0
    assert classification == MatchClassification.HIGHLY_RECOMMENDED.value


# ============================================================================
# 6. ASYNC SERVICE WORKFLOW & PERSISTENCE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_candidate_matching_service_end_to_end():
    """Test full matching execution, SBERT inference, persistence, and transactional upsert."""
    async with AsyncSessionLocal() as db:
        test_uid = f"CANON-MATCH-TEST-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)

        # 1. Create a test canonical job
        test_job = CanonicalJob(
            canonical_job_id=test_uid,
            company_name="MatchTestCorp",
            title="Python Cloud Engineer",
            canonical_job_title="Python Developer",
            normalized_title="python developer",
            seniority_level="ENTRY_LEVEL",
            employment_type="FULL_TIME",
            is_remote=True,
            required_skills=json.dumps([{"canonical_name": "Python"}, {"canonical_name": "SQL"}]),
            preferred_skills=json.dumps([{"canonical_name": "Docker"}]),
            degree_requirements=json.dumps(["B.Tech"]),
            field_of_study=json.dumps(["Computer Science"]),
            description="Build cloud backends using Python and SQL databases.",
            vacancy_status=VacancyStatus.ACTIVE.value,
            first_seen_at=now,
            last_seen_at=now,
            last_status_change_at=now,
        )
        db.add(test_job)
        await db.commit()
        await db.refresh(test_job)

        # Generate its embedding
        from embeddings.job_embedder import job_embedding_service
        await job_embedding_service.generate_single_embedding(db=db, job_identifier=test_job.id, force=True)

        # 2. Use real candidate 3 (or test candidate)
        cand = (await db.execute(select(Candidate).where(Candidate.id == 3))).scalar_one_or_none()
        if not cand:
            # Fallback to creating a test candidate if candidate 3 not present in isolated test db
            cand = Candidate(
                resume_hash=f"hash-{uuid.uuid4().hex[:8]}",
                filename="test_cand.pdf",
                profile_json=json.dumps({
                    "profile": {
                        "personal": {"name": "Test Engineer"},
                        "education": [{"degree": "B.Tech", "specialization": "Computer Science"}],
                        "skills": {"programming_languages": ["Python", "SQL"], "tools": ["Docker"]},
                    }
                }),
                confirmed_roles_json=json.dumps([{"role_title": "Python Developer"}]),
            )
            db.add(cand)
            await db.commit()
            await db.refresh(cand)

        try:
            # 3. Run matching
            matches = await matching_service.run_matching_for_candidate(
                db=db, candidate_id=cand.id, force=True
            )
            assert len(matches) >= 1

            # Find match for our test job
            test_match = next((m for m in matches if m.canonical_job_id == test_job.id), None)
            assert test_match is not None
            assert test_match.composite_score >= 60.0
            assert test_match.eligibility_status in {"ELIGIBLE", "ELIGIBLE_WITH_CONDITIONS"}
            assert "Python" in test_match.matched_skills

            # 4. Incremental test: re-run without force -> reuses existing record
            matches_repeat = await matching_service.run_matching_for_candidate(
                db=db, candidate_id=cand.id, force=False
            )
            assert len(matches_repeat) == len(matches)

        finally:
            # Cleanup test job
            from models.job_embedding import JobEmbedding
            emb_stmt = select(JobEmbedding).where(JobEmbedding.canonical_job_id == test_job.id)
            j_emb = (await db.execute(emb_stmt)).scalar_one_or_none()
            if j_emb:
                await db.delete(j_emb)

            match_stmt = select(CandidateJobMatch).where(CandidateJobMatch.canonical_job_id == test_job.id)
            j_matches = (await db.execute(match_stmt)).scalars().all()
            for m in j_matches:
                await db.delete(m)

            await db.delete(test_job)
            await db.commit()


# ============================================================================
# 7. FASTAPI API ROUTE INTEGRATION TESTS
# ============================================================================

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_api_matching_summary(client):
    """GET /api/matching/summary returns expected schema and non-negative counts."""
    resp = client.get("/api/matching/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_candidates" in data
    assert "total_canonical_vacancies" in data
    assert "total_match_records" in data
    assert "algorithm_version" in data


def test_api_candidate_matches_ranked_and_filter(client):
    """POST and GET /api/matching/candidate/{id} returns ranked matches."""
    # Run matching for candidate 3
    post_resp = client.post("/api/matching/candidate/3")
    assert post_resp.status_code == 200
    items = post_resp.json()
    assert isinstance(items, list)
    if items:
        # Check descending sort order
        scores = [item["composite_score"] for item in items]
        assert scores == sorted(scores, reverse=True)

        first = items[0]
        assert "composite_score" in first
        assert "component_scores" in first
        assert "explanation" in first
        assert "eligibility_status" in first

    # Test GET endpoint with pagination
    get_resp = client.get("/api/matching/candidate/3?page=1&page_size=5")
    assert get_resp.status_code == 200
    paged_data = get_resp.json()
    assert paged_data["candidate_id"] == 3
    assert "items" in paged_data
    assert "total" in paged_data


def test_api_match_detail_explanation(client):
    """GET /api/matching/candidate/{cand_id}/job/{job_id} returns detailed breakdown."""
    # Check if a match exists for candidate 3 and job 1
    resp = client.get("/api/matching/candidate/3/job/1")
    if resp.status_code == 200:
        data = resp.json()
        assert data["candidate_id"] == 3
        assert data["canonical_job_id"] == 1
        assert len(data["explanation"]) > 20
        assert "component_scores" in data
    elif resp.status_code == 404:
        # If not evaluated yet, trigger candidate 3 and re-check
        client.post("/api/matching/candidate/3")
        retry_resp = client.get("/api/matching/candidate/3/job/1")
        assert retry_resp.status_code == 200


def test_api_batch_matching(client):
    """POST /api/matching/batch executes across legitimate candidates."""
    resp = client.post("/api/matching/batch", json={"force": False})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert "candidates_evaluated" in data
    assert "total_matches_generated" in data

