# backend/matching/candidate_embedder.py
"""
Candidate Embedding Service for AI Job Search Agent (Phase 7).
Synthesizes clean, deterministic candidate technical representations and generates
384-dimensional L2-normalized embeddings using the local fine-tuned SBERT model.
Strictly isolates verified skills from inferred skills and preserves role provenance.
"""

import hashlib
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from embeddings.model_loader import get_model
from embeddings.embedding_service import embed_text
from models.candidate import Candidate
from models.candidate_job_match import CandidateEmbedding

logger = logging.getLogger(__name__)

DEFAULT_MODEL_NAME = "fine-tuned-sbert"
EXPECTED_DIMENSIONS = 384


def extract_candidate_skills(profile_dict: Dict[str, Any]) -> Tuple[List[str], List[str], Dict[str, List[str]]]:
    """
    Extracts verified and inferred skills from candidate profile JSON.
    Handles categorized dictionary structure:
    categories: ['programming_languages', 'frameworks', 'databases', 'tools', 'ai_ml', 'other']

    Returns:
        (verified_skills, inferred_skills, skill_sources)
    """
    profile_data = profile_dict.get("profile", profile_dict)
    skills_raw = profile_data.get("skills", {})
    inferred_raw = profile_data.get("inferred_skills", [])
    sources_raw = profile_data.get("skill_sources", {})

    verified_set = set()
    if isinstance(skills_raw, dict):
        for category, skill_list in skills_raw.items():
            if isinstance(skill_list, list):
                for s in skill_list:
                    if s and isinstance(s, str) and s.strip():
                        verified_set.add(s.strip())
            elif isinstance(skill_list, str) and skill_list.strip():
                verified_set.add(skill_list.strip())
    elif isinstance(skills_raw, list):
        for s in skills_raw:
            if isinstance(s, dict):
                name = s.get("canonical_name") or s.get("skill_name") or s.get("name")
                if name:
                    verified_set.add(str(name).strip())
            elif isinstance(s, str) and s.strip():
                verified_set.add(s.strip())

    inferred_set = set()
    if isinstance(inferred_raw, list):
        for s in inferred_raw:
            if s and isinstance(s, str) and s.strip():
                inferred_set.add(s.strip())

    # Ensure verified and inferred do not conflict; verified takes strict precedence
    inferred_set = inferred_set - verified_set

    sorted_verified = sorted(list(verified_set), key=lambda s: s.lower())
    sorted_inferred = sorted(list(inferred_set), key=lambda s: s.lower())

    return sorted_verified, sorted_inferred, sources_raw


def extract_candidate_roles(candidate: Candidate) -> Tuple[List[Dict[str, Any]], str]:
    """
    Extracts career roles according to governance rules:
    1. Confirmed roles take authoritative precedence (source="CONFIRMED").
    2. Missing confirmed roles fallback to top Phase 2 recommendations (source="PROVISIONAL").
    3. If neither exist, returns empty list with source="NO_ROLE_CONTEXT".
    """
    if candidate.confirmed_roles_json:
        try:
            confirmed = json.loads(candidate.confirmed_roles_json)
            if isinstance(confirmed, list) and confirmed:
                return confirmed, "CONFIRMED"
        except Exception as err:
            logger.warning(f"Error parsing confirmed_roles_json for candidate {candidate.id}: {err}")

    # Fallback to Phase 2 recommendations
    if candidate.recommendations_json:
        try:
            recs = json.loads(candidate.recommendations_json)
            rec_list = recs.get("recommendations", []) if isinstance(recs, dict) else recs
            if isinstance(rec_list, list) and rec_list:
                # Return top 3 provisional recommendations
                return rec_list[:3], "PROVISIONAL"
        except Exception as err:
            logger.warning(f"Error parsing recommendations_json for candidate {candidate.id}: {err}")

    return [], "NO_ROLE_CONTEXT"


