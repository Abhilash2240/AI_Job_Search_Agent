# backend/models/__init__.py
"""SQLAlchemy model exports."""
from .candidate import Candidate
from .job import Job
from .source import (
    JobSource,
    Company,
    CompanyCareerSource,
    CompanyContact,
    SourceImportBatch,
    VerificationStatus,
    SourceType,
    RelevanceCategory,
)
from .canonical_job import (
    CanonicalJob,
    CanonicalJobSource,
    DuplicateReviewGroup,
    VacancyStatus,
    DuplicateType,
    DuplicateGroupStatus,
)
from .job_embedding import JobEmbedding, EmbeddingStatus
from .candidate_job_match import (
    CandidateJobMatch,
    CandidateEmbedding,
    EligibilityStatus,
    MatchClassification,
)
from .saved_job import SavedJob
from .application import JobApplication, ApplicationStatus, ApplicationStatusHistory
from .pipeline_execution import PipelineExecution, PipelineTrigger, PipelineStatus
from .user_preferences import UserPreferences

__all__ = [
    "Candidate",
    "Job",
    "JobSource",
    "Company",
    "CompanyCareerSource",
    "CompanyContact",
    "SourceImportBatch",
    "VerificationStatus",
    "SourceType",
    "RelevanceCategory",
    "CanonicalJob",
    "CanonicalJobSource",
    "DuplicateReviewGroup",
    "VacancyStatus",
    "DuplicateType",
    "DuplicateGroupStatus",
    "JobEmbedding",
    "EmbeddingStatus",
    "CandidateJobMatch",
    "CandidateEmbedding",
    "EligibilityStatus",
    "MatchClassification",
    "SavedJob",
    "JobApplication",
    "ApplicationStatus",
    "ApplicationStatusHistory",
    "PipelineExecution",
    "PipelineTrigger",
    "PipelineStatus",
    "UserPreferences",
]
