# backend/matching/scoring.py
"""
Composite Scoring & Classification Engine for AI Job Search Agent (Phase 7).
Combines semantic similarity, skill overlap, career-role compatibility, experience,
education, and location into a normalized 0-100 score with score coverage tracking.
"""

from typing import Dict, Any, Tuple
from models.candidate_job_match import MatchClassification, EligibilityStatus

DEFAULT_SCORING_WEIGHTS = {
    "semantic": 0.35,
    "skill": 0.30,
    "role": 0.15,
    "experience": 0.10,
    "education": 0.05,
    "location": 0.05,
}


def calculate_composite_score(
    semantic_score: float,
    skill_score: float,
    role_score: float,
    experience_score: float,
    education_score: float,
    location_score: float,
    weights: Dict[str, float] = None,
    evaluable_flags: Dict[str, bool] = None,
) -> Tuple[float, float, str]:
    """
    Computes weighted composite score (0-100), calculates score coverage,
    and assigns match classification.

    Returns:
        (composite_score_100, score_coverage, match_classification)
    """
    w = weights or DEFAULT_SCORING_WEIGHTS
    flags = evaluable_flags or {k: True for k in w}

    # Normalize components to [0.0, 1.0]
    s_sem = max(0.0, min(1.0, float(semantic_score)))
    s_skl = max(0.0, min(1.0, float(skill_score)))
    s_rol = max(0.0, min(1.0, float(role_score)))
    s_exp = max(0.0, min(1.0, float(experience_score)))
    s_edu = max(0.0, min(1.0, float(education_score)))
    s_loc = max(0.0, min(1.0, float(location_score)))

    # Composite score calculation (0.0 - 1.0)
    raw_composite = (
        w["semantic"] * s_sem
        + w["skill"] * s_skl
        + w["role"] * s_rol
        + w["experience"] * s_exp
        + w["education"] * s_edu
        + w["location"] * s_loc
    )

    composite_score_100 = round(raw_composite * 100.0, 2)

    # Score Coverage: proportion of weight where candidate/job data was evaluable
    evaluable_weight = sum(w[k] for k, is_eval in flags.items() if is_eval and k in w)
    total_weight = sum(w.values())
    score_coverage = round(float(evaluable_weight / total_weight) if total_weight > 0 else 1.0, 4)

    # Classification
    if composite_score_100 >= 70.0:
        classification = MatchClassification.HIGHLY_RECOMMENDED.value
    elif composite_score_100 >= 55.0:
        classification = MatchClassification.RECOMMENDED.value
    elif composite_score_100 >= 40.0:
        classification = MatchClassification.BORDERLINE.value
    else:
        classification = MatchClassification.LOW_COMPATIBILITY.value

    return composite_score_100, score_coverage, classification

