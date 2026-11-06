"""
Test Suite for Phase 4B: Job Discovery Provider Integrations.
Covers ATS Detector, Greenhouse Provider, Lever Provider, Firecrawl Provider (with fallback),
Discovery Query Builder, Orchestrator deduplication, and FastAPI discovery endpoints.
All external network requests are strictly mocked.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch
import httpx
from httpx import Response, Request

from discovery.ats_detector import AtsDetector, AtsDetectionResult
from discovery.discovery_config import DiscoverySettings
from discovery.discovery_query_builder import (
    DiscoveryQueryBuilder,
    DiscoveryTargetCriteria,
)
from discovery.providers.base_provider import (
    DiscoveredJobData,
    ProviderNotFoundError,
    ProviderAccessDeniedError,
    ProviderRateLimitError,
)
from discovery.providers.greenhouse_provider import GreenhouseProvider
from discovery.providers.lever_provider import LeverProvider
from discovery.providers.firecrawl_provider import FirecrawlProvider
from discovery.discovery_orchestrator import DiscoveryOrchestrator


# ============================================================================
# 1. ATS DETECTOR TESTS
# ============================================================================

def test_ats_detector_from_urls():
    """Verify ATS detection across Greenhouse, Lever, Workday, SmartRecruiters, and Ashby URLs."""
    # Greenhouse
    gh_res = AtsDetector.detect_from_url("https://boards.greenhouse.io/stripe")
    assert gh_res is not None
    assert gh_res.provider == "greenhouse"
    assert gh_res.identifier == "stripe"

    gh_eu_res = AtsDetector.detect_from_url("https://boards.eu.greenhouse.io/monzo")
    assert gh_eu_res is not None
    assert gh_eu_res.provider == "greenhouse"
    assert gh_eu_res.identifier == "monzo"

    # Lever
    lever_res = AtsDetector.detect_from_url("https://jobs.lever.co/netflix")
    assert lever_res is not None
    assert lever_res.provider == "lever"
    assert lever_res.identifier == "netflix"

    # Workday
    wd_res = AtsDetector.detect_from_url("https://modmed.wd501.myworkdayjobs.com/ModMed12")
    assert wd_res is not None
    assert wd_res.provider == "workday"
    assert "modmed" in wd_res.identifier.lower()

    # SmartRecruiters
    sr_res = AtsDetector.detect_from_url("https://careers.smartrecruiters.com/Mobikon")
    assert sr_res is not None
    assert sr_res.provider == "smartrecruiters"
    assert sr_res.identifier.lower() == "mobikon"

    # Ashby
    ashby_res = AtsDetector.detect_from_url("https://jobs.ashbyhq.com/linear")
    assert ashby_res is not None
    assert ashby_res.provider == "ashby"
    assert ashby_res.identifier == "linear"

    # Non-ATS URL
    none_res = AtsDetector.detect_from_url("https://google.com/about/careers")
    assert none_res is None


def test_ats_detector_from_content_and_links():
    """Verify ATS detection from HTML snippets, embed scripts, and links."""
    # Greenhouse embed script
    html_gh = """
    <html>
      <head><title>Careers</title></head>
      <body>
        <script src="https://boards.greenhouse.io/embed/job_board/js?for=razorpay"></script>
      </body>
    </html>
    """
    res_gh = AtsDetector.detect_from_content(html_gh)
    assert res_gh is not None
    assert res_gh.provider == "greenhouse"
    assert res_gh.identifier == "razorpay"

    # Lever outbound links
    links = [
        "https://example.com/about",
        "https://jobs.lever.co/postman",
    ]
    res_lever = AtsDetector.detect_from_content("<div>Check our openings</div>", links=links)
    assert res_lever is not None
    assert res_lever.provider == "lever"
    assert res_lever.identifier == "postman"


# ============================================================================
# 2. GREENHOUSE PROVIDER TESTS (MOCKED HTTP)
# ============================================================================

def test_greenhouse_provider_discovery_success():
    """Verify parsing of valid Greenhouse board API response."""
    async def run():
        provider = GreenhouseProvider()

        mock_json = {
            "jobs": [
                {
                    "id": 101,
                    "title": "Junior Python Developer",
                    "location": {"name": "Bengaluru, India"},
                    "departments": [{"name": "Software Engineering"}],
                    "absolute_url": "https://boards.greenhouse.io/testcompany/jobs/101",
                    "updated_at": "2026-11-01T12:00:00Z",
                },
                {
                    "id": 102,
                    "title": "Backend Engineer",
                    "location": {"name": "Remote - India"},
                    "departments": [{"name": "Platform"}],
                    "absolute_url": "https://boards.greenhouse.io/testcompany/jobs/102",
                    "updated_at": "2026-11-02T12:00:00Z",
                },
            ]
        }

        mock_resp = Response(
            status_code=200,
            json=mock_json,
            request=Request("GET", "https://boards-api.greenhouse.io/v1/boards/testcompany/jobs"),
        )

        with patch.object(provider, "execute_request_with_retry", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_resp
            jobs = await provider.discover_jobs("testcompany", company_name="Test Corp")

            assert len(jobs) == 2
            assert jobs[0].provider == "greenhouse"
            assert jobs[0].external_job_id == "101"
            assert jobs[0].title == "Junior Python Developer"
            assert jobs[0].location == "Bengaluru, India"
            assert jobs[0].department == "Software Engineering"
            assert jobs[0].job_url == "https://boards.greenhouse.io/testcompany/jobs/101"
            assert jobs[0].raw_payload["board_token"] == "testcompany"

        await provider.close()

    asyncio.run(run())


def test_greenhouse_provider_handles_404_gracefully():
    """Verify 404 Not Found returns empty list without breaking."""
    async def run():
        provider = GreenhouseProvider()

        with patch.object(provider, "execute_request_with_retry", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = ProviderNotFoundError("Board not found")
            jobs = await provider.discover_jobs("nonexistent_board")
            assert jobs == []

        await provider.close()

    asyncio.run(run())


# ============================================================================
# 3. LEVER PROVIDER TESTS (MOCKED HTTP)
# ============================================================================

def test_lever_provider_discovery_success():
    """Verify parsing of valid Lever postings API response."""
    async def run():
        provider = LeverProvider()

        mock_json = [
            {
                "id": "lever-job-001",
                "text": "Python Backend Engineer",
                "createdAt": 1730000000,
                "hostedUrl": "https://jobs.lever.co/sample/lever-job-001",
                "applyUrl": "https://jobs.lever.co/sample/lever-job-001/apply",
                "categories": {
                    "department": "Engineering",
                    "location": "Hyderabad, India",
                    "commitment": "Full Time",
                },
            }
        ]

        mock_resp = Response(
            status_code=200,
            json=mock_json,
            request=Request("GET", "https://api.lever.co/v0/postings/sample"),
        )

        with patch.object(provider, "execute_request_with_retry", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_resp
            jobs = await provider.discover_jobs("sample", company_name="Sample Inc")

            assert len(jobs) == 1
            assert jobs[0].provider == "lever"
            assert jobs[0].external_job_id == "lever-job-001"
            assert jobs[0].title == "Python Backend Engineer"
            assert jobs[0].location == "Hyderabad, India"
            assert jobs[0].department == "Engineering"
            assert jobs[0].job_url == "https://jobs.lever.co/sample/lever-job-001"
            assert jobs[0].application_url == "https://jobs.lever.co/sample/lever-job-001/apply"

        await provider.close()

    asyncio.run(run())


def test_lever_provider_handles_404_gracefully():
    """Verify 404 Not Found returns empty list on Lever provider."""
    async def run():
        provider = LeverProvider()

        with patch.object(provider, "execute_request_with_retry", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = ProviderNotFoundError("Site not found")
            jobs = await provider.discover_jobs("nonexistent_site")
            assert jobs == []

        await provider.close()

    asyncio.run(run())


# ============================================================================
# 4. FIRECRAWL PROVIDER TESTS (MOCKED & FALLBACK)
# ============================================================================

def test_firecrawl_unconfigured_fallback():
    """Verify that unconfigured Firecrawl provider degrades gracefully without error."""
    async def run():
        provider = FirecrawlProvider(api_key="")
        assert await provider.is_available() is False

        # Should not throw exception and return empty collections
        mapped = await provider.map_career_urls("https://example.com/careers")
        assert mapped == []

        scraped = await provider.scrape_career_page("https://example.com/careers")
        assert scraped is None

        detected = await provider.detect_ats_from_site("https://example.com/careers")
        assert detected is None

        jobs = await provider.discover_jobs("https://example.com/careers")
        assert jobs == []

        await provider.close()

    asyncio.run(run())


def test_firecrawl_configured_mocked_map_and_detect():
    """Verify Firecrawl mapping detects embedded ATS boards when configured."""
    async def run():
        provider = FirecrawlProvider(api_key="mock_fc_key_12345")
        assert await provider.is_available() is True

        # Mock mapping response with a Greenhouse link
        mock_map_resp = Response(
            status_code=200,
            json={"success": True, "links": ["https://boards.greenhouse.io/targetcorp/jobs"]},
            request=Request("POST", "https://api.firecrawl.dev/v1/map"),
        )

        with patch.object(provider, "execute_request_with_retry", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_map_resp
            detected = await provider.detect_ats_from_site("https://targetcorp.com/careers")

            assert detected is not None
            assert detected.provider == "greenhouse"
            assert detected.identifier == "targetcorp"

        await provider.close()

    asyncio.run(run())


# ============================================================================
# 5. DISCOVERY QUERY BUILDER & TARGETING TESTS
# ============================================================================

def test_query_builder_from_confirmed_roles():
    """Verify criteria construction from confirmed candidate roles."""
    roles = [
        {
            "role_title": "Python Backend Engineer",
            "alternative_titles": ["Junior Python Developer", "API Developer"],
            "matching_skills": ["Python", "FastAPI", "SQL", "Docker"],
        }
    ]
    criteria = DiscoveryQueryBuilder.from_confirmed_roles(roles, candidate_skills=["Git", "Linux"])

    assert "Python Backend Engineer" in criteria.target_titles
    assert "Junior Python Developer" in criteria.alternative_titles
    assert "Python" in criteria.key_skills
    assert "Git" in criteria.key_skills
    assert criteria.is_fresher_friendly is True


def test_query_builder_location_evaluation():
    """Verify India and Remote location matching."""
    match_blr, _ = DiscoveryQueryBuilder.is_location_match("Bengaluru, Karnataka, India")
    assert match_blr is True

    match_hyd, _ = DiscoveryQueryBuilder.is_location_match("Hyderabad / Cyberabad")
    assert match_hyd is True

    match_remote, _ = DiscoveryQueryBuilder.is_location_match("Remote (India or Worldwide)")
    assert match_remote is True

    match_us, reason = DiscoveryQueryBuilder.is_location_match("San Francisco, CA, USA")
    assert match_us is False
    assert "outside India/Remote scope" in reason


def test_query_builder_seniority_exclusion():
    """Verify exclusion of senior/staff titles for fresher candidates."""
    is_staff, _ = DiscoveryQueryBuilder.is_senior_excluded("Staff Backend Engineer")
    assert is_staff is True

    is_vp, _ = DiscoveryQueryBuilder.is_senior_excluded("VP of Engineering")
    assert is_vp is True

    is_junior, _ = DiscoveryQueryBuilder.is_senior_excluded("Junior Python Developer")
    assert is_junior is False

    is_sde, _ = DiscoveryQueryBuilder.is_senior_excluded("Software Development Engineer I")
    assert is_sde is False


def test_query_builder_job_evaluation():
    """Verify end-to-end evaluation score and match reasons."""
    criteria = DiscoveryTargetCriteria(
        target_titles=["Python Backend Engineer", "Python Developer"],
        alternative_titles=["Junior Python Developer"],
        locations=["India", "Remote"],
    )

    matched_job = DiscoveredJobData(
        provider="greenhouse",
        external_job_id="1",
        title="Python Backend Engineer",
        location="Bengaluru, India",
    )
    is_match, score, reasons = DiscoveryQueryBuilder.evaluate_job(matched_job, criteria)
    assert is_match is True
    assert score >= 0.8
    assert any("Bengaluru" in r or "India" in r for r in reasons)


# ============================================================================
# 6. DEDUPLICATION KEY AND ORCHESTRATOR TESTS
# ============================================================================

def test_dedup_key_generation_stability():
    """Verify that deduplication key is stable, case-insensitive, and reproducible."""
    key1 = DiscoveryOrchestrator.generate_dedup_key(
        company_id=42,
        provider="Greenhouse",
        external_job_id="JOB_999",
        job_url="https://boards.greenhouse.io/company/jobs/999/",
    )
    key2 = DiscoveryOrchestrator.generate_dedup_key(
        company_id=42,
        provider="greenhouse",
        external_job_id="job_999",
        job_url="https://boards.greenhouse.io/company/jobs/999",
    )
    assert key1 == key2
    assert len(key1) == 64  # SHA256 hex string


def test_orchestrator_providers_status():
    """Verify orchestrator reports provider readiness."""
    async def run():
        orchestrator = DiscoveryOrchestrator()
        providers = await orchestrator.get_providers_status()

        assert len(providers) >= 3
        names = {p["name"] for p in providers}
        assert "greenhouse" in names
        assert "lever" in names
        assert "firecrawl" in names

    asyncio.run(run())


# ============================================================================
# 7. FASTAPI DISCOVERY ENDPOINTS TESTS
# ============================================================================

def test_api_discovery_endpoints_contract():
    """Test discovery API endpoints via httpx AsyncClient using ASGI app."""
    async def run():
        from app.main import app

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            # 1. GET /api/discovery/providers
            resp_providers = await client.get("/api/discovery/providers")
            assert resp_providers.status_code == 200
            prov_data = resp_providers.json()
            assert isinstance(prov_data, list)
            assert len(prov_data) >= 3

            # 2. GET /api/discovery/status
            resp_status = await client.get("/api/discovery/status")
            assert resp_status.status_code == 200
            status_data = resp_status.json()
            assert "status" in status_data

            # 3. GET /api/discovery/results
            resp_results = await client.get("/api/discovery/results")
            assert resp_results.status_code == 200
            results_data = resp_results.json()
            assert "total" in results_data
            assert "items" in results_data
            assert "page" in results_data

            # 4. GET /api/discovery/summary
            resp_summary = await client.get("/api/discovery/summary")
            assert resp_summary.status_code == 200
            summary_data = resp_summary.json()
            assert "total_discovered_jobs" in summary_data
            assert "jobs_by_provider" in summary_data
            assert "companies_with_jobs" in summary_data

            # 5. POST /api/discovery/run with dry_run=True, background=False
            resp_run = await client.post(
                "/api/discovery/run",
                json={"limit": 1, "dry_run": True, "background": False},
            )
            assert resp_run.status_code in (200, 202)
            run_data = resp_run.json()
            assert "status" in run_data

    asyncio.run(run())
