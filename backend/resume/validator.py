import math
import re
from collections import Counter
from typing import List, Tuple
from schemas.candidate import (
    CandidateProfile,
    ValidationResult,
    ValidationStatus,
)

# Common career and professional lexicon terms
CAREER_LEXICON = {
    "education", "experience", "skills", "projects", "work", "university",
    "college", "degree", "bachelor", "master", "phd", "btech", "mtech", "bca", "mca",
    "developer", "engineer", "software", "analyst", "intern", "internship",
    "responsibilities", "technologies", "certifications", "achievements",
    "gpa", "cgpa", "summary", "objective", "employment", "professional",
    "programming", "database", "frontend", "backend", "fullstack", "cloud",
    "machine learning", "data science", "devops", "management", "architecture"
}

# Patterns indicating documents that are NOT individual candidate resumes
NON_RESUME_SIGNATURES = [
    "installation process", "installation guide", "user manual", "setup guide",
    "table of contents", "release notes", "changelog", "system requirements",
    "project report", "lab manual", "practical report", "internship report",
    "college code", "college name", "institution code", "list of colleges",
    "exam timetable", "hall ticket", "admit card", "fee receipt", "invoice",
    "terms and conditions", "privacy policy", "disclaimer", "license agreement",
]

DISQUALIFIED_NAMES = {
    "candidate name not found",
    "project report",
    "college code",
    "college name",
    "table of contents",
    "installation guide",
    "user manual",
    "curriculum vitae",
    "resume",
    "unknown",
}


def calculate_entropy(text: str) -> float:
    """Calculate character-level Shannon entropy of the text."""
    if not text:
        return 0.0
    text_clean = text.lower()
    total_chars = len(text_clean)
    counts = Counter(text_clean)
    entropy = 0.0
    for count in counts.values():
        p = count / total_chars
        entropy -= p * math.log2(p)
    return round(entropy, 3)


def count_career_terms(text: str) -> int:
    """Count occurrences of career lexicon terms in text."""
    text_lower = text.lower()
    matches = 0
    for term in CAREER_LEXICON:
        escaped = re.escape(term)
        if re.search(rf"\b{escaped}\b", text_lower):
            matches += 1
    return matches


def detect_non_resume_signatures(text: str, filename: str = "") -> List[str]:
    """Detect keywords and signatures that identify a non-resume document."""
    reasons = []
    combined = f"{filename} {text[:3500]}".lower()
    for sig in NON_RESUME_SIGNATURES:
        if sig in combined:
            reasons.append(f"Contains non-resume document signature: '{sig}'")
    return reasons


