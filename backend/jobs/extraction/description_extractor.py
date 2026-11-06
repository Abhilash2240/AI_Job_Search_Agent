"""
Job Description Text & Section Extractor (Phase 4C).
Cleans HTML markup, strips boilerplate navigation/cookie headers,
and segments job postings into structured sections: summary, responsibilities,
qualifications, preferred qualifications, and benefits.
"""

import html
import re
from typing import Any, Dict, List, Optional, Tuple


class DescriptionExtractor:
    """Cleans and segments raw HTML or markdown job descriptions."""

    # Heading patterns for section segmentation
    RESPONSIBILITY_HEADINGS = [
        r"responsibilities",
        r"what\s+you(?:'ll|\s+will)\s+do",
        r"the\s+role",
        r"what\s+you'll\s+be\s+working\s+on",
        r"your\s+day\s+to\s+day",
        r"key\s+duties",
        r"what\s+we\s+expect\s+from\s+you",
    ]

    QUALIFICATION_HEADINGS = [
        r"requirements",
        r"qualifications",
        r"basic\s+qualifications",
        r"minimum\s+qualifications",
        r"who\s+you\s+are",
        r"what\s+you\s+need",
        r"must\s+have",
        r"what\s+you\s+bring",
        r"experience\s+and\s+skills",
    ]

    PREFERRED_HEADINGS = [
        r"preferred\s+qualifications",
        r"preferred\s+skills",
        r"bonus\s+points",
        r"nice\s+to\s+have",
        r"desirable",
        r"good\s+to\s+have",
        r"plus",
        r"additional\s+qualifications",
    ]

    BENEFITS_HEADINGS = [
        r"benefits",
        r"what\s+we\s+offer",
        r"perks\s*(?:&|and)\s*benefits",
        r"why\s+join\s+us",
        r"our\s+benefits",
        r"compensation\s*(?:&|and)\s*perks",
    ]

    NOISE_PATTERNS = [
        re.compile(r"[^\n\.]*?(?:we\s+use\s+cookies|cookie\s+preferences|cookie\s+banner|accept\s+all\s+cookies)[^\n\.]*[\.\n]?", re.IGNORECASE),
        re.compile(r"share\s+this\s+job\s*(?:on|via)?\s*(?:linkedin|twitter|facebook)?", re.IGNORECASE),
        re.compile(r"←\s*back\s+to\s+(?:jobs|careers)", re.IGNORECASE),
        re.compile(r"home\s*>\s*careers\s*>\s*.*?\n", re.IGNORECASE),
        re.compile(r"apply\s+now|apply\s+for\s+this\s+job", re.IGNORECASE),
    ]

    @classmethod
    def clean_html(cls, raw_content: str) -> str:
        """Removes HTML tags, entities, script/style blocks, and boilerplate."""
        if not raw_content:
            return ""

        text = raw_content

        # 1. Unescape HTML entities
        text = html.unescape(text)

        # 2. Strip scripts and styles
        text = re.sub(r"<(script|style|iframe|noscript)[^>]*>.*?</\1>", " ", text, flags=re.DOTALL | re.IGNORECASE)

        # 3. Convert line-break tags and paragraph tags to newlines
        text = re.sub(r"<(?:br|/p|/div|/li|/h\d)[^>]*>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<li[^>]*>", "\n• ", text, flags=re.IGNORECASE)

        # 4. Strip remaining HTML tags
        text = re.sub(r"<[^>]+>", " ", text)

        # 5. Clean up noise patterns
        for noise in cls.NOISE_PATTERNS:
            text = noise.sub(" ", text)

        # 6. Normalize whitespace
        lines = [line.strip() for line in text.split("\n")]
        # Keep non-empty lines
        cleaned_lines = []
        for line in lines:
            if line:
                cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    @classmethod
    def extract_bullets(cls, block: str) -> List[str]:
        """Extracts individual bullet points from a section block."""
        if not block:
            return []
        bullets = []
        # Match lines starting with bullet symbols or numbers
        for line in block.split("\n"):
            clean = line.strip()
            clean = re.sub(r"^[\s•\-\*–—\d\.\)]+\s*", "", clean).strip()
            if len(clean) >= 5:
                bullets.append(clean)
        return bullets

    @classmethod
    def segment_description(cls, cleaned_text: str) -> Dict[str, Any]:
        """
        Segments a cleaned description into:
        - summary
        - responsibilities
        - qualifications (Required)
        - preferred_qualifications (Preferred)
        - benefits
        """
        result = {
            "summary": "",
            "responsibilities": [],
            "qualifications": [],
            "preferred_qualifications": [],
            "benefits": [],
            "full_text": cleaned_text,
        }

        if not cleaned_text:
            return result

        lines = cleaned_text.split("\n")
        current_section = "summary"
        section_buffers: Dict[str, List[str]] = {
            "summary": [],
            "responsibilities": [],
            "qualifications": [],
            "preferred_qualifications": [],
            "benefits": [],
        }

        # Build regex patterns for heading matching
        resp_pat = re.compile(rf"^(?:{'|'.join(cls.RESPONSIBILITY_HEADINGS)})[:\s]*$", re.IGNORECASE)
        qual_pat = re.compile(rf"^(?:{'|'.join(cls.QUALIFICATION_HEADINGS)})[:\s]*$", re.IGNORECASE)
        pref_pat = re.compile(rf"^(?:{'|'.join(cls.PREFERRED_HEADINGS)})[:\s]*$", re.IGNORECASE)
        ben_pat = re.compile(rf"^(?:{'|'.join(cls.BENEFITS_HEADINGS)})[:\s]*$", re.IGNORECASE)

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # Check if line acts as a section header
            if pref_pat.match(line_str):
                current_section = "preferred_qualifications"
                continue
            elif resp_pat.match(line_str):
                current_section = "responsibilities"
                continue
            elif qual_pat.match(line_str):
                current_section = "qualifications"
                continue
            elif ben_pat.match(line_str):
                current_section = "benefits"
                continue

            section_buffers[current_section].append(line_str)

        result["summary"] = "\n".join(section_buffers["summary"]).strip()
        result["responsibilities"] = cls.extract_bullets("\n".join(section_buffers["responsibilities"]))
        result["qualifications"] = cls.extract_bullets("\n".join(section_buffers["qualifications"]))
        result["preferred_qualifications"] = cls.extract_bullets("\n".join(section_buffers["preferred_qualifications"]))
        result["benefits"] = cls.extract_bullets("\n".join(section_buffers["benefits"]))

        return result
