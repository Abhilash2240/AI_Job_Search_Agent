"""
Job Normalizer Module (Phase 4C).
Provides normalization for job titles, seniority levels, workplace types,
employment types, and geographic locations.
"""

import re
from typing import List, Optional, Tuple
from jobs.job_schema import EmploymentType, LocationInfo, SeniorityLevel, WorkplaceType


# Common city mappings for India tech hubs
INDIA_CITIES = {
    "bengaluru": ("Bengaluru", "Karnataka", "India"),
    "bangalore": ("Bengaluru", "Karnataka", "India"),
    "hyderabad": ("Hyderabad", "Telangana", "India"),
    "cyberabad": ("Hyderabad", "Telangana", "India"),
    "pune": ("Pune", "Maharashtra", "India"),
    "mumbai": ("Mumbai", "Maharashtra", "India"),
    "navi mumbai": ("Navi Mumbai", "Maharashtra", "India"),
    "delhi": ("New Delhi", "Delhi", "India"),
    "new delhi": ("New Delhi", "Delhi", "India"),
    "noida": ("Noida", "Uttar Pradesh", "India"),
    "greater noida": ("Greater Noida", "Uttar Pradesh", "India"),
    "gurgaon": ("Gurugram", "Haryana", "India"),
    "gurugram": ("Gurugram", "Haryana", "India"),
    "chennai": ("Chennai", "Tamil Nadu", "India"),
    "madras": ("Chennai", "Tamil Nadu", "India"),
    "kolkata": ("Kolkata", "West Bengal", "India"),
    "ahmedabad": ("Ahmedabad", "Gujarat", "India"),
    "kochi": ("Kochi", "Kerala", "India"),
    "cochin": ("Kochi", "Kerala", "India"),
    "trivandrum": ("Thiruvananthapuram", "Kerala", "Kerala"),
    "thiruvananthapuram": ("Thiruvananthapuram", "Kerala", "India"),
    "indore": ("Indore", "Madhya Pradesh", "India"),
    "chandigarh": ("Chandigarh", "Punjab", "India"),
    "jaipur": ("Jaipur", "Rajasthan", "India"),
}


