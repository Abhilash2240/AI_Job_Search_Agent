# backend/schemas/matching.py
"""
Pydantic Schemas for Phase 7: Candidate-to-Job Matching and Scoring Engine.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class MatchComponentScores(BaseModel):
    semantic_score: float = Field(..., description="Cosine similarity (0-1)")
    skill_score: float = Field(..., description="Weighted required and preferred skill coverage (0-1)")
    role_score: float = Field(..., description="Career-role title and domain compatibility (0-1)")
    experience_score: float = Field(..., description="Experience years and seniority level alignment (0-1)")
    education_score: float = Field(..., description="Degree and field of study compatibility (0-1)")
    location_score: float = Field(..., description="Location and remote alignment (0-1)")
    score_coverage: float = Field(..., description="Proportion of weight supported by evaluable data (0-1)")


class CandidateJobMatchItem(BaseModel):
    id: int
    candidate_id: int
    canonical_job_id: int
    canonical_job_code: str
    company_name: str
    job_title: str
    canonical_job_title: str
    composite_score: float
    component_scores: MatchComponentScores
    eligibility_status: str
    match_classification: str
    matched_skills: List[Any] = []
    missing_skills: List[str] = []
    inferred_skills_potential: List[Any] = []
    matched_roles: Optional[Dict[str, Any]] = None
    explanation: str
    disqualification_reasons: List[str] = []
    is_remote: bool = False
    location: Optional[str] = None
    seniority_level: Optional[str] = None
    employment_type: Optional[str] = None
    evaluated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CandidateMatchListResponse(BaseModel):
    candidate_id: int
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[CandidateJobMatchItem]


class BatchMatchRequest(BaseModel):
    force: bool = Field(default=False, description="Force re-evaluation even if content hashes are unchanged")


class BatchMatchResponse(BaseModel):
    status: str
    candidates_evaluated: int
    total_matches_generated: int
    summary: Dict[str, Any]


class MatchingSummaryResponse(BaseModel):
    total_candidates: int
    total_canonical_vacancies: int
    total_match_records: int
    highly_recommended_count: int
    recommended_count: int
    borderline_count: int
    low_compatibility_count: int
    eligible_count: int
    eligible_with_conditions_count: int
    ineligible_count: int
    needs_review_count: int
    failed_count: int
    average_score: float
    average_score_coverage: float
    algorithm_version: str

