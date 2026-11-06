"""
Job Similarity & Safeguard Calculator (Phase 5).
Computes title similarity, description overlap, and enforces critical safeguards
(location distinction, requisition ID protection, employment type compatibility).
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple


class JobSimilarityCalculator:
    """Calculates granular similarity scores and enforces deduplication safeguards."""

    # Common corporate EEO and boilerplate phrases to exclude before description comparison
    BOILERPLATE_PATTERNS = [
        re.compile(r"equal\s+opportunity\s+employer.*?(?:\.|\n|$)", re.IGNORECASE),
        re.compile(r"we\s+are\s+committed\s+to\s+creating\s+a\s+diverse\s+and\s+inclusive.*?(?:\.|\n|$)", re.IGNORECASE),
        re.compile(r"all\s+qualified\s+applicants\s+will\s+receive\s+consideration.*?(?:\.|\n|$)", re.IGNORECASE),
        re.compile(r"privacy\s+policy|terms\s+of\s+service|cookie\s+preferences", re.IGNORECASE),
        re.compile(r"to\s+learn\s+more\s+about\s+working\s+at.*?(?:\.|\n|$)", re.IGNORECASE),
    ]

    # Requisition ID extraction patterns
    REQ_ID_PATTERNS = [
        re.compile(r"\b(?:req(?:uisition)?|job|ref)?[-_\s#:]*([A-Z0-9]{4,12})\b", re.IGNORECASE),
        re.compile(r"\b(?:[A-Z]{2,4}-\d{3,8})\b"),
        re.compile(r"\b(?:REQ-\d+)\b", re.IGNORECASE),
    ]

    @classmethod
    def clean_text_for_comparison(cls, text: Optional[str]) -> str:
        """Strips HTML tags, boilerplate, and normalizes whitespace."""
        if not text:
            return ""
        # Strip HTML tags
        clean = re.sub(r"<[^>]+>", " ", text)
        # Strip boilerplate sentences
        for pat in cls.BOILERPLATE_PATTERNS:
            clean = pat.sub(" ", clean)
        # Normalize whitespace
        clean = re.sub(r"\s+", " ", clean).strip().lower()
        return clean

    @classmethod
    def tokenize(cls, text: str) -> List[str]:
        """Extracts alphanumeric words of length >= 2."""
        words = re.findall(r"\b[a-zA-Z0-9+#.]{2,}\b", text.lower())
        return words

    @classmethod
    def calculate_title_similarity(
        cls,
        title1: str,
        title2: str,
        canonical1: Optional[str] = None,
        canonical2: Optional[str] = None,
    ) -> float:
        """
        Calculates title similarity between two job postings:
        Combines token Jaccard similarity with canonical title alignment.
        """
        t1_clean = cls.clean_text_for_comparison(title1)
        t2_clean = cls.clean_text_for_comparison(title2)

        if not t1_clean or not t2_clean:
            return 0.0

        if t1_clean == t2_clean:
            return 1.0

        # Check canonical archetype match
        canonical_match = False
        if canonical1 and canonical2:
            c1_norm = canonical1.strip().lower()
            c2_norm = canonical2.strip().lower()
            if c1_norm == c2_norm and c1_norm not in ("software engineer", "developer", "specialist"):
                canonical_match = True

        tokens1 = set(cls.tokenize(t1_clean))
        tokens2 = set(cls.tokenize(t2_clean))

        if not tokens1 or not tokens2:
            return 0.0

        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)
        jaccard = len(intersection) / len(union)

        if canonical_match:
            return min(1.0, 0.4 + (0.6 * jaccard))

        return jaccard

    @classmethod
    def calculate_description_similarity(cls, desc1: Optional[str], desc2: Optional[str]) -> float:
        """
        Calculates description similarity using 4-word shingle Jaccard overlap.
        Excludes generic corporate boilerplate.
        """
        clean1 = cls.clean_text_for_comparison(desc1)
        clean2 = cls.clean_text_for_comparison(desc2)

        if not clean1 or not clean2:
            return 0.0

        if clean1 == clean2:
            return 1.0

        tokens1 = cls.tokenize(clean1)
        tokens2 = cls.tokenize(clean2)

        if len(tokens1) < 10 or len(tokens2) < 10:
            # Fall back to word tokens for short descriptions
            s1 = set(tokens1)
            s2 = set(tokens2)
            if not s1 or not s2:
                return 0.0
            return len(s1.intersection(s2)) / len(s1.union(s2))

        # Generate 4-word shingles
        shingles1 = set(" ".join(tokens1[i : i + 4]) for i in range(len(tokens1) - 3))
        shingles2 = set(" ".join(tokens2[i : i + 4]) for i in range(len(tokens2) - 3))

        if not shingles1 or not shingles2:
            return 0.0

        intersection = shingles1.intersection(shingles2)
        union = shingles1.union(shingles2)
        return len(intersection) / len(union)

    @classmethod
    def check_location_compatibility(
        cls,
        loc1: Optional[str],
        city1: Optional[str],
        is_remote1: bool,
        loc2: Optional[str],
        city2: Optional[str],
        is_remote2: bool,
    ) -> Tuple[bool, str]:
        """
        SAFEGUARD: Preserves distinction between separate vacancies with different locations.
        Returns (is_compatible, reason).
        """
        # If either is remote, locations are considered compatible
        if is_remote1 or is_remote2:
            return True, "remote_eligible"

        c1 = (city1 or "").strip().lower()
        c2 = (city2 or "").strip().lower()

        # Both have recognized cities
        if c1 and c2:
            if c1 == c2:
                return True, "matching_city"
            else:
                return False, f"different_cities ({city1} vs {city2})"

        # Inspect raw location strings for prominent city mismatches
        l1 = (loc1 or "").strip().lower()
        l2 = (loc2 or "").strip().lower()

        if not l1 or not l2 or l1 == "unspecified" or l2 == "unspecified":
            return True, "unspecified_location_compatible"

        major_indian_cities = [
            "bengaluru", "bangalore", "mumbai", "delhi", "gurgaon", "gurugram",
            "noida", "hyderabad", "pune", "chennai", "kolkata", "ahmedabad",
        ]

        found_in_1 = {city for city in major_indian_cities if city in l1}
        found_in_2 = {city for city in major_indian_cities if city in l2}

        # Normalize bangalore/bengaluru and gurgaon/gurugram
        found_in_1 = {"bengaluru" if c == "bangalore" else "gurugram" if c == "gurgaon" else c for c in found_in_1}
        found_in_2 = {"bengaluru" if c == "bangalore" else "gurugram" if c == "gurgaon" else c for c in found_in_2}

        if found_in_1 and found_in_2:
            if found_in_1 == found_in_2:
                return True, "matching_location_text"
            else:
                return False, f"conflicting_city_text ({list(found_in_1)} vs {list(found_in_2)})"

        return True, "compatible_fallback"

    @classmethod
    def extract_requisition_id(cls, text: Optional[str], external_id: Optional[str] = None) -> Optional[str]:
        """Extracts formal requisition / posting ID if present."""
        if external_id and re.match(r"^[A-Z0-9-_]{4,15}$", external_id.strip(), re.IGNORECASE):
            return external_id.strip().upper()

        if not text:
            return None

        for pat in cls.REQ_ID_PATTERNS:
            m = pat.search(text)
            if m:
                val = m.group(1) if m.groups() else m.group(0)
                if len(val) >= 4 and not val.isalpha():
                    return val.upper()
        return None

    @classmethod
    def check_requisition_conflict(
        cls,
        title1: str,
        ext_id1: Optional[str],
        title2: str,
        ext_id2: Optional[str],
    ) -> Tuple[bool, str]:
        """
        SAFEGUARD: Preserves distinction between vacancies with different requisition IDs.
        Returns (has_conflict, reason).
        """
        req1 = cls.extract_requisition_id(title1, ext_id1)
        req2 = cls.extract_requisition_id(title2, ext_id2)

        if req1 and req2:
            if req1 != req2:
                return True, f"different_requisition_ids ({req1} != {req2})"
            else:
                return False, "matching_requisition_ids"

        return False, "no_requisition_conflict"

    @classmethod
    def check_employment_type_compatibility(
        cls,
        type1: Optional[str],
        type2: Optional[str],
    ) -> Tuple[bool, str]:
        """
        SAFEGUARD: Preserves distinction between distinct employment types (e.g. Internship vs Full-Time).
        """
        t1 = (type1 or "").strip().upper()
        t2 = (type2 or "").strip().upper()

        if not t1 or not t2 or t1 == "UNSPECIFIED" or t2 == "UNSPECIFIED":
            return True, "unspecified_compatible"

        if t1 == t2:
            return True, "same_employment_type"

        # Incompatible pairings
        if ("INTERNSHIP" in (t1, t2) and "FULL_TIME" in (t1, t2)) or ("CONTRACT" in (t1, t2) and "FULL_TIME" in (t1, t2)):
            return False, f"incompatible_employment_type ({t1} vs {t2})"

        return True, "compatible"

