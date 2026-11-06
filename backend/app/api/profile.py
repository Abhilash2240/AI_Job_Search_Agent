import datetime
import json
import logging
import re
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.database import get_db
from models.candidate import Candidate
from schemas.candidate import CandidateProfile, SkillActionRequest
from schemas.role import (
    DetailedProfileValidation,
    RecommendationsResponse,
    ConfirmedRoleItem,
    SaveConfirmedRolesRequest,
    ConfirmedRolesResponse,
    CustomRoleRequest,
)
from intelligence.profile_validator import validate_candidate_profile_comprehensive
from intelligence.role_recommender import recommend_career_roles

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/profile", tags=["Profile & Recommendations"])


async def _get_candidate_or_404(candidate_id: int, db: AsyncSession) -> Candidate:
    stmt = select(Candidate).where(Candidate.id == candidate_id)
    result = await db.execute(stmt)
    candidate = result.scalars().first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate with ID {candidate_id} not found."
        )
    return candidate


@router.get("/{candidate_id}/validation", response_model=DetailedProfileValidation)
async def get_profile_validation(
    candidate_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve in-depth profile validation, completeness score, experience level, warnings, and suggestions."""
    candidate = await _get_candidate_or_404(candidate_id, db)
    
    data = json.loads(candidate.profile_json)
    profile = CandidateProfile(**data["profile"])
    
    detailed_val = validate_candidate_profile_comprehensive(candidate_id, profile)
    return detailed_val


@router.post("/{candidate_id}/recommendations", response_model=RecommendationsResponse)
async def generate_career_recommendations(
    candidate_id: int,
    top_n: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """Generate fine-tuned SBERT semantic career role recommendations for the candidate."""
    candidate = await _get_candidate_or_404(candidate_id, db)
    
    data = json.loads(candidate.profile_json)
    profile = CandidateProfile(**data["profile"])
    
    # Compute SBERT recommendations
    recommendations_resp = recommend_career_roles(candidate_id, profile, top_n=top_n)
    
    # Persist in DB
    candidate.recommendations_json = json.dumps(recommendations_resp.model_dump())
    await db.commit()
    await db.refresh(candidate)
    
    logger.info(f"Generated {len(recommendations_resp.recommendations)} recommendations for candidate_id={candidate_id}")
    return recommendations_resp


@router.get("/{candidate_id}/recommendations", response_model=RecommendationsResponse)
async def get_career_recommendations(
    candidate_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve saved career role recommendations for candidate, or generate them if not yet computed."""
    candidate = await _get_candidate_or_404(candidate_id, db)
    
    if candidate.recommendations_json:
        data = json.loads(candidate.recommendations_json)
        return RecommendationsResponse(**data)
        
    # If not yet generated, generate now
    data = json.loads(candidate.profile_json)
    profile = CandidateProfile(**data["profile"])
    recommendations_resp = recommend_career_roles(candidate_id, profile)
    
    candidate.recommendations_json = json.dumps(recommendations_resp.model_dump())
    await db.commit()
    await db.refresh(candidate)
    
    return recommendations_resp


@router.get("/{candidate_id}/confirmed-roles", response_model=ConfirmedRolesResponse)
async def get_confirmed_roles(
    candidate_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve confirmed / selected career roles for a candidate."""
    candidate = await _get_candidate_or_404(candidate_id, db)
    
    prof_data = json.loads(candidate.profile_json)
    cand_name = prof_data.get("profile", {}).get("personal", {}).get("name")
    
    if not candidate.confirmed_roles_json:
        return ConfirmedRolesResponse(
            candidate_id=candidate.id,
            candidate_name=cand_name,
            confirmed=False,
            confirmed_at=None,
            total_confirmed=0,
            roles=[]
        )
        
    stored_roles = json.loads(candidate.confirmed_roles_json)
    confirmed_iso = candidate.confirmed_at.isoformat() if candidate.confirmed_at else None
    
    return ConfirmedRolesResponse(
        candidate_id=candidate.id,
        candidate_name=cand_name,
        confirmed=True,
        confirmed_at=confirmed_iso,
        total_confirmed=len(stored_roles),
        roles=[ConfirmedRoleItem(**r) for r in stored_roles]
    )


@router.post("/{candidate_id}/confirmed-roles", response_model=ConfirmedRolesResponse)
async def save_confirmed_roles(
    candidate_id: int,
    payload: SaveConfirmedRolesRequest,
    db: AsyncSession = Depends(get_db)
):
    """Confirm and persist selected career roles for a candidate in the backend database."""
    candidate = await _get_candidate_or_404(candidate_id, db)
    
    prof_data = json.loads(candidate.profile_json)
    cand_name = prof_data.get("profile", {}).get("personal", {}).get("name")
    
    # Deduplicate by role_title case-insensitively while preserving order
    seen_titles = set()
    deduped_roles = []
    for r in payload.roles:
        clean_title = r.role_title.strip().lower()
        if clean_title not in seen_titles:
            seen_titles.add(clean_title)
            deduped_roles.append(r.model_dump())
            
    now = datetime.datetime.now(datetime.timezone.utc)
    candidate.confirmed_roles_json = json.dumps(deduped_roles)
    candidate.confirmed_at = now
    
    await db.commit()
    await db.refresh(candidate)
    
    logger.info(f"Candidate {candidate_id} confirmed {len(deduped_roles)} career roles.")
    return ConfirmedRolesResponse(
        candidate_id=candidate.id,
        candidate_name=cand_name,
        confirmed=True,
        confirmed_at=now.isoformat(),
        total_confirmed=len(deduped_roles),
        roles=[ConfirmedRoleItem(**r) for r in deduped_roles]
    )


@router.delete("/{candidate_id}/confirmed-roles/{role_id}", response_model=ConfirmedRolesResponse)
async def delete_confirmed_role(
    candidate_id: int,
    role_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Remove a specific role from the candidate's confirmed list."""
    candidate = await _get_candidate_or_404(candidate_id, db)
    
    prof_data = json.loads(candidate.profile_json)
    cand_name = prof_data.get("profile", {}).get("personal", {}).get("name")
    
    stored = json.loads(candidate.confirmed_roles_json) if candidate.confirmed_roles_json else []
    filtered = [r for r in stored if r["role_id"] != role_id]
    
    candidate.confirmed_roles_json = json.dumps(filtered)
    await db.commit()
    await db.refresh(candidate)
    
    confirmed_iso = candidate.confirmed_at.isoformat() if candidate.confirmed_at else None
    return ConfirmedRolesResponse(
        candidate_id=candidate.id,
        candidate_name=cand_name,
        confirmed=bool(filtered),
        confirmed_at=confirmed_iso,
        total_confirmed=len(filtered),
        roles=[ConfirmedRoleItem(**r) for r in filtered]
    )


@router.post("/{candidate_id}/custom-role", response_model=ConfirmedRoleItem)
async def add_custom_role(
    candidate_id: int,
    custom: CustomRoleRequest,
    db: AsyncSession = Depends(get_db)
):
    """Add a validated custom career role to candidate selections with transparent skill overlap."""
    candidate = await _get_candidate_or_404(candidate_id, db)
    
    prof_data = json.loads(candidate.profile_json)
    profile = CandidateProfile(**prof_data["profile"])
    
    # Calculate skill overlaps for custom role if custom skills provided
    cand_skills_set = set()
    for cat in ["programming_languages", "frameworks", "databases", "tools", "ai_ml", "other"]:
        for s in getattr(profile.skills, cat, []):
            cand_skills_set.add(s.lower())
            
    custom_skills = custom.skills or []
    matching = [s for s in custom_skills if s.lower() in cand_skills_set]
    missing = [s for s in custom_skills if s.lower() not in cand_skills_set]
    
    role_slug = re.sub(r"[^a-z0-9]+", "_", custom.role_title.strip().lower()).strip("_")
    
    custom_item = ConfirmedRoleItem(
        role_id=f"custom_{role_slug}",
        role_title=custom.role_title.strip(),
        is_custom=True,
        custom_description=custom.role_description,
        matching_skills=matching,
        missing_skills=missing,
        alternative_titles=[],
        composite_match_score=None,  # Do not fabricate scores for custom roles
        similarity_score=None
    )
    
    # Retrieve existing confirmed roles and append if not already in list
    stored = json.loads(candidate.confirmed_roles_json) if candidate.confirmed_roles_json else []
    if not any(r["role_title"].strip().lower() == custom_item.role_title.lower() for r in stored):
        stored.append(custom_item.model_dump())
        candidate.confirmed_roles_json = json.dumps(stored)
        if not candidate.confirmed_at:
            candidate.confirmed_at = datetime.datetime.now(datetime.timezone.utc)
        await db.commit()
        await db.refresh(candidate)
        
    return custom_item


@router.post("/{candidate_id}/skills/confirm", response_model=CandidateProfile)
async def confirm_candidate_skill(
    candidate_id: int,
    payload: SkillActionRequest,
    db: AsyncSession = Depends(get_db)
):
    """Confirm an uncertain or inferred skill, moving it to verified candidate skills with tracked provenance."""
    candidate = await _get_candidate_or_404(candidate_id, db)
    prof_data = json.loads(candidate.profile_json)
    profile = CandidateProfile(**prof_data["profile"])
    
    skill_name = payload.skill.strip()
    skill_lower = skill_name.lower()
    
    # Remove from inferred_skills if present
    profile.inferred_skills = [s for s in profile.inferred_skills if s.lower() != skill_lower]
    
    # Target category
    cat = payload.category or "tools"
    if cat not in ["programming_languages", "frameworks", "databases", "tools", "ai_ml", "other"]:
        cat = "tools"
        
    current_list = getattr(profile.skills, cat, [])
    if not any(s.lower() == skill_lower for s in current_list):
        current_list.append(skill_name)
        setattr(profile.skills, cat, sorted(current_list))
        
    # Set provenance
    sources = profile.skill_sources.get(skill_lower, [])
    if "candidate confirmed" not in sources:
        sources.append("candidate confirmed")
    profile.skill_sources[skill_lower] = sources
    
    # Recalculate completeness
    from resume.profile_builder import calculate_profile_completeness
    profile.profile_completeness = calculate_profile_completeness(profile)
    
    prof_data["profile"] = profile.model_dump()
    candidate.profile_json = json.dumps(prof_data)
    await db.commit()
    await db.refresh(candidate)
    
    logger.info(f"Candidate {candidate_id} confirmed skill '{skill_name}' into {cat}.")
    return profile


@router.post("/{candidate_id}/skills/reject", response_model=CandidateProfile)
async def reject_candidate_skill(
    candidate_id: int,
    payload: SkillActionRequest,
    db: AsyncSession = Depends(get_db)
):
    """Reject and remove an unsupported or uncertain skill, immediately updating candidate profile and skill count."""
    candidate = await _get_candidate_or_404(candidate_id, db)
    prof_data = json.loads(candidate.profile_json)
    profile = CandidateProfile(**prof_data["profile"])
    
    skill_name = payload.skill.strip()
    skill_lower = skill_name.lower()
    
    # Remove from inferred_skills
    profile.inferred_skills = [s for s in profile.inferred_skills if s.lower() != skill_lower]
    
    # Remove from all skill categories
    for cat in ["programming_languages", "frameworks", "databases", "tools", "ai_ml", "other"]:
        current_list = getattr(profile.skills, cat, [])
        filtered = [s for s in current_list if s.lower() != skill_lower]
        setattr(profile.skills, cat, filtered)
        
    # Remove from sources
    if skill_lower in profile.skill_sources:
        del profile.skill_sources[skill_lower]
        
    # Recalculate completeness
    from resume.profile_builder import calculate_profile_completeness
    profile.profile_completeness = calculate_profile_completeness(profile)
    
    prof_data["profile"] = profile.model_dump()
    candidate.profile_json = json.dumps(prof_data)
    await db.commit()
    await db.refresh(candidate)
    
    logger.info(f"Candidate {candidate_id} rejected skill '{skill_name}'.")
    return profile

