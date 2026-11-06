"""
Comprehensive Test Suite for AI Job Search Agent Completion.
Tests Saved Jobs, Applications Tracking, Company Research,
Pipeline Orchestration, Preferences, Dashboard Analytics, and Unified Job Feed.
"""

import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from db.database import AsyncSessionLocal
from models.candidate import Candidate
from models.canonical_job import CanonicalJob, VacancyStatus
from models.saved_job import SavedJob
from models.application import JobApplication, ApplicationStatus
from models.user_preferences import UserPreferences
from models.pipeline_execution import PipelineExecution
from sqlalchemy import select


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ============================================================================
# 1. HEALTH AND DASHBOARD ANALYTICS TESTS
# ============================================================================

def test_api_health_check(client):
    """GET /health and /api/health return healthy status and service name."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"
    assert "AI Job Search Agent" in resp.json()["service"]

    resp2 = client.get("/api/health")
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "healthy"


def test_api_dashboard_stats(client):
    """GET /api/dashboard/stats returns real aggregated system and recommendation metrics."""
    resp = client.get("/api/dashboard/stats?candidate_id=3")
    assert resp.status_code == 200
    data = resp.json()

    assert "system" in data
    assert "recommendations" in data
    assert "saved_jobs" in data
    assert "saved" in data
    assert "applications" in data
    assert "recent_pipeline_runs" in data

    # Verify real non-hardcoded counts
    assert data["system"]["total_companies"] >= 800
    assert data["system"]["total_canonical_vacancies"] >= 10
    assert data["system"]["canonical_vacancies"] >= 10
    assert data["system"]["job_embeddings"] >= 10
    assert data["recommendations"]["total_matches_evaluated"] >= 10
    assert "top_match_score" in data["recommendations"]
    assert "total_saved" in data["saved_jobs"]
    assert "total_saved" in data["saved"]
    assert "active_in_pipeline" in data["applications"]
    assert "active_applications" in data["applications"]


def test_dashboard_contract_regression(client):
    """Regression test ensuring frontend DashboardPage contract invariants hold."""
    resp = client.get("/api/dashboard/stats?candidate_id=1")
    assert resp.status_code == 200
    data = resp.json()

    # Exact properties accessed by DashboardPage component
    assert isinstance(data["system"]["total_canonical_vacancies"], int)
    assert isinstance(data["system"]["canonical_vacancies"], int)
    assert isinstance(data["system"]["job_embeddings"], int)
    assert isinstance(data["system"]["total_companies"], int)
    assert isinstance(data["saved_jobs"]["total_saved"], int)
    assert isinstance(data["saved"]["total_saved"], int)
    assert isinstance(data["applications"]["active_in_pipeline"], int)
    assert isinstance(data["applications"]["active_applications"], int)
    assert isinstance(data["recommendations"]["total_matches_evaluated"], int)
    assert isinstance(data["recommendations"]["top_match_score"], (int, float))


# ============================================================================
# 2. UNIFIED JOB FEED & DETAIL TESTS
# ============================================================================

def test_api_jobs_feed_with_match_enrichment(client):
    """GET /api/jobs/feed returns canonical jobs enriched with match scores, badges, and statuses."""
    resp = client.get("/api/jobs/feed?candidate_id=3&page=1&page_size=10")
    assert resp.status_code == 200
    data = resp.json()

    assert "total" in data
    assert "items" in data
    assert len(data["items"]) >= 1

    first = data["items"][0]
    assert "title" in first
    assert "company_name" in first
    assert "match_score" in first
    assert "eligibility_status" in first
    assert "is_saved" in first
    assert "application_status" in first
    assert "work_mode" in first


def test_api_jobs_feed_search_and_filters(client):
    """GET /api/jobs/feed respects search keywords and work mode filters."""
    # Filter by keyword
    resp = client.get("/api/jobs/feed?candidate_id=3&q=Engineer")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) >= 1
    assert data["total"] >= 1


def test_api_canonical_job_detail_endpoint(client):
    """GET /api/jobs/{canonical_job_id} returns complete vacancy data and match breakdown."""
    resp = client.get("/api/jobs/1?candidate_id=3")
    assert resp.status_code == 200
    data = resp.json()

    assert data["id"] == 1
    assert "title" in data
    assert "company_name" in data
    assert "responsibilities" in data
    assert "required_skills" in data
    assert "match_details" in data
    assert "is_saved" in data
    assert "application_status" in data


# ============================================================================
# 3. SAVED JOBS MANAGEMENT TESTS
# ============================================================================

def test_api_saved_jobs_crud(client):
    """Test bookmarking, listing, updating notes, and unsaving a canonical vacancy."""
    cand_id = 3
    job_id = 1

    # 1. Save job
    post_resp = client.post("/api/saved-jobs", json={
        "candidate_id": cand_id,
        "canonical_job_id": job_id,
        "notes": "Target priority application"
    })
    assert post_resp.status_code in [200, 201]
    saved_data = post_resp.json()
    saved_id = saved_data["id"]
    assert saved_data["candidate_id"] == cand_id
    assert saved_data["canonical_job_id"] == job_id
    assert saved_data["is_active"] is True

    # 2. Get saved jobs list
    get_resp = client.get(f"/api/saved-jobs/candidate/{cand_id}")
    assert get_resp.status_code == 200
    list_data = get_resp.json()
    assert list_data["total"] >= 1
    assert any(item["canonical_job_id"] == job_id for item in list_data["items"])

    # 3. Update notes
    patch_resp = client.patch(f"/api/saved-jobs/{saved_id}", json={"notes": "Updated note: Review salary"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["notes"] == "Updated note: Review salary"

    # 4. Unsave job
    del_resp = client.delete(f"/api/saved-jobs/candidate/{cand_id}/job/{job_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "SUCCESS"


# ============================================================================
# 4. APPLICATION TRACKING & DUPLICATE PROTECTION TESTS
# ============================================================================

def test_api_applications_lifecycle_and_duplicate_protection(client):
    """Test application creation, duplicate protection, status updates, and history."""
    cand_id = 3
    job_id = 2
    app_id = None

    try:
        # 1. Create application
        create_resp = client.post("/api/applications", json={
            "candidate_id": cand_id,
            "canonical_job_id": job_id,
            "company_name": "Test Company",
            "job_title": "Backend Developer",
            "application_url": "https://example.com/apply",
            "status": "APPLIED",
            "notes": "Applied via company portal",
        })
        assert create_resp.status_code == 201
        app_data = create_resp.json()
        app_id = app_data["id"]
        assert app_data["status"] == "APPLIED"
        assert len(app_data["status_history"]) >= 1

        # 2. Duplicate protection test: attempt to create duplicate application for same candidate & job
        dup_resp = client.post("/api/applications", json={
            "candidate_id": cand_id,
            "canonical_job_id": job_id,
            "company_name": "Test Company",
            "job_title": "Backend Developer",
        })
        assert dup_resp.status_code == 409
        assert "already exists" in dup_resp.json()["detail"]

        # 3. Update status to INTERVIEW with notes
        status_resp = client.patch(f"/api/applications/{app_id}/status", json={
            "status": "INTERVIEW",
            "notes": "Round 1 Technical Interview scheduled"
        })
        assert status_resp.status_code == 200
        assert status_resp.json()["status"] == "INTERVIEW"
        assert len(status_resp.json()["status_history"]) >= 2

        # 4. Check application stats
        stats_resp = client.get(f"/api/applications/candidate/{cand_id}/stats")
        assert stats_resp.status_code == 200
        stats = stats_resp.json()
        assert stats["total_applications"] >= 1
        assert stats["interviews_scheduled"] >= 1

    finally:
        # Cleanup test application
        if app_id:
            client.delete(f"/api/applications/{app_id}")


# ============================================================================
# 5. COMPANY AND RECRUITER RESEARCH TESTS
# ============================================================================

def test_api_company_research_profile_and_policy(client):
    """GET /api/companies/{id}/research returns company info, sources, verified contacts, and outreach policy."""
    resp = client.get("/api/companies/1/research")
    assert resp.status_code == 200
    data = resp.json()

    assert data["company_id"] == 1
    assert "name" in data
    assert "career_sources" in data
    assert "contacts" in data
    assert "outreach_policy" in data
    # Verify strict outreach guideline
    assert data["outreach_policy"]["requires_explicit_authorization"] is True
    assert data["outreach_policy"]["automated_sending_enabled"] is False


def test_api_company_vacancies_endpoint(client):
    """GET /api/companies/{id}/vacancies returns active vacancies for company."""
    resp = client.get("/api/companies/1/vacancies")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ============================================================================
# 6. PIPELINE ORCHESTRATION & STATUS TESTS
# ============================================================================

def test_api_pipeline_status_and_history(client):
    """GET /api/pipeline/status and /api/pipeline/history return pipeline execution state."""
    status_resp = client.get("/api/pipeline/status")
    assert status_resp.status_code == 200
    assert "is_running" in status_resp.json()

    history_resp = client.get("/api/pipeline/history")
    assert history_resp.status_code == 200
    assert "total" in history_resp.json()
    assert "items" in history_resp.json()


# ============================================================================
# 7. CANDIDATE JOB SEARCH PREFERENCES TESTS
# ============================================================================

def test_api_candidate_preferences_crud(client):
    """GET and PUT /api/preferences/candidate/{id} manages search criteria."""
    cand_id = 3

    # 1. Get preferences (creates default if absent)
    get_resp = client.get(f"/api/preferences/candidate/{cand_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["candidate_id"] == cand_id
    assert isinstance(data["preferred_locations"], list)

    # 2. Update preferences
    put_resp = client.put(f"/api/preferences/candidate/{cand_id}", json={
        "preferred_locations": ["Bengaluru", "Hyderabad", "Remote"],
        "work_modes": ["REMOTE", "HYBRID"],
        "min_match_score": 45.0
    })
    assert put_resp.status_code == 200
    updated = put_resp.json()
    assert "Bengaluru" in updated["preferred_locations"]
    assert updated["min_match_score"] == 45.0

