"""
Test Suite for Phase 4C: Job Description Extraction and Normalization.
Covers HTML cleanup, section segmentation, title normalization,
categorized skill extraction with evidence, experience and fresher detection,
education extraction, explicit salary extraction, location normalization,
provider-specific extractors (Greenhouse, Lever, Firecrawl),
extraction quality confidence scoring, and FastAPI job endpoints.
"""

import asyncio
import json
import pytest
import httpx
from httpx import Response, Request

from jobs.extraction.description_extractor import DescriptionExtractor
from jobs.extraction.education_extractor import EducationExtractor
from jobs.extraction.experience_extractor import ExperienceExtractor
from jobs.extraction.skill_extractor import SkillExtractor
from jobs.extraction.greenhouse_extractor import GreenhouseExtractor
from jobs.extraction.lever_extractor import LeverExtractor
from jobs.extraction.firecrawl_extractor import FirecrawlExtractor
from jobs.extraction_service import JobExtractionService
from jobs.job_schema import (
    EmploymentType,
    ExtractionStatus,
    SeniorityLevel,
    WorkplaceType,
)
from jobs.normalizer import JobNormalizer


# ============================================================================
# 1. HTML CLEANUP & SECTION SEGMENTATION TESTS
# ============================================================================

def test_html_cleanup_and_noise_removal():
    """Verify HTML stripping, boilerplate cookie removal, and whitespace formatting."""
    raw_html = """
    <html>
      <head><style>.btn { color: red; }</style></head>
      <body>
        <div class="cookie-banner">We use cookies to improve your experience. Accept all cookies</div>
        <a href="/jobs">← Back to jobs</a>
        <h1>Backend Engineer</h1>
        <p>We are looking for a skilled developer to join our team in Bengaluru.</p>
        <script>console.log('tracker');</script>
        <button>Share this job on LinkedIn</button>
      </body>
    </html>
    """
    cleaned = DescriptionExtractor.clean_html(raw_html)
    assert "<style>" not in cleaned
    assert "<script>" not in cleaned
    assert "cookie" not in cleaned.lower()
    assert "back to jobs" not in cleaned.lower()
    assert "Backend Engineer" in cleaned
    assert "Bengaluru" in cleaned


def test_section_segmentation():
    """Verify segmentation into summary, responsibilities, qualifications, and benefits."""
    job_text = """
    Company Overview
    We are building the next generation AI platform.

    Responsibilities
    • Architect and build scalable REST APIs using Python and FastAPI.
    • Collaborate with frontend engineers to integrate React applications.
    • Deploy containerized microservices to AWS with Docker.

    Requirements
    • Bachelor's degree in Computer Science or related field.
    • 2+ years of professional experience in backend development.
    • Strong proficiency in Python, SQL, and PostgreSQL.

    Preferred Qualifications
    • Experience with Kafka or message queues.
    • Familiarity with Docker and Kubernetes.

    Benefits
    • Comprehensive health insurance.
    • Remote work stipend.
    """
    segmented = DescriptionExtractor.segment_description(job_text)
    assert "AI platform" in segmented["summary"]
    assert len(segmented["responsibilities"]) == 3
    assert any("FastAPI" in r for r in segmented["responsibilities"])
    assert len(segmented["qualifications"]) == 3
    assert any("Python" in q for q in segmented["qualifications"])
    assert len(segmented["preferred_qualifications"]) == 2
    assert any("Kafka" in p for p in segmented["preferred_qualifications"])
    assert len(segmented["benefits"]) == 2


# ============================================================================
# 2. JOB TITLE & SENIORITY NORMALIZATION TESTS
# ============================================================================

def test_job_title_normalization_preserves_levels():
    """Verify title cleaning without discarding critical seniority indicators."""
    # Junior Python Developer
    cleaned1 = JobNormalizer.clean_title("Junior Python Developer (REQ-9876) - Bengaluru")
    assert cleaned1 == "Junior Python Developer"
    sen1 = JobNormalizer.detect_seniority(cleaned1)
    assert sen1 == SeniorityLevel.ENTRY_LEVEL
    canon1 = JobNormalizer.canonicalize_title(cleaned1)
    assert canon1 == "Python Developer"

    # Associate Backend Engineer
    cleaned2 = JobNormalizer.clean_title("Associate Backend Engineer [Remote - India]")
    assert cleaned2 == "Associate Backend Engineer"
    sen2 = JobNormalizer.detect_seniority(cleaned2)
    assert sen2 == SeniorityLevel.ENTRY_LEVEL
    canon2 = JobNormalizer.canonicalize_title(cleaned2)
    assert canon2 == "Backend Engineer"

    # Software Development Engineer I
    cleaned3 = JobNormalizer.clean_title("Software Development Engineer I")
    assert cleaned3 == "Software Development Engineer I"
    sen3 = JobNormalizer.detect_seniority(cleaned3)
    assert sen3 == SeniorityLevel.ENTRY_LEVEL

    # Senior Software Engineer
    cleaned4 = JobNormalizer.clean_title("Senior Software Engineer")
    sen4 = JobNormalizer.detect_seniority(cleaned4)
    assert sen4 == SeniorityLevel.SENIOR

    # Intern
    cleaned5 = JobNormalizer.clean_title("Backend Engineering Intern")
    sen5 = JobNormalizer.detect_seniority(cleaned5)
    assert sen5 == SeniorityLevel.INTERN


