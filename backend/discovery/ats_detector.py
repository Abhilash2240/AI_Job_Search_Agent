"""
ATS (Applicant Tracking System) Detector.
Detects and extracts ATS provider name and board/site identifier from URLs and page content.
Supported ATS platforms:
- Greenhouse (API-supported)
- Lever (API-supported)
- Workday (Known ATS)
- SmartRecruiters (Known ATS)
- Ashby (Known ATS)
"""

import re
from dataclasses import dataclass
from typing import Optional, Tuple
from urllib.parse import urlparse
from discovery.discovery_logger import get_logger

logger = get_logger("ats_detector")

@dataclass
class AtsDetectionResult:
    provider: str
    identifier: str
    confidence: float  # 0.0 to 1.0
    detection_source: str  # "url_domain", "url_path", "html_link", "html_script"

class AtsDetector:
    """
    Detects ATS type and tenant/board identifier from URLs or scraped content.
    """

    # URL regex patterns
    GREENHOUSE_URL_PATTERNS = [
        re.compile(r"boards\.(?:eu\.)?greenhouse\.io/(?:embed/job_board\?for=)?([^/?#]+)", re.IGNORECASE),
        re.compile(r"job-boards\.(?:eu\.)?greenhouse\.io/([^/?#]+)", re.IGNORECASE),
        re.compile(r"boards-api\.greenhouse\.io/v1/boards/([^/?#]+)", re.IGNORECASE),
    ]

    LEVER_URL_PATTERNS = [
        re.compile(r"jobs\.lever\.co/([^/?#]+)", re.IGNORECASE),
        re.compile(r"api\.lever\.co/v0/postings/([^/?#]+)", re.IGNORECASE),
    ]

    WORKDAY_URL_PATTERNS = [
        re.compile(r"([a-zA-Z0-9_-]+)\.(?:wd\d+\.)?myworkdayjobs\.com", re.IGNORECASE),
        re.compile(r"myworkdaysite\.com/(?:[a-zA-Z_-]+/)?recruiting/([a-zA-Z0-9_-]+)", re.IGNORECASE),
        re.compile(r"([a-zA-Z0-9_-]+)\.wd\d+\.com", re.IGNORECASE),
    ]

    SMARTRECRUITERS_URL_PATTERNS = [
        re.compile(r"careers\.smartrecruiters\.com/([^/?#]+)", re.IGNORECASE),
        re.compile(r"jobs\.smartrecruiters\.com/([^/?#]+)", re.IGNORECASE),
    ]

    ASHBY_URL_PATTERNS = [
        re.compile(r"jobs\.ashbyhq\.com/([^/?#]+)", re.IGNORECASE),
    ]

    # HTML / Content regex patterns
    GREENHOUSE_HTML_PATTERNS = [
        re.compile(r"boards\.greenhouse\.io/(?:embed/job_board\?for=)?([a-zA-Z0-9_-]+)", re.IGNORECASE),
        re.compile(r"job-boards\.greenhouse\.io/([a-zA-Z0-9_-]+)", re.IGNORECASE),
        re.compile(r"boards\.greenhouse\.io/embed/job_board/js\?for=([a-zA-Z0-9_-]+)", re.IGNORECASE),
        re.compile(r'data-provider=["\']greenhouse["\'].*?data-board=["\']([a-zA-Z0-9_-]+)["\']', re.IGNORECASE),
        re.compile(r'grnh\.se/([a-zA-Z0-9_-]+)', re.IGNORECASE),
    ]

    LEVER_HTML_PATTERNS = [
        re.compile(r"jobs\.lever\.co/([a-zA-Z0-9_-]+)", re.IGNORECASE),
        re.compile(r"api\.lever\.co/v0/postings/([a-zA-Z0-9_-]+)", re.IGNORECASE),
        re.compile(r'data-lever-site=["\']([a-zA-Z0-9_-]+)["\']', re.IGNORECASE),
    ]

    WORKDAY_HTML_PATTERNS = [
        re.compile(r"([a-zA-Z0-9_-]+)\.(?:wd\d+|myworkdayjobs)\.com", re.IGNORECASE),
    ]

    SMARTRECRUITERS_HTML_PATTERNS = [
        re.compile(r"smartrecruiters\.com/([a-zA-Z0-9_-]+)", re.IGNORECASE),
    ]

    ASHBY_HTML_PATTERNS = [
        re.compile(r"jobs\.ashbyhq\.com/([a-zA-Z0-9_-]+)", re.IGNORECASE),
    ]

    @classmethod
    def detect_from_url(cls, url: str) -> Optional[AtsDetectionResult]:
        """
        Inspects a URL to detect if it points directly to an ATS board.
        """
        if not url:
            return None

        # Clean url
        clean_url = url.strip()

        # 1. Greenhouse
        for pat in cls.GREENHOUSE_URL_PATTERNS:
            match = pat.search(clean_url)
            if match:
                identifier = match.group(1).split("?")[0].split("#")[0].strip()
                if identifier and identifier.lower() not in ("embed", "jobs", "v1"):
                    return AtsDetectionResult(
                        provider="greenhouse",
                        identifier=identifier,
                        confidence=0.98,
                        detection_source="url_domain"
                    )

        # 2. Lever
        for pat in cls.LEVER_URL_PATTERNS:
            match = pat.search(clean_url)
            if match:
                identifier = match.group(1).split("?")[0].split("#")[0].strip()
                if identifier and identifier.lower() not in ("v0", "postings", "apply"):
                    return AtsDetectionResult(
                        provider="lever",
                        identifier=identifier,
                        confidence=0.98,
                        detection_source="url_domain"
                    )

        # 3. Workday
        for pat in cls.WORKDAY_URL_PATTERNS:
            match = pat.search(clean_url)
            if match:
                identifier = match.group(1).strip()
                return AtsDetectionResult(
                    provider="workday",
                    identifier=identifier,
                    confidence=0.95,
                    detection_source="url_domain"
                )

        # 4. SmartRecruiters
        for pat in cls.SMARTRECRUITERS_URL_PATTERNS:
            match = pat.search(clean_url)
            if match:
                identifier = match.group(1).split("?")[0].split("#")[0].strip()
                return AtsDetectionResult(
                    provider="smartrecruiters",
                    identifier=identifier,
                    confidence=0.95,
                    detection_source="url_domain"
                )

        # 5. Ashby
        for pat in cls.ASHBY_URL_PATTERNS:
            match = pat.search(clean_url)
            if match:
                identifier = match.group(1).split("?")[0].split("#")[0].strip()
                return AtsDetectionResult(
                    provider="ashby",
                    identifier=identifier,
                    confidence=0.95,
                    detection_source="url_domain"
                )

        return None

    @classmethod
    def detect_from_content(cls, content: str, links: Optional[list] = None) -> Optional[AtsDetectionResult]:
        """
        Inspects HTML content and discovered links to detect embedded or linked ATS boards.
        """
        # First check explicitly discovered links
        if links:
            for link in links:
                if isinstance(link, str):
                    res = cls.detect_from_url(link)
                    if res:
                        res.detection_source = "html_link"
                        return res

        if not content:
            return None

        # Inspect content strings/scripts for Greenhouse
        for pat in cls.GREENHOUSE_HTML_PATTERNS:
            match = pat.search(content)
            if match:
                token = match.group(1).strip()
                if token and token.lower() not in ("embed", "jobs", "v1"):
                    return AtsDetectionResult(
                        provider="greenhouse",
                        identifier=token,
                        confidence=0.90,
                        detection_source="html_script"
                    )

        # Inspect content for Lever
        for pat in cls.LEVER_HTML_PATTERNS:
            match = pat.search(content)
            if match:
                site = match.group(1).strip()
                if site and site.lower() not in ("v0", "postings"):
                    return AtsDetectionResult(
                        provider="lever",
                        identifier=site,
                        confidence=0.90,
                        detection_source="html_script"
                    )

        # Inspect content for Ashby
        for pat in cls.ASHBY_HTML_PATTERNS:
            match = pat.search(content)
            if match:
                return AtsDetectionResult(
                    provider="ashby",
                    identifier=match.group(1).strip(),
                    confidence=0.90,
                    detection_source="html_script"
                )

        # Inspect content for SmartRecruiters
        for pat in cls.SMARTRECRUITERS_HTML_PATTERNS:
            match = pat.search(content)
            if match:
                return AtsDetectionResult(
                    provider="smartrecruiters",
                    identifier=match.group(1).strip(),
                    confidence=0.85,
                    detection_source="html_script"
                )

        # Inspect content for Workday
        for pat in cls.WORKDAY_HTML_PATTERNS:
            match = pat.search(content)
            if match:
                return AtsDetectionResult(
                    provider="workday",
                    identifier=match.group(1).strip(),
                    confidence=0.85,
                    detection_source="html_script"
                )

        return None

    @classmethod
    def detect(cls, url: Optional[str] = None, content: Optional[str] = None, links: Optional[list] = None) -> Optional[AtsDetectionResult]:
        """
        Convenience method: runs URL detection first, then content/link detection.
        """
        if url:
            res = cls.detect_from_url(url)
            if res:
                return res
        return cls.detect_from_content(content or "", links or [])