class JobNormalizer:
    """Normalizes titles, seniority, workplace, employment, and location."""

    @classmethod
    def clean_title(cls, title: str) -> str:
        """Removes trailing requisition codes, brackets, and redundant noise from title."""
        if not title:
            return ""
        clean = title.strip()
        # Clean trailing locations or requisition IDs iteratively
        for _ in range(3):
            clean = re.sub(
                r"\s*[-–—|/]\s*(?:Remote|Hybrid|India|Bengaluru|Bangalore|Hyderabad|Pune|Mumbai|Delhi|Gurgaon|Noida|USA|US)\s*$",
                "",
                clean,
                flags=re.IGNORECASE,
            )
            clean = re.sub(
                r"\s*[\(\[][^\)\]]*(?:remote|hybrid|india|req|id|job|ref|\d)[^\)\]]*[\)\]]\s*$",
                "",
                clean,
                flags=re.IGNORECASE,
            )
        # Consolidate whitespace
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    @classmethod
    def detect_seniority(cls, title: str, description_text: Optional[str] = None) -> SeniorityLevel:
        """Classifies seniority level without removing it from the title."""
        combined = f"{title} {description_text[:200] if description_text else ''}".lower()

        # 1. Executive / Director
        if re.search(r"\b(director|vp|vice president|head of|chief|cto|cpo|cio)\b", combined):
            return SeniorityLevel.DIRECTOR_EXEC

        # 2. Staff / Principal / Lead / Architect
        if re.search(r"\b(staff|principal|tech lead|team lead|lead\b|architect)\b", combined):
            return SeniorityLevel.LEAD_STAFF

        # 3. Senior
        if re.search(r"\b(senior|sr\.?|sde\s*3|sde\s*iii\b|engineer\s*3|engineer\s*iii\b|level\s*3|l3)\b", combined):
            return SeniorityLevel.SENIOR

        # 4. Intern / Trainee
        if re.search(r"\b(intern|internship|trainee|co-?op|apprentice)\b", combined):
            return SeniorityLevel.INTERN

        # 5. Entry Level / Associate / Junior / Fresher / L1 / Engineer I
        if re.search(
            r"\b(junior|jr\.?|associate|graduate|entry\s*level|fresher|sde\s*1|sde\s*i\b|engineer\s*1|engineer\s*i\b|level\s*1|l1)\b",
            combined,
        ):
            return SeniorityLevel.ENTRY_LEVEL

        # 6. Mid Level / L2 / Engineer II
        if re.search(r"\b(sde\s*2|sde\s*ii\b|engineer\s*2|engineer\s*ii\b|level\s*2|l2|mid\s*level)\b", combined):
            return SeniorityLevel.MID_LEVEL

        # Default for software engineer / developer with no prefix
        if re.search(r"\b(developer|engineer|specialist|analyst|programmer)\b", combined):
            return SeniorityLevel.MID_LEVEL

        return SeniorityLevel.UNKNOWN

    @classmethod
    def canonicalize_title(cls, title: str) -> str:
        """
        Derives canonical role archetype from normalized title.
        Preserves original title while standardizing role classification.
        """
        cleaned = cls.clean_title(title)
        lower = cleaned.lower()

        # Remove seniority modifiers for canonical comparison
        canonical = re.sub(
            r"\b(junior|jr\.?|associate|senior|sr\.?|staff|principal|lead|chief|intern|graduate|entry\s*level|i{1,3}|1|2|3)\b",
            "",
            lower,
            flags=re.IGNORECASE,
        )
        canonical = re.sub(r"\s+", " ", canonical).strip(" -–—|/,\t\r\n")
        if not canonical:
            canonical = cleaned
        canonical = canonical.title()

        if "Python" in cleaned:
            if "Backend" in cleaned:
                return "Python Backend Engineer"
            return "Python Developer"
        elif "Backend" in cleaned:
            return "Backend Engineer"
        elif "Frontend" in cleaned:
            return "Frontend Engineer"
        elif "Full" in cleaned and ("Stack" in cleaned or "stack" in cleaned):
            return "Full Stack Engineer"
        elif "Software" in cleaned and ("Engineer" in cleaned or "Developer" in cleaned):
            return "Software Engineer"
        elif "Data" in cleaned and ("Engineer" in cleaned or "Engineering" in cleaned):
            return "Data Engineer"
        elif "Machine Learning" in cleaned or "Ml Engineer" in cleaned:
            return "Machine Learning Engineer"
        elif "Devops" in cleaned:
            return "DevOps Engineer"
        elif "Qa" in cleaned or "Quality" in cleaned or "Test" in cleaned:
            return "QA Engineer"

        return canonical or cleaned

    @classmethod
    def normalize_workplace_type(
        cls, location_text: Optional[str] = None, raw_type: Optional[str] = None
    ) -> WorkplaceType:
        """Determines REMOTE, HYBRID, or ON_SITE from location text or workplace category."""
        target = f"{raw_type or ''} {location_text or ''}".lower()

        if "remote" in target or "wfh" in target or "work from home" in target or "anywhere" in target:
            if "hybrid" in target:
                return WorkplaceType.HYBRID
            return WorkplaceType.REMOTE

        if "hybrid" in target or "flexible" in target:
            return WorkplaceType.HYBRID

        if "on-site" in target or "onsite" in target or "in-office" in target or "office" in target:
            return WorkplaceType.ON_SITE

        if location_text and any(city in target for city in INDIA_CITIES):
            return WorkplaceType.ON_SITE

        return WorkplaceType.UNSPECIFIED

    @classmethod
    def normalize_employment_type(cls, raw_type: Optional[str] = None, text: Optional[str] = None) -> EmploymentType:
        """Classifies employment type: FULL_TIME, PART_TIME, CONTRACT, INTERNSHIP."""
        target = f"{raw_type or ''} {text[:300] if text else ''}".lower()

        if re.search(r"\b(intern|internship|trainee|co-?op)\b", target):
            return EmploymentType.INTERNSHIP
        if re.search(r"\b(full\s*-?\s*time|permanent|regular)\b", target):
            return EmploymentType.FULL_TIME
        if re.search(r"\b(part\s*-?\s*time)\b", target):
            return EmploymentType.PART_TIME
        if re.search(r"\b(contract|contractor|freelance|consultant)\b", target):
            return EmploymentType.CONTRACT
        if re.search(r"\b(temporary|temp)\b", target):
            return EmploymentType.TEMPORARY

        return EmploymentType.FULL_TIME  # Standard industry default for corporate postings

    @classmethod
    def normalize_location(cls, raw_location: Optional[str]) -> LocationInfo:
        """
        Parses location string into structured city, state, country, and remote eligibility.
        """
        if not raw_location or not raw_location.strip():
            return LocationInfo(
                raw_location=None,
                city=None,
                state=None,
                country=None,
                is_remote=False,
                workplace_type=WorkplaceType.UNSPECIFIED,
                eligible_locations=[],
            )

        clean_raw = raw_location.strip()
        lower = clean_raw.lower()

        is_remote = bool(re.search(r"\b(remote|wfh|anywhere|work from home|virtual)\b", lower))
        workplace_type = cls.normalize_workplace_type(location_text=clean_raw)

        city = None
        state = None
        country = None
        eligible_locations = []

        # Check for India cities
        for key, (c, s, co) in INDIA_CITIES.items():
            if re.search(rf"\b{re.escape(key)}\b", lower):
                city = c
                state = s
                country = co
                eligible_locations.append(f"{c}, {co}")
                break

        # Check for explicitly stated Country if city not matched
        if not country:
            if "india" in lower:
                country = "India"
                eligible_locations.append("India")
            elif "united states" in lower or re.search(r"\b(usa?|us)\b", lower):
                country = "United States"
                eligible_locations.append("United States")
            elif "singapore" in lower:
                country = "Singapore"
                eligible_locations.append("Singapore")
            elif "united kingdom" in lower or re.search(r"\b(uk)\b", lower):
                country = "United Kingdom"
                eligible_locations.append("United Kingdom")
            elif "germany" in lower:
                country = "Germany"
                eligible_locations.append("Germany")

        if is_remote and country:
            eligible_locations.append(f"Remote - {country}")
        elif is_remote:
            eligible_locations.append("Remote")

        return LocationInfo(
            raw_location=clean_raw,
            city=city,
            state=state,
            country=country,
            is_remote=is_remote,
            workplace_type=workplace_type,
            eligible_locations=list(dict.fromkeys(eligible_locations)),
        )
