from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from schemas.candidate import ValidationStatus


class ExperienceLevel(str, Enum):
    FRESHER = "fresher"
    ENTRY_LEVEL = "entry_level"
    MID_LEVEL = "mid_level"
    SENIOR = "senior"


class DetailedProfileValidation(BaseModel):
    candidate_id: int
    validation_status: ValidationStatus
    completeness_score: float
    experience_level: ExperienceLevel
    years_of_experience_estimated: float
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    section_analysis: Dict[str, Any] = Field(default_factory=dict)
    complete_fields: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    unverified_fields: List[str] = Field(default_factory=list)
    optional_fields: List[str] = Field(default_factory=list)


class CareerRole(BaseModel):
    role_id: str
    title: str
    description: str
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    alternative_titles_entry: List[str] = Field(default_factory=list)
    alternative_titles_experienced: List[str] = Field(default_factory=list)
    domain_keywords: List[str] = Field(default_factory=list)


class RoleRecommendation(BaseModel):
    role_id: str
    role_title: str
    composite_match_score: float = Field(..., description="Hybrid match score combining all 4 normalized components.")
    similarity_score: float = Field(..., description="Raw cosine similarity score (0.0 to 1.0) from fine-tuned SBERT model.")
    skill_match_score: float = Field(..., description="Verified technical skill overlap score (0.0 to 1.0).")
    project_alignment_score: float = Field(..., description="Project experience relevance score (0.0 to 1.0).")
    education_alignment_score: float = Field(..., description="Degree and coursework relevance score (0.0 to 1.0).")
    matching_skills: List[str] = Field(default_factory=list, description="Verified skills present in candidate profile.")
    missing_skills: List[str] = Field(default_factory=list, description="Role skills not explicitly found in candidate resume.")
    skill_evidence: Dict[str, List[str]] = Field(default_factory=dict, description="Source provenance of matching skills (e.g., projects, coursework, skills).")
    explanation: str
    alternative_titles: List[str] = Field(default_factory=list, description="Career role titles tailored to candidate experience level.")


class RecommendationsResponse(BaseModel):
    candidate_id: int
    candidate_name: Optional[str] = None
    experience_level: ExperienceLevel
    total_recommended: int
    recommendations: List[RoleRecommendation] = Field(default_factory=list)
    scoring_formula: str = "composite_match_score = (w_semantic * S_sbert) + (w_skills * S_skills) + (w_project * S_project) + (w_edu * S_edu)"
    scoring_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "semantic_similarity": 0.45,
            "skill_overlap": 0.35,
            "project_experience": 0.15,
            "education_alignment": 0.05
        }
    )
    model_version: str = "fine-tuned-sbert-384d"


class ConfirmedRoleItem(BaseModel):
    role_id: str
    role_title: str
    is_custom: bool = False
    custom_description: Optional[str] = None
    matching_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    alternative_titles: List[str] = Field(default_factory=list)
    composite_match_score: Optional[float] = None
    similarity_score: Optional[float] = None


class SaveConfirmedRolesRequest(BaseModel):
    roles: List[ConfirmedRoleItem] = Field(..., min_length=1, description="List of confirmed roles to save.")


class ConfirmedRolesResponse(BaseModel):
    candidate_id: int
    candidate_name: Optional[str] = None
    confirmed: bool
    confirmed_at: Optional[str] = None
    total_confirmed: int
    roles: List[ConfirmedRoleItem] = Field(default_factory=list)


class CustomRoleRequest(BaseModel):
    role_title: str = Field(..., min_length=2, max_length=100)
    role_description: Optional[str] = Field(default=None, max_length=500)
    skills: Optional[List[str]] = Field(default_factory=list)

