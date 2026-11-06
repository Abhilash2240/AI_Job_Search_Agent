# backend/matching/role_matcher.py
"""
Career-Role Compatibility Service for AI Job Search Agent (Phase 7).
Matches canonical job titles against candidate-confirmed career roles or provisional recommendations.
Evaluates semantic token overlap, role title synonyms, and domain alignment.
"""

import re
from typing import Dict, Any, List, Tuple, Optional

# Synonyms and domain clusters for role title matching
ROLE_CLUSTERS: Dict[str, Set_of_terms := List[str]] = {
    "backend": ["backend", "api", "server", "python", "java", "node", "django", "fastapi", "golang", "microservices"],
    "frontend": ["frontend", "react", "ui", "ux", "web", "javascript", "typescript", "angular", "vue"],
    "fullstack": ["fullstack", "full stack", "software engineer", "developer", "swe", "sde"],
    "data_engineering": ["data engineer", "etl", "pipeline", "spark", "hadoop", "sql", "warehouse"],
    "ai_ml": ["machine learning", "ai", "data scientist", "nlp", "deep learning", "cv", "vision", "agent"],
    "security": ["security", "threat detection", "infosec", "cyber", "soc", "penetration", "secops"],
    "devops": ["devops", "sre", "reliability", "infrastructure", "platform", "cloud", "aws", "kubernetes"],
    "non_technical": ["relationship manager", "procurement", "collection", "writer", "editor", "compliance", "sales", "hr", "operations"],
}


def tokenize_title(title: str) -> List[str]:
    """Tokenizes and cleans a job title string into non-stopword tokens."""
    if not title:
        return []
    clean = re.sub(r"[^a-zA-Z0-9\s]", " ", title.lower())
    tokens = [t for t in clean.split() if len(t) > 1 and t not in {"and", "or", "the", "in", "for", "at", "to", "of", "a", "an", "on", "from"}]
    return tokens


class RoleMatcher:
    """
    Evaluates alignment between candidate target career roles and canonical job titles.
    """

    def evaluate_role_compatibility(
        self,
        candidate_roles: List[Dict[str, Any]],
        role_source: str,
        canonical_title: str,
        job_title: str,
    ) -> Dict[str, Any]:
        """
        Determines the best matching career role and computes compatibility score.
        """
        if not candidate_roles or role_source == "NO_ROLE_CONTEXT":
            return {
                "role_score": 0.40,  # Neutral baseline for missing role preference
                "best_matching_role": None,
                "role_source": "UNKNOWN",
                "evidence": "Candidate has not confirmed career preferences; neutral role compatibility applied.",
                "is_evaluable": False,
            }

        job_tokens = set(tokenize_title(canonical_title) + tokenize_title(job_title))
        best_score = 0.0
        best_role_title = candidate_roles[0].get("role_title") or "Software Engineer"
        best_match_reason = "General engineering profile alignment"

        # Check for explicitly non-technical domain in canonical job title
        is_job_non_tech = any(nt in canonical_title.lower() for nt in ROLE_CLUSTERS["non_technical"])

        for role in candidate_roles:
            title = role.get("role_title") or role.get("title") or ""
            if not title:
                continue

            alt_titles = role.get("alternative_titles") or []
            cand_role_titles = [title] + alt_titles

            for cand_title in cand_role_titles:
                cand_tokens = set(tokenize_title(cand_title))
                if not cand_tokens or not job_tokens:
                    continue

                # Jaccard Token Overlap
                overlap = cand_tokens.intersection(job_tokens)
                union = cand_tokens.union(job_tokens)
                jaccard = len(overlap) / len(union) if union else 0.0

                # Domain cluster alignment
                cluster_boost = 0.0
                for cluster_name, keywords in ROLE_CLUSTERS.items():
                    cand_in_cluster = any(k in cand_title.lower() for k in keywords)
                    job_in_cluster = any(k in canonical_title.lower() for k in keywords)
                    if cand_in_cluster and job_in_cluster:
                        cluster_boost = 0.35
                        break

                current_score = min(1.0, (jaccard * 0.70) + cluster_boost)

                # Special boost for exact substring or exact match
                if cand_title.lower() in canonical_title.lower() or canonical_title.lower() in cand_title.lower():
                    current_score = max(current_score, 0.90)

                if current_score > best_score:
                    best_score = current_score
                    best_role_title = title
                    matched_terms = ", ".join(overlap) if overlap else "domain cluster alignment"
                    best_match_reason = f"Aligned with '{title}' via {matched_terms}"

        # If the job is explicitly non-technical and candidate is a software/tech role, apply strong penalty
        if is_job_non_tech and best_score < 0.6:
            best_score = min(best_score, 0.15)
            best_match_reason = f"Role domain mismatch: job '{canonical_title}' is non-technical while target role is '{best_role_title}'"

        # Scale score according to confidence of role source
        # CONFIRMED roles get full scale; PROVISIONAL roles get 0.85x multiplier
        multiplier = 1.0 if role_source == "CONFIRMED" else 0.85
        final_score = round(float(min(1.0, best_score * multiplier)), 4)

        return {
            "role_score": final_score,
            "best_matching_role": best_role_title,
            "role_source": role_source,
            "evidence": best_match_reason,
            "is_evaluable": True,
        }


role_matcher = RoleMatcher()

