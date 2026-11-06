import logging
import re
from typing import List, Dict, Optional, Tuple, Set
import numpy as np

from embeddings.model_loader import get_model
from embeddings.embedding_service import embed_text
from schemas.candidate import CandidateProfile
from schemas.role import (
    CareerRole,
    RoleRecommendation,
    RecommendationsResponse,
    ExperienceLevel,
)
from intelligence.role_catalogue import get_role_catalogue
from intelligence.profile_validator import estimate_years_of_experience, determine_experience_level

logger = logging.getLogger(__name__)

# Configurable hybrid scoring weights
HYBRID_SCORING_WEIGHTS = {
    "semantic_similarity": 0.45,   # Fine-tuned SBERT cosine similarity
    "skill_overlap": 0.35,         # Direct overlap of required and preferred skills
    "project_experience": 0.15,    # Demonstrated project implementation evidence
    "education_alignment": 0.05    # Academic degree and coursework relevance
}

# In-memory cache for precomputed role embeddings
_role_embeddings_cache: Dict[str, np.ndarray] = {}


def aggregate_candidate_skills_with_evidence(profile: CandidateProfile) -> Tuple[Set[str], Dict[str, List[str]]]:
    """Aggregate verified skills from all sections of the candidate profile,
    tracking the source provenance of each skill without inventing qualifications.
    """
    aggregated: Set[str] = set()
    evidence: Dict[str, List[str]] = {}

    def add_skill(skill: str, source: str):
        if not skill or len(skill.strip()) < 2:
            return
        s_clean = skill.strip()
        aggregated.add(s_clean)
        if s_clean not in evidence:
            evidence[s_clean] = []
        if source not in evidence[s_clean]:
            evidence[s_clean].append(source)

    # 1. Direct skills section
    for cat in ["programming_languages", "frameworks", "databases", "tools", "ai_ml", "other"]:
        for s in getattr(profile.skills, cat, []):
            add_skill(s, "skills_section")

    # 2. Education coursework
    for edu in profile.education:
        if edu.specialization:
            add_skill(edu.specialization, "education_degree")

    # 3. Project technologies and descriptions
    for proj in profile.projects:
        source_name = f"project:{proj.name or 'project'}"
        for t in proj.technologies:
            add_skill(t, source_name)
        # Check description for explicit keywords
        desc_lower = (proj.description or "").lower()
        keyword_checks = {
            "fastapi": "FastAPI",
            "django": "Django",
            "flask": "Flask",
            "docker": "Docker",
            "postgresql": "PostgreSQL",
            "redis": "Redis",
            "gemini": "Google Gemini API",
            "google gemini": "Google Gemini API",
            "rag": "RAG",
            "semantic search": "Semantic Search",
            "embeddings": "Embeddings",
            "ai agents": "AI Agents",
            "automated testing": "Automated Testing",
            "unit testing": "Unit Testing",
            "data validation": "Data Validation",
            "data pipeline": "Data Pipelines",
            "object-oriented design": "Object-Oriented Design",
            "data quality": "Data Quality",
            "ocr": "OCR",
        }
        for kw, canon in keyword_checks.items():
            if re.search(rf"\b{re.escape(kw)}\b", desc_lower):
                add_skill(canon, source_name)

    # 4. Experience & Internships
    for exp in profile.experience:
        exp_source = f"experience:{exp.company or 'work'}"
        exp_lower = (exp.responsibilities or "").lower()
        if "machine learning" in exp_lower:
            add_skill("Machine Learning", exp_source)
        if "model evaluation" in exp_lower or "f1-score" in exp_lower or "roc-auc" in exp_lower:
            add_skill("Model Evaluation", exp_source)
        if "testing" in exp_lower:
            add_skill("Automated Testing", exp_source)

    return aggregated, evidence


