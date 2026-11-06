import re
from typing import Dict, List, Any, Tuple
from schemas.candidate import CandidateProfile, ValidationStatus
from schemas.role import DetailedProfileValidation, ExperienceLevel
from resume.profile_builder import calculate_profile_completeness, audit_profile_completeness, deduplicate_skills, normalize_skill_name


def estimate_years_of_experience(profile: CandidateProfile) -> float:
    """Estimate total years of professional experience from experience entries."""
    if not profile.experience:
        return 0.0
    
    total_months = 0
    year_range_pattern = r"\b(19\d{2}|20\d{2})\s*[-–—to\s]+\s*(19\d{2}|20\d{2}|Present|Current|Ongoing)\b"
    
    for exp in profile.experience:
        duration_text = exp.duration or ""
        match = re.search(year_range_pattern, duration_text, re.IGNORECASE)
        if match:
            start_y = int(match.group(1))
            end_val = match.group(2).lower()
            end_y = 2026 if any(k in end_val for k in ["present", "current", "ongoing"]) else int(match.group(2))
            diff = max(0.5, float(end_y - start_y))
            total_months += diff * 12
        else:
            # Default to 1 year per listed experience entry if duration not explicitly parsed
            total_months += 12
            
    return round(total_months / 12.0, 1)


def determine_experience_level(profile: CandidateProfile, years_exp: float) -> ExperienceLevel:
    """Classify candidate into fresher, entry_level, mid_level, or senior."""
    if years_exp == 0.0:
        return ExperienceLevel.FRESHER
    elif years_exp <= 2.0:
        return ExperienceLevel.ENTRY_LEVEL
    elif years_exp <= 5.0:
        return ExperienceLevel.MID_LEVEL
    else:
        return ExperienceLevel.SENIOR


