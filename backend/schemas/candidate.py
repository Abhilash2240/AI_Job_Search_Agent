from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field

class ValidationStatus(str, Enum):
    VALID = "VALID"
    INCOMPLETE = "INCOMPLETE"
    INVALID = "INVALID"

class PersonalInfo(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None

class EducationItem(BaseModel):
    degree: Optional[str] = None
    specialization: Optional[str] = None
    university: Optional[str] = None
    graduation_year: Optional[str] = None
    start_year: Optional[str] = None
    end_year: Optional[str] = None
    academic_performance: Optional[str] = None

class SkillsCategorized(BaseModel):
    programming_languages: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    databases: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    ai_ml: List[str] = Field(default_factory=list)
    other: List[str] = Field(default_factory=list)

class ExperienceItem(BaseModel):
    company: Optional[str] = None
    job_title: Optional[str] = None
    duration: Optional[str] = None
    responsibilities: Optional[str] = None

class ProjectItem(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)

class InternshipItem(BaseModel):
    company: Optional[str] = None
    role: Optional[str] = None
    duration: Optional[str] = None
    responsibilities: Optional[str] = None

class CertificationItem(BaseModel):
    name: Optional[str] = None
    issuer: Optional[str] = None
    year: Optional[str] = None

class CandidateProfile(BaseModel):
    personal: PersonalInfo = Field(default_factory=PersonalInfo)
    education: List[EducationItem] = Field(default_factory=list)
    skills: SkillsCategorized = Field(default_factory=SkillsCategorized)
    skill_sources: Dict[str, List[str]] = Field(default_factory=dict)
    inferred_skills: List[str] = Field(default_factory=list)
    experience: List[ExperienceItem] = Field(default_factory=list)
    projects: List[ProjectItem] = Field(default_factory=list)
    internships: List[InternshipItem] = Field(default_factory=list)
    certifications: List[CertificationItem] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)
    profile_completeness: Optional[float] = None

class ValidationResult(BaseModel):
    status: ValidationStatus
    reasons: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    entropy: float
    career_term_count: int
    char_count: int

class ResumeUploadResponse(BaseModel):
    candidate_id: int
    resume_hash: str
    filename: Optional[str] = None
    validation: ValidationResult
    profile: CandidateProfile

class SkillActionRequest(BaseModel):
    skill: str
    category: Optional[str] = None

