"""
Job Vacancy Verification & Lifecycle Service (Phase 5).
Safely probes application and source URLs, detects posting closures,
interprets HTTP response codes and redirects, and updates vacancy status
following strict safety rules (403/429/5xx != CLOSED; 404 requires confirmation).
"""

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import httpx
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.canonical_job import CanonicalJob, VacancyStatus


class VacancyVerificationService:
    """Verifies vacancy availability and manages the lifecycle states of CanonicalJobs."""

    # Closure phrases indicating a posting has expired or been filled
    CLOSURE_PHRASES = [
        re.compile(r"no\s+longer\s+accepting\s+applications", re.IGNORECASE),
        re.compile(r"this\s+(?:position|job|opening|role)\s+(?:has\s+been|is)\s+(?:filled|closed)", re.IGNORECASE),
        re.compile(r"this\s+job\s+(?:posting\s+)?has\s+expired", re.IGNORECASE),
        re.compile(r"this\s+job\s+is\s+no\s+longer\s+available", re.IGNORECASE),
        re.compile(r"the\s+job\s+you\s+are\s+looking\s+for\s+is\s+(?:closed|unavailable)", re.IGNORECASE),
        re.compile(r"this\s+opening\s+has\s+closed", re.IGNORECASE),
    ]

    # Blocked / login / CAPTCHA indicators
    BLOCKED_PHRASES = [
        re.compile(r"please\s+verify\s+you\s+are\s+a\s+human", re.IGNORECASE),
        re.compile(r"cloudflare\s+ray\s+id", re.IGNORECASE),
        re.compile(r"sign\s*in\s+to\s+apply|login\s+required", re.IGNORECASE),
        re.compile(r"access\s+denied|forbidden", re.IGNORECASE),
    ]

    CAREERS_ROOT_PATTERNS = [
        re.compile(r"^/(?:careers|jobs|openings|work-with-us|join-us)/?$", re.IGNORECASE),
        re.compile(r"^/?$"),
    ]

    def __init__(
        self,
        consecutive_missing_threshold: int = 2,
        request_timeout: float = 12.0,
    ):
        self.consecutive_missing_threshold = consecutive_missing_threshold
        self.request_timeout = request_timeout

    def analyze_response(
        self,
        status_code: int,
        response_url: str,
        initial_url: str,
        response_text: str = "",
    ) -> Tuple[str, str, Dict[str, Any]]:
        """
        Interprets HTTP response to determine vacancy status according to Phase 5 rules.
        Returns: (tentative_status, reason, metadata_dict)
        """
        metadata = {
            "http_status": status_code,
            "response_url": response_url,
            "initial_url": initial_url,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

        # 1. HTTP 403 Forbidden -> BLOCKED (Never mark CLOSED)
        if status_code == 403:
            return VacancyStatus.BLOCKED.value, "http_403_access_forbidden", metadata

        # 2. HTTP 429 Too Many Requests -> BLOCKED (Never mark CLOSED)
        if status_code == 429:
            return VacancyStatus.BLOCKED.value, "http_429_rate_limited", metadata

        # 3. HTTP 5xx Server Error -> UNKNOWN (Never mark CLOSED)
        if 500 <= status_code < 600:
            return VacancyStatus.UNKNOWN.value, f"http_{status_code}_server_error", metadata

        # 4. HTTP 404 / 410 -> Not found candidate
        if status_code in (404, 410):
            return VacancyStatus.CLOSED.value, f"http_{status_code}_not_found", metadata

        # 5. Check if redirect led to a generic careers root rather than specific job
        try:
            from urllib.parse import urlparse
            init_path = urlparse(initial_url).path.rstrip("/")
            resp_path = urlparse(response_url).path.rstrip("/")

            if init_path != resp_path and any(p.search(resp_path) for p in self.CAREERS_ROOT_PATTERNS):
                metadata["redirect_destination"] = response_url
                return VacancyStatus.REDIRECTED.value, "redirected_to_careers_root_job_missing", metadata
        except Exception:
            pass

        # 6. HTTP 200 OK -> Inspect text content
        if 200 <= status_code < 300:
            # Check for CAPTCHA / Blocked content in 200 response
            for b_pat in self.BLOCKED_PHRASES:
                if b_pat.search(response_text[:3000]):
                    return VacancyStatus.BLOCKED.value, "blocked_or_captcha_detected", metadata

            # Check for explicit closure phrases
            for c_pat in self.CLOSURE_PHRASES:
                m = c_pat.search(response_text)
                if m:
                    metadata["closure_evidence"] = m.group(0).strip()
                    return VacancyStatus.CLOSED.value, f"closure_phrase_detected: '{m.group(0).strip()}'", metadata

            # Check if page is unusually empty
            if len(response_text.strip()) < 100:
                return VacancyStatus.NEEDS_REVIEW.value, "extremely_short_response_body", metadata

            # Healthy active vacancy
            return VacancyStatus.ACTIVE.value, "posting_active_and_accessible", metadata

        return VacancyStatus.UNKNOWN.value, f"unhandled_status_{status_code}", metadata

    async def verify_canonical_job(
        self,
        db: AsyncSession,
        job_id: int,
        client: Optional[httpx.AsyncClient] = None,
    ) -> CanonicalJob:
        """
        Verifies a single canonical job's URLs and applies lifecycle state transitions.
        """
        stmt = select(CanonicalJob).where(CanonicalJob.id == job_id)
        canonical = (await db.execute(stmt)).scalar_one_or_none()

        if not canonical:
            raise ValueError(f"Canonical job {job_id} not found.")

        target_url = canonical.canonical_application_url or canonical.canonical_source_url
        if not target_url:
            canonical.vacancy_status = VacancyStatus.NEEDS_REVIEW.value
            canonical.last_verified_at = datetime.now(timezone.utc)
            await db.commit()
            return canonical

        now = datetime.now(timezone.utc)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        tentative_status = VacancyStatus.UNKNOWN.value
        reason = "unverified"
        details: Dict[str, Any] = {}

        # Perform network check using provided or ephemeral client
        should_close_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=self.request_timeout, follow_redirects=True)
            should_close_client = True

        try:
            resp = await client.get(target_url, headers=headers)
            tentative_status, reason, details = self.analyze_response(
                status_code=resp.status_code,
                response_url=str(resp.url),
                initial_url=target_url,
                response_text=resp.text,
            )
        except httpx.TimeoutException:
            tentative_status = VacancyStatus.UNKNOWN.value
            reason = "http_request_timeout"
            details = {"error": "TimeoutException", "url": target_url}
        except httpx.ConnectError:
            tentative_status = VacancyStatus.BROKEN_LINK.value
            reason = "dns_or_connection_error"
            details = {"error": "ConnectError", "url": target_url}
        except Exception as exc:
            tentative_status = VacancyStatus.UNKNOWN.value
            reason = f"network_exception: {type(exc).__name__}"
            details = {"error": str(exc), "url": target_url}
        finally:
            if should_close_client:
                await client.aclose()

        # Update lifecycle counters & history
        canonical.verification_attempts += 1
        canonical.last_verified_at = now
        details["reason"] = reason

        old_status = canonical.vacancy_status
        new_status = old_status

        if tentative_status == VacancyStatus.ACTIVE.value:
            new_status = VacancyStatus.ACTIVE.value
            canonical.consecutive_missing_checks = 0
        elif tentative_status in (VacancyStatus.CLOSED.value, VacancyStatus.REDIRECTED.value):
            canonical.consecutive_missing_checks += 1
            if canonical.consecutive_missing_checks >= self.consecutive_missing_threshold:
                new_status = VacancyStatus.CLOSED.value
            else:
                new_status = VacancyStatus.NEEDS_REVIEW.value
                details["note"] = f"Missing count ({canonical.consecutive_missing_checks}) below threshold ({self.consecutive_missing_threshold}). Marked NEEDS_REVIEW before closing."
        elif tentative_status == VacancyStatus.BLOCKED.value:
            new_status = VacancyStatus.BLOCKED.value
        elif tentative_status == VacancyStatus.BROKEN_LINK.value:
            canonical.consecutive_missing_checks += 1
            if canonical.consecutive_missing_checks >= self.consecutive_missing_threshold:
                new_status = VacancyStatus.BROKEN_LINK.value
            else:
                new_status = VacancyStatus.NEEDS_REVIEW.value
        else:
            new_status = tentative_status

        if new_status != old_status:
            canonical.vacancy_status = new_status
            canonical.last_status_change_at = now

        canonical.verification_details = json.dumps(details)
        await db.commit()
        await db.refresh(canonical)
        return canonical


    async def run_batch_verification(
        self,
        db: AsyncSession,
        limit: int = 20,
        status_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Runs vacancy verification across a batch of CanonicalJobs."""
        query = select(CanonicalJob).order_by(CanonicalJob.last_verified_at.asc().nulls_first())
        if status_filter:
            query = query.where(CanonicalJob.vacancy_status == status_filter.upper().strip())
        if limit:
            query = query.limit(limit)

        res = await db.execute(query)
        jobs = res.scalars().all()

        summary = {
            "total_checked": len(jobs),
            "active": 0,
            "closed": 0,
            "blocked": 0,
            "broken_link": 0,
            "redirected": 0,
            "needs_review": 0,
            "unknown": 0,
        }

        async with httpx.AsyncClient(timeout=self.request_timeout, follow_redirects=True) as client:
            for c_job in jobs:
                verified = await self.verify_canonical_job(db=db, job_id=c_job.id, client=client)
                stat_key = verified.vacancy_status.lower()
                if stat_key in summary:
                    summary[stat_key] += 1
                else:
                    summary["unknown"] += 1

        return summary

    # Method alias for backward compatibility
    verify_batch = run_batch_verification


vacancy_verifier = VacancyVerificationService()