def build_candidate_semantic_text(candidate: Candidate) -> Tuple[str, str]:
    """
    Constructs a deterministic structured text representation of the candidate profile
    for SBERT embedding. Excludes personal contact data (email, phone, address).

    Returns:
        (deterministic_text, role_context_status)
    """
    profile_dict = {}
    if candidate.profile_json:
        try:
            profile_dict = json.loads(candidate.profile_json)
        except Exception:
            pass

    profile_data = profile_dict.get("profile", profile_dict)
    roles, role_source = extract_candidate_roles(candidate)
    verified_skills, inferred_skills, _ = extract_candidate_skills(profile_dict)

    sections = []

    # 1. Candidate Technical Target & Confirmed Roles
    if roles:
        role_titles = []
        for r in roles:
            title = r.get("role_title") or r.get("title") or r.get("name")
            if title:
                is_custom = r.get("is_custom", False)
                prefix = "[Custom] " if is_custom else ""
                role_titles.append(f"{prefix}{title.strip()}")
        if role_titles:
            sections.append(f"Target Career Roles ({role_source}): {', '.join(role_titles)}")
    else:
        sections.append("Target Career Roles: Software Engineering / Technical Roles (NO_ROLE_CONTEXT)")

    # 2. Verified Technical Skills (Authoritative)
    if verified_skills:
        sections.append(f"Verified Skills: {', '.join(verified_skills)}")

    # 3. Inferred Skills (Contextual only, distinct)
    if inferred_skills:
        sections.append(f"Inferred Contextual Skills: {', '.join(inferred_skills)}")

    # 4. Education
    edu_list = profile_data.get("education", [])
    if isinstance(edu_list, list) and edu_list:
        edu_parts = []
        for edu in edu_list:
            if isinstance(edu, dict):
                deg = edu.get("degree") or "Degree"
                spec = f" in {edu.get('specialization')}" if edu.get("specialization") else ""
                uni = f" from {edu.get('university')}" if edu.get("university") else ""
                edu_parts.append(f"{deg}{spec}{uni}".strip())
        if edu_parts:
            sections.append(f"Education: {'; '.join(edu_parts)}")

    # 5. Key Projects (Technologies & descriptions)
    proj_list = profile_data.get("projects", [])
    if isinstance(proj_list, list) and proj_list:
        proj_parts = []
        for p in proj_list[:4]:
            if isinstance(p, dict):
                name = p.get("name") or "Project"
                techs = p.get("technologies") or []
                desc = p.get("description") or ""
                tech_str = f" [Tech: {', '.join(techs)}]" if techs else ""
                desc_clean = desc.replace("\n", " ").strip()[:200]
                desc_str = f" - {desc_clean}" if desc_clean else ""
                proj_parts.append(f"{name}{tech_str}{desc_str}")
        if proj_parts:
            sections.append(f"Projects:\n" + "\n".join(f"- {p}" for p in proj_parts))

    # 6. Relevant Experience & Internships
    exp_list = profile_data.get("experience", [])
    if isinstance(exp_list, list) and exp_list:
        exp_parts = []
        for exp in exp_list[:3]:
            if isinstance(exp, dict):
                comp = exp.get("company") or "Company"
                title = exp.get("job_title") or "Technical Contributor"
                resp = exp.get("responsibilities") or ""
                resp_clean = resp.replace("\n", " ").strip()[:200]
                exp_parts.append(f"{title} at {comp}: {resp_clean}")
        if exp_parts:
            sections.append(f"Experience:\n" + "\n".join(f"- {e}" for e in exp_parts))

    # 7. Certifications
    certs = profile_data.get("certifications", [])
    if isinstance(certs, list) and certs:
        clean_certs = [c.strip() for c in certs if isinstance(c, str) and c.strip()]
        if clean_certs:
            sections.append(f"Certifications: {', '.join(clean_certs)}")

    if not sections:
        return "Software Developer candidate with technical profile.", role_source

    return "\n\n".join(sections).strip(), role_source


def compute_content_hash(text: str) -> str:
    """Computes a SHA-256 hash of the deterministic candidate text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class CandidateEmbeddingService:
    """
    Generates, tracks, and caches 384-dimensional semantic embeddings for candidates.
    Reuses the existing local fine-tuned SBERT model.
    """

    async def get_or_generate_embedding(
        self,
        db: AsyncSession,
        candidate: Candidate,
        force: bool = False,
    ) -> CandidateEmbedding:
        """
        Retrieves cached candidate embedding or generates a fresh one if content hash changed.
        """
        text, role_source = build_candidate_semantic_text(candidate)
        content_hash = compute_content_hash(text)

        # Check existing embedding directly
        stmt = select(CandidateEmbedding).where(CandidateEmbedding.candidate_id == candidate.id)
        existing = (await db.execute(stmt)).scalar_one_or_none()

        if existing and not force:
            if existing.status == "COMPLETED" and existing.content_hash == content_hash:
                return existing

        try:
            vec = embed_text(text)
            norm = float(np.linalg.norm(vec))
            if norm == 0.0:
                raise ValueError("Embedding returned zero vector")

            if existing is None:
                existing = CandidateEmbedding(
                    candidate_id=candidate.id,
                    model_name=DEFAULT_MODEL_NAME,
                    dimensions=len(vec),
                    content_hash=content_hash,
                    status="COMPLETED",
                    last_error=None,
                )
                existing.set_vector(vec)
                db.add(existing)
            else:
                existing.content_hash = content_hash
                existing.dimensions = len(vec)
                existing.model_name = DEFAULT_MODEL_NAME
                existing.status = "COMPLETED"
                existing.last_error = None
                existing.set_vector(vec)

            await db.commit()
            await db.refresh(existing)
            return existing

        except Exception as err:
            logger.error(f"Error embedding candidate {candidate.id}: {err}")
            if existing is None:
                existing = CandidateEmbedding(
                    candidate_id=candidate.id,
                    model_name=DEFAULT_MODEL_NAME,
                    dimensions=EXPECTED_DIMENSIONS,
                    content_hash=content_hash,
                    status="FAILED",
                    last_error=str(err),
                )
                db.add(existing)
            else:
                existing.status = "FAILED"
                existing.last_error = str(err)

            await db.commit()
            await db.refresh(existing)
            return existing


candidate_embedding_service = CandidateEmbeddingService()

