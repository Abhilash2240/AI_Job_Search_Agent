# backend/matching/eligibility.py
"""
Eligibility & Compatibility Engine for AI Job Search Agent (Phase 7).
Evaluates experience/seniority guardrails, degree alignment, location/remote compatibility,
employment type, and vacancy lifecycle states.
Eligibility determinations are kept distinct from numerical scores.
"""

import json
import re
from typing import Dict, Any, List, Optional, Tuple
from models.canonical_job import CanonicalJob, VacancyStatus
from models.candidate_job_match import EligibilityStatus


DEGREE_EQUIVALENCE: Dict[str, Set_of_terms := List[str]] = {
    "bachelor": ["bachelor", "b.tech", "btech", "b.e.", "be", "b.s.", "bs", "undergraduate"],
    "master": ["master", "m.tech", "mtech", "m.s.", "ms", "postgraduate"],
    "phd": ["phd", "doctorate"],
}

FIELD_EQUIVALENCE: Dict[str, List[str]] = {
    "computer_science": ["computer science", "information technology", "cse", "it", "software engineering", "data science", "computer engineering"],
}


def parse_json_list(val: Any) -> List[str]:
    if not val:
        return []
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
        except Exception:
            parsed = [val]
    else:
        parsed = val
    if isinstance(parsed, list):
        return [str(x).strip() for x in parsed if x and str(x).strip()]
    return []


