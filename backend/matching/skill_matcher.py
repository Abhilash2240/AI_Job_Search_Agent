# backend/matching/skill_matcher.py
"""
Skill Matching Service for AI Job Search Agent (Phase 7).
Compares verified candidate skills against required and preferred job skills.
Supports exact matching, case normalization, and approved skill aliases.
Strictly separates verified candidate competencies from unverified inferred skills.
"""

import json
import re
from typing import Dict, Any, List, Set, Tuple, Optional

# Approved exact technological aliases (strictly non-contradictory)
SKILL_ALIASES: Dict[str, str] = {
    # Cloud & DevOps
    "amazon web services": "AWS",
    "aws": "AWS",
    "gcp": "Google Cloud Platform",
    "google cloud": "Google Cloud Platform",
    "google cloud platform": "Google Cloud Platform",
    "azure": "Azure",
    "microsoft azure": "Azure",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "docker": "Docker",
    # Databases
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "mongo": "MongoDB",
    "mongodb": "MongoDB",
    "ms sql": "Microsoft SQL Server",
    "mssql": "Microsoft SQL Server",
    "mysql": "MySQL",
    "redis": "Redis",
    "supabase": "Supabase",
    # Languages & Frameworks
    "python": "Python",
    "python3": "Python",
    "py": "Python",
    "golang": "Go",
    "go": "Go",
    "js": "JavaScript",
    "javascript": "JavaScript",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "node": "Node.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "express": "Express.js",
    "expressjs": "Express.js",
    "express.js": "Express.js",
    "react": "React",
    "reactjs": "React",
    "react.js": "React",
    # AI / ML
    "gemini": "Google Gemini API",
    "gemini api": "Google Gemini API",
    "google gemini": "Google Gemini API",
    "google gemini api": "Google Gemini API",
    "llm": "LLMs",
    "llms": "LLMs",
    "large language models": "LLMs",
    "machine learning": "Machine Learning",
    "ml": "Machine Learning",
    "rag": "RAG",
    "retrieval-augmented generation": "RAG",
    "semantic search": "Semantic Search",
    "embeddings": "Embeddings",
    "ai agents": "AI Agents",
    # Methodologies & Tools
    "git": "Git",
    "github": "GitHub",
    "rest": "REST APIs",
    "rest api": "REST APIs",
    "rest apis": "REST APIs",
    "restful": "REST APIs",
    "unit test": "Unit Testing",
    "unit testing": "Unit Testing",
    "automated testing": "Automated Testing",
    "ci/cd": "CI/CD",
    "cicd": "CI/CD",
    "data pipeline": "Data Pipelines",
    "data pipelines": "Data Pipelines",
    "sql": "SQL",
    "jwt": "JWT",
    "json web token": "JWT",
    "linux": "Linux",
    "bash": "Bash",
    "shell": "Bash",
}


def canonicalize_skill(skill_name: Optional[str]) -> str:
    """Normalizes skill name using approved aliases or title-case fallback."""
    if not skill_name:
        return ""
    clean = skill_name.strip()
    lower = clean.lower()
    return SKILL_ALIASES.get(lower, clean)


def parse_job_skills(skills_field: Any) -> List[Dict[str, Any]]:
    """Parses JSON string or list of job skills into uniform dictionaries."""
    if not skills_field:
        return []
    parsed = skills_field
    if isinstance(skills_field, str):
        try:
            parsed = json.loads(skills_field)
        except Exception:
            parsed = [skills_field]

    result = []
    if isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, dict):
                name = item.get("canonical_name") or item.get("skill_name") or item.get("name")
                if name:
                    canon = canonicalize_skill(str(name))
                    result.append({
                        "skill_name": str(name).strip(),
                        "canonical_name": canon,
                        "category": item.get("category", "General"),
                        "evidence_snippet": item.get("evidence_snippet", ""),
                        "is_required": item.get("is_required", True),
                    })
            elif isinstance(item, str) and item.strip():
                canon = canonicalize_skill(item)
                result.append({
                    "skill_name": item.strip(),
                    "canonical_name": canon,
                    "category": "General",
                    "evidence_snippet": "",
                    "is_required": True,
                })
    return result