# ============================================================================
# 3. SKILL EXTRACTION WITH PROVENANCE & REQUIRED/PREFERRED SPLIT
# ============================================================================

def test_skill_extraction_and_provenance():
    """Verify extraction of skills, canonicalization, categories, and evidence snippet."""
    summary = "Leading fintech company in Bangalore."
    responsibilities = [
        "Develop high-throughput REST APIs using Python and FastAPI.",
        "Manage data pipelines with PostgreSQL and Redis.",
    ]
    qualifications = [
        "Proficiency with Docker and AWS cloud infrastructure.",
        "Strong problem solving and communication skills.",
    ]
    preferred_qualifications = [
        "Hands-on experience with Kubernetes and Kafka.",
    ]
    full_text = f"{summary}\n" + "\n".join(responsibilities + qualifications + preferred_qualifications)

    req_skills, pref_skills = SkillExtractor.extract_from_segmented_job(
        summary=summary,
        responsibilities=responsibilities,
        qualifications=qualifications,
        preferred_qualifications=preferred_qualifications,
        full_text=full_text,
    )

    req_canonicals = {s.canonical_name: s for s in req_skills}
    pref_canonicals = {s.canonical_name: s for s in pref_skills}

    # Verify required skills
    assert "Python" in req_canonicals
    assert req_canonicals["Python"].category == "Programming Languages"
    assert "FastAPI" in req_canonicals["Python"].evidence_snippet
    assert req_canonicals["Python"].is_required is True

    assert "FastAPI" in req_canonicals
    assert req_canonicals["FastAPI"].category == "Frameworks"

    assert "PostgreSQL" in req_canonicals
    assert req_canonicals["PostgreSQL"].category == "Databases"

    assert "Docker" in req_canonicals
    assert req_canonicals["Docker"].category == "DevOps"

    assert "AWS" in req_canonicals
    assert req_canonicals["AWS"].category == "Cloud Platforms"

    # Verify preferred skills
    assert "Kubernetes" in pref_canonicals
    assert pref_canonicals["Kubernetes"].is_required is False
    assert pref_canonicals["Kubernetes"].category == "DevOps"

    assert "Apache Kafka" in pref_canonicals
    assert pref_canonicals["Apache Kafka"].is_required is False


# ============================================================================
# 4. EXPERIENCE & FRESHER ELIGIBILITY EXTRACTION TESTS
# ============================================================================

def test_experience_and_fresher_extraction():
    """Verify experience parsing across ranges, minimums, and fresher indicators."""
    # 0-1 years / Fresher
    exp1 = ExperienceExtractor.extract_experience("0-1 years of experience in software development. Freshers welcome to apply.")
    assert exp1.min_years == 0.0
    assert exp1.max_years == 1.0
    assert exp1.is_fresher_eligible is True
    assert exp1.seniority_level == SeniorityLevel.ENTRY_LEVEL

    # 2-4 years
    exp2 = ExperienceExtractor.extract_experience("Requirements: 2 to 4 years of hands-on experience with Python backend systems.")
    assert exp2.min_years == 2.0
    assert exp2.max_years == 4.0
    assert exp2.is_fresher_eligible is False
    assert exp2.seniority_level == SeniorityLevel.MID_LEVEL

    # 3+ years
    exp3 = ExperienceExtractor.extract_experience("Candidate must have 3+ years of experience in distributed systems.")
    assert exp3.min_years == 3.0
    assert exp3.max_years is None
    assert exp3.is_fresher_eligible is False

    # Internship
    exp4 = ExperienceExtractor.extract_experience("Software Engineering Intern for summer batch.")
    assert exp4.is_internship is True
    assert exp4.is_fresher_eligible is True
    assert exp4.seniority_level == SeniorityLevel.INTERN

    # Unspecified experience must not be assumed 0
    exp5 = ExperienceExtractor.extract_experience("Looking for a passionate engineer to join our core team.")
    assert exp5.min_years is None
    assert exp5.max_years is None
    assert exp5.is_fresher_eligible is False


# ============================================================================
# 5. EDUCATION REQUIREMENTS EXTRACTION TESTS
# ============================================================================

