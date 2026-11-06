import pytest
import numpy as np

from schemas.candidate import (
    CandidateProfile,
    PersonalInfo,
    EducationItem,
    SkillsCategorized,
    ExperienceItem,
    ProjectItem,
    ValidationStatus,
)
from schemas.role import ExperienceLevel
from intelligence.profile_validator import (
    validate_candidate_profile_comprehensive,
    estimate_years_of_experience,
    determine_experience_level,
)
from intelligence.role_recommender import (
    recommend_career_roles,
    build_candidate_semantic_text,
    get_role_embeddings,
)
from intelligence.role_catalogue import get_role_catalogue
from embeddings.model_loader import get_model


def test_sbert_model_dimension_and_loading():
    """Verify that fine-tuned SBERT model loads and outputs 384-dimensional embeddings."""
    model = get_model()
    dim = model.get_sentence_embedding_dimension()
    assert dim == 384, f"Expected 384 dimensions, got {dim}"
    
    vec = model.encode("Test sentence for embedding", normalize_embeddings=True)
    assert vec.shape == (384,)
    # Unit norm test
    norm = np.linalg.norm(vec)
    assert np.isclose(norm, 1.0, atol=1e-3)


def test_role_catalogue_initialization():
    """Verify that all 10 initial career roles exist in the catalogue."""
    roles = get_role_catalogue()
    assert len(roles) == 10
    role_ids = [r.role_id for r in roles]
    assert "python_backend_engineer" in role_ids
    assert "ai_ml_engineer" in role_ids
    assert "full_stack_developer" in role_ids
    assert "software_engineer" in role_ids
    assert "data_engineer" in role_ids


def test_fresher_profile_validation():
    """Verify that freshers without employment history are classified correctly without penalties."""
    fresher_profile = CandidateProfile(
        personal=PersonalInfo(
            name="Aarav Sharma",
            email="aarav@example.com",
            phone="+91 9876543210",
            location="Hyderabad, India"
        ),
        education=[
            EducationItem(
                degree="Bachelor of Technology",
                specialization="Computer Science",
                university="SR University",
                graduation_year="2027",
                start_year="2023",
                end_year="2027",
                academic_performance="CGPA: 9.1 / 10"
            )
        ],
        skills=SkillsCategorized(
            programming_languages=["Python", "SQL", "C++"],
            frameworks=["FastAPI"],
            databases=["PostgreSQL"],
            tools=["Git", "Docker"],
            ai_ml=["PyTorch", "Scikit-Learn"],
            other=["REST APIs", "Data Structures"]
        ),
        projects=[
            ProjectItem(
                name="Stock Trading Simulator",
                description="Built automated stock trading platform with real-time data ingestion and backtesting.",
                technologies=["Python", "FastAPI", "PostgreSQL", "Docker"]
            )
        ],
        experience=[]  # Freshers have no formal employment
    )
    
    val = validate_candidate_profile_comprehensive(candidate_id=1, profile=fresher_profile)
    assert val.validation_status == ValidationStatus.VALID
    assert val.experience_level == ExperienceLevel.FRESHER
    assert val.years_of_experience_estimated == 0.0
    assert val.completeness_score >= 80.0
    assert len(val.suggestions) > 0


def test_experienced_profile_validation():
    """Verify experienced engineer classification and completeness."""
    senior_profile = CandidateProfile(
        personal=PersonalInfo(name="Elena Rostova", email="elena@example.com", phone="+1 555-0100"),
        education=[EducationItem(degree="M.S.", university="MIT", graduation_year="2018")],
        skills=SkillsCategorized(
            programming_languages=["Python", "Go"],
            frameworks=["Django", "FastAPI"],
            databases=["PostgreSQL", "Redis"],
            tools=["Docker", "Kubernetes", "AWS"]
        ),
        experience=[
            ExperienceItem(
                company="TechCorp",
                job_title="Senior Software Engineer",
                duration="2018 - Present",
                responsibilities="Designed microservices and distributed transaction systems."
            )
        ]
    )
    
    val = validate_candidate_profile_comprehensive(candidate_id=2, profile=senior_profile)
    assert val.validation_status == ValidationStatus.VALID
    assert val.experience_level in [ExperienceLevel.SENIOR, ExperienceLevel.MID_LEVEL]
    assert val.years_of_experience_estimated >= 4.0


def test_incomplete_profile_validation():
    """Verify that profiles lacking critical sections are flagged as incomplete."""
    incomplete_profile = CandidateProfile(
        personal=PersonalInfo(name=None, email=None, phone=None),
        skills=SkillsCategorized(programming_languages=["Python"]),
        education=[],
        experience=[],
        projects=[]
    )
    val = validate_candidate_profile_comprehensive(candidate_id=3, profile=incomplete_profile)
    assert val.validation_status in [ValidationStatus.INCOMPLETE, ValidationStatus.INVALID]
    assert len(val.warnings) > 0


def test_sbert_career_role_recommendation_ranking():
    """Verify SBERT role recommendations rank by cosine similarity and identify skill overlaps."""
    profile = CandidateProfile(
        personal=PersonalInfo(name="Gundelli Abhilash", email="abhilash@example.com"),
        education=[EducationItem(degree="Bachelor of Technology", university="SR University", graduation_year="2027")],
        skills=SkillsCategorized(
            programming_languages=["Python", "SQL"],
            frameworks=["FastAPI"],
            databases=["PostgreSQL"],
            tools=["Docker", "Git"],
            ai_ml=["PyTorch", "Sentence-Transformers"]
        ),
        projects=[
            ProjectItem(
                name="AI Job Search Agent",
                description="Fine-tuned Sentence-BERT model and built job matching engine.",
                technologies=["Python", "PyTorch", "FastAPI", "PostgreSQL"]
            )
        ]
    )
    
    recs_resp = recommend_career_roles(candidate_id=10, profile=profile, top_n=5)
    assert recs_resp.candidate_id == 10
    assert len(recs_resp.recommendations) == 5
    
    # Verify ranking order (descending composite match score)
    scores = [r.composite_match_score for r in recs_resp.recommendations]
    assert scores == sorted(scores, reverse=True)
    
    # Check that Python-related and AI/ML-related roles rank prominently
    top_role_ids = [r.role_id for r in recs_resp.recommendations[:3]]
    assert any(k in top_role_ids for k in ["python_backend_engineer", "ai_ml_engineer", "python_developer", "ai_engineer"])
    
    # Verify skill breakdown and explanation
    top_rec = recs_resp.recommendations[0]
    assert len(top_rec.matching_skills) > 0
    assert top_rec.similarity_score > 0.4
    assert len(top_rec.explanation) > 10