class EligibilityEngine:
    """
    Evaluates candidate eligibility against job requirements with strict guardrails.
    """

    def evaluate_experience(
        self,
        candidate_exp_years: float,
        candidate_level: str,
        job_min_years: Optional[float],
        job_max_years: Optional[float],
        job_seniority: Optional[str],
        job_title: Optional[str] = None,
    ) -> Tuple[float, Optional[str], bool]:
        """
        Calculates experience score and detects hard seniority disqualifications.
        Returns:
            (experience_score, disqualification_reason, is_disqualified)
        """
        cand_level_norm = (candidate_level or "ENTRY_LEVEL").upper()
        job_level_norm = (job_seniority or "ENTRY_LEVEL").upper()
        t_clean = (job_title or "").lower()

        # Hard guardrail 1: Fresher/Entry-level candidate applying to Senior/Staff/Lead/Manager roles
        if cand_level_norm in {"FRESHER", "ENTRY_LEVEL", "JUNIOR"}:
            senior_title_indicators = [
                "sde iv", "sde 4", "sde iii", "sde 3", "staff engineer", "principal", 
                "lead", "architect", "director", "senior manager", "head of", "senior software engineer"
            ]
            if any(ind in t_clean for ind in senior_title_indicators):
                return (
                    0.0,
                    f"Seniority mismatch: Role '{job_title}' requires senior/staff leadership; candidate is {cand_level_norm} ({candidate_exp_years} yrs).",
                    True,
                )

            if job_level_norm in {"LEAD_STAFF", "DIRECTOR", "PRINCIPAL"} or (job_min_years is not None and job_min_years >= 4.0):
                return (
                    0.0,
                    f"Seniority mismatch: Candidate is {cand_level_norm} ({candidate_exp_years} yrs) while role requires {job_level_norm} ({job_min_years or '4+'} yrs).",
                    True,
                )

        # Hard guardrail 2: Experience deficit vs explicit job minimum
        if job_min_years is not None and job_min_years > 0:
            deficit = job_min_years - candidate_exp_years
            if deficit >= 2.5:
                # Severe deficit (2.5+ years) -> Hard disqualification for freshers
                return (
                    0.0,
                    f"Experience deficit: Role explicitly requires {job_min_years} years; candidate has {candidate_exp_years} years (deficit of {deficit:.2f} yrs).",
                    True,
                )
            elif deficit > 0:
                # Explicit deficit exists (e.g. 0.75 yrs vs 2.0 yrs, deficit = 1.25 yrs) -> Not fully eligible
                score = max(0.10, 1.0 - (deficit / max(job_min_years, 1.0)) * 0.5)
                return (
                    round(score, 4),
                    f"Experience requirement condition: Role explicitly requires {job_min_years} years; candidate has {candidate_exp_years} years (deficit of {deficit:.2f} yrs).",
                    False,
                )
            else:
                # Fully satisfies minimum years
                return (1.0, None, False)

        # If job does not state min experience, evaluate seniority level alignment
        if job_level_norm in {"ENTRY_LEVEL", "FRESHER", "INTERNSHIP"}:
            return (1.0, None, False)
        elif job_level_norm == "MID_LEVEL":
            if cand_level_norm in {"MID_LEVEL", "SENIOR"}:
                return (1.0, None, False)
            else:
                return (0.70, None, False)  # Fresher applying to mid-level
        elif job_level_norm == "SENIOR":
            if cand_level_norm == "SENIOR":
                return (1.0, None, False)
            else:
                return (0.40, None, False)

        return (0.80, None, False)  # Default neutral experience score

    def evaluate_education(
        self,
        candidate_education: List[Dict[str, Any]],
        job_degrees: List[str],
        job_fields: List[str],
    ) -> Tuple[float, str]:
        """
        Evaluates degree level and field of study alignment.
        Returns:
            (education_score, education_status)
        """
        if not job_degrees and not job_fields:
            return (0.85, "NOT_REQUIRED")

        if not candidate_education:
            return (0.40, "UNKNOWN")

        cand_degrees = []
        cand_specs = []
        for edu in candidate_education:
            if isinstance(edu, dict):
                cand_degrees.append((edu.get("degree") or "").lower())
                cand_specs.append((edu.get("specialization") or "").lower())

        degree_matched = False
        if job_degrees:
            for jd in job_degrees:
                jd_lower = jd.lower()
                # Check degree clusters
                for cluster, terms in DEGREE_EQUIVALENCE.items():
                    if any(t in jd_lower for t in terms):
                        if any(any(t in cd for t in terms) for cd in cand_degrees):
                            degree_matched = True
                            break
                if degree_matched:
                    break
        else:
            degree_matched = True  # Degree level not restricted

        field_matched = False
        if job_fields:
            for jf in job_fields:
                jf_lower = jf.lower()
                for cluster, terms in FIELD_EQUIVALENCE.items():
                    if any(t in jf_lower for t in terms):
                        if any(any(t in cs for t in terms) for cs in cand_specs):
                            field_matched = True
                            break
                if field_matched:
                    break
        else:
            field_matched = True

        if degree_matched and field_matched:
            return (1.0, "MATCHED")
        elif degree_matched or field_matched:
            return (0.70, "PARTIAL_MATCH")
        else:
            return (0.30, "MISMATCH")

    def evaluate_location(
        self,
        candidate_location: Optional[str],
        is_job_remote: bool,
        job_location: Optional[str],
        job_city: Optional[str],
        job_country: Optional[str],
    ) -> Tuple[float, str, bool]:
        """
        Evaluates location and remote compatibility.
        Returns:
            (location_score, location_status, is_evaluable)
        """
        # If job is remote, candidate matches universally and location is fully evaluable
        if is_job_remote:
            return (1.0, "REMOTE_ELIGIBLE", True)

        if not candidate_location or not candidate_location.strip():
            # Candidate location missing: Return UNKNOWN, do not award assumed city match, non-evaluable
            return (0.50, "UNKNOWN", False)

        cand_clean = candidate_location.strip().lower()
        job_loc_str = f"{job_location or ''} {job_city or ''} {job_country or ''}".lower()

        if cand_clean in job_loc_str:
            return (1.0, "LOCATION_MATCHED", True)

        # Regional / Country match
        if "india" in cand_clean and "india" in job_loc_str:
            return (0.80, "COUNTRY_MATCHED", True)

        return (0.20, "GEOGRAPHIC_GAP", True)

    def determine_overall_eligibility(
        self,
        job: CanonicalJob,
        is_exp_disqualified: bool,
        exp_reason: Optional[str],
        edu_status: str,
        loc_status: str,
    ) -> Tuple[str, List[str]]:
        """
        Synthesizes component checks into final EligibilityStatus.
        """
        reasons = []

        # 1. Vacancy Lifecycle Status Check
        vac_status = (job.vacancy_status or "ACTIVE").upper()
        if vac_status in {VacancyStatus.CLOSED.value, VacancyStatus.EXPIRED.value, VacancyStatus.BROKEN_LINK.value}:
            return (EligibilityStatus.INELIGIBLE.value, [f"Vacancy is no longer active (status: {vac_status})."])

        if vac_status in {VacancyStatus.BLOCKED.value, VacancyStatus.NEEDS_REVIEW.value, VacancyStatus.UNKNOWN.value}:
            reasons.append(f"Vacancy verification status requires caution ({vac_status}).")

        # 2. Seniority & Experience Checks
        if is_exp_disqualified:
            reasons.append(exp_reason or "Seniority or experience requirement mismatch.")
            return (EligibilityStatus.INELIGIBLE.value, reasons)
        elif exp_reason:
            # Explicit experience deficit exists -> Condition must be flagged!
            reasons.append(exp_reason)

        # 3. Education Check
        if edu_status == "MISMATCH":
            reasons.append("Academic degree or field does not align with stated requirement.")
        elif edu_status == "PARTIAL_MATCH":
            reasons.append("Degree level aligns; specific specialization may need verification.")

        # 4. Location Check
        if loc_status == "GEOGRAPHIC_GAP":
            reasons.append("On-site role located outside candidate's stated geographic region.")
        elif loc_status == "UNKNOWN":
            reasons.append("Candidate location is unspecified; on-site location compatibility requires verification.")

        if reasons:
            return (EligibilityStatus.ELIGIBLE_WITH_CONDITIONS.value, reasons)

        return (EligibilityStatus.ELIGIBLE.value, ["Candidate meets all foundational eligibility criteria."])


eligibility_engine = EligibilityEngine()

