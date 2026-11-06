"""
Greenhouse Job Description Extractor (Phase 4C).
Reuses Greenhouse structured job payload (content HTML, metadata, location, departments)
without re-fetching or redundant scraping.
"""

from typing import Any, Dict
from jobs.extraction.base_extractor import BaseJobExtractor


class GreenhouseExtractor(BaseJobExtractor):
    """Extracts normalized job information from Greenhouse job board payloads."""

    def __init__(self):
        super().__init__(provider_name="greenhouse")

    def extract_raw_content(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts raw fields from Greenhouse API job payload.
        Sample structure:
        {
          "id": 12345,
          "title": "Software Engineer",
          "content": "<p>Description HTML...</p>",
          "location": {"name": "Bengaluru, India"},
          "absolute_url": "https://boards.greenhouse.io/...",
          "departments": [{"name": "Engineering"}]
        }
        """
        if not payload:
            return {}

        loc = payload.get("location")
        location_name = loc.get("name") if isinstance(loc, dict) else str(loc or "")

        # Greenhouse provides full description HTML inside "content"
        description_html = payload.get("content") or payload.get("description") or ""

        return {
            "external_id": str(payload.get("id") or ""),
            "title": payload.get("title") or "",
            "description": description_html,
            "location": location_name,
            "application_url": payload.get("absolute_url") or "",
            "source_url": payload.get("absolute_url") or "",
            "departments": [d.get("name") for d in payload.get("departments", []) if isinstance(d, dict)],
            "employment_type": payload.get("employment_type"),
        }

