"""
Education Requirements Extractor (Phase 4C).
Extracts degree qualifications, fields of study, and preferred educational backgrounds.
"""

import re
from typing import List, Tuple
from jobs.job_schema import EducationRequirements


DEGREE_PATTERNS = [
    (re.compile(r"\b(B\.?Tech(?:nology)?|Bachelor of Technology)\b", re.IGNORECASE), "B.Tech"),
    (re.compile(r"\b(B\.?E\.?|Bachelor of Engineering)\b", re.IGNORECASE), "B.E."),
    (re.compile(r"\b(B\.?S\.?|B\.?Sc\.?|Bachelor of Science)\b", re.IGNORECASE), "B.S."),
    (re.compile(r"\b(B\.?C\.?A\.?|Bachelor of Computer Applications)\b", re.IGNORECASE), "BCA"),
    (re.compile(r"\b(?:bachelor'?s(?:\s+degree)?|undergraduate(?:\s+degree)?)\b", re.IGNORECASE), "Bachelor's Degree"),
    (re.compile(r"\b(M\.?Tech(?:nology)?|Master of Technology)\b", re.IGNORECASE), "M.Tech"),
    (re.compile(r"\b(M\.?E\.?|Master of Engineering)\b", re.IGNORECASE), "M.E."),
    (re.compile(r"\b(M\.?S\.?|M\.?Sc\.?|Master of Science)\b", re.IGNORECASE), "M.S."),
    (re.compile(r"\b(M\.?C\.?A\.?|Master of Computer Applications)\b", re.IGNORECASE), "MCA"),
    (re.compile(r"\b(?:master'?s(?:\s+degree)?|postgraduate(?:\s+degree)?)\b", re.IGNORECASE), "Master's Degree"),
    (re.compile(r"\b(Ph\.?D\.?|Doctorate|Doctor of Philosophy)\b", re.IGNORECASE), "Ph.D."),
    (re.compile(r"\b(Diploma|Associate'?s(?:\s+degree)?)\b", re.IGNORECASE), "Diploma"),
]

FIELDS_OF_STUDY = [
    (re.compile(r"\b(?:computer\s+science|cs)\b", re.IGNORECASE), "Computer Science"),
    (re.compile(r"\b(?:information\s+technology|it)\b", re.IGNORECASE), "Information Technology"),
    (re.compile(r"\b(?:software\s+engineering)\b", re.IGNORECASE), "Software Engineering"),
    (re.compile(r"\b(?:data\s+science)\b", re.IGNORECASE), "Data Science"),
    (re.compile(r"\b(?:electrical|electronics|ece|eee)\b", re.IGNORECASE), "Electrical & Electronics Engineering"),
    (re.compile(r"\b(?:mathematics|math|statistics|stats)\b", re.IGNORECASE), "Mathematics & Statistics"),
    (re.compile(r"\b(?:quantitative\s+field|related\s+technical\s+field)\b", re.IGNORECASE), "Quantitative / Technical Field"),
]


class EducationExtractor:
    """Extracts degree levels and majors from job descriptions."""

    @classmethod
    def extract_education(
        cls,
        qualifications: List[str],
        preferred_qualifications: List[str],
        full_text: str,
    ) -> EducationRequirements:
        """Extracts required and preferred degree requirements and majors."""
        req_degrees = []
        pref_degrees = []
        majors = []
        evidence = None

        # Check preferred qualifications first
        pref_text = "\n".join(preferred_qualifications)
        for pattern, degree_name in DEGREE_PATTERNS:
            if pattern.search(pref_text):
                pref_degrees.append(degree_name)

        # Check required qualifications and full text
        req_text = "\n".join(qualifications)
        target_text = req_text if req_text.strip() else full_text

        for pattern, degree_name in DEGREE_PATTERNS:
            match = pattern.search(target_text)
            if match:
                if degree_name not in pref_degrees and degree_name not in req_degrees:
                    req_degrees.append(degree_name)
                if not evidence:
                    evidence = match.group(0).strip()

        # Check fields of study
        all_text = f"{pref_text}\n{target_text}"
        for pattern, major in FIELDS_OF_STUDY:
            if pattern.search(all_text):
                if major not in majors:
                    majors.append(major)

        return EducationRequirements(
            degree_requirements=list(dict.fromkeys(req_degrees)),
            fields_of_study=list(dict.fromkeys(majors)),
            preferred_education=list(dict.fromkeys(pref_degrees)),
            evidence=evidence,
        )

