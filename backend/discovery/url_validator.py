# backend/discovery/url_validator.py
"""URL normalization and quality validation utilities for Job Discovery Source Registry.

Adheres strictly to Phase 4A scope constraints:
- Safe scheme addition for unambiguous domains.
- Detection of malformed, truncated, and suspicious URLs.
- Default status is NOT_CHECKED (never automatically mark VALID).
"""

import re
from typing import Tuple, Optional
from urllib.parse import urlparse, urlunparse

from models.source import VerificationStatus

# Common top-level and second-level domains
VALID_TLD_REGEX = re.compile(
    r"\.(com|in|org|net|io|ai|co|app|dev|tech|careers|jobs|bike|ae|uk|ca|de|fr|jp|edu|gov|ac\.in|co\.in|org\.in|co\.uk)(\/|$)",
    re.IGNORECASE
)

REPLACEMENT_CHAR = "\ufffd"
PLACEHOLDER_VALUES = {"", "\ufffd", "—", "-", "none", "null", "n/a", "na", ".", ".."}


def is_placeholder(val: Optional[str]) -> bool:
    """Check if value is empty or a placeholder character."""
    if not val:
        return True
    cleaned = val.strip().lower()
    return cleaned in PLACEHOLDER_VALUES or set(cleaned).issubset({"\ufffd", "—", "-", " "})


def normalize_url(raw_url: Optional[str]) -> Tuple[Optional[str], str, Optional[str]]:
    """Normalize a raw URL safely and return (normalized_url, verification_status, primary_domain).
    
    Returns:
    --------
    normalized_url : Optional[str]
        Cleaned, normalized URL with scheme and lowercased domain, or None if empty/placeholder.
    verification_status : str
        One of VerificationStatus values: NOT_CHECKED, REQUIRES_MANUAL_REVIEW, or BROKEN.
    primary_domain : Optional[str]
        Extracted root or base domain (e.g. 'accenture.com').
    """
    if is_placeholder(raw_url):
        return None, VerificationStatus.NOT_CHECKED.value, None

    url = raw_url.strip()
    
    # Strip wrapping quotes, brackets, or angle brackets
    url = url.strip("\"'<>()[];,")

    # Detect truncation markers or replacement characters
    is_truncated = False
    if REPLACEMENT_CHAR in url or "..." in url:
        is_truncated = True
        url = url.replace(REPLACEMENT_CHAR, "").replace("...", "").rstrip("-")

    # Detect suspicious trailing hyphens on LinkedIn or career links indicating cut off text
    if url.endswith("-") and ("linkedin.com/company/" in url.lower() or "careers" in url.lower()):
        is_truncated = True

    # Detect if URL contains spaces
    if " " in url:
        # Check if space is inside a path that can be fixed or if malformed
        parts = url.split(" ")
        if len(parts) == 2 and any(p.startswith("http") or "." in p for p in parts):
            url = "".join(parts)  # repair wrapped line artifact e.g. 'development-jo bs'
        else:
            return url, VerificationStatus.REQUIRES_MANUAL_REVIEW.value, None

    # Check for scheme
    has_scheme = url.startswith("http://") or url.startswith("https://")
    if not has_scheme:
        # Check if it looks like an unambiguous domain or path
        if VALID_TLD_REGEX.search(url) or url.startswith("www."):
            url = "https://" + url
        else:
            return url, VerificationStatus.REQUIRES_MANUAL_REVIEW.value, None

    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception:
        return url, VerificationStatus.REQUIRES_MANUAL_REVIEW.value, None

    # Hostname validation
    netloc = (parsed.netloc or "").strip().lower()
    if not netloc or "." not in netloc:
        return url, VerificationStatus.REQUIRES_MANUAL_REVIEW.value, None

    # Check if host ends with valid characters
    if not re.match(r"^[a-z0-9\.\-]+(:[0-9]+)?$", netloc):
        return url, VerificationStatus.REQUIRES_MANUAL_REVIEW.value, None

    # Extract primary domain
    primary_domain = _extract_primary_domain(netloc)

    # Normalize path: remove redundant trailing slash for plain domains
    path = parsed.path
    if path == "/" or not path:
        path = ""
    elif path.endswith("/") and len(path) > 1:
        # Keep trailing slash only if not a file
        path = path.rstrip("/")

    # Reassemble normalized URL
    scheme = parsed.scheme.lower()
    normalized = urlunparse((
        scheme,
        netloc,
        path,
        parsed.params,
        parsed.query,
        ""  # drop fragments
    ))

    status = (
        VerificationStatus.REQUIRES_MANUAL_REVIEW.value
        if is_truncated
        else VerificationStatus.NOT_CHECKED.value
    )

    return normalized, status, primary_domain


def _extract_primary_domain(netloc: str) -> Optional[str]:
    """Extract base domain from netloc (e.g. 'careers.google.com' -> 'google.com')."""
    # Strip port if present
    host = netloc.split(":")[0].lower()
    if host.startswith("www."):
        host = host[4:]

    parts = host.split(".")
    if len(parts) <= 2:
        return host
    
    # Handle two-part TLDs like .co.in, .co.uk, .ac.in
    if len(parts) >= 3 and parts[-2] in {"co", "com", "org", "net", "gov", "ac", "res"} and len(parts[-1]) <= 3:
        return ".".join(parts[-3:])
    
    return ".".join(parts[-2:])
