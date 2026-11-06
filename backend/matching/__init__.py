# backend/matching/__init__.py
"""
Matching Engine Package for AI Job Search Agent (Phase 7).
"""

from .candidate_embedder import candidate_embedding_service, extract_candidate_skills, extract_candidate_roles
from .skill_matcher import skill_matcher
from .role_matcher import role_matcher
from .eligibility import eligibility_engine
from .scoring import calculate_composite_score
from .explanation import generate_match_explanation
from .matching_service import matching_service

__all__ = [
    "candidate_embedding_service",
    "extract_candidate_skills",
    "extract_candidate_roles",
    "skill_matcher",
    "role_matcher",
    "eligibility_engine",
    "calculate_composite_score",
    "generate_match_explanation",
    "matching_service",
]