def validate_candidate_profile_comprehensive(
    candidate_id: int,
    profile: CandidateProfile
) -> DetailedProfileValidation:
    """Comprehensive validation of candidate profile with sectional breakdown,
    warnings, suggestions, and fresher-friendly heuristics.
    """
    warnings: List[str] = []
    suggestions: List[str] = []
    section_analysis: Dict[str, Any] = {}
    
    # 1. Personal Information Section
    personal_issues = []
    if not profile.personal.name:
        personal_issues.append("Candidate name is missing.")
        suggestions.append("Add your full name clearly at the very top of your resume.")
    if not profile.personal.email:
        personal_issues.append("Email address is missing.")
        suggestions.append("Include a professional email address (e.g., name@gmail.com).")
    elif not re.match(r"^[^@]+@[^@]+\.[^@]+$", profile.personal.email):
        personal_issues.append("Email address format appears invalid.")
        warnings.append("Verify your email address syntax.")
    if not profile.personal.phone:
        personal_issues.append("Contact phone number is missing.")
        suggestions.append("Include a phone number with country code for recruiter outreach.")
    if not profile.personal.location:
        personal_issues.append("Location is not specified.")
        suggestions.append("Mention your current city/state or remote preference.")
        
    section_analysis["personal"] = {
        "status": "complete" if not personal_issues else "partial",
        "missing_fields": personal_issues
    }
    
    # 2. Education Section
    edu_issues = []
    if not profile.education:
        edu_issues.append("No degree or university history identified.")
        suggestions.append("Add your education section with your degree, university name, and graduation year.")
    else:
        for idx, edu in enumerate(profile.education):
            if not edu.degree:
                edu_issues.append(f"Education item #{idx+1} is missing degree name.")
            if not edu.university:
                edu_issues.append(f"Education item #{idx+1} is missing university/institution name.")
            if not edu.graduation_year:
                suggestions.append(f"Include your graduation year for {edu.degree or 'your degree'}.")
                
    section_analysis["education"] = {
        "status": "complete" if not edu_issues else "partial",
        "entry_count": len(profile.education),
        "missing_fields": edu_issues
    }
    
    # 3. Skills Analysis & Normalization
    skills_obj = deduplicate_skills(profile.skills)
    total_skills = (
        len(skills_obj.programming_languages) +
        len(skills_obj.frameworks) +
        len(skills_obj.databases) +
        len(skills_obj.tools) +
        len(skills_obj.ai_ml) +
        len(skills_obj.other)
    )
    
    skill_issues = []
    if total_skills == 0:
        skill_issues.append("No technical skills detected in the profile.")
        warnings.append("Your resume does not list recognizable technical skills.")
        suggestions.append("Add an explicit 'Technical Skills' section listing programming languages, tools, and databases.")
    elif total_skills < 4:
        warnings.append(f"Only {total_skills} skills detected. Expanding your skills section will improve job matches.")
        suggestions.append("List key libraries, frameworks, developer tools, and databases you are familiar with.")
        
    section_analysis["skills"] = {
        "status": "complete" if total_skills >= 5 else "partial",
        "total_skills_count": total_skills,
        "breakdown": {
            "programming_languages": skills_obj.programming_languages,
            "frameworks": skills_obj.frameworks,
            "databases": skills_obj.databases,
            "tools": skills_obj.tools,
            "ai_ml": skills_obj.ai_ml,
            "other": skills_obj.other,
        }
    }
    
    # 4. Experience & Internships
    years_exp = estimate_years_of_experience(profile)
    exp_level = determine_experience_level(profile, years_exp)
    
    exp_status = "present" if profile.experience else ("internships_only" if profile.internships else "none")
    if exp_level == ExperienceLevel.FRESHER:
        # Do not penalize freshers!
        if profile.projects:
            suggestions.append("As a fresher, highlight technical metrics, architecture, and live links in your projects.")
        else:
            suggestions.append("Add 2 or 3 detailed software projects to showcase your practical coding abilities.")
    else:
        if not profile.experience:
            warnings.append("No professional work experience detected.")
            
    section_analysis["experience"] = {
        "status": exp_status,
        "years_estimated": years_exp,
        "experience_level": exp_level.value,
        "entry_count": len(profile.experience),
        "internships_count": len(profile.internships)
    }
    
    # 5. Projects Section
    proj_issues = []
    if not profile.projects:
        if exp_level == ExperienceLevel.FRESHER:
            warnings.append("Freshers strongly benefit from a dedicated Projects section demonstrating applied skills.")
        suggestions.append("Add academic or personal projects showing technologies used and problems solved.")
    else:
        for idx, p in enumerate(profile.projects):
            if not p.technologies:
                suggestions.append(f"Explicitly list the tech stack used in project '{p.name or f'#{idx+1}'}'.")
                
    section_analysis["projects"] = {
        "status": "complete" if profile.projects else "missing",
        "count": len(profile.projects)
    }
    
    # 6. Overall Completeness & Validation Status
    completeness, complete_fields, missing_fields, unverified_fields, optional_fields = audit_profile_completeness(profile)
    
    # Freshers with good education, skills, and projects should be VALID
    if total_skills == 0 and not profile.education and not profile.experience:
        val_status = ValidationStatus.INVALID
    elif total_skills < 2 and not profile.experience and not profile.projects:
        val_status = ValidationStatus.INCOMPLETE
    elif not profile.personal.email and not profile.personal.phone and not profile.personal.name:
        val_status = ValidationStatus.INCOMPLETE
    else:
        val_status = ValidationStatus.VALID
        
    return DetailedProfileValidation(
        candidate_id=candidate_id,
        validation_status=val_status,
        completeness_score=completeness,
        experience_level=exp_level,
        years_of_experience_estimated=years_exp,
        warnings=warnings,
        suggestions=suggestions,
        section_analysis=section_analysis,
        complete_fields=complete_fields,
        missing_fields=missing_fields,
        unverified_fields=unverified_fields,
        optional_fields=optional_fields,
    )

