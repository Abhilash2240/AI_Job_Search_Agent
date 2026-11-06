"""
Canonical URL Normalizer (Phase 5).
Normalizes application and source URLs, removes tracking/query artifacts,
and resolves provider-specific ATS permalinks into canonical identifiers.
"""

import hashlib
import re
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from typing import Optional, Tuple


class CanonicalUrlNormalizer:
    """Normalizes job posting and application URLs across providers."""

    # Query parameters that convey tracking, campaign, or transient session info
    TRACKING_PARAMS = {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "gh_jid",
        "lever-origin",
        "lever-source",
        "ref",
        "source",
        "mode",
        "fbclid",
        "gclid",
        "trk",
        "tracking",
        "session_id",
        "sid",
        "origin",
    }

    # Patterns for canonical ATS job identifiers
    GREENHOUSE_PATTERN = re.compile(
        r"boards\.greenhouse\.io/(?:embed/job_app\?.*token=|([^/]+)/jobs/)?(\d+)",
        re.IGNORECASE,
    )
    GREENHOUSE_BOARD_PATTERN = re.compile(
        r"boards\.greenhouse\.io/([^/]+)/jobs/(\d+)",
        re.IGNORECASE,
    )
    LEVER_PATTERN = re.compile(
        r"jobs\.lever\.co/([^/]+)/([a-zA-Z0-9_-]+)",
        re.IGNORECASE,
    )

    @classmethod
    def normalize_url(cls, raw_url: Optional[str]) -> str:
        """
        Cleans and normalizes a job URL:
        1. Strips tracking query parameters.
        2. Lowercases scheme and host.
        3. Removes default ports (:80, :443) and 'www.' prefix.
        4. Strips trailing slashes, redundant slashes, and fragments.
        5. Alphabetically sorts remaining query parameters.
        """
        if not raw_url or not isinstance(raw_url, str):
            return ""

        url = raw_url.strip()
        if not url:
            return ""

        # Prepend https:// if scheme is missing
        if not re.match(r"^[a-zA-Z]+://", url):
            url = f"https://{url}"

        try:
            parsed = urlparse(url)
        except Exception:
            return url.strip().rstrip("/")

        scheme = "https" if parsed.scheme in ("http", "https") else parsed.scheme.lower()
        netloc = parsed.netloc.lower()

        # Remove default port
        if netloc.endswith(":80") or netloc.endswith(":443"):
            netloc = netloc.rsplit(":", 1)[0]

        # Standardize www prefix
        if netloc.startswith("www."):
            netloc = netloc[4:]

        # Clean path: normalize multiple consecutive slashes
        path = re.sub(r"/{2,}", "/", parsed.path)
        path = path.rstrip("/")

        # Filter out tracking query parameters
        filtered_query_pairs = []
        if parsed.query:
            query_pairs = parse_qsl(parsed.query, keep_blank_values=False)
            for k, v in query_pairs:
                if k.lower() not in cls.TRACKING_PARAMS:
                    filtered_query_pairs.append((k, v))
            filtered_query_pairs.sort(key=lambda x: x[0])

        new_query = urlencode(filtered_query_pairs) if filtered_query_pairs else ""

        # Assemble normalized URL without fragment
        clean_url = urlunparse((scheme, netloc, path, "", new_query, ""))
        return clean_url

    @classmethod
    def extract_ats_key(cls, url: str) -> Optional[Tuple[str, str, str]]:
        """
        Extracts standardized (provider, board/site, job_id) tuple if the URL is a recognized ATS permalink.
        Returns None if not recognized.
        """
        if not url:
            return None

        # Greenhouse embed URL check (e.g. /embed/job_app?for=stripe&token=123)
        if "boards.greenhouse.io/embed/job_app" in url:
            try:
                parsed = urlparse(url)
                qp = dict(parse_qsl(parsed.query))
                board = qp.get("for", "").lower()
                token = qp.get("token", "")
                if board and token:
                    return ("greenhouse", board, token)
            except Exception:
                pass

        # Greenhouse boards match
        gh_match = cls.GREENHOUSE_BOARD_PATTERN.search(url)
        if gh_match:
            board = gh_match.group(1).lower()
            job_id = gh_match.group(2)
            return ("greenhouse", board, job_id)

        # Lever match
        lever_match = cls.LEVER_PATTERN.search(url)
        if lever_match:
            site = lever_match.group(1).lower()
            job_id = lever_match.group(2).lower()
            return ("lever", site, job_id)

        return None

    @classmethod
    def get_canonical_permalink(cls, url: str) -> str:
        """
        Converts ATS URLs into their canonical standard permalink.
        For example:
        'https://jobs.lever.co/cred/abc-123/apply?ref=xyz' -> 'https://jobs.lever.co/cred/abc-123'
        """
        ats_info = cls.extract_ats_key(url)
        if ats_info:
            provider, entity, job_id = ats_info
            if provider == "greenhouse":
                return f"https://boards.greenhouse.io/{entity}/jobs/{job_id}"
            elif provider == "lever":
                return f"https://jobs.lever.co/{entity}/{job_id}"

        return cls.normalize_url(url)

    @classmethod
    def generate_url_hash(cls, url: str) -> str:
        """Generates a reproducible SHA-256 fingerprint from the normalized URL."""
        norm = cls.normalize_url(url)
        return hashlib.sha256(norm.encode("utf-8")).hexdigest()
