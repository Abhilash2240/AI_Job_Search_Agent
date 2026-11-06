"""
Lightweight Candidate Role Relevance Classifier (Phase 5).
Evaluates canonical vacancy relevance against confirmed candidate roles
and verified skill profiles using keyword & title token alignment.
Kept strictly separate from deduplication and fine-tuned SBERT embeddings.
"""

from typing import Any, Dict, List, Optional, Set
import re


class RoleRelevanceClassifier:
    """Lightweight rule-based role classifier for candidate job filtering."""

    @classmethod
    def evaluate_relevance(
        cls,
        canonical_title: str,
        job_skills: List[Dict[str, Any]],
        confirmed_roles: List[str],
        candidate_skills: List[str],
    ) -> Dict[str, Any]:
        """
        Calculates a transparent relevance score [0.0 - 1.0] for a candidate's confirmed roles.
        Does not discard non-matching vacancies.
        """
        if not confirmed_roles:
            return {
                "is_relevant": True,
                "relevance_score": 0.5,
                "matching_roles": [],
                "matching_skills": [],
                "reason": "no_confirmed_roles_specified_all_visible",
            }

        # 1. Title Token Overlap with Confirmed Roles
        title_tokens = set(re.findall(r"\b[a-zA-Z0-9+#.]{2,}\b", canonical_title.lower()))
        matched_roles = []

        for role in confirmed_roles:
            role_tokens = set(re.findall(r"\b[a-zA-Z0-9+#.]{2,}\b", role.lower()))
            overlap = title_tokens.intersection(role_tokens)
            # If at least 50% of the confirmed role words match or core archetype matches
            if len(overlap) >= max(1, len(role_tokens) * 0.5):
                matched_roles.append(role)

        title_match_score = 0.6 if matched_roles else 0.0

        # 2. Skill Overlap
        cand_skills_lower = {s.lower().strip() for s in candidate_skills if s}
        job_skills_lower = set()

        for s in job_skills:
            if isinstance(s, dict):
                name = s.get("canonical_name") or s.get("skill_name") or s.get("name") or ""
                if name:
                    job_skills_lower.add(name.lower().strip())
            elif isinstance(s, str):
                job_skills_lower.add(s.lower().strip())

        matched_skills = list(cand_skills_lower.intersection(job_skills_lower))
        skill_score = min(0.4, len(matched_skills) * 0.1)

        total_score = round(title_match_score + skill_score, 2)
        is_relevant = total_score >= 0.40

        return {
            "is_relevant": is_relevant,
            "relevance_score": total_score,
            "matching_roles": matched_roles,
            "matching_skills": matched_skills,
            "reason": f"matched_{len(matched_roles)}_roles_and_{len(matched_skills)}_skills",
        }

