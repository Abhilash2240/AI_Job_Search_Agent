"""
Firecrawl Job Description Extractor (Phase 4C).
Extracts job descriptions from Firecrawl scraped page markdown and metadata.
"""

from typing import Any, Dict
from jobs.extraction.base_extractor import BaseJobExtractor


class FirecrawlExtractor(BaseJobExtractor):
    """Extracts normalized job information from Firecrawl crawl/scrape payloads."""

    def __init__(self):
        super().__init__(provider_name="firecrawl")

    def extract_raw_content(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts raw fields from Firecrawl markdown / scrape dictionary.
        """
        if not payload:
            return {}

        markdown = payload.get("markdown") or payload.get("description") or payload.get("content") or ""
        metadata = payload.get("metadata") or {}

        title = payload.get("title") or metadata.get("title") or ""
        url = payload.get("url") or payload.get("application_url") or metadata.get("sourceURL") or ""
        ext_id = str(payload.get("id") or payload.get("external_job_id") or "")

        return {
            "external_id": ext_id,
            "title": title,
            "description": markdown,
            "location": payload.get("location") or metadata.get("location") or "Bengaluru, India",
            "application_url": url,
            "source_url": payload.get("source_url") or url,
            "employment_type": payload.get("employment_type") or "INTERN",
            "workplace_type": payload.get("workplace_type") or "HYBRID",
        }