def test_education_requirements_extraction():
    """Verify degree and major extraction."""
    qualifications = [
        "Must possess a B.Tech or B.E. in Computer Science, Information Technology, or related quantitative field.",
    ]
    preferred = [
        "Master's Degree (M.Tech / M.S.) in Software Engineering is a plus.",
    ]

    edu = EducationExtractor.extract_education(
        qualifications=qualifications,
        preferred_qualifications=preferred,
        full_text="\n".join(qualifications + preferred),
    )

    assert "B.Tech" in edu.degree_requirements
    assert "B.E." in edu.degree_requirements
    assert "Computer Science" in edu.fields_of_study
    assert "Information Technology" in edu.fields_of_study
    assert "Master's Degree" in edu.preferred_education
    assert edu.evidence is not None


# ============================================================================
# 6. EXPLICIT SALARY EXTRACTION TESTS
# ============================================================================

def test_explicit_salary_extraction():
    """Verify compensation extraction only when explicitly published."""
    # INR LPA range
    sal1 = ExperienceExtractor.extract_salary("Salary range: 8 - 12 LPA depending on interview performance.")
    assert sal1 is not None
    assert sal1.min_amount == 800000.0
    assert sal1.max_amount == 1200000.0
    assert sal1.currency == "INR"
    assert sal1.period == "YEAR"

    # INR monthly
    sal2 = ExperienceExtractor.extract_salary("Compensation: INR 45,000 per month.")
    assert sal2 is not None
    assert sal2.min_amount == 45000.0
    assert sal2.currency == "INR"
    assert sal2.period == "MONTH"

    # Stipend
    sal3 = ExperienceExtractor.extract_salary("Monthly stipend of Rs. 25,000 during 6-month training.")
    assert sal3 is not None
    assert sal3.min_amount == 25000.0
    assert sal3.currency == "INR"
    assert sal3.period == "STIPEND"

    # USD annual
    sal4 = ExperienceExtractor.extract_salary("Base compensation: $90,000 - $130,000 per year.")
    assert sal4 is not None
    assert sal4.min_amount == 90000.0
    assert sal4.max_amount == 130000.0
    assert sal4.currency == "USD"
    assert sal4.period == "YEAR"

    # Unspecified compensation must return None
    sal5 = ExperienceExtractor.extract_salary("Competitive salary with stock options and health benefits.")
    assert sal5 is None


# ============================================================================
# 7. LOCATION NORMALIZATION TESTS
# ============================================================================

def test_location_normalization():
    """Verify city, state, country, workplace type, and remote tags."""
    # Bengaluru On-site
    loc1 = JobNormalizer.normalize_location("Bengaluru, Karnataka, India")
    assert loc1.city == "Bengaluru"
    assert loc1.state == "Karnataka"
    assert loc1.country == "India"
    assert loc1.is_remote is False
    assert loc1.workplace_type == WorkplaceType.ON_SITE

    # Remote - India
    loc2 = JobNormalizer.normalize_location("Remote - India (Work from anywhere in India)")
    assert loc2.country == "India"
    assert loc2.is_remote is True
    assert loc2.workplace_type == WorkplaceType.REMOTE
    assert any("Remote" in el for el in loc2.eligible_locations)

    # Hybrid Hyderabad
    loc3 = JobNormalizer.normalize_location("Hybrid - Hyderabad, Telangana")
    assert loc3.city == "Hyderabad"
    assert loc3.country == "India"
    assert loc3.workplace_type == WorkplaceType.HYBRID


# ============================================================================
# 8. PROVIDER EXTRACTORS TESTS (GREENHOUSE, LEVER, FIRECRAWL)
# ============================================================================

def test_greenhouse_extractor_pipeline():
    """Verify Greenhouse extractor using structured API payload."""
    extractor = GreenhouseExtractor()
    payload = {
        "id": 99911,
        "title": "Junior Python Backend Developer",
        "content": """
        <div>
          <p>We are seeking a junior engineer to join our platform team.</p>
          <h3>Responsibilities</h3>
          <ul>
            <li>Build REST APIs with FastAPI and Python.</li>
            <li>Write unit tests with Pytest.</li>
          </ul>
          <h3>Requirements</h3>
          <ul>
            <li>0-1 years experience. Freshers welcome.</li>
            <li>Bachelor's degree in Computer Science.</li>
            <li>Basic knowledge of Docker and PostgreSQL.</li>
          </ul>
        </div>
        """,
        "location": {"name": "Bengaluru, India"},
        "absolute_url": "https://boards.greenhouse.io/company/jobs/99911",
        "departments": [{"name": "Platform"}],
    }

    job = extractor.run_pipeline(raw_payload=payload, company_name="Fintech Corp")
    assert job["canonical_job_title"] == "Python Backend Engineer"
    assert job["seniority_level"] == "ENTRY_LEVEL"
    assert job["city"] == "Bengaluru"
    assert job["country"] == "India"
    assert job["experience_min_years"] == 0.0
    assert job["experience_max_years"] == 1.0
    assert any(s.canonical_name == "Python" for s in job["required_skills"])
    assert any(s.canonical_name == "FastAPI" for s in job["required_skills"])
    assert "B.Tech" in job["degree_requirements"] or "Bachelor's Degree" in job["degree_requirements"]
    assert job["extraction_status"] == ExtractionStatus.COMPLETE.value
    assert job["extraction_confidence"] >= 0.85


