import pytest
from resume.extractor import (
    extract_personal_info,
    extract_skills,
    extract_education,
    extract_experience,
    extract_projects,
    extract_certifications,
)
from resume.profile_builder import (
    build_candidate_profile,
    deduplicate_skills,
)

SAMPLE_RESUME = """
Alex Mercer
alex.mercer@example.com
(555) 234-5678
San Francisco, CA

SUMMARY
Senior Software Engineer with 5+ years of experience building high-scale distributed backend systems.

EDUCATION
B.Tech in Computer Science and Engineering
Stanford University
2018 - 2022
GPA: 3.9/4.0

SKILLS
Programming Languages: Python, Go, TypeScript, C++, python
Frameworks: React, FastAPI, Django, Node.js
Databases: PostgreSQL, Redis, MongoDB
Tools: Docker, Kubernetes, AWS, Git, CI/CD
AI & ML: PyTorch, Scikit-Learn, Sentence-Transformers, Hugging Face

WORK EXPERIENCE
Senior Backend Developer
Stripe
Jan 2022 - Present
Built low-latency payment processing pipelines handling 10k TPS.

PROJECTS
Job Match AI
Built an intelligent job matching platform with FastAPI and PyTorch.
Technologies: Python, PyTorch, PostgreSQL, Docker

CERTIFICATIONS
AWS Certified Solutions Architect
Amazon Web Services
2023
"""

def test_extract_personal_info():
    personal = extract_personal_info(SAMPLE_RESUME)
    assert personal.name == "Alex Mercer"
    assert personal.email == "alex.mercer@example.com"
    assert personal.phone is not None and "555" in personal.phone
    assert personal.location == "San Francisco, CA"

def test_missing_contact_info():
    text = "Software Engineer with experience in Python and Docker.\nEDUCATION\nB.Tech"
    personal = extract_personal_info(text)
    assert personal.email is None
    assert personal.phone is None

def test_extract_skills_categorized():
    skills = extract_skills(SAMPLE_RESUME)
    assert "Python" in skills.programming_languages
    assert "Go" in skills.programming_languages
    assert "FastAPI" in skills.frameworks
    assert "PostgreSQL" in skills.databases
    assert "Docker" in skills.tools
    assert "PyTorch" in skills.ai_ml

def test_duplicate_skills_deduplication():
    skills = extract_skills("Skills: Python, python, PYTHON, React, React.js, reactjs, Docker, docker")
    deduped = deduplicate_skills(skills)
    assert deduped.programming_languages.count("Python") == 1
    assert deduped.frameworks.count("React") == 1
    assert deduped.tools.count("Docker") == 1

def test_extract_education():
    education = extract_education(SAMPLE_RESUME)
    assert len(education) >= 1
    entry = education[0]
    assert "B.Tech" in entry.degree
    assert "Stanford University" in entry.university
    assert entry.graduation_year in ["2018", "2022"]
    assert entry.specialization == "Computer Science and Engineering"

def test_missing_education():
    text = "John Smith\nSkills: Python, Java, Docker\nExperience: Software Engineer at Google"
    education = extract_education(text)
    assert education == []

def test_extract_experience():
    experience = extract_experience(SAMPLE_RESUME)
    assert len(experience) >= 1
    assert any("Senior Backend Developer" in (e.job_title or "") for e in experience)

def test_no_experience():
    text = """
    Jane Student
    jane@example.com
    EDUCATION
    B.S. in Computer Science
    University of Washington
    SKILLS
    Python, C++
    PROJECTS
    Chess Engine in Python
    """
    experience = extract_experience(text)
    assert experience == []

def test_extract_projects():
    projects = extract_projects(SAMPLE_RESUME)
    assert len(projects) >= 1
    assert "Job Match AI" in projects[0].name

def test_extract_certifications():
    certs = extract_certifications(SAMPLE_RESUME)
    assert len(certs) >= 1
    assert any("AWS" in c.name for c in certs)