class SkillMatcher:
    """
    Evaluates skill compatibility with strict provenance preservation.
    Only verified candidate skills contribute to positive coverage scores.
    """

    def evaluate_skills(
        self,
        verified_skills: List[str],
        inferred_skills: List[str],
        skill_sources: Dict[str, List[str]],
        job_required_skills: Any,
        job_preferred_skills: Any,
    ) -> Dict[str, Any]:
        """
        Calculates required and preferred skill coverage and identifies gaps.
        """
        parsed_required = parse_job_skills(job_required_skills)
        parsed_preferred = parse_job_skills(job_preferred_skills)

        # Build lookup set for verified skills
        verified_map: Dict[str, str] = {}  # canonical lower -> original display name
        for s in verified_skills:
            canon = canonicalize_skill(s)
            verified_map[canon.lower()] = s

        inferred_map: Dict[str, str] = {}
        for s in inferred_skills:
            canon = canonicalize_skill(s)
            inferred_map[canon.lower()] = s

        # 1. Match Required Skills
        matched_required: List[Dict[str, Any]] = []
        missing_required: List[str] = []
        for req in parsed_required:
            canon_lower = req["canonical_name"].lower()
            if canon_lower in verified_map:
                original_name = verified_map[canon_lower]
                # Lookup evidence
                evidence = skill_sources.get(original_name.lower(), ["verified candidate profile"])
                matched_required.append({
                    "skill_name": req["skill_name"],
                    "canonical_name": req["canonical_name"],
                    "candidate_evidence": evidence,
                    "is_verified": True,
                })
            else:
                missing_required.append(req["canonical_name"])

        # 2. Match Preferred Skills
        matched_preferred: List[Dict[str, Any]] = []
        missing_preferred: List[str] = []
        for pref in parsed_preferred:
            canon_lower = pref["canonical_name"].lower()
            if canon_lower in verified_map:
                original_name = verified_map[canon_lower]
                evidence = skill_sources.get(original_name.lower(), ["verified candidate profile"])
                matched_preferred.append({
                    "skill_name": pref["skill_name"],
                    "canonical_name": pref["canonical_name"],
                    "candidate_evidence": evidence,
                    "is_verified": True,
                })
            else:
                missing_preferred.append(pref["canonical_name"])

        # 3. Identify Inferred Potential Overlaps (strictly excluded from positive score)
        inferred_overlap: List[Dict[str, Any]] = []
        for missing_name in (missing_required + missing_preferred):
            canon_lower = canonicalize_skill(missing_name).lower()
            if canon_lower in inferred_map:
                inferred_overlap.append({
                    "skill_name": missing_name,
                    "candidate_inferred_skill": inferred_map[canon_lower],
                    "note": "Potential skill to verify; not counted as confirmed competence.",
                })

        # 4. Coverage Calculations
        total_req = len(parsed_required)
        total_pref = len(parsed_preferred)

        if total_req > 0:
            req_coverage = len(matched_required) / total_req
        else:
            req_coverage = 0.0

        if total_pref > 0:
            pref_coverage = len(matched_preferred) / total_pref
            pref_evaluable = True
        else:
            # Vacancy lists no preferred skills: explicitly 0.0 coverage; no unearned points awarded
            pref_coverage = 0.0
            pref_evaluable = False

        # Strictly apply the agreed formula:
        # Skill score = 0.75 * required coverage + 0.25 * preferred coverage
        skill_score = 0.75 * req_coverage + 0.25 * pref_coverage

        is_evaluable = (total_req > 0 or total_pref > 0)

        return {
            "skill_score": round(float(skill_score), 4),
            "required_coverage": round(float(req_coverage), 4),
            "preferred_coverage": round(float(pref_coverage), 4),
            "total_required": total_req,
            "total_preferred": total_pref,
            "matched_required": matched_required,
            "missing_required": missing_required,
            "matched_preferred": matched_preferred,
            "missing_preferred": missing_preferred,
            "inferred_overlap": inferred_overlap,
            "is_evaluable": is_evaluable,
        }


skill_matcher = SkillMatcher()

