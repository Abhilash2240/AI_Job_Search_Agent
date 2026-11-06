# backend/matching/explanation.py
"""
Explanation Engine for AI Job Search Agent (Phase 7).
Generates transparent, evidence-based natural language explanations for match recommendations.
Synthesizes verified skills, missing requirements, career roles, experience, and eligibility.
"""

from typing import Dict, Any, List


def generate_match_explanation(
    canonical_job_title: str,
    company_name: str,
    composite_score: float,
    match_classification: str,
    matched_role_title: str,
    role_source: str,
    matched_skills: List[Dict[str, Any]],
    missing_required_skills: List[str],
    missing_preferred_skills: List[str],
    inferred_skills: List[Dict[str, Any]],
    eligibility_status: str,
    eligibility_reasons: List[str],
    experience_status: str,
    education_status: str,
    location_status: str,
) -> str:
    """
    Constructs an evidence-backed narrative explaining the match and flagging any concerns.
    """
    sentences = []

    # 1. Headline summary
    if matched_role_title:
        role_note = f" (confirmed preference)" if role_source == "CONFIRMED" else " (provisional preference)"
        sentences.append(
            f"The vacancy '{canonical_job_title}' at {company_name} aligns with the candidate's target role '{matched_role_title}'{role_note} "
            f"with an overall match score of {composite_score:.1f}/100 ({match_classification.replace('_', ' ')})."
        )
    else:
        sentences.append(
            f"The vacancy '{canonical_job_title}' at {company_name} was evaluated with an overall match score of {composite_score:.1f}/100."
        )

    # 2. Verified Skill Alignment
    if matched_skills:
        skill_names = [s["canonical_name"] for s in matched_skills]
        evidence_sample = matched_skills[0].get("candidate_evidence", ["resume"])[0]
        sentences.append(
            f"Verified candidate competencies matched key requirements: {', '.join(skill_names[:5])} (e.g. demonstrated in {evidence_sample})."
        )
    else:
        sentences.append("None of the explicit skill requirements were proven in the verified candidate profile.")

    # 3. Missing Skills / Gaps
    if missing_required_skills:
        sentences.append(
            f"Key required skills not yet confirmed in profile: {', '.join(missing_required_skills[:4])}."
        )
    elif not matched_skills and not missing_required_skills:
        sentences.append("The vacancy description did not state explicit technical skill requirements.")

    # 4. Inferred Skills Context (if any)
    if inferred_skills:
        inferred_names = [s["candidate_inferred_skill"] for s in inferred_skills]
        sentences.append(
            f"Contextual skills identified for verification: {', '.join(inferred_names[:3])}."
        )

    # 5. Experience & Seniority
    if "Seniority mismatch" in " ".join(eligibility_reasons):
        sentences.append("Caution: Seniority mismatch detected between candidate level and job requirements.")
    elif experience_status == "SATISFIED":
        sentences.append("Candidate experience satisfies the stated minimum years.")

    # 6. Location & Workplace
    if location_status == "REMOTE_ELIGIBLE":
        sentences.append("This role is eligible for remote work.")
    elif location_status == "LOCATION_MATCHED":
        sentences.append("The job location matches the candidate's geographic preference.")
    elif location_status in {"UNKNOWN", "UNSPECIFIED_CANDIDATE_LOCATION"}:
        sentences.append("Candidate location is unspecified; on-site location compatibility is unknown and not counted as evaluated evidence.")

    # 7. Final Eligibility Statement
    if eligibility_status == "INELIGIBLE":
        reasons_str = "; ".join(eligibility_reasons)
        sentences.append(f"Eligibility Alert: Role is classified as INELIGIBLE ({reasons_str}).")
    elif eligibility_status == "ELIGIBLE_WITH_CONDITIONS":
        reasons_str = "; ".join(eligibility_reasons)
        sentences.append(f"Eligibility note: {reasons_str}.")

    return " ".join(sentences)

