"""
Lever Job Description Extractor (Phase 4C).
Reuses Lever structured postings payload (description, lists, additional, categories)
without redundant network roundtrips.
"""

from typing import Any, Dict
from jobs.extraction.base_extractor import BaseJobExtractor


class LeverExtractor(BaseJobExtractor):
    """Extracts normalized job information from Lever postings API payloads."""

    def __init__(self):
        super().__init__(provider_name="lever")

    def extract_raw_content(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts raw fields from Lever API posting payload.
        Sample structure:
        {
          "id": "lever-123",
          "text": "Backend Engineer",
          "categories": {"location": "Hyderabad, India", "commitment": "Full Time"},
          "description": "<p>Overview...</p>",
          "lists": [{"text": "Responsibilities", "content": "<li>...</li>"}],
          "additional": "<p>Benefits...</p>",
          "hostedUrl": "https://jobs.lever.co/...",
          "applyUrl": "https://jobs.lever.co/.../apply"
        }
        """
        if not payload:
            return {}

        categories = payload.get("categories") or {}
        location_name = categories.get("location") or categories.get("workplaceType") or ""
        commitment = categories.get("commitment")

        # Assemble full description from intro, lists, and additional sections
        desc_parts = []
        if payload.get("description"):
            desc_parts.append(payload["description"])
        elif payload.get("descriptionBody"):
            desc_parts.append(payload["descriptionBody"])
        elif payload.get("opening"):
            desc_parts.append(payload["opening"])
        elif payload.get("descriptionPlain"):
            desc_parts.append(payload["descriptionPlain"])

        lists = payload.get("lists") or []
        for lst in lists:
            header = lst.get("text") or ""
            content = lst.get("content") or ""
            if header:
                desc_parts.append(f"<h3>{header}</h3>")
            if content:
                desc_parts.append(content)

        if payload.get("additional"):
            desc_parts.append(payload["additional"])
        elif payload.get("additionalPlain"):
            desc_parts.append(payload["additionalPlain"])

        full_description_html = "\n".join(desc_parts)

        return {
            "external_id": str(payload.get("id") or ""),
            "title": payload.get("text") or "",
            "description": full_description_html,
            "location": location_name,
            "application_url": payload.get("applyUrl") or payload.get("hostedUrl") or "",
            "source_url": payload.get("hostedUrl") or "",
            "employment_type": commitment,
        }