def build_candidate_semantic_text(profile: CandidateProfile) -> str:
    """Synthesize a structured textual representation of candidate qualifications for SBERT embedding."""
    parts = []

    if profile.personal.name:
        parts.append(f"Candidate: {profile.personal.name}")

    if profile.education:
        edu_strs = []
        for e in profile.education:
            deg = e.degree or "Degree"
            spec = f" in {e.specialization}" if e.specialization else ""
            uni = f" from {e.university}" if e.university else ""
            edu_strs.append(f"{deg}{spec}{uni}".strip())
        if edu_strs:
            parts.append(f"Education: {'; '.join(edu_strs)}.")

    all_skills = []
    for cat in ["programming_languages", "frameworks", "databases", "tools", "ai_ml", "other"]:
        all_skills.extend(getattr(profile.skills, cat, []))
    if all_skills:
        parts.append(f"Technical Skills: {', '.join(all_skills)}.")

    if profile.projects:
        proj_strs = []
        for p in profile.projects[:4]:
            t_str = f" [Technologies: {', '.join(p.technologies)}]" if p.technologies else ""
            desc = f" - {p.description[:250]}" if p.description else ""
            proj_strs.append(f"{p.name or 'Project'}{t_str}{desc}")
        parts.append(f"Key Projects: {' | '.join(proj_strs)}")

    if profile.experience:
        exp_strs = []
        for exp in profile.experience[:3]:
            title = exp.job_title or "Engineer"
            comp = f" at {exp.company}" if exp.company else ""
            resp = f": {exp.responsibilities[:200]}" if exp.responsibilities else ""
            exp_strs.append(f"{title}{comp}{resp}")
        parts.append(f"Experience: {' | '.join(exp_strs)}")

    if not parts:
        return "Software Developer candidate with technical skills."
    return "\n".join(parts)


def build_role_semantic_text(role: CareerRole) -> str:
    """Build comprehensive semantic text for a career role."""
    return (
        f"Role Title: {role.title}.\n"
        f"Description: {role.description}\n"
        f"Required Skills: {', '.join(role.required_skills)}.\n"
        f"Preferred Skills: {', '.join(role.preferred_skills)}."
    )


def get_role_embeddings(roles: List[CareerRole]) -> Dict[str, np.ndarray]:
    """Retrieve or compute unit-normalized SBERT embeddings for all catalogue roles."""
    global _role_embeddings_cache
    for role in roles:
        if role.role_id not in _role_embeddings_cache:
            role_text = build_role_semantic_text(role)
            vec = embed_text(role_text)
            _role_embeddings_cache[role.role_id] = vec
    return _role_embeddings_cache


def calculate_skill_overlap(
    verified_skills: Set[str],
    role: CareerRole
) -> Tuple[float, List[str], List[str]]:
    """Compute verified skill overlap and distinguish present skills from skills not found in resume."""
    verified_lower = {s.lower(): s for s in verified_skills}

    matching_skills: List[str] = []
    missing_skills: List[str] = []

    # Check required skills (70% weight in skill score)
    req_matched = 0
    for r_skill in role.required_skills:
        if r_skill.lower() in verified_lower:
            matching_skills.append(r_skill)
            req_matched += 1
        else:
            missing_skills.append(r_skill)

    # Check preferred skills (30% weight in skill score)
    pref_matched = 0
    for p_skill in role.preferred_skills:
        if p_skill.lower() in verified_lower:
            if p_skill not in matching_skills:
                matching_skills.append(p_skill)
            pref_matched += 1
        else:
            if p_skill not in missing_skills:
                missing_skills.append(p_skill)

    req_score = req_matched / max(1, len(role.required_skills))
    pref_score = pref_matched / max(1, len(role.preferred_skills)) if role.preferred_skills else 1.0

    skill_score = (0.70 * req_score) + (0.30 * pref_score)
    return round(skill_score, 4), matching_skills, missing_skills


def calculate_project_alignment(profile: CandidateProfile, role: CareerRole) -> float:
    """Measure relevance of candidate's project portfolio to the career role."""
    if not profile.projects:
        return 0.5

    all_proj_text = " ".join([f"{p.name} {' '.join(p.technologies)} {p.description}" for p in profile.projects]).lower()

    matches = 0
    for kw in role.domain_keywords:
        if re.search(rf"\b{re.escape(kw)}\b", all_proj_text):
            matches += 1

    ratio = matches / max(1, len(role.domain_keywords))
    return round(min(1.0, 0.4 + (0.6 * ratio)), 4)


def calculate_education_alignment(profile: CandidateProfile, role: CareerRole) -> float:
    """Assess degree relevance to role (e.g. CS degree matching technical software roles)."""
    if not profile.education:
        return 0.5

    all_edu_text = " ".join([f"{e.degree} {e.specialization}" for e in profile.education]).lower()
    if any(k in all_edu_text for k in ["computer science", "software engineering", "information technology", "data science"]):
        return 1.0
    elif any(k in all_edu_text for k in ["engineering", "mathematics", "statistics", "physics"]):
        return 0.8
    return 0.6


