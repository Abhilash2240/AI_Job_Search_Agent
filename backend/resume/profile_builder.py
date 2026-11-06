from typing import List, Dict, Any, Optional, Tuple
from schemas.candidate import (
    CandidateProfile,
    PersonalInfo,
    EducationItem,
    SkillsCategorized,
    ExperienceItem,
    ProjectItem,
    InternshipItem,
    CertificationItem,
)
from resume.extractor import (
    extract_personal_info,
    extract_skills,
    extract_skills_with_sources,
    extract_education,
    extract_experience,
    extract_projects,
    extract_internships,
    extract_certifications,
    extract_achievements,
    CANONICAL_SKILL_NAMES,
)


def normalize_skill_name(skill: str) -> str:
    """Normalize a skill string to its canonical display form."""
    cleaned = skill.strip()
    return CANONICAL_SKILL_NAMES.get(cleaned.lower(), cleaned)


def deduplicate_skills(skills_obj: SkillsCategorized) -> SkillsCategorized:
    """Ensure uniqueness of skills in each category and across categories."""
    seen = set()
    deduped = {}
    
    for category in ["programming_languages", "frameworks", "databases", "tools", "ai_ml", "other"]:
        raw_list = getattr(skills_obj, category, [])
        cat_deduped = []
        for s in raw_list:
            norm = normalize_skill_name(s)
            if norm.lower() not in seen:
                seen.add(norm.lower())
                cat_deduped.append(norm)
        deduped[category] = cat_deduped

    return SkillsCategorized(**deduped)


def audit_profile_completeness(profile: CandidateProfile) -> Tuple[float, List[str], List[str], List[str], List[str]]:
    """Audit profile completeness with strict differentiation between complete, missing, unverified, and optional fields.
    
    Returns:
        (completeness_score, complete_fields, missing_fields, unverified_fields, optional_fields)
        
    Guarantees:
    - Never awards 100% completeness if required information is absent.
    - Accurately identifies missing fields like Location, Job Title, or Project Tech Stacks.
    """
    score = 0.0
    complete_fields = []
    missing_fields = []
    unverified_fields = []
    optional_fields = []
    
    # 1. Personal Information (20% total, 5% each)
    if profile.personal.name and len(profile.personal.name.strip()) >= 2:
        score += 5.0
        complete_fields.append("Full Name")
    else:
        missing_fields.append("Full Name")
        
    if profile.personal.email and "@" in profile.personal.email:
        score += 5.0
        complete_fields.append("Email Address")
    else:
        missing_fields.append("Email Address")
        
    if profile.personal.phone and len(profile.personal.phone.strip()) >= 7:
        score += 5.0
        complete_fields.append("Phone Number")
    else:
        missing_fields.append("Phone Number")
        
    if profile.personal.location and len(profile.personal.location.strip()) >= 3:
        score += 5.0
        complete_fields.append("Personal Geographic Location")
    else:
        missing_fields.append("Personal Geographic Location")

    # 2. Education (25% total)
    if profile.education and len(profile.education) > 0:
        has_primary = any(e.degree and e.university for e in profile.education)
        if has_primary:
            score += 15.0
            complete_fields.append("Degree & University")
        else:
            score += 8.0
            unverified_fields.append("Incomplete Degree or University Details")
            
        has_years = any(e.graduation_year or (e.start_year and e.end_year) for e in profile.education)
        if has_years:
            score += 5.0
            complete_fields.append("Graduation / Batch Years")
        else:
            missing_fields.append("Graduation Year")
            
        has_cgpa = any(bool(e.academic_performance) for e in profile.education)
        if has_cgpa:
            score += 5.0
            complete_fields.append("Academic Performance / CGPA")
        else:
            optional_fields.append("Academic Performance / CGPA")
    else:
        missing_fields.append("Education History")

    # 3. Verified Technical Skills (25% total)
    total_skills = (
        len(profile.skills.programming_languages) +
        len(profile.skills.frameworks) +
        len(profile.skills.databases) +
        len(profile.skills.tools) +
        len(profile.skills.ai_ml) +
        len(profile.skills.other)
    )
    if total_skills >= 8:
        score += 25.0
        complete_fields.append(f"Verified Technical Skills ({total_skills} verified)")
    elif total_skills >= 4:
        score += 16.0
        unverified_fields.append(f"Moderate Skills Breadth ({total_skills} skills)")
    elif total_skills >= 1:
        score += 8.0
        unverified_fields.append(f"Limited Skills Breadth ({total_skills} skills)")
    else:
        missing_fields.append("Technical Skills Section")

    # 4. Verified Projects (15% total)
    if profile.projects and len(profile.projects) >= 2:
        has_complete_projects = all(p.name and (p.technologies or p.description) for p in profile.projects)
        if has_complete_projects:
            score += 15.0
            complete_fields.append(f"Engineered Projects ({len(profile.projects)} projects)")
        else:
            score += 10.0
            unverified_fields.append("Projects missing explicit tech stack")
    elif profile.projects and len(profile.projects) == 1:
        score += 10.0
        complete_fields.append("Single Project Listed")
    else:
        missing_fields.append("Technical Projects")

    # 5. Experience / Internships (10% total)
    has_full_exp = any(e.company and e.job_title for e in profile.experience)
    has_any_exp = bool(profile.experience or profile.internships)
    if has_full_exp:
        score += 10.0
        complete_fields.append("Professional Work Experience")
    elif has_any_exp:
        # Partial experience entry (e.g. participant/open-source without formal title)
        score += 5.0
        unverified_fields.append("Experience missing formal Job Title or Duration")
    else:
        optional_fields.append("Professional Work Experience (Fresher Profile)")

    # 6. Certifications & Achievements (5% total)
    if profile.certifications or profile.achievements:
        score += 5.0
        complete_fields.append("Certifications / Achievements")
    else:
        optional_fields.append("Certifications & Extra-Curricular Achievements")

    final_score = min(100.0, round(score, 1))
    return final_score, complete_fields, missing_fields, unverified_fields, optional_fields


def calculate_profile_completeness(profile: CandidateProfile) -> float:
    """Calculate profile completeness score as a percentage between 0 and 100."""
    score, _, _, _, _ = audit_profile_completeness(profile)
    return score


def build_candidate_profile(text: str) -> CandidateProfile:
    """Extract, normalize, and construct structured candidate profile from text with strict provenance."""
    personal = extract_personal_info(text)
    education = extract_education(text)
    experience = extract_experience(text)
    projects = extract_projects(text)
    internships = extract_internships(text)
    certifications = extract_certifications(text)
    achievements = extract_achievements(text)
    
    # Extract verified skills with evidence source tracking
    raw_skills, skill_sources, inferred_skills = extract_skills_with_sources(
        text=text,
        projects=projects,
        experience=experience,
        education=education,
        certifications=certifications
    )
    skills = deduplicate_skills(raw_skills)
    
    profile = CandidateProfile(
        personal=personal,
        education=education,
        skills=skills,
        skill_sources=skill_sources,
        inferred_skills=inferred_skills,
        experience=experience,
        projects=projects,
        internships=internships,
        certifications=certifications,
        achievements=achievements,
        profile_completeness=None
    )
    
    profile.profile_completeness = calculate_profile_completeness(profile)
    return profile

