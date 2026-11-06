import pytest
from resume.validator import (
    validate_resume,
    calculate_entropy,
    count_career_terms,
)
from resume.profile_builder import build_candidate_profile
from schemas.candidate import ValidationStatus

VALID_RESUME_TEXT = """
Sarah Jenkins
sarah.jenkins@example.com
(415) 555-0199
San Francisco, CA

PROFESSIONAL SUMMARY
Full Stack Engineer with 4 years of experience building modern cloud applications.

EDUCATION
B.Tech in Computer Science
University of California, Berkeley
Graduated: 2020
GPA: 3.8

SKILLS
Python, JavaScript, TypeScript, React, Node.js, FastAPI, PostgreSQL, Docker, AWS, Git

EXPERIENCE
Software Engineer | Acme Technologies
2020 - Present
Designed and maintained high-throughput REST APIs and microservices.

PROJECTS
Cloud Task Manager
Built real-time task manager using React and FastAPI.
Technologies: Python, React, PostgreSQL
"""

ONLY_SKILLS_TEXT = """
Python, Java, C++, JavaScript, TypeScript, Go, Rust, React, Vue, Angular, Node.js,
Docker, Kubernetes, AWS, GCP, PostgreSQL, MongoDB, Redis, Git, Linux
"""

IRRELEVANT_TEXT = """
The domestic cat is a small, typically carnivorous mammal. It is the only domesticated
species in the family Felidae and is often referred to as the house cat to distinguish
it from the wild members of the family. Shoes and shirts are available for purchase at the mall.
Apples, bananas, and oranges are fresh fruits.
"""

REPETITIVE_GIBBERISH_TEXT = "a " * 100

def test_entropy_calculation():
    # Normal English text usually has entropy between 3.5 and 4.8
    ent_normal = calculate_entropy("This is a sample sentence demonstrating normal character distribution.")
    assert 3.0 < ent_normal < 5.0
    
    # Monotonous repetitive text has low entropy
    ent_low = calculate_entropy("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    assert ent_low < 1.0

def test_validate_valid_resume():
    profile = build_candidate_profile(VALID_RESUME_TEXT)
    result = validate_resume(VALID_RESUME_TEXT, profile)
    assert result.status == ValidationStatus.VALID
    assert len(result.reasons) > 0
    assert result.entropy > 3.0
    assert result.career_term_count >= 5

def test_validate_only_technical_skills():
    profile = build_candidate_profile(ONLY_SKILLS_TEXT)
    result = validate_resume(ONLY_SKILLS_TEXT, profile)
    assert result.status == ValidationStatus.INCOMPLETE
    assert any("only" in r.lower() or "lacks" in r.lower() or "skills" in r.lower() for r in result.reasons)
    assert "Education history" in result.missing_information

def test_validate_irrelevant_document():
    profile = build_candidate_profile(IRRELEVANT_TEXT)
    result = validate_resume(IRRELEVANT_TEXT, profile)
    assert result.status == ValidationStatus.INVALID
    assert any("non-career" in r.lower() or "irrelevant" in r.lower() or "terminology" in r.lower() for r in result.reasons)

def test_validate_low_entropy_gibberish():
    profile = build_candidate_profile(REPETITIVE_GIBBERISH_TEXT)
    result = validate_resume(REPETITIVE_GIBBERISH_TEXT, profile)
    assert result.status == ValidationStatus.INVALID
    assert any("entropy" in r.lower() or "repetitive" in r.lower() for r in result.reasons)

def test_validate_short_text():
    short_text = "Hi my name is Bob"
    profile = build_candidate_profile(short_text)
    result = validate_resume(short_text, profile)
    assert result.status == ValidationStatus.INVALID
    assert any("insufficient text" in r.lower() for r in result.reasons)

def test_profile_completeness_calculation():
    full_profile = build_candidate_profile(VALID_RESUME_TEXT)
    assert full_profile.profile_completeness is not None
    assert full_profile.profile_completeness >= 70.0
    
    sparse_profile = build_candidate_profile(ONLY_SKILLS_TEXT)
    assert sparse_profile.profile_completeness is not None
    assert sparse_profile.profile_completeness < 50.0