def generate_evidence_explanation(
    role: CareerRole,
    matching_skills: List[str],
    missing_skills: List[str],
    composite_score: float,
    semantic_sim: float,
    skill_evidence: Dict[str, List[str]],
    profile: CandidateProfile
) -> str:
    """Generate clear, evidence-based explanation separating verified match from skills not in resume."""
    proj_names = [p.name for p in profile.projects if p.name]
    top_matches = matching_skills[:5]

    evidence_phrases = []
    for s in top_matches:
        sources = skill_evidence.get(s, [])
        clean_sources = [src.split(":")[0].replace("_", " ") for src in sources]
        clean_sources_unique = list(dict.fromkeys(clean_sources))
        if clean_sources_unique:
            evidence_phrases.append(f"{s} ({', '.join(clean_sources_unique[:2])})")
        else:
            evidence_phrases.append(s)

    matched_text = f"Verified alignment on key skills: {', '.join(evidence_phrases)}."
    
    proj_text = ""
    if proj_names:
        proj_text = f" Supported by practical implementations in {', '.join(proj_names[:2])}."

    missing_text = ""
    if missing_skills:
        missing_sample = ", ".join(missing_skills[:3])
        missing_text = f" Role skills not explicitly found in resume: {missing_sample}."

    return (
        f"Overall Match: {composite_score:.1%} (Semantic Similarity: {semantic_sim:.1%}). "
        f"{matched_text}{proj_text}{missing_text}"
    )


def select_alternative_titles(role: CareerRole, exp_level: ExperienceLevel) -> List[str]:
    """Provide experience-level appropriate alternative titles (removing senior titles for freshers)."""
    if exp_level in [ExperienceLevel.FRESHER, ExperienceLevel.ENTRY_LEVEL]:
        return role.alternative_titles_entry
    else:
        return role.alternative_titles_experienced


def recommend_career_roles(
    candidate_id: int,
    profile: CandidateProfile,
    top_n: int = 10,
    weights: Optional[Dict[str, float]] = None
) -> RecommendationsResponse:
    """Compute SBERT embeddings and hybrid match scores, returning transparently ranked career recommendations."""
    scoring_weights = weights or HYBRID_SCORING_WEIGHTS
    w_sem = scoring_weights.get("semantic_similarity", 0.45)
    w_skill = scoring_weights.get("skill_overlap", 0.35)
    w_proj = scoring_weights.get("project_experience", 0.15)
    w_edu = scoring_weights.get("education_alignment", 0.05)

    roles = get_role_catalogue()
    role_embeddings = get_role_embeddings(roles)

    # 1. Aggregate candidate verified skills with source attribution
    verified_skills, skill_evidence = aggregate_candidate_skills_with_evidence(profile)

    # 2. Generate candidate profile embedding
    candidate_text = build_candidate_semantic_text(profile)
    candidate_vec = embed_text(candidate_text)

    years_exp = estimate_years_of_experience(profile)
    exp_level = determine_experience_level(profile, years_exp)

    # 3. Score each role
    scored_roles = []
    edu_score = calculate_education_alignment(profile, roles[0])

    for role in roles:
        r_vec = role_embeddings[role.role_id]
        raw_cosine = float(np.dot(candidate_vec, r_vec))
        semantic_sim = max(0.0, min(1.0, raw_cosine))

        skill_score, matching_skills, missing_skills = calculate_skill_overlap(verified_skills, role)
        proj_score = calculate_project_alignment(profile, role)

        composite_score = (
            (w_sem * semantic_sim) +
            (w_skill * skill_score) +
            (w_proj * proj_score) +
            (w_edu * edu_score)
        )
        composite_score = round(max(0.0, min(1.0, composite_score)), 4)

        # Build evidence map for matching skills
        matched_evidence = {s: skill_evidence.get(s, ["resume"]) for s in matching_skills}

        explanation = generate_evidence_explanation(
            role=role,
            matching_skills=matching_skills,
            missing_skills=missing_skills,
            composite_score=composite_score,
            semantic_sim=semantic_sim,
            skill_evidence=skill_evidence,
            profile=profile
        )

        alt_titles = select_alternative_titles(role, exp_level)

        rec = RoleRecommendation(
            role_id=role.role_id,
            role_title=role.title,
            composite_match_score=composite_score,
            similarity_score=round(semantic_sim, 4),
            skill_match_score=skill_score,
            project_alignment_score=proj_score,
            education_alignment_score=edu_score,
            matching_skills=matching_skills,
            missing_skills=missing_skills,
            skill_evidence=matched_evidence,
            explanation=explanation,
            alternative_titles=alt_titles
        )
        scored_roles.append(rec)

    # 4. Rank by composite match score descending
    scored_roles.sort(key=lambda r: r.composite_match_score, reverse=True)
    top_roles = scored_roles[:top_n]

    return RecommendationsResponse(
        candidate_id=candidate_id,
        candidate_name=profile.personal.name,
        experience_level=exp_level,
        total_recommended=len(top_roles),
        recommendations=top_roles,
        scoring_weights=scoring_weights,
        model_version="fine-tuned-sbert-384d"
    )
