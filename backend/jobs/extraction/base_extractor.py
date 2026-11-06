"""
Base Job Extractor Module (Phase 4C).
Provides the standard extraction pipeline, confidence score calculation,
missing field tracking, and abstract interface for provider-specific extractors.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from jobs.extraction.description_extractor import DescriptionExtractor
from jobs.extraction.education_extractor import EducationExtractor
from jobs.extraction.experience_extractor import ExperienceExtractor
from jobs.extraction.skill_extractor import SkillExtractor
from jobs.job_schema import (
    EducationRequirements,
    ExperienceRequirements,
    ExtractionStatus,
    LocationInfo,
    SalaryInfo,
    SeniorityLevel,
    SkillWithEvidence,
)
from jobs.normalizer import JobNormalizer


class BaseJobExtractor(ABC):
    """Abstract base extractor providing standardized extraction pipeline and quality scoring."""

    def __init__(self, provider_name: str):
        self.provider_name = provider_name

    @abstractmethod
    def extract_raw_content(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts unnormalized raw fields from the provider payload."""
        pass

    def run_pipeline(
        self,
        raw_payload: Dict[str, Any],
        fallback_title: str = "",
        fallback_location: Optional[str] = None,
        source_url: Optional[str] = None,
        application_url: Optional[str] = None,
        company_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes complete extraction and normalization pipeline on raw job payload.
        """
        raw_data = self.extract_raw_content(raw_payload)

        raw_title = raw_data.get("title") or fallback_title or "Untitled Role"
        raw_description_html = raw_data.get("description") or ""
        raw_loc = raw_data.get("location") or fallback_location
        app_url = raw_data.get("application_url") or application_url or source_url
        src_url = raw_data.get("source_url") or source_url
        ext_id = str(raw_data.get("external_id") or "")

        # 1. Clean HTML & segment description
        cleaned_text = DescriptionExtractor.clean_html(raw_description_html)
        segmented = DescriptionExtractor.segment_description(cleaned_text)

        summary = segmented["summary"]
        responsibilities = segmented["responsibilities"]
        qualifications = segmented["qualifications"]
        preferred_qualifications = segmented["preferred_qualifications"]
        benefits = segmented["benefits"]
        full_text = segmented["full_text"]

        # 2. Normalize title and seniority
        canonical_title = JobNormalizer.canonicalize_title(raw_title)
        cleaned_title = JobNormalizer.clean_title(raw_title)
        seniority = JobNormalizer.detect_seniority(raw_title, full_text)

        # 3. Extract skills with evidence
        req_skills, pref_skills = SkillExtractor.extract_from_segmented_job(
            summary=summary,
            responsibilities=responsibilities,
            qualifications=qualifications,
            preferred_qualifications=preferred_qualifications,
            full_text=full_text,
        )

        # 4. Extract experience & compensation
        exp_req = ExperienceExtractor.extract_experience(full_text, title=raw_title)
        salary_info = ExperienceExtractor.extract_salary(full_text)

        # If seniority was unknown from title, use experience seniority
        if seniority == SeniorityLevel.UNKNOWN and exp_req.seniority_level != SeniorityLevel.UNKNOWN:
            seniority = exp_req.seniority_level

        # 5. Extract education
        edu_req = EducationExtractor.extract_education(
            qualifications=qualifications,
            preferred_qualifications=preferred_qualifications,
            full_text=full_text,
        )

        # 6. Normalize location and workplace type
        loc_info = JobNormalizer.normalize_location(raw_loc)
        emp_type = JobNormalizer.normalize_employment_type(raw_data.get("employment_type"), full_text)

        # 7. Quality evaluation: Missing fields & Confidence calculation
        missing_fields: List[str] = []
        confidence_points = 0.0

        if cleaned_title and len(cleaned_title) >= 3:
            confidence_points += 0.15
        else:
            missing_fields.append("Job Title")

        if cleaned_text and len(cleaned_text) >= 80:
            confidence_points += 0.25
        elif cleaned_text:
            confidence_points += 0.15
            missing_fields.append("Comprehensive Description")
        else:
            missing_fields.append("Job Description")

        if req_skills or pref_skills:
            confidence_points += 0.20
        else:
            missing_fields.append("Technical Skills")

        if loc_info.city or loc_info.country or loc_info.is_remote:
            confidence_points += 0.15
        else:
            missing_fields.append("Structured Location")

        if exp_req.min_years is not None or exp_req.is_fresher_eligible:
            confidence_points += 0.10
        else:
            missing_fields.append("Explicit Experience Requirements")

        if edu_req.degree_requirements:
            confidence_points += 0.05
        else:
            missing_fields.append("Explicit Education Requirements")

        if salary_info and (salary_info.min_amount or salary_info.max_amount):
            confidence_points += 0.10
        else:
            missing_fields.append("Published Salary")

        extraction_confidence = round(confidence_points, 2)

        # Determine extraction status
        if not cleaned_text or len(cleaned_text) < 30:
            status = ExtractionStatus.FAILED.value
        elif len(cleaned_text) < 100 or extraction_confidence < 0.40:
            status = ExtractionStatus.NEEDS_REVIEW.value
        elif len(missing_fields) <= 3 and "Job Title" not in missing_fields and "Job Description" not in missing_fields:
            status = ExtractionStatus.COMPLETE.value
        else:
            status = ExtractionStatus.PARTIAL.value

        return {
            "external_job_id": ext_id or None,
            "canonical_job_title": canonical_title,
            "title": cleaned_title or raw_title,
            "company": company_name or "Unknown Company",
            "location": loc_info.raw_location or "Unspecified",
            "description": full_text or raw_description_html,
            "responsibilities": responsibilities,
            "qualifications": qualifications,
            "required_skills": req_skills,
            "preferred_skills": pref_skills,
            "employment_type": emp_type.value,
            "experience_min_years": exp_req.min_years,
            "experience_max_years": exp_req.max_years,
            "seniority_level": seniority.value,
            "workplace_type": loc_info.workplace_type.value,
            "seniority": seniority.value,
            "location_raw": loc_info.raw_location,
            "city": loc_info.city,
            "state": loc_info.state,
            "country": loc_info.country,
            "is_remote": loc_info.is_remote,
            "eligible_locations": loc_info.eligible_locations,
            "degree_requirements": edu_req.degree_requirements,
            "field_of_study": edu_req.fields_of_study,
            "salary_min": salary_info.min_amount if salary_info else None,
            "salary_max": salary_info.max_amount if salary_info else None,
            "salary_currency": salary_info.currency if salary_info else None,
            "salary_period": salary_info.period if salary_info else None,
            "application_url": app_url,
            "source_url": src_url,
            "provider": self.provider_name,
            "source_job_id": ext_id or None,
            "extraction_status": status,
            "extraction_confidence": extraction_confidence,
            "missing_fields": missing_fields,
        }