def test_lever_extractor_pipeline():
    """Verify Lever extractor using structured lists and categories."""
    extractor = LeverExtractor()
    payload = {
        "id": "lever-uuid-456",
        "text": "Backend Engineer",
        "categories": {
            "location": "Hyderabad, India",
            "commitment": "Full Time",
            "department": "Engineering",
        },
        "description": "<p>Join our core engineering department.</p>",
        "lists": [
            {
                "text": "What you will do",
                "content": "<li>Design backend services using Python and SQL.</li>",
            },
            {
                "text": "Requirements",
                "content": "<li>2+ years of experience with AWS and Docker.</li><li>Salary: 10-15 LPA.</li>",
            },
        ],
        "hostedUrl": "https://jobs.lever.co/company/lever-uuid-456",
        "applyUrl": "https://jobs.lever.co/company/lever-uuid-456/apply",
    }

    job = extractor.run_pipeline(raw_payload=payload, company_name="Tech Solutions")
    assert job["title"] == "Backend Engineer"
    assert job["city"] == "Hyderabad"
    assert job["experience_min_years"] == 2.0
    assert job["salary_min"] == 1000000.0
    assert job["salary_max"] == 1500000.0
    assert job["salary_currency"] == "INR"
    assert job["application_url"] == "https://jobs.lever.co/company/lever-uuid-456/apply"


def test_firecrawl_extractor_pipeline():
    """Verify Firecrawl extractor with markdown input."""
    extractor = FirecrawlExtractor()
    payload = {
        "title": "Associate Software Engineer",
        "url": "https://startup.com/careers/associate-engineer",
        "markdown": """
        # Associate Software Engineer
        Location: Remote - India

        ## Role Overview
        Work on cloud microservices with Go and Python.

        ## Qualifications
        - 0 to 2 years experience.
        - Knowledge of Git and Linux.
        """,
    }

    job = extractor.run_pipeline(raw_payload=payload, company_name="AI Startup")
    assert job["canonical_job_title"] == "Software Engineer"
    assert job["is_remote"] is True
    assert job["experience_min_years"] == 0.0
    assert job["experience_max_years"] == 2.0
    assert any(s.canonical_name == "Python" for s in job["required_skills"])


# ============================================================================
# 9. EXTRACTION QUALITY & CONFIDENCE SCORING TESTS
# ============================================================================

def test_extraction_quality_scoring():
    """Verify confidence calculation and missing field tagging."""
    extractor = GreenhouseExtractor()

    # Sparse payload missing description
    sparse_payload = {
        "title": "Software Engineer",
        "content": "",
        "location": {"name": "Bangalore"},
    }
    sparse_job = extractor.run_pipeline(raw_payload=sparse_payload)
    assert sparse_job["extraction_status"] == ExtractionStatus.FAILED.value
    assert sparse_job["extraction_confidence"] < 0.40
    assert "Job Description" in sparse_job["missing_fields"]


# ============================================================================
# 10. FASTAPI NORMALIZED JOBS API TESTS
# ============================================================================

def test_api_jobs_endpoints_contract():
    """Test normalized job endpoints via httpx AsyncClient."""
    async def run():
        from app.main import app

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            # 1. GET /api/jobs/normalized
            resp_list = await client.get("/api/jobs/normalized")
            assert resp_list.status_code == 200
            list_data = resp_list.json()
            assert "total" in list_data
            assert "items" in list_data
            assert "page" in list_data

            # 2. GET /api/jobs/extraction/summary
            resp_sum = await client.get("/api/jobs/extraction/summary")
            assert resp_sum.status_code == 200
            sum_data = resp_sum.json()
            assert "total_normalized_jobs" in sum_data
            assert "by_status" in sum_data
            assert "average_confidence" in sum_data

            # 3. POST /api/jobs/extract (batch run with limit=0 to verify route acceptance)
            resp_extract = await client.post("/api/jobs/extract", json={"limit": 0, "background": False})
            assert resp_extract.status_code == 200
            extract_data = resp_extract.json()
            assert "status" in extract_data

    asyncio.run(run())

