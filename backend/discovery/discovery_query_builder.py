"""
Discovery Query Builder & Targeting Evaluator.
Builds query parameters and match predicates based on candidate's confirmed roles,
skills, experience level, and geographic preferences (India & Remote).
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from discovery.discovery_logger import get_logger
from discovery.providers.base_provider import DiscoveredJobData

logger = get_logger("query_builder")


INDIA_TECH_LOCATIONS = {
    "india",
    "bengaluru",
    "bangalore",
    "hyderabad",
    "pune",
    "gurgaon",
    "gurugram",
    "noida",
    "delhi",
    "delhi ncr",
    "mumbai",
    "chennai",
    "kolkata",
    "ahmedabad",
    "kochi",
    "trivandrum",
    "indore",
    "chandigarh",
}

REMOTE_INDICATORS = {
    "remote",
    "anywhere",
    "work from home",
    "wfh",
    "hybrid",
    "virtual",
    "distributed",
}

SENIOR_TITLES_EXCLUSION = [
    r"\bstaff\b",
    r"\bprincipal\b",
    r"\bdirector\b",
    r"\bvice president\b",
    r"\bvp\b",
    r"\bhead of\b",
    r"\blead\b",
    r"\btech lead\b",
    r"\barchitect\b",
    r"\bmanager\b",
    r"\bsr\.\b",
    r"\bsenior\b",
]


@dataclass
class DiscoveryTargetCriteria:
    """Targeting specification compiled from candidate profile & confirmed roles."""
    target_titles: List[str] = field(default_factory=list)
    alternative_titles: List[str] = field(default_factory=list)
    key_skills: List[str] = field(default_factory=list)
    locations: List[str] = field(default_factory=lambda: ["India", "Remote"])
    is_fresher_friendly: bool = True
    max_experience_years: Optional[float] = 2.0


class DiscoveryQueryBuilder:
    """
    Constructs search criteria from candidate confirmed roles and validates
    whether discovered job vacancies match candidate targets.
    """

    @classmethod
    def from_confirmed_roles(
        cls,
        confirmed_roles: List[Dict[str, Any]],
        candidate_skills: Optional[List[str]] = None,
        is_fresher: bool = True,
    ) -> DiscoveryTargetCriteria:
        """
        Builds criteria from candidate's confirmed roles data stored in the database.
        """
        titles: Set[str] = set()
        alt_titles: Set[str] = set()
        skills: Set[str] = set(candidate_skills or [])

        for role in confirmed_roles:
            role_title = role.get("role_title") or role.get("title")
            if role_title:
                titles.add(role_title.strip())

            for alt in role.get("alternative_titles") or []:
                if alt:
                    alt_titles.add(alt.strip())

            for skill in role.get("matching_skills") or []:
                if skill:
                    skills.add(skill.strip())

        # If no confirmed roles supplied, provide sensible developer defaults
        if not titles:
            titles = {"Python Developer", "Backend Engineer", "Software Engineer"}

        return DiscoveryTargetCriteria(
            target_titles=sorted(list(titles)),
            alternative_titles=sorted(list(alt_titles)),
            key_skills=sorted(list(skills)),
            locations=["India", "Remote"],
            is_fresher_friendly=is_fresher,
            max_experience_years=2.0 if is_fresher else None,
        )

    @classmethod
    def is_location_match(cls, location_text: Optional[str]) -> Tuple[bool, str]:
        """
        Checks if job location matches India or Remote.
        If location is empty or unspecified, returns True (cannot disqualify).
        """
        if not location_text:
            return True, "Location unspecified (passed)"

        clean = location_text.lower()

        # Check India cities & regions
        for loc in INDIA_TECH_LOCATIONS:
            if loc in clean:
                return True, f"Matched India location: {loc}"

        # Check Remote
        for rem in REMOTE_INDICATORS:
            if rem in clean:
                return True, f"Matched remote location: {rem}"

        # Check generic terms
        if "global" in clean or "worldwide" in clean or "apac" in clean:
            return True, "Matched global/APAC location"

        return False, f"Location '{location_text}' is outside India/Remote scope"

    @classmethod
    def is_senior_excluded(cls, title: str) -> Tuple[bool, Optional[str]]:
        """
        Detects whether the job title carries high-seniority flags unsuitable for 0-2 yrs candidates.
        """
        title_lower = title.lower()
        for pattern in SENIOR_TITLES_EXCLUSION:
            if re.search(pattern, title_lower):
                return True, f"Excluded by seniority title pattern: {pattern}"
        return False, None

    @classmethod
    def evaluate_job(
        cls,
        job: DiscoveredJobData,
        criteria: DiscoveryTargetCriteria,
        strict_seniority: bool = False,
    ) -> Tuple[bool, float, List[str]]:
        """
        Evaluates a discovered job against target criteria.
        Returns:
            (is_match, relevance_score [0.0 - 1.0], match_reasons)
        """
        title_clean = job.title.strip().lower()
        reasons: List[str] = []
        score = 0.5  # Base discovery baseline score

        # 1. Check seniority exclusion (only if candidate is fresher and strict mode is on)
        if criteria.is_fresher_friendly and strict_seniority:
            is_senior, exclusion_reason = cls.is_senior_excluded(job.title)
            if is_senior:
                return False, 0.0, [exclusion_reason]

        # 2. Location evaluation
        loc_match, loc_reason = cls.is_location_match(job.location)
        if loc_match:
            score += 0.2
            reasons.append(loc_reason)
        else:
            # If explicit non-India location (e.g. "Berlin, Germany"), penalize heavily
            score -= 0.3
            reasons.append(loc_reason)

        # 3. Title matching
        title_matched = False
        # Direct exact or substring title match
        for target in criteria.target_titles:
            t_low = target.lower()
            if t_low in title_clean or title_clean in t_low:
                score += 0.3
                title_matched = True
                reasons.append(f"Title matches target role: {target}")
                break

        # Alternative title match
        if not title_matched:
            for alt in criteria.alternative_titles:
                a_low = alt.lower()
                if a_low in title_clean or title_clean in a_low:
                    score += 0.25
                    title_matched = True
                    reasons.append(f"Title matches alternative role: {alt}")
                    break

        # Keyword matching in title (e.g. "python", "backend", "software engineer", "developer")
        core_keywords = ["python", "backend", "developer", "engineer", "software", "api", "data"]
        matched_kw = [kw for kw in core_keywords if kw in title_clean]
        if matched_kw:
            score += min(0.2, len(matched_kw) * 0.05)
            reasons.append(f"Title contains relevant tech keywords: {', '.join(matched_kw)}")

        # Normalization
        final_score = max(0.0, min(1.0, round(score, 4)))
        is_match = (title_matched or len(matched_kw) >= 1) and (loc_match or not job.location)

        return is_match, final_score, reasons

