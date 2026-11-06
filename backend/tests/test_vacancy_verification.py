"""
Test Suite for Phase 5: Vacancy Verification & Lifecycle Tracking.
Covers HTTP status safety rules (403, 429, 5xx != CLOSED),
closure phrase detection, redirect inspection, consecutive check thresholds,
and verification API endpoints with mocked network requests.
"""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
import httpx
from sqlalchemy import select

from models.canonical_job import (
    CanonicalJob,
    CanonicalJobSource,
    VacancyStatus,
)
from verification.vacancy_verifier import VacancyVerificationService


# ============================================================================
# 1. RESPONSE ANALYSIS & SAFETY RULES TESTS
# ============================================================================

def test_response_analysis_safety_rules():
    """Verify that 403, 429, and 5xx are never marked CLOSED."""
    verifier = VacancyVerificationService()

    # 1. HTTP 403 Forbidden -> BLOCKED
    stat, reason, _ = verifier.analyze_response(
        status_code=403,
        response_url="https://boards.greenhouse.io/company/jobs/1",
        initial_url="https://boards.greenhouse.io/company/jobs/1",
    )
    assert stat == VacancyStatus.BLOCKED.value
    assert "forbidden" in reason

    # 2. HTTP 429 Rate Limited -> BLOCKED
    stat, reason, _ = verifier.analyze_response(
        status_code=429,
        response_url="https://jobs.lever.co/company/1",
        initial_url="https://jobs.lever.co/company/1",
    )
    assert stat == VacancyStatus.BLOCKED.value
    assert "rate_limited" in reason

    # 3. HTTP 500 / 503 Server Error -> UNKNOWN
    stat, reason, _ = verifier.analyze_response(
        status_code=503,
        response_url="https://company.com/jobs/1",
        initial_url="https://company.com/jobs/1",
    )
    assert stat == VacancyStatus.UNKNOWN.value
    assert "server_error" in reason

    # 4. HTTP 200 with CAPTCHA / Bot Challenge -> BLOCKED
    captcha_html = "<html><head><title>Verify you are human</title></head><body>Please verify you are a human. Cloudflare Ray ID: abc</body></html>"
    stat, reason, _ = verifier.analyze_response(
        status_code=200,
        response_url="https://company.com/jobs/1",
        initial_url="https://company.com/jobs/1",
        response_text=captcha_html,
    )
    assert stat == VacancyStatus.BLOCKED.value


def test_closure_phrase_detection():
    """Verify explicit closure detection inside 200 responses."""
    verifier = VacancyVerificationService()

    closed_html = "<div>Thank you for your interest. This position has been filled.</div>"
    stat, reason, details = verifier.analyze_response(
        status_code=200,
        response_url="https://boards.greenhouse.io/company/jobs/1",
        initial_url="https://boards.greenhouse.io/company/jobs/1",
        response_text=closed_html,
    )
    assert stat == VacancyStatus.CLOSED.value
    assert "closure_phrase_detected" in reason
    assert "has been filled" in details.get("closure_evidence", "").lower()


def test_redirect_to_careers_root_detection():
    """Verify that redirects to generic /careers or home page indicate vacancy removal."""
    verifier = VacancyVerificationService()

    stat, reason, _ = verifier.analyze_response(
        status_code=200,
        response_url="https://company.com/careers",
        initial_url="https://company.com/careers/software-engineer-123",
        response_text="<h1>Browse all available openings</h1>",
    )
    assert stat == VacancyStatus.REDIRECTED.value
    assert "careers_root" in reason


# ============================================================================
# 2. CONSECUTIVE MISSING CHECKS LIFECYCLE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_consecutive_missing_checks_lifecycle():
    """Verify that a single 404 sets NEEDS_REVIEW; two consecutive 404s transitions to CLOSED."""
    import uuid
    from db.database import AsyncSessionLocal
    verifier = VacancyVerificationService(consecutive_missing_threshold=2)

    async with AsyncSessionLocal() as db:
        unique_id = f"CANON-TEST-VERIFY-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)
        job = CanonicalJob(
            canonical_job_id=unique_id,
            company_name="LifecycleCorp",
            title="Systems Architect",
            canonical_job_title="Systems Architect",
            normalized_title="systems architect",
            description="High scalability cloud architecture.",
            canonical_application_url="https://example.com/jobs/systems-arch",
            vacancy_status=VacancyStatus.ACTIVE.value,
            first_seen_at=now,
            last_seen_at=now,
            last_status_change_at=now,
            consecutive_missing_checks=0,
            verification_attempts=0,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)

        # Mock Client for 1st 404 check
        mock_resp_404 = httpx.Response(status_code=404, request=httpx.Request("GET", job.canonical_application_url))
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp_404

        # 1st Check: Single 404 should NOT mark CLOSED immediately
        v1 = await verifier.verify_canonical_job(db=db, job_id=job.id, client=mock_client)
        assert v1.consecutive_missing_checks == 1
        assert v1.vacancy_status == VacancyStatus.NEEDS_REVIEW.value  # Guarded!

        # 2nd Check: Consecutive 404 reaches threshold -> Transitions to CLOSED
        v2 = await verifier.verify_canonical_job(db=db, job_id=job.id, client=mock_client)
        assert v2.consecutive_missing_checks == 2
        assert v2.vacancy_status == VacancyStatus.CLOSED.value

        # 3rd Check: Mock active 200 response -> Recovers to ACTIVE, resets counter
        mock_resp_200 = httpx.Response(
            status_code=200,
            request=httpx.Request("GET", job.canonical_application_url),
            text="<h1>Systems Architect</h1><p>Full job description and active apply button. Looking for senior cloud engineer to join our team.</p>",
        )
        mock_client.get.return_value = mock_resp_200

        v3 = await verifier.verify_canonical_job(db=db, job_id=job.id, client=mock_client)
        assert v3.consecutive_missing_checks == 0
        assert v3.vacancy_status == VacancyStatus.ACTIVE.value

        # Cleanup
        await db.delete(job)
        await db.commit()
