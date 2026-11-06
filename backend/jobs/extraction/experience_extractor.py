"""
Experience & Compensation Extractor (Phase 4C).
Extracts minimum/maximum years of experience, fresher eligibility,
internship status, and explicit published salary/stipend information.
Never fabricates or assumes 0 years for unspecified experience.
"""

import re
from typing import Optional, Tuple
from jobs.job_schema import ExperienceRequirements, SalaryInfo, SeniorityLevel


class ExperienceExtractor:
    """Extracts experience requirements, fresher eligibility, and explicit compensation."""

    # Regex patterns for experience ranges
    EXPERIENCE_PATTERNS = [
        # 0-1 years / 0 to 2 years
        (
            re.compile(r"\b(0)\s*(?:-|to)\s*([0-2])\s*(?:\+)?\s*years?\b", re.IGNORECASE),
            lambda m: (float(m.group(1)), float(m.group(2)), True),
        ),
        # 2-4 years / 3 to 5 years
        (
            re.compile(r"\b(\d+)\s*(?:-|to)\s*(\d+)\s*(?:\+)?\s*years?\b", re.IGNORECASE),
            lambda m: (float(m.group(1)), float(m.group(2)), float(m.group(1)) == 0),
        ),
        # 1+ years / 2+ years / 5+ years
        (
            re.compile(r"\b(\d+)\s*\+\s*years?(?:\s+of)?(?:\s+experience)?\b", re.IGNORECASE),
            lambda m: (float(m.group(1)), None, float(m.group(1)) == 0),
        ),
        # at least 2 years / minimum 3 years
        (
            re.compile(r"\b(?:at least|minimum|min)\s*(\d+)\s*years?\b", re.IGNORECASE),
            lambda m: (float(m.group(1)), None, float(m.group(1)) == 0),
        ),
        # up to 2 years
        (
            re.compile(r"\b(?:up to|maximum|max)\s*(\d+)\s*years?\b", re.IGNORECASE),
            lambda m: (0.0, float(m.group(1)), True),
        ),
    ]

    FRESHER_INDICATORS = [
        re.compile(r"\bfreshers?\s+(?:welcome|eligible|can apply|preferred)\b", re.IGNORECASE),
        re.compile(r"\b(?:entry\s*level|no\s+prior\s+experience\s+required|zero\s+experience)\b", re.IGNORECASE),
        re.compile(r"\b(?:recent|college|university)\s+graduates?\b", re.IGNORECASE),
        re.compile(r"\b0\s*(?:-|to)\s*[12]\s*years?\b", re.IGNORECASE),
    ]

    INTERNSHIP_INDICATORS = [
        re.compile(r"\b(intern|internship|trainee|co-?op)\b", re.IGNORECASE),
    ]

    # Salary patterns
    # INR: ₹8,00,000 - ₹12,00,000 / 8-12 LPA / 50k per month / stipend 25,000
    SALARY_INR_LPA = re.compile(
        r"(?:(?:inr|rs\.?|₹)\s*)?(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*(?:lpa\b|(?:lakhs?|lac|lacs?)\s*(?:per\s*annum|pa\b|/yr))",
        re.IGNORECASE,
    )
    SALARY_INR_EXACT_LPA = re.compile(
        r"(?:(?:salary|ctc|package|compensation|remuneration|pay)\s*(?:of|:|is)?\s*(?:(?:inr|rs\.?|₹)\s*)?(\d+(?:\.\d+)?)\s*(?:lpa|lakhs?|lac|lacs?)\b)|(?:(?:(?:inr|rs\.?|₹)\s*)?(\d+(?:\.\d+)?)\s*lpa\b)",
        re.IGNORECASE,
    )
    SALARY_INR_RANGE = re.compile(
        r"(?:(?:salary|ctc|package|compensation|remuneration|pay)\s*(?:of|:|is)?\s*)?(?:(?:inr|rs\.?|₹)\s*)([0-9,]{5,})\s*(?:-|to)\s*(?:(?:inr|rs\.?|₹)\s*)?([0-9,]{5,})\s*(?:per\s*(?:annum|year)|/yr|pa\b)",
        re.IGNORECASE,
    )
    SALARY_INR_MONTHLY = re.compile(
        r"(?:(?:inr|rs\.?|₹)\s*)([0-9,]+)\s*(?:-|to)?\s*(?:(?:inr|rs\.?|₹)\s*)?([0-9,]+)?\s*(?:per\s*month|/month|pm)\b",
        re.IGNORECASE,
    )
    SALARY_STIPEND = re.compile(
        r"(?:stipend|stipend\s*of)\s*(?:(?:inr|rs\.?|₹)\s*)?([0-9,]+)(?:\s*(?:-|to)\s*([0-9,]+))?\b",
        re.IGNORECASE,
    )

    # USD: $80,000 - $120,000 / $45/hr
    SALARY_USD_RANGE = re.compile(
        r"\$([0-9,]+)\s*(?:-|to)\s*\$([0-9,]+)\s*(?:per\s*(?:year|annum)|/yr)?\b",
        re.IGNORECASE,
    )
    SALARY_USD_HOURLY = re.compile(
        r"\$([0-9,]+(?:\.\d+)?)\s*(?:-|to)?\s*(?:\$([0-9,]+(?:\.\d+)?))?\s*(?:/hr|per\s*hour)\b",
        re.IGNORECASE,
    )

    @classmethod
    def extract_experience(cls, text: str, title: str = "") -> ExperienceRequirements:
        """
        Parses text for explicit years of experience, fresher eligibility, and internship tags.
        """
        if not text:
            return ExperienceRequirements()

        combined = f"{title}\n{text}"
        min_years = None
        max_years = None
        is_fresher = False
        evidence = None

        # 1. Match numeric experience patterns
        for pattern, extractor in cls.EXPERIENCE_PATTERNS:
            match = pattern.search(text)
            if match:
                mn, mx, fresh = extractor(match)
                min_years = mn
                max_years = mx
                is_fresher = fresh
                evidence = match.group(0).strip()
                break

        # 2. Check explicit fresher indicators
        for f_pat in cls.FRESHER_INDICATORS:
            f_match = f_pat.search(combined)
            if f_match:
                is_fresher = True
                if min_years is None:
                    min_years = 0.0
                    max_years = max_years or 1.0
                if not evidence:
                    evidence = f_match.group(0).strip()
                break

        # 3. Check internship indicators
        is_intern = bool(any(i_pat.search(combined) for i_pat in cls.INTERNSHIP_INDICATORS))
        if is_intern:
            is_fresher = True
            min_years = 0.0
            max_years = max_years or 1.0
            seniority = SeniorityLevel.INTERN
        elif is_fresher or (min_years is not None and min_years <= 1.0):
            seniority = SeniorityLevel.ENTRY_LEVEL
        elif min_years is not None and min_years >= 5.0:
            seniority = SeniorityLevel.SENIOR
        elif min_years is not None and min_years >= 2.0:
            seniority = SeniorityLevel.MID_LEVEL
        else:
            seniority = SeniorityLevel.UNKNOWN

        return ExperienceRequirements(
            min_years=min_years,
            max_years=max_years,
            is_fresher_eligible=is_fresher,
            is_internship=is_intern,
            seniority_level=seniority,
            evidence=evidence,
        )

    @classmethod
    def extract_salary(cls, text: str) -> Optional[SalaryInfo]:
        """
        Extracts explicitly published compensation details. Never estimates or fabricates.
        """
        if not text:
            return None

        # 1. Check INR LPA Range (e.g. 6-10 LPA)
        m = cls.SALARY_INR_LPA.search(text)
        if m:
            mn = float(m.group(1)) * 100000
            mx = float(m.group(2)) * 100000
            return SalaryInfo(
                min_amount=mn,
                max_amount=mx,
                currency="INR",
                period="YEAR",
                raw_text=m.group(0).strip(),
            )

        # 2. Check INR Exact LPA (e.g. 8 LPA)
        m = cls.SALARY_INR_EXACT_LPA.search(text)
        if m:
            val_str = m.group(1) or m.group(2)
            val = float(val_str) * 100000
            return SalaryInfo(
                min_amount=val,
                max_amount=val,
                currency="INR",
                period="YEAR",
                raw_text=m.group(0).strip(),
            )

        # 3. Check INR Absolute Range (e.g. ₹600,000 - ₹900,000)
        m = cls.SALARY_INR_RANGE.search(text)
        if m:
            mn = float(m.group(1).replace(",", ""))
            mx = float(m.group(2).replace(",", ""))
            return SalaryInfo(
                min_amount=mn,
                max_amount=mx,
                currency="INR",
                period="YEAR",
                raw_text=m.group(0).strip(),
            )

        # 4. Check Stipend (e.g. stipend 25,000)
        m = cls.SALARY_STIPEND.search(text)
        if m:
            mn = float(m.group(1).replace(",", ""))
            mx = float(m.group(2).replace(",", "")) if m.group(2) else mn
            return SalaryInfo(
                min_amount=mn,
                max_amount=mx,
                currency="INR",
                period="STIPEND",
                raw_text=m.group(0).strip(),
            )

        # 5. Check INR Monthly (e.g. ₹40,000 per month)
        m = cls.SALARY_INR_MONTHLY.search(text)
        if m:
            mn = float(m.group(1).replace(",", ""))
            mx = float(m.group(2).replace(",", "")) if m.group(2) else mn
            return SalaryInfo(
                min_amount=mn,
                max_amount=mx,
                currency="INR",
                period="MONTH",
                raw_text=m.group(0).strip(),
            )

        # 6. Check USD Annual Range (e.g. $100,000 - $140,000)
        m = cls.SALARY_USD_RANGE.search(text)
        if m:
            mn = float(m.group(1).replace(",", ""))
            mx = float(m.group(2).replace(",", ""))
            return SalaryInfo(
                min_amount=mn,
                max_amount=mx,
                currency="USD",
                period="YEAR",
                raw_text=m.group(0).strip(),
            )

        # 7. Check USD Hourly (e.g. $45/hr)
        m = cls.SALARY_USD_HOURLY.search(text)
        if m:
            mn = float(m.group(1).replace(",", ""))
            mx = float(m.group(2).replace(",", "")) if m.group(2) else mn
            return SalaryInfo(
                min_amount=mn,
                max_amount=mx,
                currency="USD",
                period="HOUR",
                raw_text=m.group(0).strip(),
            )

        return None