def validate_resume(text: str, profile: CandidateProfile, filename: str = "") -> ValidationResult:
    """
    Classify uploaded document as VALID, INCOMPLETE, or INVALID.
    
    Evaluates:
    1. Text length and Shannon entropy.
    2. Non-resume document signatures (manuals, college lists, project reports).
    3. Career lexicon presence.
    4. Candidate contact & identity validity.
    5. Structural completeness of candidate profile.
    """
    char_count = len(text.strip())
    entropy = calculate_entropy(text)
    career_terms = count_career_terms(text)
    non_resume_hits = detect_non_resume_signatures(text, filename)

    # ── 1. Basic length and emptiness check ──────────────────────────────────
    if char_count < 60:
        return ValidationResult(
            status=ValidationStatus.INVALID,
            reasons=["Document contains insufficient text (fewer than 60 characters)."],
            missing_information=["Full resume text", "Contact details", "Skills", "Education"],
            entropy=entropy,
            career_term_count=career_terms,
            char_count=char_count,
        )

    # ── 2. Low entropy / repetitive gibberish check ────────────────────────────
    if entropy < 2.5:
        return ValidationResult(
            status=ValidationStatus.INVALID,
            reasons=["Document text has unnaturally low entropy, indicating repetitive or corrupted characters."],
            missing_information=["Legible resume content"],
            entropy=entropy,
            career_term_count=career_terms,
            char_count=char_count,
        )

    # Calculate extracted skills count
    total_skills = (
        len(profile.skills.programming_languages)
        + len(profile.skills.frameworks)
        + len(profile.skills.databases)
        + len(profile.skills.tools)
        + len(profile.skills.ai_ml)
        + len(profile.skills.other)
    )

    # ── 3. Domain relevance / Career lexicon check ────────────────────────────
    if career_terms < 2 and total_skills < 2:
        return ValidationResult(
            status=ValidationStatus.INVALID,
            reasons=["Document does not contain standard career or resume terminology (irrelevant non-career document)."],
            missing_information=["Education history", "Professional experience", "Technical skills"],
            entropy=entropy,
            career_term_count=career_terms,
            char_count=char_count,
        )

    # ── 4. Explicit non-resume document detection ─────────────────────────────
    has_contact = bool(profile.personal.email or profile.personal.phone)
    extracted_name = (profile.personal.name or "").strip().lower()
    is_disqualified_name = extracted_name in DISQUALIFIED_NAMES or any(kw in extracted_name for kw in ["report", "college code", "installation", "manual"])

    if non_resume_hits and not has_contact:
        return ValidationResult(
            status=ValidationStatus.INVALID,
            reasons=[
                "Document does not appear to be a candidate resume. " + "; ".join(non_resume_hits[:2]) + ". Please upload a valid resume."
            ],
            missing_information=["Candidate Contact Info", "Candidate Resume Sections"],
            entropy=entropy,
            career_term_count=career_terms,
            char_count=char_count,
        )

    # If the document is large (> 50,000 characters) and has no contact info, it's a book/catalog/list
    if char_count > 50000 and not has_contact:
        return ValidationResult(
            status=ValidationStatus.INVALID,
            reasons=["Document is an institutional catalog or tabular list, not an individual candidate resume."],
            missing_information=["Candidate email address", "Candidate phone number"],
            entropy=entropy,
            career_term_count=career_terms,
            char_count=char_count,
        )

    # If extracted name is a document title and no contact info exists
    if is_disqualified_name and not has_contact:
        return ValidationResult(
            status=ValidationStatus.INVALID,
            reasons=["Document does not appear to be a candidate resume (lacks candidate contact details and valid candidate name)."],
            missing_information=["Candidate Full Name", "Email address", "Phone number"],
            entropy=entropy,
            career_term_count=career_terms,
            char_count=char_count,
        )

    # ── 5. Profile components & completeness ──────────────────────────────────
    has_education = len(profile.education) > 0
    has_experience = len(profile.experience) > 0 or len(profile.internships) > 0
    has_projects = len(profile.projects) > 0

    missing_info = []
    if not profile.personal.email:
        missing_info.append("Email address")
    if not profile.personal.phone:
        missing_info.append("Phone number")
    if not has_education:
        missing_info.append("Education history")
    if total_skills == 0:
        missing_info.append("Technical skills")
    if not has_experience and not has_projects:
        missing_info.append("Work experience or project portfolio")

    # INCOMPLETE scenarios:
    # A) Has skills only, but no education, no experience, and no projects
    if total_skills > 0 and not has_education and not has_experience and not has_projects:
        return ValidationResult(
            status=ValidationStatus.INCOMPLETE,
            reasons=["Resume contains technical skills only, but lacks education, work experience, and project history."],
            missing_information=missing_info,
            entropy=entropy,
            career_term_count=career_terms,
            char_count=char_count,
        )

    # B) Has no education AND no experience AND no projects
    if not has_education and not has_experience and not has_projects:
        return ValidationResult(
            status=ValidationStatus.INCOMPLETE,
            reasons=["Resume lacks essential career background (no education, experience, or projects identified)."],
            missing_information=missing_info,
            entropy=entropy,
            career_term_count=career_terms,
            char_count=char_count,
        )

    # C) Has education or projects or experience, but total skills is zero and missing critical sections
    if total_skills == 0 and not has_experience:
        return ValidationResult(
            status=ValidationStatus.INCOMPLETE,
            reasons=["Resume has minimal information and lacks both verifiable technical skills and professional experience."],
            missing_information=missing_info,
            entropy=entropy,
            career_term_count=career_terms,
            char_count=char_count,
        )

    # ── 6. VALID scenario ─────────────────────────────────────────────────────
    return ValidationResult(
        status=ValidationStatus.VALID,
        reasons=["Document successfully validated as a legitimate career resume with relevant candidate qualifications."],
        missing_information=missing_info,
        entropy=entropy,
        career_term_count=career_terms,
        char_count=char_count,
    )
